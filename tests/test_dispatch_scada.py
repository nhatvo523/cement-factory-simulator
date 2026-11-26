import unittest
from itertools import chain, repeat
from pathlib import Path
from unittest.mock import patch

from factory_sim.core.config import load_plant, load_scenario, read_json
from factory_sim.core.engine import simulate
from factory_sim.core.telemetry import load_tag_config, public_frames
from factory_sim.server import AVAILABLE_SCENARIOS, CONFIGS, DISPATCH_SCENARIOS, EFFICIENCY_SCENARIOS, SCENARIOS, LiveOperation
from solver_fingerprint import release_stockpile_assets, solver_fingerprints


class DispatchScadaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plant, cls.assets = load_plant(CONFIGS / "model_types", CONFIGS / "plants/bulk_material_line.json")
        cls.catalog = load_tag_config(CONFIGS / "model_types", cls.assets, cls.plant)

    def raw(self, name, step=60, duration=5400):
        scenario = load_scenario(CONFIGS / "scenarios" / f"{name}.json", self.assets)
        return list(simulate({**self.plant, "step_s": step}, self.assets, {**scenario, "duration_s": duration}))

    def project(self, frames, **settings):
        return list(public_frames(frames, self.catalog["tags"], self.plant, self.assets,
                                  signal_conditioning={**self.catalog["signal_conditioning"], **settings}))

    @staticmethod
    def read(frame, tag):
        return frame["measurements"][tag.split(".", 1)[0]][tag]

    def test_slip_ramp_has_its_own_fingerprints_and_correlated_signals(self):
        name, = DISPATCH_SCENARIOS
        self.assertEqual(len(set(AVAILABLE_SCENARIOS)), 68)
        self.assertNotIn(name, SCENARIOS + EFFICIENCY_SCENARIOS)
        raw = self.raw(name)
        fixture = read_json(Path(__file__).with_name("z04_dispatch_fingerprints.json"))
        assets = release_stockpile_assets(self.assets)
        scenario = load_scenario(CONFIGS / "scenarios" / f"{name}.json", assets)
        self.assertEqual(solver_fingerprints(simulate(self.plant, assets, scenario)), fixture[name])
        frames = self.project(raw, noise_enabled=False)
        phases = frames[10:14]
        flows = [row["equipment"]["BC-501"]["outlet_tph"] for row in raw[10:14]]
        self.assertTrue(all(33.5 <= flow <= 34.5 for flow in flows[:2]))
        self.assertEqual(flows[2:], [32, 28])
        speeds = [self.read(frame, "BC-501.belt.speed_m_s") for frame in phases]
        self.assertTrue(all(a > b for a, b in zip(speeds, speeds[1:])))
        self.assertAlmostEqual(speeds[-1], .525, delta=.01)
        for frame in phases:
            self.assertEqual(self.read(frame, "BC-501.drive_pulley.speed_m_s"), .75)
            self.assertTrue(self.read(frame, "BC-501.run_feedback"))
            self.assertFalse(self.read(frame, "BC-501.trip_feedback"))
        for tag in ("BC-501.drive.current_a", "BC-501.bearing.vibration_mm_s", "BC-501.bearing.temperature_c"):
            self.assertGreater(self.read(phases[-1], tag), self.read(phases[0], tag))
        self.assertTrue(phases[-1]["alarms"]["BC-501"]["BC-501.belt.speed_m_s.alarm_L"])

    def test_live_ramp_waits_for_relative_offsets(self):
        with patch("factory_sim.server.monotonic", return_value=100) as clock:
            live = LiveOperation()
            live.read(list(DISPATCH_SCENARIOS))
            for elapsed, expected in ((2, None), (62, .1), (122, .2), (182, .3)):
                clock.return_value = 100 + elapsed
                live.read([])
                observed = live.frame["equipment"]["BC-501"].get("active_faults", [])
                self.assertEqual(observed[0]["severity"] if observed else None, expected)

    def test_packer_jam_stops_new_bags_and_lets_existing_measurement_pulses_arrive(self):
        raw = self.raw("bag_packer_jam", step=1, duration=650)
        frames = self.project(raw, noise_enabled=False)
        before, first, settled = (frames[i] for i in (599, 600, 624))
        self.assertTrue(self.read(first, "PK-501.fault_feedback"))
        self.assertLess(self.read(first, "PK-501.rotor_drive.current_a"), self.read(before, "PK-501.rotor_drive.current_a"))
        self.assertEqual(self.read(settled, "PK-501.rotor_drive.current_a"), 0)
        self.assertEqual(self.read(settled, "PK-501.bags_count"), self.read(before, "PK-501.bags_count"))
        self.assertLess(self.read(first, "BC-501.discharge.bags_count"), self.read(settled, "BC-501.discharge.bags_count"))
        self.assertEqual(self.read(settled, "BC-501.discharge.bags_count"), self.read(settled, "PK-501.bags_count"))
        self.assertEqual(self.read(settled, "PK-501.checkweigher.bag_weight_kg"), 50)
        self.assertGreater(raw[624]["equipment"]["SL-401"]["grades"]["A"], raw[599]["equipment"]["SL-401"]["grades"]["A"])

    def test_checkweigher_alarms_on_average_not_single_bag(self):
        raw = self.raw("baseline", step=1, duration=180)
        tag = "PK-501.checkweigher.bag_weight_kg"
        alarm = tag + ".alarm_H"
        with patch("factory_sim.core.telemetry.Random") as rng:
            rng.return_value.gauss.side_effect = chain([4], repeat(0, 9), repeat(.7))
            frames = self.project(raw)
        self.assertTrue(any(self.read(frame, tag) == 54 for frame in frames))
        self.assertFalse(any(frame["alarms"]["PK-501"][alarm] for frame in frames[:60]))
        self.assertTrue(frames[-1]["alarms"]["PK-501"][alarm])
        self.assertEqual(self.project(raw), self.project(raw))
