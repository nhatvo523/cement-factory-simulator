"""Reduced kiln–raw mill heat balance and clinker quality for the material solver."""

from collections import deque
from math import expm1

from factory_sim.equipment import DryerMill, Material


def approach(value, target, step_s, time_constant_s):
    return value + (target - value) * -expm1(-step_s / time_constant_s)


class KilnRawMillCoupling:
    def __init__(self, config, step_s):
        self.config = config
        self.step_s = step_s
        self.kiln = config["assets"]["kiln"]
        self.cooler = config["assets"]["cooler"]
        self.preheater = config["assets"]["preheater"]
        self.draft_fan = config["assets"]["draft_fan"]
        self.mill = config["assets"]["mill"]
        self.meal_silo = config["assets"]["meal_silo"]
        self.clinker_silo = config["assets"]["clinker_silo"]
        self.mode = "DRYING"
        self.bypass = 0.0
        self.stable_s = 0
        self.stopped_s = 0
        self.was_running = True
        self.burning_c = config["kiln"]["nominal_burning_c"]
        self.exhaust_c = config["drying"]["nominal_exhaust_c"]
        self.recovered_kw = None
        self.ramp_tph = None
        self.silo_free_lime_pct = config["kiln"]["nominal_free_lime_pct"]
        self.lab_queue = deque()
        lab = config["lab"]
        self.lab_schedule = lab["profiles"][lab["analysis_type"]]
        self.next_sample_s = self.lab_schedule["sample_interval_s"]

    def route_gas(self, ready, kiln_running):
        gas = self.config["gas_route"]
        if not kiln_running:
            self.mode = "NO_KILN_GAS"
            self.bypass = 0
            self.stable_s = self.stopped_s = 0
            return 1.0, 1.0
        if self.mode == "NO_KILN_GAS":
            self.mode = "DRYING"
        warm = min(self.exhaust_c, self.config["drying"]["backup_air_c"]) >= gas["return_hot_c"]
        cold = self.exhaust_c <= gas["dropout_c"]
        self.stopped_s = 0 if self.was_running else self.stopped_s + self.step_s
        stopped = not ready or self.stopped_s >= gas["stop_confirm_s"]
        if self.mode in {"DRYING", "TO_DRYING"} and (stopped or
                (self.mode == "TO_DRYING" and cold)):
            self.mode = "TO_BYPASS"
            self.stable_s = 0
            self.ramp_tph = gas["pilot_feed_tph"]
        if self.mode == "BYPASS":
            self.stable_s = self.stable_s + self.step_s if ready and self.was_running and warm else 0
            if self.stable_s >= gas["stable_run_s"]:
                self.mode = "TO_DRYING"
        travel = self.step_s / gas["damper_travel_s"]
        if self.mode == "TO_BYPASS":
            self.bypass = min(1.0, self.bypass + travel)
            if self.bypass == 1:
                self.mode = "BYPASS"
        elif self.mode == "TO_DRYING":
            self.bypass = max(0.0, self.bypass - travel)
            if self.bypass == 0:
                self.mode = "DRYING"
        if self.mode in {"TO_DRYING", "DRYING"} and self.ramp_tph is not None:
            self.ramp_tph += self.step_s * gas["restart_ramp_tph_per_s"]
        flow_factor = 1 + self.bypass * (gas["bypass_airflow_factor"] - 1)
        pressure_factor = 1 + self.bypass * (gas["bypass_pressure_factor"] - 1)
        return flow_factor, pressure_factor

    def prepare_drying(self, airflow, parameters, mill_running):
        cfg = self.config["drying"]
        ambient = self.config["ambient_c"]
        nominal_kw = parameters["evaporation_capacity_tph"] * cfg["water_evaporation_kwh_per_t"]
        backup_kw = nominal_kw * parameters["backup_heat_fraction"]
        self.nominal_recovered_kw = max(0, nominal_kw - backup_kw)
        # Effective heat held in the duct/mill decays after the hot gas supply is lost.
        routed_kw = (airflow * max(0, self.exhaust_c - ambient) * cfg["gas_heat_capacity_kw_per_m3_s_c"]
                     * (1 - self.bypass))
        if not mill_running:
            routed_kw = 0
        if self.recovered_kw is None:
            self.recovered_kw = routed_kw
        else:
            self.recovered_kw = approach(self.recovered_kw, routed_kw, self.step_s, cfg["heat_hold_time_s"])
        available_kw = backup_kw + self.recovered_kw
        nominal_fraction = available_kw / nominal_kw if nominal_kw else 0
        return {**parameters, "heat_availability_fraction":
                min(parameters["heat_availability_fraction"], nominal_fraction, 1.0)}

    def dryer_feed(self, dry_limit, hours, airflow):
        """Feed up to the stable minimum in deep heat deficit, subject to real availability."""
        cfg = self.config["drying"]
        feed_limit = max(dry_limit, cfg["minimum_stable_feed_tph"] * hours) if airflow > 0 else 0
        if self.ramp_tph is not None:
            feed_limit = min(feed_limit, self.ramp_tph * hours)
        return feed_limit

    @staticmethod
    def dried_unit(unit, amount, hours, airflow, parameters):
        target = DryerMill.dry(unit, parameters)
        if not amount:
            return target
        evaporation = DryerMill.evaporation_limit(parameters, airflow) * hours / amount
        return Material(unit.dry, max(target.water, unit.water - evaporation))

    def finish(self, data, opening, inflow, outflow, specific_fuel, time_s):
        ambient = self.config["ambient_c"]
        cfg = self.config["kiln"]
        kiln = data[self.kiln]
        mill = data[self.mill]
        load = kiln["inlet_tph"] / cfg["reference_feed_tph"]
        recovered_kw = data[self.cooler]["recovered_heat_kw"]
        secondary = recovered_kw * cfg["secondary_heat_share"] / cfg["reference_recovered_kw"]
        tertiary = recovered_kw * (1 - cfg["secondary_heat_share"]) / cfg["reference_recovered_kw"]
        target = (cfg["nominal_burning_c"] + cfg["fuel_gain_c"] * (specific_fuel / cfg["reference_fuel_per_feed"] - 1)
                  + cfg["secondary_heat_gain_c"] * (secondary - cfg["secondary_heat_share"])
                  + cfg["tertiary_heat_gain_c"] * (tertiary - (1 - cfg["secondary_heat_share"]))
                  - cfg["load_gain_c"] * (load - 1)) if load else ambient
        self.burning_c = approach(self.burning_c, max(ambient, target), self.step_s, cfg["burning_time_s"])
        drying = self.config["drying"]
        exhaust_target = ambient + (drying["nominal_exhaust_c"] - ambient) * (
            min(1.0, max(0.0, (self.burning_c - ambient) / (cfg["nominal_burning_c"] - ambient))))
        self.exhaust_c = approach(self.exhaust_c, exhaust_target, self.step_s, drying["exhaust_time_s"])

        residence = cfg["reference_residence_s"] / max(load, cfg["minimum_residence_load"]) if load else None
        clinker = inflow[self.clinker_silo].dry
        free_lime = None
        if clinker and residence is not None:
            free_lime = min(cfg["maximum_free_lime_pct"], max(cfg["minimum_free_lime_pct"],
                            cfg["nominal_free_lime_pct"] +
                            cfg["free_lime_per_degree"] * (cfg["nominal_burning_c"] - self.burning_c) +
                            cfg["free_lime_residence_gain_pct"] * (cfg["reference_residence_s"] / residence - 1)))
        kiln.update(burning_zone_internal_c=self.burning_c, clinker_residence_s=residence,
                    clinker_free_lime_pct=free_lime)
        kiln["components"]["burning_zone"]["temperature_c"] = self.burning_c
        data[self.cooler]["clinker_free_lime_pct"] = free_lime
        remaining = max(0, opening[self.clinker_silo].dry - outflow[self.clinker_silo].dry)
        actual_stock = remaining + clinker
        data[self.clinker_silo]["outlet_clinker_free_lime_pct"] = (
            self.silo_free_lime_pct if outflow[self.clinker_silo].dry else None)
        if clinker and free_lime is not None:
            # Well-mixed outgoing clinker carries the opening concentration. Incoming quality is blended by dry mass.
            self.silo_free_lime_pct += clinker / actual_stock * (free_lime - self.silo_free_lime_pct)
        data[self.clinker_silo]["stock_free_lime_pct"] = self.silo_free_lime_pct if actual_stock else None
        cyclone_factor = 1 + self.bypass * (self.config["gas_route"]["cyclone_bypass_pressure_factor"] - 1)
        data[self.preheater].update(top_exhaust_internal_c=self.exhaust_c, gas_pressure_factor=cyclone_factor)
        self.was_running = mill["operating_state"] == "RUNNING"
        if self.mode == "DRYING" and self.ramp_tph is not None and self.ramp_tph >= self.config["gas_route"]["full_feed_tph"]:
            self.ramp_tph = None
        wet = bool(mill["outlet_moisture_fraction"] is not None and
                   mill["outlet_moisture_fraction"] > drying["wet_threshold_fraction"])
        meal_moisture = data[self.meal_silo]["inventory_moisture_fraction"]
        data[self.meal_silo]["wet_meal"] = meal_moisture is not None and meal_moisture > drying["wet_threshold_fraction"]
        recovered_ratio = min(1, self.recovered_kw / self.nominal_recovered_kw) if self.nominal_recovered_kw else 0
        gas_in = (drying["backup_air_c"] +
                  (drying["nominal_exhaust_c"] - drying["backup_air_c"]) * recovered_ratio
                  if self.was_running else None)
        gas_out = (max(ambient, gas_in - mill["evaporated_water_tph"] * drying["outlet_drop_c_per_tph"])
                   if gas_in is not None else None)
        mill.update(gas_mode=self.mode, bypass_position_fraction=self.bypass, wet_meal=wet,
                    recovered_drying_heat_kw=self.recovered_kw, restart_feed_limit_tph=self.ramp_tph,
                    gas_inlet_temperature_c=gas_in, gas_outlet_temperature_c=gas_out)
        return self.lab_results(time_s, free_lime)

    def lab_results(self, time_s, free_lime):
        cfg = self.lab_schedule
        if time_s >= self.next_sample_s:
            self.next_sample_s += ((time_s - self.next_sample_s) // cfg["sample_interval_s"] + 1) * cfg["sample_interval_s"]
            if free_lime is not None:
                self.lab_queue.append((time_s, free_lime))
        results = {}
        while self.lab_queue and self.lab_queue[0][0] + cfg["report_delay_s"] <= time_s:
            taken, value = self.lab_queue.popleft()
            results.setdefault(self.cooler, {}).setdefault("free_lime_pct", []).append(
                {"sampled_at_s": taken, "reported_at_s": time_s, "value": value})
        return results
