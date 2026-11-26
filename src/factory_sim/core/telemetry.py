"""Project solver frames onto the configured public SCADA tags."""

from collections import deque
from hashlib import sha256
from math import expm1, fsum, prod, sqrt
from pathlib import Path
from random import Random

from factory_sim.core.config import read_json
from factory_sim.core.signal_conditioning import alarm_value, conditioned_value


def load_tag_config(model_directory, assets, plant=None, conditioning_enabled=None):
    path = Path(model_directory).parent / "operating_profiles/equipment_tags.json"
    if not path.is_file():
        return {"tags": [], "ground_truth_default": False}
    config = read_json(path)
    if conditioning_enabled is not None:
        config.setdefault("signal_conditioning", {})["enabled"] = conditioning_enabled
    definitions = {tag["tag_id"]: tag for tag in config["tags"]}

    def source_assets(tag, seen=()):
        tag_id = tag["tag_id"]
        if tag_id in seen:
            raise ValueError(f"Circular SCADA source reference: {tag_id}")
        source = tag["source"]
        dependencies = {source["asset"]}
        if mass_asset := source.get("bag_mass_asset"):
            dependencies.add(mass_asset)
        if permissive := tag.get("rule", {}).get("permissive"):
            dependencies.add(permissive["asset"])
        for term in source.get("passive_model", {}).get("terms", []):
            dependencies.update(factor["asset"] for factor in term["factors"])
        if temp := source.get("mill_temperature"):
            dependencies.update((temp["gas"]["asset"], temp["wear"]["asset"]))
        if lab := source.get("blaine"):
            dependencies.add(lab["rotor"]["asset"])
        for group, field in (("electric_power", "current_tag"), ("mill_temperature", "power_tag"),
                             ("oil_pressure", "bearing_tag"), ("rule", "input_tag")):
            reference = (tag if group == "rule" else source).get(group, {}).get(field)
            if reference:
                if reference not in definitions:
                    raise ValueError(f"Unknown SCADA source reference: {reference}")
                dependencies.update(source_assets(definitions[reference], (*seen, tag_id)))
        return dependencies

    tags = []
    for tag in config["tags"]:
        if tag.get("channel") == "alarm" or tag.get("requires_conditioning"):
            if not config.get("signal_conditioning", {}).get("enabled"):
                continue
        if tag.get("requires") and not (plant or {}).get(tag["requires"], {}).get("enabled"):
            continue
        source = tag["source"]
        if source_assets(tag) <= assets.keys():
            if "blaine" in source:
                lab = config["blaine_lab"]
                tag = {**tag, "lab_schedule": lab["profiles"][lab["analysis_type"]], "lab_seed": lab["seed"]}
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


def passive_target(frame, source, value, term_state=None, step_s=0):
    """Weighted state proxies for display only. The solver never reads these."""
    model = source["passive_model"]
    if model.get("requires_positive_source") and (value is None or value <= 0):
        return model["inactive"]
    target = model["base"] if "base" in model else value
    if target is None:
        return None
    for index, term in enumerate(model.get("terms", [])):
        factors = []
        for factor in term["factors"]:
            observed = read_source(frame, factor)
            if observed is None:
                return None
            ratio = max(0, observed / factor.get("reference", 1))
            ratio = min(ratio, factor.get("max_ratio", float("inf")))
            factors.append(ratio ** factor.get("power", 1) + factor.get("offset", 0))
        contribution = term["gain"] * prod(factors)
        if term_state is not None and (tau := term.get("fall_time_constant_s")):
            previous = term_state.get(index, contribution)
            if contribution < previous:
                contribution = previous + (contribution - previous) * -expm1(-step_s / tau)
            term_state[index] = contribution
        target += contribution
    return target


def electrical_power(current, model):
    if current is None:
        return None
    load = min(1, max(0, current / model["rated_current_a"]))
    cos_phi = model["cos_phi_idle"] + load * (model["cos_phi_rated"] - model["cos_phi_idle"])
    return sqrt(3) * model["voltage_kv"] * current * cos_phi


