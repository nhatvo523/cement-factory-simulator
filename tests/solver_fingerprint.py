"""Separate regression surfaces for the material and thermal solver."""

import hashlib
import json


MATERIAL_FIELDS = {
    "inlet_tph", "outlet_tph", "fresh_inlet_tph", "recycle_tph", "inventory_t", "grades",
    "evaporated_water_tph", "process_co2_tph", "operating_state", "trip_reason",
}
THERMAL_FIELDS = {
    "airflow_m3_s", "evaporation_limit_tph", "recovered_heat_kw", "gas_mode", "wet_meal",
    "bypass_position_fraction", "gas_pressure_factor", "recovered_drying_heat_kw", "clinker_residence_s",
}


def thermal_fields(values):
    result = {}
    for key, value in values.items():
        if key in THERMAL_FIELDS or key.endswith(("_temperature_c", "_internal_c", "_lime_pct", "_moisture_fraction")) or key in {
            "temperature_c", "draft_suction_pa", "differential_pressure_pa", "thermal_power_kw", "heat_fraction",
        }:
            result[key] = value
        elif key == "components":
            result[key] = {name: selected for name, group in value.items() if (selected := thermal_fields(group))}
    return result


def solver_fingerprints(frames):
    material, thermal = [], []
    for frame in frames:
        equipment = frame["equipment"]
        material.append({"time_s": frame["time_s"], "events": frame["events"], "balance": frame["balance"],
                         "equipment": {asset: {key: value for key, value in values.items() if key in MATERIAL_FIELDS}
                                       for asset, values in equipment.items()}})
        thermal.append({"time_s": frame["time_s"], "lab": frame.get("lab", {}),
                        "equipment": {asset: thermal_fields(values) for asset, values in equipment.items()}})
    return {name: hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            for name, values in (("material", material), ("thermal_quality", thermal))}
