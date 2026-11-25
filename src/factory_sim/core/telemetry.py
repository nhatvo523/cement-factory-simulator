"""Project solver frames onto the configured public SCADA tags."""

from collections import deque
from math import expm1, prod
from pathlib import Path

from factory_sim.core.config import read_json
from factory_sim.core.signal_conditioning import alarm_value, conditioned_value


def load_tag_config(model_directory, assets, plant=None, conditioning_enabled=None):
    path = Path(model_directory).parent / "operating_profiles/equipment_tags.json"
    if not path.is_file():
        return {"tags": [], "ground_truth_default": False}
    config = read_json(path)
    if conditioning_enabled is not None:
        config.setdefault("signal_conditioning", {})["enabled"] = conditioning_enabled
    tags = []
    for tag in config["tags"]:
        if tag.get("channel") == "alarm" or tag.get("requires_conditioning"):
            if not config.get("signal_conditioning", {}).get("enabled"):
                continue
        if tag.get("requires") and not (plant or {}).get(tag["requires"], {}).get("enabled"):
            continue
        source = tag["source"]
        dependencies = {source["asset"]}
        if permissive := tag.get("rule", {}).get("permissive"):
            dependencies.add(permissive["asset"])
        model = source.get("passive_model", {})
        for term in model.get("terms", []):
            dependencies.update(factor["asset"] for factor in term["factors"])
        if dependencies <= assets.keys():
            tags.append(tag)
    if len({tag["tag_id"] for tag in tags}) != len(tags):
        raise ValueError("Duplicate SCADA tag")
    measurements = {(tag["device_id"], tag["tag_id"]) for tag in tags if not tag.get("channel")}
    for tag in tags:
        if tag.get("channel") == "alarm" and (tag["device_id"], tag["rule"]["input_tag"]) not in measurements:
            raise ValueError(f"Alarm references missing SCADA measurement: {tag['tag_id']}")
        if (quality := tag.get("quality_tag")) and (tag["device_id"], quality) not in measurements:
            raise ValueError(f"Measurement references missing SCADA quality tag: {tag['tag_id']}")
    return {**config, "tags": tags}


def read_source(frame, source):
    value = frame.get(source.get("section", "equipment"), {}).get(source["asset"])
    for field in source["field"].split("."):
        value = value.get(field) if isinstance(value, dict) else None
    if fault := source.get("fault"):
        value = next((event["severity"] for event in value or []
                      if (event["component"], event["fault"]) == (fault["component"], fault["fault"])), 0)
    if "state_factors" in source:
        return source["state_factors"].get(value, source["default"])
    return source.get("default") if value is None else value


def passive_target(frame, source, value):
    """Weighted state proxies for display only. The solver never reads these."""
    model = source["passive_model"]
    if model.get("requires_positive_source") and (value is None or value <= 0):
        return model["inactive"]
    target = model["base"] if "base" in model else value
    if target is None:
        return None
    for term in model.get("terms", []):
        factors = []
        for factor in term["factors"]:
            observed = read_source(frame, factor)
            if observed is None:
                return None
            ratio = max(0, observed / factor.get("reference", 1))
            ratio = min(ratio, factor.get("max_ratio", float("inf")))
            factors.append(ratio ** factor.get("power", 1) + factor.get("offset", 0))
        target += term["gain"] * prod(factors)
    return target


