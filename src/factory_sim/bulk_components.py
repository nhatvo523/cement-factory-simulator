"""Component faults for bulk handling assets, independent of plant IDs."""

from factory_sim.core.variation import wave


class BulkComponents:
    def __init__(self, parameters):
        self.parameters = parameters
        self.faults = {}

    def inject(self, component, fault, severity, time_s):
        self.faults[component, fault] = {
            "component": component, "fault": fault, "severity": severity, "at_s": time_s,
        }

    def severity(self, component, fault):
        return self.faults.get((component, fault), {}).get("severity", 0)

    def elapsed(self, component, fault, time_s):
        event = self.faults.get((component, fault))
        return time_s - event["at_s"] if event else 0

    def annotate(self, values, state, components, trip=None):
        values.update(operating_state=state, components=components, trip_reason=trip,
                      active_faults=list(self.faults.values()))

    def accepts_inlet(self, time_s):
        return True


class BeltConveyor(BulkComponents):
    FAULTS = {
        "belt": {"slip", "misalignment"}, "discharge_chute": {"blockage"}, "belt_scale": {"signal_loss"},
    }

    def tripped(self, time_s):
        return self.elapsed("belt", "misalignment", time_s) >= self.parameters["trip_delay_s"]

    def accepts_inlet(self, time_s):
        return not self.tripped(time_s)

    def outlet_limit(self, time_s):
        return (int(self.accepts_inlet(time_s)) * self.parameters["rated_flow_tph"]
                * min(1 - self.severity("belt", "slip"), 1 - self.severity("discharge_chute", "blockage")))

    def telemetry(self, values, measures, time_s, seed):
        tripped = self.tripped(time_s)
        blocked = self.severity("discharge_chute", "blockage")
        misaligned = self.severity("belt", "misalignment")
        lost = self.severity("belt_scale", "signal_loss")
        speed = self.parameters["belt_speed_m_s"] * (1 - self.severity("belt", "slip"))
        flow_reading = None if lost else measures.get("outlet_tph", values["outlet_tph"])
        if "outlet_tph" in measures:
            measures["outlet_tph"] = flow_reading
        state = "TRIPPED" if tripped else ("BLOCKED" if blocked == 1 else "RUNNING")
        self.annotate(values, state, {
            "belt": {"speed_m_s": 0 if tripped else speed},
            "discharge_chute": {"condition": "BLOCKED" if blocked else "CLEAR"},
            "misalignment_switch": {"condition": "ACTIVE" if misaligned else "NORMAL"},
            "belt_scale": {"measured_flow_tph": flow_reading,
                           "signal_quality": "BAD" if lost else "GOOD"},
        }, "belt_misalignment" if tripped else None)


class Stockpile(BulkComponents):
    FAULTS = {"level_sensor": {"false_high"}, "stacker_drive": {"drive_failure"}}

    def accepts_inlet(self, time_s):
        high = self.parameters["high_level_interlock"] and self.severity("level_sensor", "false_high")
        return not (high or self.severity("stacker_drive", "drive_failure"))

    def outlet_limit(self, time_s):
        return float("inf")

    def telemetry(self, values, measures, time_s, seed):
        false_high = self.severity("level_sensor", "false_high")
        speed = 0 if self.severity("stacker_drive", "drive_failure") else 1
        level = values["level_fraction"]
        level_reading = 1 if false_high else measures.get("level_fraction", level)
        if "level_fraction" in measures:
            measures["level_fraction"] = level_reading
        state = "INLET_BLOCKED" if not self.accepts_inlet(time_s) else (
            "FULL" if level >= 1 - 1e-9 else ("EMPTY" if level <= 1e-9 else "AVAILABLE"))
        self.annotate(values, state, {
            "level_sensor": {"measured_level_fraction": level_reading},
            "stacker_drive": {"speed_fraction": speed},
        })


class Reclaimer(BulkComponents):
    FAULTS = {"reclaim_mechanism": {"jam"}}

    def tripped(self, time_s):
        return self.elapsed("reclaim_mechanism", "jam", time_s) >= self.parameters["trip_delay_s"]

    def capacity(self, parameters, time_s):
        return 0 if self.tripped(time_s) else parameters["capacity_tph"] * (1 - self.severity("reclaim_mechanism", "jam"))

    def telemetry(self, values, measures, time_s, seed):
        tripped = self.tripped(time_s)
        jam = self.severity("reclaim_mechanism", "jam")
        load = min(1, values["outlet_tph"] / self.parameters["capacity_tph"])
        current = self.parameters["motor_current_a"] * (0.3 + 0.7 * load + jam)
        current *= 1 + 0.02 * wave(seed, "reclaimer_current", time_s, 390)
        running = not tripped and (values["outlet_tph"] > 0 or jam)
        state = "TRIPPED" if tripped else ("RUNNING" if running else "IDLE")
        self.annotate(values, state, {
            "reclaim_mechanism": {"speed_rpm": self.parameters["reclaim_speed_rpm"] * (1 - jam) if running else 0},
            "main_motor": {"current_a": current if running else 0},
        }, "reclaimer_overload" if tripped else None)


class FeedBin(BulkComponents):
    FAULTS = {"outlet_chute": {"bridging"}, "level_sensor": {"signal_loss"}}

    def outlet_limit(self, time_s):
        return self.parameters["outlet_capacity_tph"] * (1 - self.severity("outlet_chute", "bridging"))

    def telemetry(self, values, measures, time_s, seed):
        bridging = self.severity("outlet_chute", "bridging")
        lost = self.severity("level_sensor", "signal_loss")
        level = values["level_fraction"]
        level_reading = None if lost else measures.get("level_fraction", level)
        if "level_fraction" in measures:
            measures["level_fraction"] = level_reading
        state = "OUTLET_BLOCKED" if bridging == 1 else (
            "FULL" if level >= 1 - 1e-9 else ("EMPTY" if level <= 1e-9 else "AVAILABLE"))
        self.annotate(values, state, {
            "outlet_chute": {"condition": "BRIDGING" if bridging else "CLEAR"},
            "level_sensor": {"measured_level_fraction": level_reading,
                             "signal_quality": "BAD" if lost else "GOOD"},
        })


BULK_COMPONENT_MODELS = {
    "belt_conveyor": BeltConveyor, "stockpile": Stockpile, "reclaimer": Reclaimer, "feed_bin": FeedBin,
}
