"""Parallel finish mills, grade-specific cement storage and dispatch."""

from factory_sim.equipment import Material
from factory_sim.core.variation import sampled_values


def device_faults(config):
    devices = {}
    for section, roles in (
        ("mills", {"feeder": "drive", "mill": "drive", "separator": "rotor", "fan": "drive"}),
        ("dispatch", {"feeder": "drive", "packer": "filling_head", "conveyor": "belt",
                      "loader": "drive", "spout": "loading_spout", "scale": "load_cell"}),
    ):
        for line in config[section]:
            for role, asset in line["equipment"].items():
                if asset in devices or asset == config["silo"]:
                    raise ValueError(f"Duplicate dispatch equipment: {asset}")
                devices[asset] = {roles[role]: {"unavailable"}}
    devices[config["silo"]] = {}
    return devices


class CementDispatch:
    def __init__(self, config):
        self.config = config
        self.stock = {grade: Material(dry=p["initial_t"]) for grade, p in config["grades"].items()}
        self.faults = {}

    def inject(self, asset, component, fault, severity, time_s):
        self.faults[asset] = {"component": component, "fault": fault, "severity": severity, "at_s": time_s}

    def available(self, line):
        return 1 - max((self.faults.get(key, {}).get("severity", 0) for key in line["equipment"].values()), default=0)

    def total_stock(self):
        return Material(sum(value.dry for value in self.stock.values()), sum(value.water for value in self.stock.values()))

    def step(self, clinker, hours):
        data = {}
        additions = Material()
        delivered = Material()
        intake = dict.fromkeys(self.stock, 0.0)
        discharge = dict.fromkeys(self.stock, 0.0)
        opening = self.stock.copy()
        spaces = {grade: max(0, self.config["grades"][grade]["capacity_t"] - stock.total)
                  for grade, stock in opening.items()}
        plans = []
        for line in self.config["mills"]:
            grade = line["grade"]
            blend = line["additive_per_clinker"]
            reserved = min(line["capacity_tph"] * self.available(line) * hours, spaces[grade])
            spaces[grade] -= reserved
            demand = reserved / (1 + blend)
            plans.append((line, demand))
        requested = sum(demand for _, demand in plans)
        allocation = min(1, clinker.total / requested) if requested else 0
        clinker_used = clinker.scaled(requested * allocation / clinker.total) if clinker.total else Material()
        for line, demand in plans:
            grade = line["grade"]
            consumed = demand * allocation
            portion = clinker.scaled(consumed / clinker.total) if clinker.total else Material()
            additive = Material(dry=consumed * line["additive_per_clinker"])
            additions = additions.plus(additive)
            cement = portion.plus(additive)
            intake[grade] += cement.total
            recycle = cement.total * (1 / line["fines_fraction"] - 1)
            flow, circulating = cement.total / hours, recycle / hours
            equipment = line["equipment"]
            data[equipment["feeder"]] = {"inlet_tph": consumed / hours, "outlet_tph": flow}
            data[equipment["mill"]] = {"fresh_inlet_tph": flow, "outlet_tph": flow + circulating, "recycle_tph": circulating}
            data[equipment["separator"]] = {"inlet_tph": flow + circulating, "outlet_tph": flow, "recycle_tph": circulating}
            data[equipment["fan"]] = {"airflow_m3_s": line["airflow_m3_s"] if consumed else 0}
            self.stock[grade] = self.stock[grade].plus(cement)

        remaining = {grade: value.total for grade, value in opening.items()}
        for line in self.config["dispatch"]:
            grade = line["grade"]
            shipped = min(max(0, remaining[grade]), line["demand_tph"] * self.available(line) * hours)
            remaining[grade] -= shipped
            discharge[grade] += shipped
            stored = opening[grade]
            portion = stored.scaled(shipped / stored.total) if stored.total else Material()
            self.stock[grade] = self.stock[grade].minus(portion)
            delivered = delivered.plus(portion)
            for role, asset in line["equipment"].items():
                data[asset] = {"outlet_tph": shipped / hours} if role != "scale" else {"dispatch_flow_tph": shipped / hours}
            if "packer" in line["equipment"]:
                data[line["equipment"]["packer"]]["bags_per_min"] = shipped / hours * 1000 / line["bag_mass_kg"] / 60

        data[self.config["silo"]] = {
            "inventory_t": self.total_stock().total,
            "inlet_tph": sum(intake.values()) / hours,
            "outlet_tph": sum(discharge.values()) / hours,
            "grades": {grade: stock.total for grade, stock in self.stock.items()},
        }
        for asset, values in data.items():
            fault = self.faults.get(asset)
            flowing = any(value > 0 for key, value in values.items() if key.endswith(("_tph", "_m3_s")))
            values["operating_state"] = "TRIPPED" if fault and fault["severity"] == 1 else ("RUNNING" if flowing else "IDLE")
            values["active_faults"] = [fault] if fault else []
        return clinker_used, additions, delivered, data

    @staticmethod
    def measurements(data, seed, time_s):
        measured = {}
        for asset, values in data.items():
            channels = {name: {"relative_amplitude": 0.01, "period_s": 205}
                        for name, reading in values.items() if type(reading) in (float, int)}
            measured[asset] = sampled_values(values, channels, f"{seed}:{asset}:sensor", time_s)
            if "grades" in values:
                grades = values["grades"]
                channels = {grade: {"relative_amplitude": 0.01, "period_s": 211} for grade in grades}
                measured[asset]["grades"] = sampled_values(grades, channels, f"{seed}:{asset}:grade", time_s)
                measured[asset]["inventory_t"] = sum(measured[asset]["grades"].values())
        return measured
