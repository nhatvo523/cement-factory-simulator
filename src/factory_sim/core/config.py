"""Load model contracts, asset instances and scenarios from JSON."""

import json
import math
from pathlib import Path

from factory_sim.equipment import IMPLEMENTATIONS
from factory_sim.bulk_components import BULK_COMPONENT_MODELS
from factory_sim.milling_components import MILLING_COMPONENT_MODELS
from factory_sim.kiln_components import KILN_COMPONENT_MODELS
from factory_sim.crusher import FAULTS as CRUSHER_FAULTS
from factory_sim.cement_dispatch import device_faults


COMPONENT_MODELS = {**BULK_COMPONENT_MODELS, **MILLING_COMPONENT_MODELS, **KILN_COMPONENT_MODELS}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_parameter(name, value, rule):
    if (type(value) not in (float, int) or not math.isfinite(value)
            or value < rule.get("min", 0) or value > rule.get("max", math.inf)):
        raise ValueError(f"Invalid value for {name}: {value!r}")


def load_plant(model_directory, path):
    models = {}
    for file in sorted(Path(model_directory).glob("*.json")):
        model = read_json(file)
        if model["id"] in models or model["implementation"] not in IMPLEMENTATIONS:
            raise ValueError(f"Invalid model registration: {model['id']}")
        component_model = model.get("component_model")
        if component_model is not None and component_model not in COMPONENT_MODELS:
            raise ValueError(f"Unknown component model: {component_model}")
        models[model["id"]] = model
    plant = read_json(path)
    for key, feed in plant["feeds"].items():
        check_parameter(f"{key}.feed.flow_tph", feed["flow_tph"], {})
        check_parameter(f"{key}.feed.moisture_fraction", feed["moisture_fraction"], {"max": 0.999})
    assets = {}
    for asset in plant["equipment"]:
        key = asset["id"]
        if key in assets:
            raise ValueError(f"Duplicate equipment: {key}")
        model = models[asset["model_type"]]
        parameters = asset["parameters"]
        if parameters.keys() != model["parameters"].keys():
            raise ValueError(f"Parameter mismatch for {key}")
        for name, rule in model["parameters"].items():
            check_parameter(f"{key}.{name}", parameters[name], rule)
        if parameters.get("initial_t", 0) > parameters.get("capacity_t", math.inf):
            raise ValueError(f"Initial inventory exceeds capacity: {key}")
        assets[key] = {**asset, "model": model}
    dispatch = plant.get("cement_dispatch")
    if dispatch:
        source = dispatch["clinker_source"]
        if assets.get(source, {}).get("model", {}).get("implementation") != "storage":
            raise ValueError("Cement dispatch requires a clinker storage source")
        for grade, settings in dispatch["grades"].items():
            check_parameter(grade + ".initial_t", settings["initial_t"], {"max": settings["capacity_t"]})
            check_parameter(grade + ".capacity_t", settings["capacity_t"], {"min": 0.001})
        for line in dispatch["mills"]:
            if line["grade"] not in dispatch["grades"] or set(line["equipment"]) != {"feeder", "mill", "separator", "fan"}:
                raise ValueError("Invalid cement mill grade or equipment")
            for name in ("capacity_tph", "additive_per_clinker", "airflow_m3_s"):
                check_parameter(name, line[name], {})
            check_parameter("fines_fraction", line["fines_fraction"], {"min": 0.001, "max": 1})
        for line in dispatch["dispatch"]:
            roles = set(line["equipment"])
            if line["grade"] not in dispatch["grades"] or roles not in (
                    {"feeder", "packer", "conveyor", "loader"}, {"feeder", "spout", "scale"}):
                raise ValueError("Invalid cement dispatch grade or equipment")
            check_parameter("demand_tph", line["demand_tph"], {})
            if "packer" in roles:
                check_parameter("bag_mass_kg", line["bag_mass_kg"], {"min": 0.001})
        for key, catalog in device_faults(dispatch).items():
            if key in assets:
                raise ValueError(f"Duplicate equipment: {key}")
            assets[key] = {"parameters": {}, "model": {"implementation": "dispatch_device", "parameters": {}, "ports": {}},
                           "dispatch_faults": catalog}
    used_ports = set()
    for connection in plant["connections"]:
        source, target = connection["from"], connection["to"]
        if source in used_ports or target in used_ports:
            raise ValueError(f"Port already connected: {source} -> {target}")
        used_ports.update((source, target))
        source_id, source_port = source.split(".", 1)
        target_id, target_port = target.split(".", 1)
        out_port = assets[source_id]["model"]["ports"][source_port]
        in_port = assets[target_id]["model"]["ports"][target_port]
        if out_port != ["out", connection["kind"]] or in_port != ["in", connection["kind"]]:
            raise ValueError(f"Incompatible ports: {source} -> {target}")
    return plant, assets


def load_scenario(path, assets):
    scenario = read_json(path)
    if type(scenario["duration_s"]) is not int or scenario["duration_s"] <= 0:
        raise ValueError("Scenario duration must be a positive integer")
    for event in scenario["events"]:
        if type(event["at_s"]) is not int or not 0 <= event["at_s"] < scenario["duration_s"]:
            raise ValueError(f"Event outside scenario: {event}")
        key, parameter = event["target"].split(".", 1)
        if "." in parameter:
            component, fault = parameter.split(".", 1)
            model = assets[key]["model"]
            runtime = COMPONENT_MODELS.get(model.get("component_model"))
            catalog = runtime.FAULTS if runtime else (
                CRUSHER_FAULTS if model["implementation"] == "rotor_crusher" else assets[key].get("dispatch_faults", {}))
            if fault not in catalog.get(component, ()):
                raise ValueError(f"Unknown component fault: {event['target']}")
            check_parameter(event["target"], event["value"], {"min": 0.01, "max": 1})
            continue
        rule = assets[key]["model"]["parameters"][parameter]
        if not rule.get("runtime", False):
            raise ValueError(f"Parameter cannot change during a run: {event['target']}")
        check_parameter(event["target"], event["value"], rule)
    profile_name = scenario.get("operating_profile")
    if profile_name is not None:
        if not isinstance(profile_name, str) or not profile_name or not profile_name.replace("_", "").isalnum():
            raise ValueError("Invalid operating profile name")
        profile = read_json(Path(path).parent.parent / "operating_profiles" / f"{profile_name}.json")
        if type(profile["seed"]) is not int:
            raise ValueError("Operating profile seed must be an integer")
        groups = [profile.get("feed_variation", {}), profile.get("parameter_variation", {}),
                  profile.get("measurements", {})]
        for group in groups:
            for key, signals in group.items():
                if key not in assets:
                    raise ValueError(f"Unknown operating profile equipment: {key}")
                for name, settings in signals.items():
                    check_parameter(f"{key}.{name}.relative_amplitude", settings["relative_amplitude"], {"max": 1})
                    check_parameter(f"{key}.{name}.period_s", settings["period_s"], {"min": 1})
        for key, parameters in groups[1].items():
            for name in parameters:
                if not assets[key]["model"]["parameters"].get(name, {}).get("runtime"):
                    raise ValueError(f"Parameter cannot vary at runtime: {key}.{name}")
        scenario["profile"] = profile
    return scenario
