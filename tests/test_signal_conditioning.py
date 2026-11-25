import math
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from factory_sim.core.config import load_plant, load_scenario, read_json
from factory_sim.core.engine import simulate
from factory_sim.core.signal_conditioning import alarm_value, conditioned_value
from factory_sim.core.telemetry import load_tag_config, public_frames
from factory_sim.server import CONFIGS, SCENARIOS
from solver_fingerprint import solver_fingerprints


class SignalConditioningTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plant, cls.assets = load_plant(CONFIGS / "model_types", CONFIGS / "plants/bulk_material_line.json")
        cls.catalog = load_tag_config(CONFIGS / "model_types", cls.assets, cls.plant)
        cls.settings = cls.catalog["signal_conditioning"]
        cls.tags = {tag["tag_id"]: tag for tag in cls.catalog["tags"]}

    def solve(self, name="baseline", plant=None, events=None):
        scenario = load_scenario(CONFIGS / "scenarios" / f"{name}.json", self.assets)
        if events is not None:
            scenario["events"] = events
        return list(simulate(plant or self.plant, self.assets, scenario))

    def project(self, frames, plant=None, tags=None, **overrides):
        return list(public_frames(frames, tags or self.catalog["tags"], plant or self.plant, self.assets,
                                  signal_conditioning={**self.settings, **overrides}))

    @staticmethod
    def reading(frame, tag_id, channel="measurements"):
        return frame[channel][tag_id.split(".", 1)[0]][tag_id]

    def test_catalog_has_no_continuous_dry_meal_moisture_or_free_lime(self):
        for tag in self.tags.values():
            source = str(tag["source"])
            if "free_lime" in tag["tag_id"] or "free_lime" in source:
                self.assertEqual(tag["channel"], "lab")
            if "moisture" in tag["tag_id"] or "moisture" in source:
                self.assertEqual(tag["channel"], "lab")
        self.assertIn("RM-201.gas_outlet_temperature_c", self.tags)

    def test_solver_material_and_thermal_fingerprints_and_bypass_gate_for_65_cases(self):
        expected = read_json(Path(__file__).with_name("phase_b_solver_fingerprints.json"))
        self.assertEqual(set(expected), set(SCENARIOS))
        for name in SCENARIOS:
            with self.subTest(scenario=name):
                frames = self.solve(name)
                self.assertEqual(solver_fingerprints(frames), expected[name])
                for frame in frames:
                    eq = frame["equipment"]
                    if eq["drying_mill"]["bypass_position_fraction"]:
                        self.assertGreater(eq["rotary_kiln"]["inlet_tph"], 0)

    def test_seed_and_projection_switch_keep_solver_invariant(self):
        frames = self.solve()
        truth = solver_fingerprints(frames)
        enabled = self.project(frames)
        self.assertEqual(enabled, self.project(frames))
        self.assertNotEqual(enabled, self.project(frames, seed=self.settings["seed"] + 1))
        self.assertNotEqual(enabled, self.project(frames, noise_enabled=False))
        self.assertEqual(truth, solver_fingerprints(frames))
        off = load_tag_config(CONFIGS / "model_types", self.assets, self.plant, conditioning_enabled=False)
        expected = list(public_frames(frames, off["tags"], self.plant, self.assets))
        self.assertEqual(self.project(frames, tags=off["tags"], enabled=False), expected)
        for frame in expected:
            self.assertNotIn("alarms", frame)
            self.assertNotIn("SL-301.level_high_switch", frame["measurements"]["SL-301"])

    def test_first_order_and_saturation_quantization_transport_and_sampling(self):
        for tag_id in ("PH-301.cyclone_1.gas_temperature_c", "PH-301.cyclone_1.gauge_pressure_pa"):
            tag = deepcopy(self.tags[tag_id])
            cfg = tag["conditioning"]
            cfg["sample_period_s"] = 0
            state = {}
            conditioned_value(-50, tag, state, 1, 1, 0, False)
            conditioned_value(50, tag, state, 2, 1, 0, False)
            value = state["filtered"]
            tau = -1 / math.log((50 - value) / 100)
            self.assertAlmostEqual(tau, cfg["time_constant_s"])
        raw = deepcopy(self.tags["RM-201.gas_outlet_temperature_c"])
        raw["conditioning"].update(time_constant_s=0, transport_delay_s=2, sample_period_s=2)
        state = {}
        readings = [conditioned_value(v, raw, state, t, 1, 0, False)
                    for t, v in enumerate([-10, 123.46, 123.46, 123.46, 600, 600, 600], 1)]
        self.assertEqual(readings, [0, 0, 123.5, 123.5, 123.5, 123.5, raw["conditioning"]["range_max"]])

    def test_debounce_deadband_and_mode_mask(self):
        tag = self.tags["KF-301.run_feedback"]
        instrument = {}
        readings = [conditioned_value(raw, tag, instrument, t, 1, 0, False)
                    for t, raw in enumerate([True, False, False, False, True], 1)]
        self.assertEqual(readings, [True, True, True, False, True])
        rule = {"severity": "L", "by_mode": {"RUNNING": 100, "STARTING": 80}, "deadband": 5,
                "debounce_on_s": 2, "debounce_off_s": 2}
        alarm = {}
        self.assertFalse(alarm_value(90, rule, alarm, "STARTING", 1, 1))
        self.assertFalse(alarm_value(90, rule, alarm, "RUNNING", 2, 1))
        self.assertTrue(alarm_value(90, rule, alarm, "RUNNING", 3, 1))
        self.assertTrue(alarm_value(103, rule, alarm, "RUNNING", 4, 1))
        self.assertTrue(alarm_value(107, rule, alarm, "RUNNING", 5, 1))
        self.assertFalse(alarm_value(107, rule, alarm, "RUNNING", 6, 1))
        self.assertFalse(alarm_value(50, rule, alarm, "STOPPED", 7, 1))

    def test_trip_response_order_and_restart_alarm_mask(self):
        plant = {**self.plant, "step_s": 1}
        for scenario, current, run, temp in (
            ("kiln_id_fan_trip", "CF-301.fan_drive.current_a", "CF-301.run_feedback", "PH-301.cyclone_1.gas_temperature_c"),
            ("cement_separator_a_trip", "CM-401A.drive.current_a", "CM-401A.run_feedback", None),
            ("bag_packer_jam", "PK-501.bags_per_min", "PK-501.run_feedback", None),
        ):
            config = load_scenario(CONFIGS / "scenarios" / f"{scenario}.json", self.assets)
            config.update(duration_s=100)
            config["events"][0]["at_s"] = 70
            public = self.project(simulate(plant, self.assets, config), plant=plant, noise_enabled=False)
            first, third = public[70], public[72]
            self.assertTrue(self.reading(first, run))
            self.assertFalse(self.reading(third, run))
            if current.endswith("current_a"):
                self.assertLess(self.reading(first, current), 1)
                self.assertEqual(self.reading(third, current), 0)
                noisy = self.project(simulate(plant, self.assets, config), plant=plant, noise_enabled=True)
                self.assertEqual(self.reading(noisy[72], current), 0)
            else:
                self.assertGreater(self.reading(first, current), 0)
                self.assertGreater(self.reading(third, current), 0)
            if temp:
                self.assertGreater(self.reading(third, temp), 780)

        target = "drying_mill.hydraulic_unit.pressure_loss"
        events = [{"at_s": 600, "target": target, "value": 1},
                  {"at_s": 900, "target": target, "value": 0, "clear": True}]
        frames = self.solve(events=events)
        readings = self.project(frames)
        tag = "RM-201.gas_inlet_temperature_c.alarm_L"
        for physical, measured in zip(frames[10:15], readings[10:15], strict=True):
            self.assertEqual(physical["equipment"]["drying_mill"]["operating_state"], "TRIPPED")
            self.assertFalse(self.reading(measured, tag, "alarms"))
        self.assertTrue(any(self.reading(frame, "RM-201.run_feedback") for frame in readings[15:]))

    def test_level_mass_temperature_and_lab_schedule(self):
        baseline = self.solve()
        published = self.project(baseline)
        for before, after, frame in zip(baseline, baseline[1:], published[1:]):
            old, new = (f["equipment"]["product_silo"] for f in (before, after))
            self.assertAlmostEqual(new["inventory_t"] - old["inventory_t"],
                                   (new["inlet_tph"] - new["outlet_tph"]) / 60)
            level = self.reading(frame, "SL-301.level_sensor.measured_level_fraction")
            self.assertLessEqual(abs(level - 100 * new["level_fraction"]), 1.2)
            temperatures = [self.reading(frame, f"PH-301.cyclone_{i}.gas_temperature_c") for i in range(1, 5)]
            self.assertTrue(all(a > b for a, b in zip(temperatures, temperatures[1:])))
        manual = deepcopy(self.plant)
        manual["thermal_coupling"]["lab"]["analysis_type"] = "manual_hourly"
        samples = self.solve(plant=manual)
        reports = [sample for f in samples for sample in f.get("lab", {}).get("clinker_cooler", {}).get("free_lime_pct", [])]
        self.assertEqual([(r["sampled_at_s"], r["reported_at_s"]) for r in reports], [(3600, 5400)])
