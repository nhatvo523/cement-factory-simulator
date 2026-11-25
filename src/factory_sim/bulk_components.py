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
    """Bridge scraper with a chain drive and two reversing travel axes."""

    FAULTS = {"scraper_chain": {"jam"}, "bridge_travel": {"stall"}, "harrow_encoder": {"signal_loss"}}

    def __init__(self, parameters):
        super().__init__(parameters)
        self.bridge = TravelAxis(parameters["bridge_travel_m"], parameters["bridge_speed_m_min"])
        self.harrow = TravelAxis(parameters["harrow_travel_m"], parameters["harrow_speed_m_min"])
        self.totalized_t = 0.0
        self.trip = None

    def trip_reason(self, time_s):
        if self.trip is None:
            if self.elapsed("scraper_chain", "jam", time_s) >= self.parameters["trip_delay_s"]:
                self.trip = "reclaimer_overload"
            elif self.elapsed("bridge_travel", "stall", time_s) >= self.parameters["travel_trip_delay_s"]:
                self.trip = "reclaimer_travel_stall"
        return self.trip

    def capacity(self, parameters, time_s):
        if self.trip_reason(time_s) or self.severity("bridge_travel", "stall"):
            return 0
        return parameters["capacity_tph"] * (1 - self.severity("scraper_chain", "jam"))

    def telemetry(self, values, measures, time_s, seed, *, step_s, stock_available, discharge_ready):
        trip = self.trip_reason(time_s)
        jam = self.severity("scraper_chain", "jam")
        stalled = self.severity("bridge_travel", "stall")
        running = not trip and stock_available and discharge_ready and (values["outlet_tph"] > 0 or jam or stalled)
        load = min(1, values["outlet_tph"] / self.parameters["capacity_tph"])
        current = self.parameters["motor_current_a"] * (0.3 + 0.7 * load + jam)
        current *= 1 + 0.02 * wave(seed, "reclaimer_current", time_s, 390)
        state = "TRIPPED" if trip else ("RUNNING" if running else "IDLE")
        if not running and not trip:
            if not discharge_ready:
                values["waiting_reason"] = "reclaimer_discharge_unavailable"
            elif not stock_available:
                values["waiting_reason"] = "reclaimer_stock_empty"
        bridge = self.bridge.readings(step_s, running and not stalled and not jam)
        harrow = self.harrow.readings(step_s, running and not stalled and not jam)
        encoder_lost = self.severity("harrow_encoder", "signal_loss")
        flow = measures.get("outlet_tph")
        if flow is not None:
            self.totalized_t += flow * step_s / 3600
            measures["reclaimed_total_t"] = self.totalized_t
        self.annotate(values, state, {
            "scraper_chain": {
                "speed_m_s": self.parameters["chain_speed_m_s"] * (1 - jam) if running else 0,
                "current_a": current if running else 0,
            },
            "bridge_travel": bridge,
            "harrow_travel": {"end_limit": harrow["end_limit"], "direction": harrow["direction"]},
            "harrow_encoder": {"position_m": None if encoder_lost else harrow["position_m"],
                               "travel_speed_m_min": None if encoder_lost else harrow["travel_speed_m_min"],
                               "signal_quality": "BAD" if encoder_lost else "GOOD"},
            "discharge_interlock": {"condition": "READY" if discharge_ready else "NOT_READY"},
        }, trip)


class TravelAxis:
    def __init__(self, length_m, speed_m_min):
        self.length = length_m
        self.speed = speed_m_min
        self.position = 0.0
        self.forward = True

    def readings(self, step_s, moving):
        speed = self.speed if moving else 0
        distance = speed * step_s / 60
        self.position = max(0, min(self.length, self.position + (distance if self.forward else -distance)))
        direction = ("FORWARD" if self.forward else "REVERSE") if moving else "STATIONARY"
        limit = "AT_START" if self.position == 0 else ("AT_END" if self.position == self.length else "NORMAL")
        if moving and limit != "NORMAL":
            self.forward = limit == "AT_START"
        return {"position_m": self.position, "travel_speed_m_min": speed,
                "direction": direction, "end_limit": limit}


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
