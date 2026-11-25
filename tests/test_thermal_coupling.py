import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from factory_sim.core.config import load_plant, load_scenario
from factory_sim.core.engine import simulate
from factory_sim.core.telemetry import load_tag_config, public_frames
from factory_sim.server import CONFIGS, LiveOperation
from factory_sim.thermal_coupling import KilnRawMillCoupling


class ThermalCouplingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plant, cls.assets = load_plant(CONFIGS / "model_types", CONFIGS / "plants/bulk_material_line.json")
        cls.config = cls.plant["thermal_coupling"]
        cls.tags = load_tag_config(CONFIGS / "model_types", cls.assets, cls.plant)["tags"]

    def scenario(self, name="baseline"):
        return load_scenario(CONFIGS / "scenarios" / f"{name}.json", self.assets)

    def run_frames(self, name="baseline", **overrides):
        return list(simulate(self.plant, self.assets, {**self.scenario(name), **overrides}))

    def test_nominal_operating_baseline_within_configured_tolerance(self):
        phase_a = deepcopy(self.plant)
        phase_a["thermal_coupling"]["enabled"] = False
        self.assertTrue(self.config["enabled"])
        tolerance = self.config["baseline_tolerance"]
        limits = {"inventory_t": "mass_t", "inlet_tph": "flow_tph", "outlet_tph": "flow_tph",
                  "fresh_inlet_tph": "flow_tph", "airflow_m3_s": "airflow_m3_s",
                  "evaporation_limit_tph": "flow_tph", "evaporated_water_tph": "flow_tph",
                  "inventory_moisture_fraction": "moisture_fraction",
                  "outlet_moisture_fraction": "moisture_fraction"}
        for before, after in zip(simulate(phase_a, self.assets, self.scenario()), self.run_frames(), strict=True):
            for asset, signals in before["equipment"].items():
                actual = after["equipment"][asset]
                for key, rule in limits.items():
                    if key not in signals:
                        continue
                    if signals[key] is None:
                        self.assertIsNone(actual[key])
                    else:
                        allowed = tolerance[rule] + abs(signals[key]) * tolerance["relative"]
                        self.assertLessEqual(abs(signals[key] - actual[key]), allowed, (before["time_s"], asset, key))
                self.assertEqual(actual.get("operating_state"), signals.get("operating_state"))
                self.assertEqual(actual.get("trip_reason"), signals.get("trip_reason"))

    def test_draft_trip_keeps_residual_heat_then_limits_raw_mill_feed(self):
        previous, first, second = [frame["equipment"] for frame in self.run_frames("kiln_id_fan_trip")[9:12]]
        self.assertEqual(first["kiln_id_fan"]["airflow_m3_s"], 0)
        self.assertEqual(first["downstream_feeder"]["outlet_tph"], 0)
        for asset, key in (("rotary_kiln", "burning_zone_internal_c"),
                           ("preheater", "top_exhaust_internal_c"),
                           ("drying_mill", "recovered_drying_heat_kw"),
                           ("drying_mill", "fresh_inlet_tph")):
            self.assertGreater(previous[asset][key], first[asset][key])
            self.assertGreater(first[asset][key], second[asset][key])
            self.assertGreater(second[asset][key], 0)
        self.assertGreater(first["product_silo"]["inventory_t"], previous["product_silo"]["inventory_t"])
        self.assertGreater(second["product_silo"]["inventory_t"], first["product_silo"]["inventory_t"])
        self.assertAlmostEqual(second["drying_mill"]["outlet_moisture_fraction"], 0.005)
        self.assertFalse(second["product_silo"]["wet_meal"])

    def test_deep_heat_shortage_runs_at_floor_and_marks_wet_meal(self):
        events = [{"at_s": 600, "target": "drying_mill.heat_availability_fraction", "value": 0.15}]
        normal, shortage = self.run_frames(events=events)[9:11]
        mill = shortage["equipment"]["drying_mill"]
        self.assertAlmostEqual(mill["fresh_inlet_tph"], self.config["drying"]["minimum_stable_feed_tph"])
        self.assertGreater(mill["outlet_moisture_fraction"], 0.005)
        self.assertTrue(mill["wet_meal"])
        self.assertTrue(shortage["equipment"]["separator"]["wet_meal"])
        stock = shortage["equipment"]["product_silo"]
        self.assertTrue(stock["wet_meal"])
        self.assertGreater(stock["inventory_moisture_fraction"],
                           normal["equipment"]["product_silo"]["inventory_moisture_fraction"])
        self.assertAlmostEqual(shortage["balance"]["water_residual_t"], 0)

    def test_raw_mill_reset_moves_damper_and_ramps_feed(self):
        target = "drying_mill.hydraulic_unit.pressure_loss"
        events = [{"at_s": 600, "target": target, "value": 1},
                  {"at_s": 900, "target": target, "value": 0, "clear": True}]
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "reset.json"
            path.write_text(json.dumps({"id": "reset", "duration_s": 1500, "events": events}), encoding="utf-8")
            load_scenario(path, self.assets)
        frames = self.run_frames(events=events)
        mill = [frame["equipment"]["drying_mill"] for frame in frames]
        self.assertEqual([data["gas_mode"] for data in mill[9:12]], ["DRYING", "TO_BYPASS", "BYPASS"])
        self.assertGreater(mill[10]["bypass_position_fraction"], 0)
        self.assertLess(mill[10]["bypass_position_fraction"], 1)
        self.assertGreater(frames[11]["equipment"]["kiln_id_fan"]["airflow_m3_s"],
                           frames[9]["equipment"]["kiln_id_fan"]["airflow_m3_s"])
        self.assertLess(frames[11]["equipment"]["kiln_id_fan"]["components"]["draft_sensor"]["draft_suction_pa"],
                        frames[9]["equipment"]["kiln_id_fan"]["components"]["draft_sensor"]["draft_suction_pa"])
        self.assertNotEqual(frames[11]["equipment"]["preheater"]["gas_pressure_factor"], 1)
        readings = list(public_frames(frames[:12], self.tags, self.plant, self.assets))
        for device, tag in (("PH-301", "PH-301.cyclone_4.gauge_pressure_pa"),
                            ("CF-301", "CF-301.draft_gauge_pa")):
            drying = readings[9]["measurements"][device][tag]
            bypass = readings[11]["measurements"][device][tag]
            self.assertLess(drying, bypass)
            self.assertLess(bypass, 0)
        self.assertEqual([data["gas_mode"] for data in mill[15:19]], ["BYPASS", "BYPASS", "TO_DRYING", "DRYING"])
        self.assertLess(mill[15]["fresh_inlet_tph"], mill[17]["fresh_inlet_tph"])
        self.assertLess(mill[17]["fresh_inlet_tph"], mill[18]["fresh_inlet_tph"])
        self.assertEqual({data["gas_mode"] for data in mill[18:]}, {"DRYING"})

    def test_return_hysteresis_blocks_cold_restarts_and_keeps_travel_stable(self):
        coupling = KilnRawMillCoupling(self.config, 20)
        gas = self.config["gas_route"]
        coupling.mode, coupling.bypass = "BYPASS", 1
        coupling.exhaust_c = (gas["return_hot_c"] + gas["dropout_c"]) / 2
        for _ in range(12):
            coupling.route_gas(True)
        self.assertEqual(coupling.mode, "BYPASS")
        coupling.exhaust_c = gas["return_hot_c"] + 1
        for _ in range(gas["stable_run_s"] // coupling.step_s):
            coupling.route_gas(True)
        self.assertEqual(coupling.mode, "TO_DRYING")
        coupling.exhaust_c = gas["return_hot_c"] - 1
        coupling.route_gas(True)
        self.assertEqual(coupling.mode, "TO_DRYING")
        coupling.exhaust_c = gas["dropout_c"] - 1
        coupling.route_gas(True)
        self.assertEqual(coupling.mode, "TO_BYPASS")

    def test_underfiring_raises_free_lime_and_only_reports_delayed_samples(self):
        events = [{"at_s": 600, "target": "rotary_kiln.main_burner.fuel_loss", "value": 0.45}]
        frames = self.run_frames(events=events)
        first = frames[9]["equipment"]
        later = frames[19]["equipment"]
        kiln = later["rotary_kiln"]
        self.assertLess(kiln["burning_zone_internal_c"], first["rotary_kiln"]["burning_zone_internal_c"])
        self.assertGreater(kiln["clinker_free_lime_pct"], first["rotary_kiln"]["clinker_free_lime_pct"])
        self.assertEqual(kiln["operating_state"], "RUNNING")
        self.assertLess(later["clinker_silo"]["stock_free_lime_pct"], kiln["clinker_free_lime_pct"])
        stream = list(public_frames(frames, self.tags, self.plant, self.assets))
        self.assertEqual(stream, list(public_frames(self.run_frames(events=events), self.tags, self.plant, self.assets)))
        lab_tag = "CL-301.lab.free_lime_pct"
        self.assertTrue(all(lab_tag not in frame["measurements"]["CL-301"] for frame in stream))
        reports = [sample for frame in stream for sample in frame.get("lab", {}).get("CL-301", {}).get(lab_tag, [])]
        self.assertEqual(reports[0]["sampled_at_s"], 600)
        self.assertEqual(reports[1]["sampled_at_s"], 1200)
        self.assertGreater(reports[1]["value"], reports[0]["value"])
        self.assertTrue(all(row["reported_at_s"] - row["sampled_at_s"] == self.config["lab"]["report_delay_s"]
                            for row in reports))
        self.assertNotIn("RM-201.recovered_drying_heat_kw", stream[0]["measurements"]["RM-201"])
        self.assertAlmostEqual(stream[0]["measurements"]["PH-301"]["PH-301.cyclone_4.gas_temperature_c"],
                               frames[0]["equipment"]["preheater"]["top_exhaust_internal_c"])

    def test_live_poll_collects_lab_result_even_after_reporting_tick(self):
        with patch("factory_sim.server.monotonic", return_value=100) as clock:
            operation = LiveOperation()
            clock.return_value = 1000
            frame = operation.read([])["frame"]
        report = frame["lab"]["CL-301"]["CL-301.lab.free_lime_pct"][0]
        self.assertEqual(report["reported_at_s"], 900)
        self.assertGreater(frame["time_s"], report["reported_at_s"])
