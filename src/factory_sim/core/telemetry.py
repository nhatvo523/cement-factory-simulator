"""Project solver frames onto the configured public SCADA tags."""

from collections import deque
from pathlib import Path

from factory_sim.core.config import read_json


def load_tag_config(model_directory, assets):
    path = Path(model_directory).parent / "operating_profiles/equipment_tags.json"
    if not path.is_file():
        return {"tags": [], "ground_truth_default": False}
    config = read_json(path)
    tags = [tag for tag in config["tags"] if tag["source"]["asset"] in assets]
    if len({tag["tag_id"] for tag in tags}) != len(tags):
        raise ValueError("Duplicate SCADA tag")
    return {**config, "tags": tags}


def public_frames(frames, tags, plant, assets, ground_truth=False):
    previous_time = 0
    bag_remainder = 0.0
    bag_count = 0
    bag_history = deque([(0, 0)])
    bag_tags = [tag for tag in tags if tag["source"].get("transform") == "bags_count"]
    bag_source = bag_tags[0]["source"] if bag_tags else None
    compartments = {entry["grade"]: entry for entry in
                    plant.get("cement_dispatch", {}).get("compartments", {}).values()}
    for frame in frames:
        time_s = frame["time_s"]
        if bag_source:
            bag_asset = bag_source["asset"]
            bag_mass = assets[bag_asset]["parameters"]["bag_mass_kg"]
            flow = frame["equipment"][bag_asset][bag_source["field"]]
            bag_remainder += flow * (time_s - previous_time) * 1000 / (3600 * bag_mass)
            completed = int(bag_remainder)
            bag_remainder -= completed
            bag_count += completed
            bag_history.append((time_s, bag_count))
            while len(bag_history) > 1 and bag_history[1][0] <= time_s - 60:
                bag_history.popleft()
        previous_time = time_s
        readings = {}
        for tag in tags:
            source = tag["source"]
            value = frame[source["section"]].get(source["asset"])
            for field in source["field"].split("."):
                value = value.get(field) if isinstance(value, dict) else None
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
            readings.setdefault(tag["device_id"], {})[tag["tag_id"]] = value
        public = {"time_s": time_s, "measurements": readings}
        if ground_truth:
            public["ground_truth"] = {key: frame[key] for key in ("equipment", "balance", "events")}
        yield public
