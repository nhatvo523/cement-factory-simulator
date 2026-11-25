"""Reusable component behavior for dosing, grinding, separation and gas handling."""

from math import exp

from factory_sim.bulk_components import BulkComponents


class WeighFeeder(BulkComponents):
    FAULTS = {"feeder_drive": {"jam"}, "load_cell": {"positive_bias", "signal_loss"}}

    def apply(self, parameters, time_s):
        jam = self.severity("feeder_drive", "jam")
        bias = self.severity("load_cell", "positive_bias")
        lost = self.severity("load_cell", "signal_loss")
        self.limit_fraction = 0 if lost else (1 - jam) / (1 + bias)
        self.trip = "feeder_drive_jam" if jam == 1 else ("feeder_scale_unavailable" if lost else None)
        return {**parameters, "capacity_tph": parameters["capacity_tph"] * self.limit_fraction}

    def telemetry(self, values, measures, time_s, seed):
        lost = self.severity("load_cell", "signal_loss")
        bias = self.severity("load_cell", "positive_bias")
        if "outlet_tph" in measures:
            measures["outlet_tph"] = None if lost else measures["outlet_tph"] * (1 + bias)
        speed = self.parameters["belt_speed_m_s"] * self.limit_fraction if values["outlet_tph"] else 0
        self.annotate(values, "TRIPPED" if self.trip else values["operating_state"], {
            "feeder_drive": {"speed_m_s": speed},
            "load_cell": {"signal_quality": "BAD" if lost else "GOOD"},
        }, self.trip)


class GrindingMill(BulkComponents):
    FAULTS = {
        "grinding_roller": {"wear", "imbalance"}, "hydraulic_unit": {"pressure_loss"},
        "mill_vibration_sensor": {"signal_loss"},
    }

    def apply(self, parameters, time_s):
        wear = self.severity("grinding_roller", "wear")
        imbalance = self.severity("grinding_roller", "imbalance")
        pressure_loss = self.severity("hydraulic_unit", "pressure_loss")
        self.trip = None
        if pressure_loss == 1:
            self.trip = "mill_low_hydraulic_pressure"
        elif self.elapsed("grinding_roller", "imbalance", time_s) >= parameters["vibration_trip_delay_s"]:
            self.trip = "mill_high_vibration"
        limit = 0 if self.trip else min(1 - 0.25 * wear, 1 - 0.4 * imbalance, 1 - pressure_loss)
        return {**parameters, "capacity_tph": parameters["capacity_tph"] * limit}

    def telemetry(self, values, measures, time_s, seed):
        running = values["operating_state"] == "RUNNING"
        imbalance = self.severity("grinding_roller", "imbalance")
        pressure_loss = self.severity("hydraulic_unit", "pressure_loss")
        sensor_lost = self.severity("mill_vibration_sensor", "signal_loss")
        load = min(1, values["inlet_tph"] / self.parameters["capacity_tph"])
        self.annotate(values, "TRIPPED" if self.trip else values["operating_state"], {
            "main_motor": {"current_a": self.parameters["motor_current_a"] * (0.3 + 0.7 * load) if running else 0},
            "hydraulic_unit": {"pressure_bar": self.parameters["grinding_pressure_bar"] * (1 - pressure_loss)},
            "mill_vibration_sensor": {
                "vibration_mm_s": None if sensor_lost else ((2.5 + 6 * imbalance) if running else 0),
                "signal_quality": "BAD" if sensor_lost else "GOOD",
            },
        }, self.trip)


class AirSeparator(BulkComponents):
    FAULTS = {"separator_drive": {"underspeed", "trip"}}

    def apply(self, parameters, time_s):
        self.drive_trip = bool(self.severity("separator_drive", "trip"))
        self.speed_fraction = 0 if self.drive_trip else 1 - self.severity("separator_drive", "underspeed")
        # For this calibrated scenario, low speed coarsens the cut and sends less material to recycle.
        fines = parameters["fines_fraction"] + (1 - parameters["fines_fraction"]) * 0.35 * (1 - self.speed_fraction)
        return {**parameters, "fines_fraction": fines,
                "capacity_tph": 0 if self.drive_trip else parameters["capacity_tph"]}

    def telemetry(self, values, measures, time_s, seed):
        self.annotate(values, "TRIPPED" if self.drive_trip else "RUNNING", {
            "separator_drive": {"speed_rpm": self.parameters["rotor_speed_rpm"] * self.speed_fraction},
        }, "separator_drive_trip" if self.drive_trip else None)


class RawMillFan(BulkComponents):
    FAULTS = {"fan_drive": {"trip"}, "impeller": {"degradation"}, "damper": {"stuck_low"},
              "fan_bearing": {"overheating"}}

    def __init__(self, parameters):
        super().__init__(parameters)
        self.temperature = parameters["bearing_temperature_c"]
        self.last_time_s = 0
        self.trip = False

    def apply(self, parameters, time_s):
        heating = self.severity("fan_bearing", "overheating")
        elapsed = time_s - self.last_time_s
        if heating and not self.trip:
            elapsed = min(elapsed, self.elapsed("fan_bearing", "overheating", time_s))
        target = 25 if self.trip else parameters["bearing_temperature_c"] + 60 * heating
        self.temperature += (target - self.temperature) * (1 - exp(-elapsed / 100))
        self.last_time_s = time_s
        if not self.trip:
            if self.severity("fan_drive", "trip"):
                self.trip = "fan_drive_trip"
            elif self.temperature >= parameters["bearing_trip_c"]:
                self.trip = "fan_bearing_overtemperature"
        self.running = not self.trip and parameters["airflow_m3_s"] > 0
        self.damper_fraction = 1 - self.severity("damper", "stuck_low")
        impeller_fraction = 1 - self.severity("impeller", "degradation")
        airflow = 0 if self.trip else parameters["airflow_m3_s"] * min(self.damper_fraction, impeller_fraction)
        return {**parameters, "airflow_m3_s": airflow}

    def telemetry(self, values, measures, time_s, seed):
        state = "TRIPPED" if self.trip else ("RUNNING" if self.running else "STOPPED")
        self.annotate(values, state, {
            "fan_drive": {"speed_rpm": self.parameters["fan_speed_rpm"] if self.running else 0},
            "damper": {"opening_fraction": self.damper_fraction},
            "fan_bearing": {"temperature_c": self.temperature},
        }, self.trip or None)


MILLING_COMPONENT_MODELS = {
    "weigh_feeder": WeighFeeder, "grinding_mill": GrindingMill,
    "air_separator": AirSeparator, "raw_mill_fan": RawMillFan,
}
