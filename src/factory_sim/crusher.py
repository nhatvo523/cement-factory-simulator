"""Component behavior for a simplified rotor crusher."""

from factory_sim.core.variation import wave


FAULTS = {
    "rotor": {"jam", "tool_wear"},
    "main_motor": {"cooling_loss"},
    "drive_end_bearing": {"high_friction"},
    "lubrication": {"pressure_loss"},
    "vibration_sensor": {"signal_loss"},
}


class RotorCrusher:
    def __init__(self, parameters):
        self.faults = {}
        self.trip = None
        self.motor_temperature = parameters["motor_temperature_c"]
        self.bearing_temperature = parameters["bearing_temperature_c"]
        self.other_bearing_temperature = self.bearing_temperature - 3

    def inject(self, component, fault, severity, time_s):
        self.faults[component, fault] = {"component": component, "fault": fault,
                                        "severity": severity, "at_s": time_s}

    def severity(self, component, fault):
        return self.faults.get((component, fault), {}).get("severity", 0)

    def capacity(self, parameters, time_s):
        jam = self.severity("rotor", "jam")
        oil_loss = self.severity("lubrication", "pressure_loss")
        jam_event = self.faults.get(("rotor", "jam"))
        oil_event = self.faults.get(("lubrication", "pressure_loss"))
        if self.trip is None:
            if jam and (jam == 1 or time_s - jam_event["at_s"] >= 60):
                self.trip = "motor_overcurrent"
            elif oil_loss and time_s - oil_event["at_s"] >= 60:
                self.trip = "low_oil_pressure"
            elif self.motor_temperature >= parameters["motor_trip_c"]:
                self.trip = "motor_overtemperature"
            elif self.bearing_temperature >= parameters["bearing_trip_c"]:
                self.trip = "bearing_overtemperature"
        wear = self.severity("rotor", "tool_wear")
        return 0 if self.trip else parameters["capacity_tph"] * min(1 - jam, 1 - 0.25 * wear)

    def telemetry(self, values, parameters, seed, time_s, step_s):
        running = not self.trip and parameters["capacity_tph"] > 0
        load = min(1, values["inlet_tph"] / parameters["capacity_tph"]) if running else 0
        jam = self.severity("rotor", "jam")
        wear = self.severity("rotor", "tool_wear")
        cooling = self.severity("main_motor", "cooling_loss")
        friction = self.severity("drive_end_bearing", "high_friction")
        oil_loss = self.severity("lubrication", "pressure_loss")
        signal_lost = bool(self.severity("vibration_sensor", "signal_loss"))
        motor_target = parameters["motor_temperature_c"] + 55 * cooling if running else 25
        bearing_target = parameters["bearing_temperature_c"] + 45 * friction + 25 * oil_loss if running else 25
        other_bearing_target = parameters["bearing_temperature_c"] - 3 + 25 * oil_loss if running else 25
        heat_response = step_s / (300 + step_s)
        self.motor_temperature += (motor_target - self.motor_temperature) * heat_response
        self.bearing_temperature += (bearing_target - self.bearing_temperature) * heat_response
        self.other_bearing_temperature += (other_bearing_target - self.other_bearing_temperature) * heat_response
        variation = 1 + 0.02 * wave(seed, "crusher", time_s, 390)
        current = parameters["motor_current_a"] * (0.25 + 0.75 * load + jam) * variation if running else 0
        vibration = (2.8 + 4 * friction + 3 * jam) * variation if running else 0
        values.update({
            "operating_state": "TRIPPED" if self.trip else ("RUNNING" if running else "STOPPED"),
            "health_state": "DEGRADED" if self.faults else "HEALTHY",
            "trip_reason": self.trip,
            "active_faults": list(self.faults.values()),
            "components": {
                "main_motor": {"current_a": current, "winding_temperature_c": self.motor_temperature},
                "rotor": {"speed_rpm": parameters["rotor_speed_rpm"] * (1 - 0.8 * jam) if running else 0,
                          "tool_wear_fraction": min(1, 0.1 + wear)},
                "drive_end_bearing": {"temperature_c": self.bearing_temperature},
                "non_drive_end_bearing": {"temperature_c": self.other_bearing_temperature},
                "lubrication": {"pressure_bar": parameters["oil_pressure_bar"] * (1 - oil_loss) if running else 0},
                "vibration_sensor": {"vibration_mm_s": None if signal_lost else vibration,
                                     "signal_quality": "BAD" if signal_lost else "GOOD"},
            },
        })
