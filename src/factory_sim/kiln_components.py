"""Reduced kiln-line process models and component-level faults."""

from factory_sim.bulk_components import BulkComponents
from factory_sim.equipment import Material
from factory_sim.milling_components import RawMillFan


class KilnStage(BulkComponents):
    def configure(self, parameters, fraction, trip=None):
        self.trip = trip
        return {**parameters, "capacity_tph": parameters["capacity_tph"] * (0 if trip else fraction)}

    def transform(self, material, parameters):
        return material

    def report(self, values, components):
        if self.trip:
            state = "TRIPPED"
        else:
            state = "RUNNING" if values["inlet_tph"] else "IDLE"
        self.annotate(values, state, components, self.trip)


class CyclonePreheater(KilnStage):
    FAULTS = {"cyclone": {"blockage"}}

    def apply(self, parameters, time_s, exhaust_m3_s, kiln_heat_fraction=1.0):
        draft_fraction = min(1, exhaust_m3_s / parameters["reference_exhaust_m3_s"])
        self.draft_fraction = draft_fraction
        self.heat_fraction = kiln_heat_fraction
        blockage = self.severity("cyclone", "blockage")
        self.differential_pressure = parameters["cyclone_dp_pa"] * draft_fraction ** 2 * (1 + 3 * blockage)
        self.low_draft = draft_fraction < parameters["minimum_draft_fraction"]
        self.limited_draft = draft_fraction < 0.7
        fraction = min(1 - blockage, draft_fraction)
        return self.configure(parameters, 0 if self.low_draft else fraction)

    def transform(self, material, parameters):
        return Material(material.dry, 0)

    def telemetry(self, values, measures, time_s, seed):
        if self.low_draft:
            values["process_notice"] = "kiln_low_draft"
        elif self.limited_draft:
            values["process_notice"] = "kiln_limited_draft"
        self.report(values, {
            "cyclone": {"differential_pressure_pa": self.differential_pressure},
            "preheater_outlet": {"temperature_c": 25 + (self.parameters["outlet_temperature_c"] - 25) * self.heat_fraction
                                 if values["outlet_tph"] else None},
            "preheater_exhaust_heat": {"heat_fraction": min(self.heat_fraction, self.draft_fraction)},
        })


class Precalciner(KilnStage):
    FAULTS = {"calciner_burner": {"fuel_loss"}}

    def apply(self, parameters, time_s):
        loss = self.severity("calciner_burner", "fuel_loss")
        trip = "calciner_fuel_unavailable" if loss == 1 else None
        return self.configure(parameters, 1 - loss, trip)

    def transform(self, material, parameters):
        return Material(material.dry * (1 - parameters["co2_release_fraction"]), material.water)

    def telemetry(self, values, measures, time_s, seed):
        self.report(values, {
            "calciner_burner": {"fuel_flow_tph": self.parameters["fuel_per_feed"] * values["inlet_tph"]},
            "calciner_outlet": {"temperature_c": self.parameters["outlet_temperature_c"]
                                if values["outlet_tph"] else None},
        })


class RotaryKiln(KilnStage):
    FAULTS = {"kiln_drive": {"trip"}, "main_burner": {"fuel_loss"}}

    def apply(self, parameters, time_s):
        fuel_loss = self.severity("main_burner", "fuel_loss")
        if self.severity("kiln_drive", "trip"):
            reason = "kiln_drive_trip"
        else:
            reason = "kiln_fuel_unavailable" if fuel_loss == 1 else None
        return self.configure(parameters, 1 - fuel_loss, reason)

    def transform(self, material, parameters):
        return Material(material.dry * (1 - parameters["co2_release_fraction"]), material.water)

    def telemetry(self, values, measures, time_s, seed):
        fuel = self.parameters["fuel_per_feed"] * values["inlet_tph"]
        fuel_credit = values.get("recovered_heat_kw", 0) / self.parameters["fuel_energy_kwh_t"]
        self.report(values, {
            "kiln_drive": {"speed_rpm": self.parameters["rotation_rpm"] if values["inlet_tph"] else 0},
            "main_burner": {"fuel_flow_tph": max(0, fuel - fuel_credit)},
            "burning_zone": {"temperature_c": self.parameters["outlet_temperature_c"]
                             if values["outlet_tph"] else None},
        })


class ClinkerCooler(KilnStage):
    FAULTS = {"cooler_fan": {"airflow_loss"}, "grate_drive": {"jam"}}

    def apply(self, parameters, time_s):
        self.air_fraction = 1 - self.severity("cooler_fan", "airflow_loss")
        reason = "cooler_grate_jam" if self.severity("grate_drive", "jam") else None
        if self.air_fraction == 0 and not reason:
            reason = "cooler_air_unavailable"
        return self.configure(parameters, self.air_fraction, reason)

    def telemetry(self, values, measures, time_s, seed):
        self.report(values, {
            "cooler_fan": {"airflow_m3_s": self.parameters["airflow_m3_s"] * self.air_fraction},
            "grate_drive": {"speed_m_s": self.parameters["grate_speed_m_s"] if values["inlet_tph"] else 0},
            "cooler_outlet": {"temperature_c": self.outlet_temperature() if values["outlet_tph"] else None},
            "cooler_heat_recovery": {"thermal_power_kw": values.get("recovered_heat_kw", 0)},
        })

    def outlet_temperature(self):
        return self.parameters["clinker_temperature_c"] + 180 * (1 - self.air_fraction)

    def recovered_heat_kw(self, clinker_tph, hot_temperature_c):
        delta = max(0, hot_temperature_c - self.outlet_temperature())
        return (clinker_tph / 3.6 * self.parameters["clinker_specific_heat_kj_kg_k"] * delta
                * self.parameters["heat_recovery_fraction"] * self.air_fraction)


class KilnDraftFan(RawMillFan):
    FAULTS = {**RawMillFan.FAULTS, "fan_drive": {"trip"}}

    def apply(self, parameters, time_s):
        actual = super().apply(parameters, time_s)
        if self.severity("fan_drive", "trip"):
            self.running = False
            actual["airflow_m3_s"] = 0
        return actual

    def telemetry(self, values, measures, time_s, seed):
        super().telemetry(values, measures, time_s, seed)
        ratio = values["airflow_m3_s"] / self.parameters["reference_airflow_m3_s"]
        values["components"]["draft_sensor"] = {"draft_suction_pa": self.parameters["reference_suction_pa"] * ratio ** 2}
        if self.severity("fan_drive", "trip"):
            values.update(operating_state="TRIPPED", trip_reason="kiln_id_fan_drive_trip")


KILN_COMPONENT_MODELS = {
    "cyclone_preheater": CyclonePreheater, "precalciner": Precalciner, "rotary_kiln": RotaryKiln,
    "clinker_cooler": ClinkerCooler, "kiln_draft_fan": KilnDraftFan,
}