def finish_lab_sample(frame, tag, state, time_s):
    schedule = tag["lab_schedule"]
    interval = schedule["sample_interval_s"]
    state.setdefault("next_sample", interval)
    queue = state.setdefault("samples", deque())
    if time_s >= state["next_sample"]:
        state["next_sample"] += ((time_s - state["next_sample"]) // interval + 1) * interval
        source = tag["source"]
        if read_source(frame, source):
            model = source["blaine"]
            speed = read_source(frame, model["rotor"])
            seed = sha256(f"{tag['lab_seed']}:{tag['tag_id']}:{time_s}".encode()).digest()
            noise = Random(seed).gauss(0, model["noise_sigma"])
            reading = tag["normal"] + model["speed_gain"] * (speed / model["reference_rpm"] - 1) + noise
            low, high = tag["range"]
            queue.append((time_s, round(max(low, min(high, reading)), 1)))
    reports = []
    while queue and queue[0][0] + schedule["report_delay_s"] <= time_s:
        taken, value = queue.popleft()
        reports.append({"sampled_at_s": taken, "reported_at_s": time_s, "value": value})
    return reports


def public_frames(frames, tags, plant, assets, ground_truth=False, signal_conditioning=None):
    previous_time = 0
    bag_remainder = 0.0
    bag_count = 0
    bag_history = deque([(0, 0)])
    thermal_state = {}
    passive_term_state = {}
    lab_state = {}
    instrument_state, alarm_state, run_since = {}, {}, {}
    settings = signal_conditioning or {}
    enabled = settings.get("enabled", False)
    alarm_tags = [tag for tag in tags if tag.get("channel") == "alarm"]
    tags = [tag for tag in tags if tag.get("channel") != "alarm"]
    by_id = {tag["tag_id"]: tag for tag in tags}
    quality_tags = {tag["tag_id"]: tag["quality_tag"] for tag in tags if "quality_tag" in tag}
    bag_tags = [tag for tag in tags if tag["source"].get("transform") == "bags_count"]
    bag_source = bag_tags[0]["source"] if bag_tags else None
    bag_transforms = {tag["source"].get("transform"): tag for tag in tags}
    checkweigher = bag_transforms.get("bag_weight")
    delayed_bags = bag_transforms.get("delayed_bag_count")
    loading_counter = bag_transforms.get("loaded_bag_count")
    belt_arrivals = deque()
    belt_count = loading_count = 0
    loading_remainder = 0.0
    bag_weight = bag_average = None
    if checkweigher:
        sample_cfg = checkweigher["sample_model"]
        recent_weights = deque(maxlen=sample_cfg["average_bags"])
        seed = sha256(f"{settings.get('seed', 0)}:{checkweigher['tag_id']}".encode()).digest()
        bag_rng = Random(seed)
    compartments = {entry["grade"]: entry for entry in
                    plant.get("cement_dispatch", {}).get("compartments", {}).values()}
    for frame in frames:
        time_s = frame["time_s"]
        step_s = time_s - previous_time
        if bag_source:
            bag_asset = bag_source["asset"]
            bag_mass = assets[bag_asset]["parameters"]["bag_mass_kg"]
            flow = frame["equipment"][bag_asset][bag_source["field"]]
            rate = flow * 1000 / (3600 * bag_mass)
            opening_remainder = bag_remainder
            bag_remainder += flow * step_s * 1000 / (3600 * bag_mass)
            completed = int(bag_remainder)
            bag_remainder -= completed
            bag_count += completed
            bag_history.append((time_s, bag_count))
            while len(bag_history) > 1 and bag_history[1][0] <= time_s - 60:
                bag_history.popleft()
            if checkweigher and completed:
                low, high = checkweigher["range"]
                resolution = sample_cfg["resolution_kg"]
                for _ in range(completed):
                    noise = bag_rng.gauss(0, sample_cfg["noise_sigma_kg"]) if enabled and settings["noise_enabled"] else 0
                    bag_weight = max(low, min(high, round((bag_mass + noise) / resolution) * resolution))
                    recent_weights.append(bag_weight)
                if len(recent_weights) == recent_weights.maxlen:
                    bag_average = fsum(recent_weights) / len(recent_weights)
            if delayed_bags:
                delay = delayed_bags["conditioning"]["transport_delay_s"] if enabled else 0
                for number in range(1, completed + 1):
                    completed_at = min(time_s, previous_time + (number - opening_remainder) / rate)
                    belt_arrivals.append(completed_at + delay)
                while belt_arrivals and belt_arrivals[0] <= time_s:
                    belt_arrivals.popleft()
                    belt_count += 1
        if loading_counter:
            source = loading_counter["source"]
            mass = assets[source["bag_mass_asset"]]["parameters"]["bag_mass_kg"]
            loading_remainder += (read_source(frame, source) or 0) * step_s * 1000 / (3600 * mass)
            completed = int(loading_remainder)
            loading_count += completed
            loading_remainder -= completed
        previous_time = time_s
        readings = {}
        lab = {}
        estimates = {}

        def model_value(tag_id):
            if tag_id not in estimates:
                src = by_id[tag_id]["source"]
                actual = read_source(frame, src)
                if "passive_model" in src:
                    actual = passive_target(frame, src, actual, passive_term_state.setdefault(tag_id, {}), step_s)
                if power := src.get("electric_power"):
                    current = actual if power.get("use_source_current") else model_value(power["current_tag"])
                    actual = electrical_power(current, power)
                if temp := src.get("mill_temperature"):
                    demand = model_value(temp["power_tag"])
                    if not demand:
                        actual = temp["ambient_c"]
                    else:
                        air = read_source(frame, temp["gas"]) / temp["reference_airflow"]
                        wear = read_source(frame, temp["wear"])
                        actual = (temp["normal_c"] + temp["power_gain_c"] * (demand / temp["reference_kw"] - 1)
                                  + temp["cooling_gain_c"] * (1 - air) + temp["wear_gain_c"] * wear)
                if oil := src.get("oil_pressure"):
                    bearing = thermal_state.get(oil["bearing_tag"], oil["reference_c"])
                    actual = (oil["normal_bar"] - oil["drift_bar_per_c"] * (bearing - oil["reference_c"])
                              if actual else 0)
                estimates[tag_id] = actual
            return estimates[tag_id]

        for tag in tags:
            source = tag["source"]
            value = read_source(frame, source)
            if tag.get("channel") == "lab":
                if "blaine" in source:
                    value = finish_lab_sample(frame, tag, lab_state.setdefault(tag["tag_id"], {}), time_s)
                if value:
                    lab.setdefault(tag["device_id"], {})[tag["tag_id"]] = value
                continue
            field = source["field"].rsplit(".", 1)[-1]
            transform = source.get("transform")
            if transform == "bags_count":
                value = bag_count
            elif transform == "bags_per_min":
                value = bag_count - bag_history[0][1]
            elif transform == "bag_weight":
                value = bag_weight
            elif transform == "delayed_bag_count":
                value = belt_count
            elif transform == "loaded_bag_count":
                value = loading_count
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
            elif any(key in source for key in ("passive_model", "electric_power", "mill_temperature", "oil_pressure")):
                value = model_value(tag["tag_id"])
            if value is not None and coupled_value is None and "time_constant_s" in tag:
                tag_id = tag["tag_id"]
                previous = thermal_state.get(tag_id, value)
                tau = tag.get("fall_time_constant_s", tag["time_constant_s"]) if value < previous else tag["time_constant_s"]
                weight = -expm1(-step_s / tau)
                value = previous + weight * (value - previous)
                thermal_state[tag_id] = value
            if enabled and "conditioning" in tag and tag["conditioning"]["kind"] != "counter":
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
                if rule.get("use_bag_average"):
                    value = bag_average
                if reference := rule.get("reference_tag"):
                    reference_value = device_readings.get(reference)
                    value = value / reference_value if value is not None and reference_value else None
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