def public_frames(frames, tags, plant, assets, ground_truth=False, signal_conditioning=None):
    previous_time = 0
    bag_remainder = 0.0
    bag_count = 0
    bag_history = deque([(0, 0)])
    thermal_state = {}
    instrument_state, alarm_state, run_since = {}, {}, {}
    settings = signal_conditioning or {}
    enabled = settings.get("enabled", False)
    alarm_tags = [tag for tag in tags if tag.get("channel") == "alarm"]
    tags = [tag for tag in tags if tag.get("channel") != "alarm"]
    quality_tags = {tag["tag_id"]: tag["quality_tag"] for tag in tags if "quality_tag" in tag}
    bag_tags = [tag for tag in tags if tag["source"].get("transform") == "bags_count"]
    bag_source = bag_tags[0]["source"] if bag_tags else None
    compartments = {entry["grade"]: entry for entry in
                    plant.get("cement_dispatch", {}).get("compartments", {}).values()}
    for frame in frames:
        time_s = frame["time_s"]
        step_s = time_s - previous_time
        if bag_source:
            bag_asset = bag_source["asset"]
            bag_mass = assets[bag_asset]["parameters"]["bag_mass_kg"]
            flow = frame["equipment"][bag_asset][bag_source["field"]]
            bag_remainder += flow * step_s * 1000 / (3600 * bag_mass)
            completed = int(bag_remainder)
            bag_remainder -= completed
            bag_count += completed
            bag_history.append((time_s, bag_count))
            while len(bag_history) > 1 and bag_history[1][0] <= time_s - 60:
                bag_history.popleft()
        previous_time = time_s
        readings = {}
        lab = {}
        for tag in tags:
            source = tag["source"]
            value = read_source(frame, source)
            if tag.get("channel") == "lab":
                if value:
                    lab.setdefault(tag["device_id"], {})[tag["tag_id"]] = value
                continue
            field = source["field"].rsplit(".", 1)[-1]
            transform = source.get("transform")
            if transform == "bags_count":
                value = bag_count
            elif transform == "bags_per_min":
                value = bag_count - bag_history[0][1]
            elif value is not None:
                if transform == "run":
                    value = value == "RUNNING"
                elif transform == "trip":
                    value = value == "TRIPPED"
                elif transform == "negate":
                    value = -value if value else 0.0
                elif transform == "percent":
                    value *= 100
                elif transform == "cell_level":
                    value = min(100.0, 100 * value / compartments[field]["capacity_t"])
                if "contact" in source:
                    contact = source["contact"]
                    value = value >= contact["high"] if "high" in contact else value <= contact["low"]
            coupled = source.get("coupled")
            coupled_value = read_source(frame, coupled) if coupled else None
            if coupled_value is not None:
                value = coupled_value * coupled["scale"] + coupled["offset"]
            elif "passive_model" in source:
                value = passive_target(frame, source, value)
            if value is not None and coupled_value is None and "time_constant_s" in tag:
                tag_id = tag["tag_id"]
                previous = thermal_state.get(tag_id, value)
                weight = -expm1(-step_s / tag["time_constant_s"])
                value = previous + weight * (value - previous)
                thermal_state[tag_id] = value
            if enabled and "conditioning" in tag:
                value = conditioned_value(value, tag, instrument_state.setdefault(tag["tag_id"], {}),
                                          time_s, step_s, settings["seed"], settings["noise_enabled"])
            readings.setdefault(tag["device_id"], {})[tag["tag_id"]] = value
        public = {"time_s": time_s, "measurements": readings}
        if enabled:
            modes = {}
            for tag in alarm_tags:
                asset = tag["source"]["asset"]
                if asset in modes:
                    continue
                running = frame["equipment"][asset].get("operating_state") == "RUNNING"
                previous = run_since.get(asset)
                if not running:
                    run_since[asset] = None
                    modes[asset] = "STOPPED"
                else:
                    if asset not in run_since:
                        run_since[asset] = time_s - settings["startup_hold_s"]
                    elif previous is None:
                        run_since[asset] = time_s - step_s
                    modes[asset] = ("STARTING" if time_s - run_since[asset] < settings["startup_hold_s"]
                                    else "RUNNING")
            alarms = {}
            for tag in alarm_tags:
                device, alarm_id = tag["device_id"], tag["tag_id"]
                rule = tag["rule"]
                device_readings = readings[device]
                input_tag = rule["input_tag"]
                value = device_readings.get(input_tag)
                if (quality := quality_tags.get(input_tag)) and device_readings.get(quality) == "BAD":
                    value = None
                if (permissive := rule.get("permissive")) and (read_source(frame, permissive) or 0) <= 0:
                    value = None
                alarms.setdefault(device, {})[alarm_id] = alarm_value(
                    value, rule, alarm_state.setdefault(alarm_id, {}), modes[tag["source"]["asset"]], time_s, step_s)
            if alarms:
                public["alarms"] = alarms
        if lab:
            public["lab"] = lab
        if ground_truth:
            public["ground_truth"] = {key: frame[key] for key in ("equipment", "balance", "events")}
        yield public
