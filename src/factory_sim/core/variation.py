"""Reproducible, smooth operating variation and independent sensor signals."""

from hashlib import sha256
from math import sin, tau


def wave(seed, channel, time_s, period_s):
    phases = sha256(f"{seed}:{channel}".encode()).digest()
    slow = tau * (time_s / period_s + phases[0] / 256)
    fast = tau * (time_s / (period_s * 0.43) + phases[1] / 256)
    return 0.75 * sin(slow) + 0.25 * sin(fast)


def operating_values(nominal, variations, seed, time_s, bounds=None):
    actual = nominal.copy()
    for name, settings in variations.items():
        value = nominal[name] * (1 + settings["relative_amplitude"] *
                                 wave(seed, name, time_s, settings["period_s"]))
        rule = (bounds or {}).get(name, {})
        actual[name] = max(rule.get("min", 0), min(rule.get("max", float("inf")), value))
    return actual


def sampled_values(values, signals, seed, time_s):
    measurements = {}
    for name, settings in signals.items():
        value = values[name]
        if value is None:
            measurements[name] = None
            continue
        relative = settings["relative_amplitude"] * wave(seed, name, time_s, settings["period_s"])
        upper = 1.0 if name.endswith("_fraction") else float("inf")
        measurements[name] = max(0.0, min(upper, value * (1 + relative)))
    return measurements


# Component readouts derived from the corresponding simulated instrument.
# Maintenance state and model parameters are excluded from this list.
COMPONENT_ANALOG_SIGNALS = {
    "current_a": {"relative_amplitude": 0.006, "period_s": 155},
    "winding_temperature_c": {"relative_amplitude": 0.002, "period_s": 210},
    "temperature_c": {"relative_amplitude": 0.002, "period_s": 190},
    "speed_rpm": {"relative_amplitude": 0.003, "period_s": 175},
    "speed_m_s": {"relative_amplitude": 0.004, "period_s": 165},
    "position_m": {"relative_amplitude": 0.001, "period_s": 181},
    "travel_speed_m_min": {"relative_amplitude": 0.004, "period_s": 207},
    "speed_fraction": {"relative_amplitude": 0.004, "period_s": 165},
    "pressure_bar": {"relative_amplitude": 0.006, "period_s": 180},
    "vibration_mm_s": {"relative_amplitude": 0.01, "period_s": 135},
}
COMPONENT_READOUTS = {
    "condition", "signal_quality", "measured_level_fraction", "measured_flow_tph", "direction", "end_limit",
}


def sampled_components(components, seed, time_s):
    result = {}
    for component, values in components.items():
        analog = {name: rule for name, rule in COMPONENT_ANALOG_SIGNALS.items() if name in values}
        readings = sampled_values(values, analog, f"{seed}:{component}", time_s)
        readings.update({name: value for name, value in values.items() if name in COMPONENT_READOUTS})
        if readings:
            result[component] = readings
    return result
