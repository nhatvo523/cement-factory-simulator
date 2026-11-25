"""Two-phase solver for buffered bulk-material lines with local separator recycle."""

from copy import deepcopy
from itertools import count
from math import isclose

from factory_sim.equipment import DryerMill, Fan, Material, Separator, Storage, Throughput
from factory_sim.core.variation import operating_values, sampled_components, sampled_values
from factory_sim.crusher import RotorCrusher
from factory_sim.bulk_components import BULK_COMPONENT_MODELS, Reclaimer
from factory_sim.milling_components import MILLING_COMPONENT_MODELS
from factory_sim.kiln_components import KILN_COMPONENT_MODELS, ClinkerCooler, CyclonePreheater, KilnStage, RotaryKiln
from factory_sim.cement_dispatch import CementDispatch
from factory_sim.finishing_components import FINISHING_COMPONENT_MODELS
from factory_sim.thermal_coupling import KilnRawMillCoupling


def segments(plant, assets, branch_assets=()):
    routes, parents, fans, returns = {}, {}, {}, {}
    for connection in plant["connections"]:
        source, target = (connection[k].split(".")[0] for k in ("from", "to"))
        if source in branch_assets or target in branch_assets:
            continue
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
    material_assets = {key for key, kind in kinds.items() if kind != "fan" and key not in branch_assets}
    heads = set(plant["feeds"])
    if heads != material_assets - parents.keys():
        raise ValueError("Each material line needs one external feed")
    for key, kind in kinds.items():
        if key in branch_assets:
            continue
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
    dispatch_config = plant.get("cement_dispatch")
    dispatch = CementDispatch(dispatch_config, plant["connections"], assets) if dispatch_config else None
    branch_assets = dispatch.assets if dispatch else set()
    paths, kinds, fans, routes = segments(plant, assets, branch_assets)
    if dispatch and dispatch.source in routes:
        raise ValueError("Cement dispatch source must end the clinker line")
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
    process_models = {**MILLING_COMPONENT_MODELS, **KILN_COMPONENT_MODELS, **FINISHING_COMPONENT_MODELS}
    process_components = {
        key: process_models[asset["model"]["component_model"]](nominal[key])
        for key, asset in assets.items() if asset["model"].get("component_model") in process_models
    }
    component_models = {**crushers, **bulk_components, **process_components}
    thermal_stages = {key: runtime for key, runtime in process_components.items() if isinstance(runtime, KilnStage)}
    preheaters = {key: runtime for key, runtime in thermal_stages.items() if isinstance(runtime, CyclonePreheater)}
    exhausts = {source: target for target, source in fans.items() if kinds[target] == "fan"}
    if not preheaters.keys() <= exhausts.keys():
        raise ValueError("Each cyclone preheater requires a gas connection to its exhaust fan")
    heat_routes, kiln_preheat, raw_heat = {}, {}, {}
    for connection in plant["connections"]:
        if connection["kind"] == "heat":
            source, target = (connection[name].split(".")[0] for name in ("from", "to"))
            if isinstance(thermal_stages.get(source), ClinkerCooler) and isinstance(thermal_stages.get(target), RotaryKiln):
                heat_routes[source] = target
            elif isinstance(thermal_stages.get(source), RotaryKiln) and target in preheaters:
                kiln_preheat[target] = source
            elif source in preheaters and kinds[target] == "dryer_mill":
                raw_heat[target] = source
            else:
                raise ValueError(f"Unsupported heat recovery route: {source} -> {target}")
    kiln_heat = dict.fromkeys(kiln_preheat.values(), 1.0)
    recovered_fraction = dict.fromkeys(raw_heat, 1.0)
    coupling_config = plant.get("thermal_coupling", {})
    coupling = KilnRawMillCoupling(coupling_config, step) if coupling_config.get("enabled") else None
    if coupling and routes.get(routes.get(coupling.mill)) != coupling.meal_silo:
        raise ValueError("Thermal coupling requires a mill, separator and adjacent meal silo")
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
                if event.get("clear"):
                    component_models[key].faults.pop((component, fault), None)
                else:
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
        for key, runtime in process_components.items():
            if key not in preheaters:
                params[key] = runtime.apply(params[key], start)
        pressure_factor = 1.0
        if coupling:
            mill = coupling.mill
            ready = (params[mill]["capacity_tph"] > 0 and params[routes[mill]]["capacity_tph"] > 0
                     and Fan.airflow(params[fans[mill]]) > 0)
            flow_factor, pressure_factor = coupling.route_gas(ready)
            fan = coupling.draft_fan
            params[fan] = {**params[fan], "airflow_m3_s": Fan.airflow(params[fan]) * flow_factor}
            params[mill] = coupling.prepare_drying(Fan.airflow(params[fan]), params[mill], ready)
        for key, runtime in preheaters.items():
            params[key] = runtime.apply(params[key], start, Fan.airflow(params[exhausts[key]]),
                                        kiln_heat.get(kiln_preheat.get(key), 1.0))
        for mill, source in raw_heat.items():
            fraction = min(preheaters[source].heat_fraction, preheaters[source].draft_fraction)
            recovered_fraction[mill] = fraction
            if coupling and mill == coupling.mill:
                continue
            backup = params[mill]["backup_heat_fraction"]
            params[mill] = {**params[mill], "heat_availability_fraction":
                            min(params[mill]["heat_availability_fraction"], backup + (1 - backup) * fraction)}
        opening_total = sum_materials(stocks.values())
        if dispatch:
            opening_total = opening_total.plus(dispatch.total_stock())
        inflow = {key: Material() for key in stocks}
        outflow = {key: Material() for key in stocks}
        boundary_in, boundary_out = Material(), Material()
        evaporated = co2_released = 0.0
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
                if dispatch and origin == dispatch.source:
                    accepted, additions, delivered = dispatch.step(
                        source, hours, params, data, process_components[dispatch.silo].blocked, start)
                    outflow[origin] = accepted
                    boundary_in = boundary_in.plus(additions)
                    boundary_out = boundary_out.plus(delivered)
                    continue
                outflow[origin] = source
                boundary_out = boundary_out.plus(source)
                continue
            limit = source.total
            unit = source.scaled(1 / source.total) if source.total else Material()
            transformations = {}
            wet_mill = None
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
                    drying_limit = DryerMill.drying_limit(p, airflow, unit.moisture, hours)
                    feed_limit = (coupling.dryer_feed(drying_limit, hours, airflow)
                                  if coupling and key == coupling.mill else drying_limit)
                    limit = min(limit, Throughput.input_limit(p, hours) / (1 + coarse), feed_limit)
                    if limit > drying_limit:
                        wet_mill = key
                        provisional = coupling.dried_unit(unit, limit, hours, airflow, p)
                        _, gross_recycle = Separator.circulating_flow(provisional.total, params[routes[key]])
                        limit = min(limit, Throughput.input_limit(p, hours) / (1 + gross_recycle))
                        dried = coupling.dried_unit(unit, limit, hours, airflow, p)
                        _, coarse = Separator.circulating_flow(dried.total, params[routes[key]])
                    transformations[key] = (unit, dried, coarse)
                    unit = dried
                elif kind == "separator":
                    gross, coarse = Separator.circulating_flow(unit.total, p)
                    if gross:
                        limit = min(limit, Throughput.input_limit(p, hours) / gross)
                    transformations[key] = (unit, unit, coarse)
                elif key in thermal_stages:
                    if unit.total:
                        limit = min(limit, Throughput.input_limit(p, hours) / unit.total)
                    treated = thermal_stages[key].transform(unit, p)
                    transformations[key] = (unit, treated, 0)
                    unit = treated
                else:
                    if unit.total:
                        limit = min(limit, Throughput.input_limit(p, hours) / unit.total)
                    transformations[key] = (unit, unit, 0)
            if wet_mill:
                raw, _, _ = transformations[wet_mill]
                mill_fan = data[fans[wet_mill]]["airflow_m3_s"]
                unit = coupling.dried_unit(raw, limit, hours, mill_fan, params[wet_mill])
                separator = routes[wet_mill]
                _, coarse = Separator.circulating_flow(unit.total, params[separator])
                transformations[wet_mill] = (raw, unit, coarse)
                transformations[separator] = (unit, unit, coarse)
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
                released = (enter.dry - leave.dry) * limit
                co2_released += released
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
                if key in thermal_stages:
                    data[key]["process_co2_tph"] = released / hours

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
        expected = opening_total.plus(boundary_in).minus(boundary_out).minus(Material(co2_released, evaporated))
        inventory = sum_materials(stocks.values())
        if dispatch:
            inventory = inventory.plus(dispatch.total_stock())
        errors = inventory.minus(expected)
        if not all(isclose(v, 0, abs_tol=1e-8) for v in (errors.dry, errors.water)):
            raise RuntimeError(f"Mass balance failure at {start + step} s")
        for key, values in data.items():
            operating = values.get("airflow_m3_s", values.get("inlet_tph", 0)) or values.get("outlet_tph", 0)
            if key not in stocks and "operating_state" not in values:
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
        for source, target in heat_routes.items():
            hot_temperature = (coupling.burning_c if coupling and target == coupling.kiln
                               else params[target]["outlet_temperature_c"])
            recovered = thermal_stages[source].recovered_heat_kw(
                data[source]["outlet_tph"], hot_temperature)
            data[source]["recovered_heat_kw"] = recovered
            data[target]["recovered_heat_kw"] = recovered
        measured = {key: sampled_values(data[key], config, f"{seed}:{key}:sensor", start + step)
                    for key, config in signals.items()}
        if dispatch:
            stock = data[dispatch.silo]["grades"]
            level_signal = signals.get(dispatch.silo, {}).get("inventory_t")
            if level_signal:
                measured[dispatch.silo]["grades"] = sampled_values(
                    stock, dict.fromkeys(stock, level_signal), f"{seed}:{dispatch.silo}:grade", start + step)
                measured[dispatch.silo]["inventory_t"] = sum(measured[dispatch.silo]["grades"].values())
                measured[dispatch.silo]["level_fraction"] = (measured[dispatch.silo]["inventory_t"] /
                    sum(p["capacity_t"] for p in dispatch.settings.values()))
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
        for key, runtime in process_components.items():
            runtime.telemetry(data[key], measured.get(key, {}), start, f"{seed}:{key}")
            if kinds[key] == "dryer_mill":
                if params[routes[key]]["capacity_tph"] == 0:
                    data[key]["process_notice"] = "mill_separator_unavailable"
                elif data[fans[key]]["airflow_m3_s"] < 0.7 * params[key]["reference_airflow_m3_s"]:
                    data[key]["process_notice"] = "mill_low_airflow"
                if key in raw_heat:
                    fraction = recovered_fraction[key]
                    data[key]["components"]["mill_hot_gas"] = {"heat_fraction": fraction}
                    if fraction < 0.8 and "process_notice" not in data[key]:
                        data[key]["process_notice"] = "mill_kiln_heat_reduced"
        for key in kiln_heat:
            reference = params[key]["heat_reference_tph"]
            kiln_heat[key] = min(1.0, data[key]["inlet_tph"] / reference) * (1 - thermal_stages[key].severity("main_burner", "fuel_loss"))
        lab = {}
        if coupling:
            fuel_loss = thermal_stages[coupling.kiln].severity("main_burner", "fuel_loss")
            fuel = params[coupling.kiln]["fuel_per_feed"] * (1 - fuel_loss)
            lab = coupling.finish(data, opening_stocks, inflow, outflow,
                                  fuel, start + step)
            data[routes[coupling.mill]]["wet_meal"] = data[coupling.mill]["wet_meal"]
            draft = data[coupling.draft_fan]["components"]["draft_sensor"]
            draft["draft_suction_pa"] *= pressure_factor
        for key in component_models:
            components = sampled_components(data[key]["components"], f"{seed}:{key}:sensor", start + step)
            measured.setdefault(key, {})["components"] = components
        yield {"time_s": start + step, "events": interval_events, "equipment": data,
               **({"lab": lab} if lab else {}),
               "measurements": measured,
               "balance": {"dry_residual_t": errors.dry, "water_residual_t": errors.water,
                           "evaporated_water_t": evaporated, "process_co2_t": co2_released,
                           "boundary_input_t": boundary_in.total,
                           "boundary_output_t": boundary_out.total, "inventory_t": inventory.total}}


def sum_materials(amounts):
    total = Material()
    for material in amounts:
        total = total.plus(material)
    return total
