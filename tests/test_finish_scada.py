import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from factory_sim.core.config import load_plant, load_scenario, read_json
from factory_sim.core.engine import simulate
from factory_sim.core.signal_conditioning import conditioned_value
from factory_sim.core.telemetry import electrical_power, load_tag_config, public_frames
from factory_sim.server import CONFIGS, EFFICIENCY_SCENARIOS, ExplorerHandler, LiveOperation, SCENARIOS
from solver_fingerprint import solver_fingerprints


class FinishScadaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plant, cls.assets = load_plant(CONFIGS / "model_types", CONFIGS / "plants/bulk_material_line.json")
        cls.catalog = load_tag_config(CONFIGS / "model_types", cls.assets, cls.plant)

    def raw(self, name="baseline", events=None):
        scenario = load_scenario(CONFIGS / "scenarios" / f"{name}.json", self.assets)
        if events is not None:
            scenario["events"] = events
        return list(simulate(self.plant, self.assets, scenario))

    def project(self, frames, **settings):
        return list(public_frames(frames, self.catalog["tags"], self.plant, self.assets,
                                  signal_conditioning={**self.catalog["signal_conditioning"], **settings}))

    @staticmethod
    def reading(frame, tag):
        return frame["measurements"][tag.split(".")[0]][tag]

    def test_efficiency_ramps_have_separate_fingerprints_and_coordinated_readings(self):
        hashes = read_json(Path(__file__).with_name("z03_efficiency_loss_fingerprints.json"))
        self.assertFalse(set(SCENARIOS) & hashes.keys())
        api = ExplorerHandler.__new__(ExplorerHandler)
        for side, name in zip("AB", EFFICIENCY_SCENARIOS, strict=True):
            with self.subTest(side=side):
                raw = self.raw(name)
                self.assertEqual(solver_fingerprints(raw)["material"], hashes[name])
                ramp = raw[10:19]
                separator = f"SP-401{side}"
                measured = self.project(raw, noise_enabled=False)[10:19]
                outputs = [frame["equipment"][separator] for frame in ramp]
                self.assertEqual(len({row["fines_fraction"] for row in outputs}), 9)
                self.assertGreater(outputs[-1]["recycle_tph"], outputs[0]["recycle_tph"] + 5)
                for tag in (f"{separator}.separator_drive.current_a", f"{separator}.separator.differential_pressure_pa",
                            f"CM-401{side}.drive.current_a", f"CM-401{side}.drive.power_kw"):
                    values = [self.reading(frame, tag) for frame in measured]
                    self.assertGreater(values[-1], values[0])
                    self.assertGreaterEqual(len(set(values)), 6)
                for frame in measured:
                    self.assertTrue(self.reading(frame, f"{separator}.run_feedback"))
                    self.assertFalse(self.reading(frame, f"{separator}.trip_feedback"))
                events = api.operation({"fault": [name + "@1200"]}, True)["frames"]
                times = [event["at_s"] for frame in events for event in frame["ground_truth"]["events"]]
                self.assertEqual(times, list(range(1200, 1681, 60)))

    def test_live_injection_retains_offsets_and_legacy_events_start_next_tick(self):
        with patch("factory_sim.server.monotonic", return_value=100) as clock:
            op = LiveOperation()
            op.read([EFFICIENCY_SCENARIOS[0], "cement_separator_b_trip"])
            clock.return_value = 101
            op.read([])
            first = op.frame["events"]
            self.assertEqual([event["at_s"] for event in first], [1, 1])
            self.assertEqual(op.frame["equipment"]["SP-401A"]["fines_fraction"], 0.58)
            clock.return_value = 159
            op.read([])
            self.assertEqual(op.frame["equipment"]["SP-401A"]["fines_fraction"], 0.58)
            clock.return_value = 161
            op.read([])
            self.assertEqual(op.frame["events"][0]["at_s"], 61)
            self.assertEqual(op.frame["equipment"]["SP-401A"]["fines_fraction"], 0.57)

    def test_trip_preserves_residual_temperature_and_oil_while_rotor_current_falls(self):
        for side in "AB":
            raw = self.raw(f"cement_separator_{side.lower()}_trip")
            frames = self.project(raw, noise_enabled=False)
            before, after, later = frames[9:12]
            sp, cm = f"SP-401{side}", f"CM-401{side}"
            self.assertEqual(self.reading(after, sp + ".separator_drive.current_a"), 0)
            self.assertTrue(self.reading(after, sp + ".trip_feedback"))
            self.assertGreater(self.reading(after, sp + ".separator.differential_pressure_pa"), 0)
            self.assertEqual(self.reading(after, cm + ".drive.power_kw"), 0)
            for tag in (cm + ".outlet.gas_temperature_c", cm + ".lubrication.pressure_bar"):
                self.assertGreater(self.reading(before, tag), self.reading(after, tag))
                self.assertGreater(self.reading(after, tag), self.reading(later, tag))

    def test_blaine_underspeed_lowers_lab_result_and_efficiency_loss_preserves_it(self):
        def samples(frames):
            return {row["sampled_at_s"]: row["value"] for frame in frames
                    for row in frame.get("lab", {}).get("SP-401A", {}).get("SP-401A.lab.blaine_m2_kg", [])}

        baseline = self.project(self.raw())
        underspeed = self.project(self.raw(events=[
            {"at_s": 600, "target": "SP-401A.separator_drive.underspeed", "value": .25},
        ]))
        degrade = self.project(self.raw(EFFICIENCY_SCENARIOS[0]))
        self.assertAlmostEqual(samples(baseline)[1200] - samples(underspeed)[1200], 30, delta=.11)
        self.assertEqual(samples(baseline)[1200], samples(degrade)[1200])
        first = baseline[14]["lab"]["SP-401A"]["SP-401A.lab.blaine_m2_kg"][0]
        self.assertEqual((first["sampled_at_s"], first["reported_at_s"]), (600, 900))
        self.assertNotIn("SP-401A.lab.blaine_m2_kg", baseline[14]["measurements"]["SP-401A"])
        manual = deepcopy(self.catalog["tags"])
        for tag in manual:
            if "lab_schedule" in tag:
                tag["lab_schedule"] = {"sample_interval_s": 3600, "report_delay_s": 1800}
        reports = list(public_frames(self.raw(), manual, self.plant, self.assets))
        self.assertEqual(list(samples(reports)), [3600])

    def test_power_factor_and_per_tag_noise(self):
        raw = self.raw()
        model = next(t["source"]["electric_power"] for t in self.catalog["tags"]
                     if t["tag_id"] == "CM-401A.drive.power_kw")
        self.assertGreater(electrical_power(160, model) / 160, electrical_power(80, model) / 80)
        noisy = self.project(raw)
        self.assertEqual(noisy, self.project(raw))
        self.assertNotEqual(noisy, self.project(raw, seed=10))
        i_id, kw_id = "CM-401A.drive.current_a", "CM-401A.drive.power_kw"
        states = []
        for tag_id in (i_id, kw_id):
            tag = next(tag for tag in self.catalog["tags"] if tag["tag_id"] == tag_id)
            state = {}
            conditioned_value(tag["normal"], tag, state, 1, 1, 70521, True)
            states.append(state["rng"].getstate())
        self.assertNotEqual(*states)

    def test_mill_gas_temperature_reaches_warning_for_sustained_low_airflow(self):
        full = self.project(self.raw(), noise_enabled=False)
        self.assertTrue(all(abs(self.reading(frame, "CM-401A.outlet.gas_temperature_c") - 95) < 5
                            for frame in full[4:12]))
        derated = self.project(self.raw(events=[
            {"at_s": 600, "target": "FN-401A.impeller.degradation", "value": .55},
        ]), noise_enabled=False)
        alarm = "CM-401A.outlet.gas_temperature_c.alarm_H"
        self.assertFalse(derated[9]["alarms"]["CM-401A"][alarm])
        self.assertTrue(any(frame["alarms"]["CM-401A"][alarm] for frame in derated[10:28]))
