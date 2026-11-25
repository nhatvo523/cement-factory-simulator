"""Two-phase solver for buffered bulk-material lines with local separator recycle."""

from copy import deepcopy
from itertools import count
from math import isclose

from factory_sim.equipment import DryerMill, Fan, Material, Separator, Storage, Throughput
from factory_sim.core.variation import operating_values, sampled_components, sampled_values
from factory_sim.crusher import RotorCrusher
from factory_sim.bulk_components import BULK_COMPONENT_MODELS, Reclaimer
from factory_sim.milling_components import MILLING_COMPONENT_MODELS


def segments(plant, assets):
    routes, parents, fans, returns = {}, {}, {}, {}
    for connection in plant["connections"]:
        source, target = (connection[k].split(".")[0] for k in ("from", "to"))
        kind = connection["kind"]
        if kind == "material":
            if source in routes or target in parents:
                raise ValueError("This solver supports one material inlet and outlet per asset")
            routes[source] = target
            parents[target] = source
        elif kind == "gas":
            fans[target] = source
        elif kind == "recycle":
            returns[source] = target
    kinds = {key: asset["model"]["implementation"] for key, asset in assets.items()}
    material_assets = {key for key, kind in kinds.items() if kind != "fan"}
    heads = set(plant["feeds"])
    if heads != material_assets - parents.keys():
        raise ValueError("Each material line needs one external feed")
    for key, kind in kinds.items():
        if kind == "dryer_mill" and (
            kinds.get(fans.get(key)) != "fan" or kinds.get(routes.get(key)) != "separator"
            or returns.get(routes.get(key)) != key
        ):
            raise ValueError(f"Dryer mill requires a fan and an adjacent separator recycle: {key}")
        if kind == "separator" and (kinds.get(parents.get(key)) != "dryer_mill" or returns.get(key) != parents[key]):
            raise ValueError(f"Unsupported separator recycle: {key}")
    paths, seen = [], set()
    for head in sorted(heads):
        path, origin = [], None
        node = head
        while node is not None:
            if node in seen:
                raise ValueError("Unexpected material cycle")
            seen.add(node)
            path.append(node)
            if kinds[node] == "storage":
                paths.append((head, origin, path))
                path = [node]
                origin = node
            node = routes.get(node)
        if path:
            paths.append((head, origin, path))
    if seen != material_assets:
        raise ValueError("Disconnected material cycle")
    return paths, kinds, fans, routes


