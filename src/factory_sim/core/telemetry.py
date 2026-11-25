"""Project solver frames onto the configured public SCADA tags."""

from collections import deque
from math import expm1, prod
from pathlib import Path

from factory_sim.core.config import read_json


def load_tag_config(model_directory, assets, plant=None):
    path = Path(model_directory).parent / "operating_profiles/equipment_tags.json"
    if not path.is_file():
        return {"tags": [], "ground_truth_default": False}
    config = read_json(path)
    tags = []
    for tag in config["tags"]:
        if tag.get("requires") and not (plant or {}).get(tag["requires"], {}).get("enabled"):
            continue
        source = tag["source"]
        dependencies = {source["asset"]}
        model = source.get("passive_model", {})
        for term in model.get("terms", []):
            dependencies.update(factor["asset"] for factor in term["factors"])
        if dependencies <= assets.keys():
            tags.append(tag)
    if len({tag["tag_id"] for tag in tags}) != len(tags):
        raise ValueError("Duplicate SCADA tag")
    return {**config, "tags": tags}


def read_source(frame, source):
    value = frame.get(source.get("section", "equipment"), {}).get(source["asset"])
    for field in source["field"].split("."):
        value = value.get(field) if isinstance(value, dict) else None
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


def public_frames(frames, tags, plant, assets, ground_truth=False):
    previous_time = 0
    bag_remainder = 0.0
    bag_count = 0
    bag_history = deque([(0, 0)])
    thermal_state = {}
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
            readings.setdefault(tag["device_id"], {})[tag["tag_id"]] = value
        public = {"time_s": time_s, "measurements": readings}
        if lab:
            public["lab"] = lab
        if ground_truth:
            public["ground_truth"] = {key: frame[key] for key in ("equipment", "balance", "events")}
        yield public
