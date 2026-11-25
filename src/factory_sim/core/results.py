"""Result contract shared by the CLI and the web server."""

from factory_sim.core.config import load_plant, load_scenario
from factory_sim.core.engine import simulate
from factory_sim.core.telemetry import load_tag_config, public_frames


def solve_result(model_directory, plant_path, scenario_path, fault_schedule=()):
    plant, assets = load_plant(model_directory, plant_path)
    scenario = load_scenario(scenario_path, assets)
    for fault_path, at_s in fault_schedule:
        fault = load_scenario(fault_path, assets)
        if at_s < 0 or at_s > 86400 or at_s % plant["step_s"]:
            raise ValueError("Invalid fault injection time")
        offset = min(event["at_s"] for event in fault["events"])
        for event in fault["events"]:
            event_time = at_s + event["at_s"] - offset
            scenario["events"].append({**event, "at_s": event_time})
            scenario["duration_s"] = max(scenario["duration_s"], event_time + 5400)
    result = {
        "schema_version": 1,
        "plant_id": plant["id"],
        "scenario_id": scenario["id"],
        "operating_profile": scenario.get("operating_profile"),
        "variation_seed": scenario.get("profile", {}).get("seed"),
        "provenance": plant["provenance"],
        "step_s": plant["step_s"],
        "time_reference": "End of interval. Event at_s applies from the interval start.",
        "value_kind": "simulated_physical",
        "units": {"time_s": "s", "*_tph": "t/h", "*_t": "t", "*_fraction": "1", "*_m3_s": "m³/s"},
        "frames": list(simulate(plant, assets, scenario)),
    }
    return result, plant, assets


def build_result(model_directory, plant_path, scenario_path, fault_schedule=(), ground_truth=None):
    result, plant, assets = solve_result(model_directory, plant_path, scenario_path, fault_schedule)
    config = load_tag_config(model_directory, assets)
    if ground_truth is None:
        ground_truth = config.get("ground_truth_default", False)
    result.update(schema_version=2, value_kind="scada", tags=config["tags"],
                  units={"time_s": "s"})
    result["frames"] = list(public_frames(result["frames"], config["tags"], plant, assets, ground_truth))
    return result
