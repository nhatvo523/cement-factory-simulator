"""Component behavior for finish mills, cement storage and loading equipment."""

from factory_sim.bulk_components import BulkComponents


class FinishDrive(BulkComponents):
    COMPONENT = "drive"
    FAULTS = {"drive": {"unavailable"}, "bearing": {"wear"}}

    def apply(self, parameters, time_s):
        self.unavailable = self.severity(self.COMPONENT, "unavailable")
        self.wear = self.severity("bearing", "wear")
        return {**parameters, "capacity_tph": parameters["capacity_tph"] *
                (1 - self.unavailable) * (1 - 0.35 * self.wear)}

    def telemetry(self, values, measures, time_s, seed):
        rated = self.parameters["capacity_tph"]
        load = min(1, values["inlet_tph"] / rated) if rated else 0
        active = load > 0
        trip = self.COMPONENT + "_unavailable" if self.unavailable == 1 else None
        components = {
            self.COMPONENT: {"condition": "UNAVAILABLE" if trip else ("RUNNING" if active else "READY")},
        }
        if "bearing" in self.FAULTS:
            components[self.COMPONENT]["current_a"] = self.parameters["motor_current_a"] * (0.3 + 0.7 * load) if active else 0
            components["bearing"] = {"vibration_mm_s": (2.4 + 5 * self.wear) if active else 0}
        self.annotate(values, "TRIPPED" if trip else values["operating_state"], components, trip)


class BagPacker(FinishDrive):
    COMPONENT = "filling_head"
    FAULTS = {"filling_head": {"unavailable"}}


class BulkSpout(FinishDrive):
    COMPONENT = "loading_spout"
    FAULTS = {"loading_spout": {"unavailable"}}


class BagConveyor(FinishDrive):
    COMPONENT = "belt"
    FAULTS = {"belt": {"unavailable", "slip"}}

    def apply(self, parameters, time_s):
        effective = super().apply(parameters, time_s)
        self.speed_fraction = 1 - self.severity("belt", "slip")
        effective["capacity_tph"] *= self.speed_fraction
        return effective

    def telemetry(self, values, measures, time_s, seed):
        super().telemetry(values, measures, time_s, seed)
        values["components"]["belt"]["speed_m_s"] = (
            self.parameters["belt_speed_m_s"] * self.speed_fraction if values["outlet_tph"] else 0)


class TruckScale(FinishDrive):
    COMPONENT = "load_cell"
    FAULTS = {"load_cell": {"unavailable", "positive_bias"}}

    def telemetry(self, values, measures, time_s, seed):
        super().telemetry(values, measures, time_s, seed)
        bias = self.severity("load_cell", "positive_bias")
        for name in ("truck_net_t", "dispatch_flow_tph"):
            if name in measures:
                measures[name] = None if self.unavailable else measures[name] * (1 + bias)
        values["components"]["load_cell"]["signal_quality"] = "BAD" if self.unavailable else "GOOD"


class SiloBank(BulkComponents):
    FAULTS = {"level_sensor": {"signal_loss"}, "outlet_gate": {"unavailable"}}

    def apply(self, parameters, time_s):
        self.blocked = self.severity("outlet_gate", "unavailable")
        return parameters

    def telemetry(self, values, measures, time_s, seed):
        lost = self.severity("level_sensor", "signal_loss")
        if lost:
            for name in ("inventory_t", "level_fraction", "grades"):
                if name in measures:
                    measures[name] = None
        self.annotate(values, "OUTLET_BLOCKED" if self.blocked == 1 else values["operating_state"], {
            "level_sensor": {"signal_quality": "BAD" if lost else "GOOD"},
            "outlet_gate": {"condition": "BLOCKED" if self.blocked == 1 else "READY"},
        })


FINISHING_COMPONENT_MODELS = {
    "finish_drive": FinishDrive, "bag_packer": BagPacker, "bulk_spout": BulkSpout,
    "bag_conveyor": BagConveyor, "truck_scale": TruckScale, "silo_bank": SiloBank,
}
