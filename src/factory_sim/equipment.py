"""Reusable equipment laws. Asset IDs and plant wiring belong in configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    dry: float = 0.0
    water: float = 0.0

    @property
    def total(self):
        return self.dry + self.water

    @property
    def moisture(self):
        return self.water / self.total if self.total else 0.0

    def scaled(self, factor):
        return Material(self.dry * factor, self.water * factor)

    def plus(self, other):
        return Material(self.dry + other.dry, self.water + other.water)

    def minus(self, other):
        return self.plus(other.scaled(-1))

    @classmethod
    def wet_mass(cls, tonnes, moisture):
        return cls(tonnes * (1 - moisture), tonnes * moisture)


class Storage:
    @staticmethod
    def acceptance(parameters, inventory):
        return max(0.0, parameters["capacity_t"] - inventory.total)


class Throughput:
    @staticmethod
    def input_limit(parameters, hours):
        return parameters["capacity_tph"] * hours


class Fan:
    @staticmethod
    def airflow(parameters):
        return parameters["airflow_m3_s"]


class DryerMill(Throughput):
    @staticmethod
    def evaporation_limit(parameters, airflow):
        return parameters["evaporation_capacity_tph"] * min(
            parameters["heat_availability_fraction"],
            airflow / parameters["reference_airflow_m3_s"],
            1.0,
        )

    @staticmethod
    def drying_limit(parameters, airflow, moisture, hours):
        target = parameters["target_moisture_fraction"]
        water_removed_per_tonne = max(0.0, (moisture - target) / (1 - target))
        if water_removed_per_tonne == 0:
            return float("inf")
        evaporation_tph = DryerMill.evaporation_limit(parameters, airflow)
        return evaporation_tph * hours / water_removed_per_tonne

    @staticmethod
    def dry(material, parameters):
        target = parameters["target_moisture_fraction"]
        water = min(material.water, material.dry * target / (1 - target))
        return Material(material.dry, water)


class Separator(Throughput):
    @staticmethod
    def circulating_flow(fines, parameters):
        fraction = parameters["fines_fraction"]
        total = fines / fraction
        return total, total - fines


IMPLEMENTATIONS = {
    "rotor_crusher": Throughput,
    "storage": Storage,
    "throughput": Throughput,
    "fan": Fan,
    "dryer_mill": DryerMill,
    "separator": Separator,
}