def simulate(plant, assets, scenario, live_events=None):
    paths, kinds, fans, routes = segments(plant, assets)
    parents = {target: source for source, target in routes.items()}
    step = plant["step_s"]
    if type(step) is not int or step <= 0 or scenario["duration_s"] % step:
        raise ValueError("Duration must be a multiple of the positive step_s")
    hours = step / 3600
    nominal = {key: deepcopy(asset["parameters"]) for key, asset in assets.items()}
    crushers = {key: RotorCrusher(nominal[key]) for key, kind in kinds.items() if kind == "rotor_crusher"}
    bulk_components = {
        key: BULK_COMPONENT_MODELS[asset["model"]["component_model"]](nominal[key])
        for key, asset in assets.items() if asset["model"].get("component_model") in BULK_COMPONENT_MODELS
    }
    milling_components = {
        key: MILLING_COMPONENT_MODELS[asset["model"]["component_model"]](nominal[key])
        for key, asset in assets.items() if asset["model"].get("component_model") in MILLING_COMPONENT_MODELS
    }
    component_models = {**crushers, **bulk_components, **milling_components}
    params = nominal
    profile = scenario.get("profile", {})
    seed = profile.get("seed", 0)
    feed_variation = profile.get("feed_variation", {})
    parameter_variation = profile.get("parameter_variation", {})
    signals = profile.get("measurements", {})
    if not feed_variation.keys() <= plant["feeds"].keys():
        raise ValueError("Operating profile targets a missing external feed")
    stocks = {key: Material.wet_mass(p["initial_t"], p["initial_moisture_fraction"])
              for key, p in params.items() if kinds[key] == "storage"}
    events = {}
    for event in scenario["events"]:
        if event["at_s"] % step:
            raise ValueError("Events must align with the simulation time step")
        events.setdefault(event["at_s"], []).append(event)

    starts = range(0, scenario["duration_s"], step) if live_events is None else count(0, step)
    for start in starts:
        interval_events = events.get(start, [])
        if live_events:
            interval_events = interval_events + [{**event, "at_s": start} for event in live_events]
            live_events.clear()
        for event in interval_events:
            key, name = event["target"].split(".", 1)
            if "." in name:
                component, fault = name.split(".", 1)
                component_models[key].inject(component, fault, event["value"], start)
            else:
                nominal[key][name] = event["value"]
        params = {**nominal, **{
            key: operating_values(nominal[key], variation, f"{seed}:{key}:operating", start,
                                  assets[key]["model"]["parameters"])
            for key, variation in parameter_variation.items()
        }}
        for key, crusher in crushers.items():
            params[key] = {**params[key], "capacity_tph": crusher.capacity(params[key], start)}
        for key, runtime in bulk_components.items():
            if kinds[key] == "throughput":
                params[key] = {**params[key], "capacity_tph": runtime.capacity(params[key], start)}
        for key, runtime in milling_components.items():
            params[key] = runtime.apply(params[key], start)
        opening_total = sum_materials(stocks.values())
        inflow = {key: Material() for key in stocks}
        outflow = {key: Material() for key in stocks}
        boundary_in, boundary_out = Material(), Material()
        evaporated = 0.0
        data = {key: {} for key in assets}
        for key, kind in kinds.items():
            if kind == "fan":
                data[key] = {"airflow_m3_s": Fan.airflow(params[key])}
                data[key]["nominal_airflow_m3_s"] = nominal[key]["airflow_m3_s"]

        for head, origin, path in paths:
            # Opening inventory is available for this interval. Additions enter at commit.
            if origin:
                source = stocks[origin]
                if origin in bulk_components and source.total > 0:
                    available = min(source.total, bulk_components[origin].outlet_limit(start) * hours)
                    source = source.scaled(available / source.total)
            else:
                feed = plant["feeds"][head]
                feed = operating_values(feed, feed_variation.get(head, {}), f"{seed}:{head}:feed", start,
                                        {"moisture_fraction": {"max": 0.999}})
                source = Material.wet_mass(feed["flow_tph"] * hours, feed["moisture_fraction"])
            nodes = path[1:] if origin else path
            if not nodes:
                outflow[origin] = source
                boundary_out = boundary_out.plus(source)
                continue
            limit = source.total
            unit = source.scaled(1 / source.total) if source.total else Material()
            transformations = {}
            for key in nodes:
                kind, p = kinds[key], params[key]
                if kind == "storage":
                    if key in bulk_components and not bulk_components[key].accepts_inlet(start):
                        limit = 0
                    elif unit.total:
                        limit = min(limit, Storage.acceptance(p, stocks[key]) / unit.total)
                elif kind == "dryer_mill":
                    airflow = data[fans[key]]["airflow_m3_s"]
                    dried = DryerMill.dry(unit, p)
                    _, coarse = Separator.circulating_flow(dried.total, params[routes[key]])
                    limit = min(limit, Throughput.input_limit(p, hours) / (1 + coarse),
                                DryerMill.drying_limit(p, airflow, unit.moisture, hours))
                    transformations[key] = (unit, dried, coarse)
                    unit = dried
                elif kind == "separator":
                    gross, coarse = Separator.circulating_flow(unit.total, p)
                    if gross:
                        limit = min(limit, Throughput.input_limit(p, hours) / gross)
                    transformations[key] = (unit, unit, coarse)
                else:
                    if unit.total:
                        limit = min(limit, Throughput.input_limit(p, hours) / unit.total)
                    transformations[key] = (unit, unit, 0)
            initial = source.scaled(limit / source.total) if source.total else Material()
            if origin:
                outflow[origin] = initial
            else:
                boundary_in = boundary_in.plus(initial)
            output = unit.scaled(limit)
            if nodes[-1] in stocks:
                inflow[nodes[-1]] = output
            else:
                boundary_out = boundary_out.plus(output)
            for key, (enter, leave, recycle) in transformations.items():
                water_removed = (enter.water - leave.water) * limit
                evaporated += water_removed
                data[key] = {
                    "inlet_tph": (enter.total + recycle) * limit / hours,
                    "outlet_tph": (leave.total + recycle) * limit / hours if kinds[key] == "dryer_mill" else leave.total * limit / hours,
                    "fresh_inlet_tph": enter.total * limit / hours if kinds[key] != "separator" else 0.0,
                    "inlet_moisture_fraction": enter.moisture if limit else None,
                    "outlet_moisture_fraction": leave.moisture if limit else None,
                    "evaporated_water_tph": water_removed / hours,
                    "recycle_tph": recycle * limit / hours,
                }
                if kinds[key] == "separator":
                    del data[key]["fresh_inlet_tph"]

        opening_stocks = stocks.copy()
        for key, opening in opening_stocks.items():
            close = opening.minus(outflow[key]).plus(inflow[key])
            capacity = params[key]["capacity_t"]
            if min(close.dry, close.water) < -1e-8 or close.total > capacity + 1e-8:
                raise RuntimeError(f"Inventory out of bounds: {key}")
            stocks[key] = close
            data[key] = {
                "inventory_t": close.total, "level_fraction": close.total / capacity,
                "inventory_moisture_fraction": close.moisture if close.total else None,
                "inlet_tph": inflow[key].total / hours, "outlet_tph": outflow[key].total / hours,
            }
        expected = opening_total.plus(boundary_in).minus(boundary_out).minus(Material(water=evaporated))
        inventory = sum_materials(stocks.values())
        errors = inventory.minus(expected)
        if not all(isclose(v, 0, abs_tol=1e-8) for v in (errors.dry, errors.water)):
            raise RuntimeError(f"Mass balance failure at {start + step} s")
        for key, values in data.items():
            operating = values.get("airflow_m3_s", values.get("inlet_tph", 0)) or values.get("outlet_tph", 0)
            if key not in stocks:
                values["operating_state"] = "RUNNING" if operating else "STOPPED"
            if "capacity_tph" in params[key]:
                values["configured_capacity_tph"] = nominal[key]["capacity_tph"]
                if key in crushers or (key in parameter_variation and "capacity_tph" in parameter_variation[key]):
                    values["effective_capacity_tph"] = params[key]["capacity_tph"]
            if kinds[key] == "dryer_mill":
                values["target_moisture_fraction"] = params[key]["target_moisture_fraction"]
                values["evaporation_limit_tph"] = DryerMill.evaporation_limit(
                    params[key], data[fans[key]]["airflow_m3_s"])
            if kinds[key] == "separator":
                values["fines_fraction"] = params[key]["fines_fraction"]
        for key, crusher in crushers.items():
            crusher.telemetry(data[key], nominal[key], f"{seed}:{key}", start + step, step)
        measured = {key: sampled_values(data[key], config, f"{seed}:{key}:sensor", start + step)
                    for key, config in signals.items()}
        for key, runtime in bulk_components.items():
            route_status = {}
            if isinstance(runtime, Reclaimer):
                upstream = opening_stocks.get(parents.get(key))
                destination = routes.get(key)
                downstream = opening_stocks.get(destination)
                receiving_model = bulk_components.get(destination)
                route_status = {
                    "step_s": step,
                    "stock_available": upstream is None or upstream.total > 1e-9,
                    "discharge_ready": (downstream is None or Storage.acceptance(params[destination], downstream) > 1e-9)
                    and (receiving_model is None or receiving_model.accepts_inlet(start)),
                }
            runtime.telemetry(data[key], measured.get(key, {}), start, f"{seed}:{key}", **route_status)
        for key, runtime in milling_components.items():
            runtime.telemetry(data[key], measured.get(key, {}), start, f"{seed}:{key}")
            if kinds[key] == "dryer_mill":
                if params[routes[key]]["capacity_tph"] == 0:
                    data[key]["process_notice"] = "mill_separator_unavailable"
                elif data[fans[key]]["airflow_m3_s"] < 0.7 * params[key]["reference_airflow_m3_s"]:
                    data[key]["process_notice"] = "mill_low_airflow"
        for key in component_models:
            components = sampled_components(data[key]["components"], f"{seed}:{key}:sensor", start + step)
            measured.setdefault(key, {})["components"] = components
        yield {"time_s": start + step, "events": interval_events, "equipment": data,
               "measurements": measured,
               "balance": {"dry_residual_t": errors.dry, "water_residual_t": errors.water,
                           "evaporated_water_t": evaporated, "boundary_input_t": boundary_in.total,
                           "boundary_output_t": boundary_out.total, "inventory_t": inventory.total}}


def sum_materials(amounts):
    total = Material()
    for material in amounts:
        total = total.plus(material)
    return total
