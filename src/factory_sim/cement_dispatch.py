"""Solve connected finish-grinding and dispatch branches around compartment storage."""

from factory_sim.equipment import Material, Separator


class CementDispatch:
    def __init__(self, config, connections, assets):
        self.source = config["clinker_source"]
        self.silo = config["silo"]
        self.compartments = config["compartments"]
        if not self.compartments:
            raise ValueError("Cement dispatch requires at least one compartment")
        routes = {edge["from"]: edge["to"] for edge in connections
                  if edge["kind"] == "material" and edge["from"] != self.source + ".outlet"}
        parents = {target: source for source, target in routes.items()}
        supports = {edge["to"]: edge["from"] for edge in connections if edge["kind"] in {"gas", "recycle"}}
        feeds = {edge["to"] for edge in connections if edge["from"] == self.source + ".outlet"}
        self.mills = {}
        self.loading = {}
        self.assets = {self.silo}
        for port, settings in self.compartments.items():
            grade = settings["grade"]
            separator = parents[f"{self.silo}.inlet_{port}"].split(".")[0]
            mill = parents[f"{separator}.inlet"].split(".")[0]
            feeder = parents[f"{mill}.inlet"].split(".")[0]
            fan = supports[f"{mill}.air_in"].split(".")[0]
            models = [assets[key]["model"].get("component_model") for key in (feeder, mill, separator)]
            if models != ["weigh_feeder", "finish_drive", "air_separator"] or not {
                    "capacity_tph", "reference_airflow_m3_s"} <= assets[mill]["parameters"].keys():
                raise ValueError(f"Incompatible grinding equipment in compartment {grade}")
            if assets[fan]["model"]["implementation"] != "fan":
                raise ValueError(f"Grinding air must come from a fan in compartment {grade}")
            if feeder + ".inlet" not in feeds or supports[f"{mill}.recycle_in"] != separator + ".coarse_out":
                raise ValueError(f"Invalid finish grinding circuit in compartment {grade}")
            self.mills[grade] = (feeder, mill, separator, fan)
            path = []
            target = routes.get(f"{self.silo}.outlet_{port}")
            while target:
                asset = target.split(".")[0]
                if asset in path:
                    raise ValueError(f"Dispatch material cycle in compartment {grade}")
                if assets[asset]["model"].get("component_model") not in {
                        "weigh_feeder", "bag_packer", "bag_conveyor", "bulk_spout", "finish_drive", "truck_scale"}:
                    raise ValueError(f"Incompatible dispatch equipment: {asset}")
                path.append(asset)
                target = routes.get(asset + ".outlet")
            if not path:
                raise ValueError(f"Missing discharge route in compartment {grade}")
            branch = (*self.mills[grade], *path)
            if grade in self.loading or len(set(branch)) != len(branch) or self.assets.intersection(branch):
                raise ValueError(f"Shared equipment or duplicate grade in compartment {grade}")
            self.assets.update(branch)
            self.loading[grade] = path
        if feeds != {line[0] + ".inlet" for line in self.mills.values()}:
            raise ValueError("Clinker outlet must feed the configured grinding circuits")
        self.settings = {value["grade"]: value for value in self.compartments.values()}
        self.stock = {grade: Material(dry=p["initial_t"]) for grade, p in self.settings.items()}
        self.trucks = {key: (0.0, 0.0) for path in self.loading.values() for key in path
                       if assets[key]["model"].get("component_model") == "truck_scale"}
        if any(key in self.trucks for path in self.loading.values() for key in path[:-1]):
            raise ValueError("A truck scale must terminate its loading route")
        for edge in connections:
            source, target = (edge[field].split(".")[0] for field in ("from", "to"))
            if (source in self.assets) != (target in self.assets) and edge["from"] != self.source + ".outlet":
                raise ValueError(f"Unsupported boundary connection for cement dispatch: {source} -> {target}")

    def total_stock(self):
        return Material(sum(value.dry for value in self.stock.values()), sum(value.water for value in self.stock.values()))

    def step(self, clinker, hours, params, data, blocked, time_s):
        opening = self.stock.copy()
        requests = {}
        for grade, (feeder, mill, separator, fan) in self.mills.items():
            recipe = self.settings[grade]
            blend = 1 + recipe["gypsum_per_clinker"] + recipe["additive_per_clinker"]
            fines = params[separator]["fines_fraction"]
            airflow = data[fan]["airflow_m3_s"]
            air_limit = min(1, airflow / params[mill]["reference_airflow_m3_s"])
            space = max(0, recipe["capacity_t"] - opening[grade].total)
            if air_limit < 0.7:
                data[mill]["process_notice"] = "mill_low_airflow"
            if space < 1e-9:
                data[mill]["waiting_reason"] = "cement_compartment_full"
            product_capacity = min(params[feeder]["capacity_tph"],
                                   params[mill]["capacity_tph"] * fines * air_limit,
                                   params[separator]["capacity_tph"] * fines)
            requests[grade] = min(space, product_capacity * hours) / blend
        demand = sum(requests.values())
        allocation = min(1, clinker.total / demand) if demand else 0
        accepted, additions, delivered = Material(), Material(), Material()
        for grade, (feeder, mill, separator, fan) in self.mills.items():
            recipe = self.settings[grade]
            used = requests[grade] * allocation
            portion = clinker.scaled(used / clinker.total) if clinker.total else Material()
            gypsum = used * recipe["gypsum_per_clinker"]
            additive = used * recipe["additive_per_clinker"]
            additions = additions.plus(Material(dry=gypsum + additive))
            accepted = accepted.plus(portion)
            cement = portion.plus(Material(dry=gypsum + additive))
            flow = cement.total / hours
            gross, coarse = Separator.circulating_flow(flow, params[separator])
            data[feeder].update(inlet_tph=flow, outlet_tph=flow, gypsum_tph=gypsum / hours,
                                additive_tph=additive / hours, clinker_tph=used / hours)
            data[mill].update(inlet_tph=gross, outlet_tph=gross, fresh_inlet_tph=flow, recycle_tph=coarse)
            data[separator].update(inlet_tph=gross, outlet_tph=flow, recycle_tph=coarse)
            path = self.loading[grade]
            stock = opening[grade]
            capacity = min(params[key]["capacity_tph"] for key in path) * hours * (1 - blocked)
            shipped = min(stock.total, capacity)
            if not stock.total:
                data[path[0]]["waiting_reason"] = "cement_compartment_empty"
            for key in path:
                if key in self.trucks:
                    weight, ready_at = self.trucks[key]
                    target = params[key]["truck_target_t"]
                    if ready_at and time_s >= ready_at:
                        weight, ready_at = 0.0, 0.0
                    shipped = 0 if ready_at else min(shipped, max(0, target - weight))
                    weight += shipped
                    if not ready_at and weight >= target - 1e-9:
                        ready_at = time_s + hours * 3600 + params[key]["exchange_s"]
                    self.trucks[key] = weight, ready_at
                    data[key].update(truck_net_t=weight, dispatch_flow_tph=shipped / hours)
                    if ready_at and not shipped:
                        data[key]["waiting_reason"] = "truck_exchange"
            portion = stock.scaled(shipped / stock.total) if stock.total else Material()
            self.stock[grade] = stock.minus(portion).plus(cement)
            delivered = delivered.plus(portion)
            for key in path:
                data[key].update(inlet_tph=shipped / hours, outlet_tph=shipped / hours)
                if "bag_mass_kg" in params[key]:
                    data[key]["bags_per_min"] = shipped * 1000 / hours / 60 / params[key]["bag_mass_kg"]
        total = self.total_stock().total
        capacity = sum(p["capacity_t"] for p in self.settings.values())
        data[self.silo] = {
            "inventory_t": total, "level_fraction": total / capacity,
            "inlet_tph": (accepted.total + additions.total) / hours,
            "outlet_tph": delivered.total / hours,
            "grades": {grade: stock.total for grade, stock in self.stock.items()},
            "operating_state": "FULL" if total >= capacity - 1e-9 else ("AVAILABLE" if total else "EMPTY"),
        }
        return accepted, additions, delivered
