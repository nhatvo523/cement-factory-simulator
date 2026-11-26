import unittest
from math import sqrt

from factory_sim.core.config import load_plant, load_scenario
from factory_sim.core.engine import simulate
from factory_sim.core.signal_conditioning import conditioned_value
from factory_sim.core.telemetry import load_tag_config, passive_target, public_frames, read_source
from factory_sim.server import CONFIGS


class MotorPowerTest(unittest.TestCase):
    def test_zone_one_and_two_power_uses_physical_current_and_independent_noise(self):
        plant, assets = load_plant(CONFIGS / "model_types", CONFIGS / "plants/bulk_material_line.json")
        catalog = load_tag_config(CONFIGS / "model_types", assets, plant)
        tags = {tag["tag_id"]: tag for tag in catalog["tags"]}
        stems = ("CR-101.main_motor", "RM-201.main_motor", "RC-101.scraper_chain",
                 "FN-201.fan_drive", "KL-301.kiln_drive", "CF-301.fan_drive")
        scenario = load_scenario(CONFIGS / "scenarios/baseline.json", assets)
        scenario["duration_s"] = 1200
        scenario["events"] = [
            {"at_s": 600, "target": "crusher.rotor.jam", "value": 1},
            {"at_s": 720, "target": "kiln_id_fan.fan_drive.trip", "value": 1},
        ]
        raw = list(simulate(plant, assets, scenario))

        def project(**settings):
            return list(public_frames(raw, catalog["tags"], plant, assets,
                                      signal_conditioning={**catalog["signal_conditioning"], **settings}))

        plain, noisy, noiseless = project(enabled=False), project(), project(noise_enabled=False)
        self.assertEqual(noisy, project())
        for stem in stems:
            with self.subTest(stem=stem):
                device = stem.split(".")[0]
                power_id, current_id = stem + ".power_kw", stem + ".current_a"
                config = tags[power_id]["source"]["electric_power"]
                current_source = {**tags[current_id]["source"], "section": "equipment"}

                def expected(current):
                    load = min(1, max(0, current / config["rated_current_a"]))
                    factor = (1 - load) * config["cos_phi_idle"] + load * config["cos_phi_rated"]
                    return sqrt(3) * config["voltage_kv"] * current * factor

                self.assertTrue(tags[power_id]["assumed"])
                self.assertAlmostEqual(tags[power_id]["normal"], expected(tags[current_id]["normal"]), delta=.05)
                self.assertFalse(any(tag_id.startswith(power_id + ".alarm_") for tag_id in tags))
                for frame, published in zip(raw, plain, strict=True):
                    amps = read_source(frame, current_source)
                    if "passive_model" in current_source:
                        amps = passive_target(frame, current_source, amps)
                    self.assertAlmostEqual(published["measurements"][device][power_id], expected(amps))
                with_noise = [f["measurements"][device][power_id] for f in noisy]
                without_noise = [f["measurements"][device][power_id] for f in noiseless]
                self.assertNotEqual(with_noise, without_noise)
                current_state, power_state = {}, {}
                for point, state in ((current_id, current_state), (power_id, power_state)):
                    tag = tags[point]
                    conditioned_value(tag["normal"], tag, state, 1, 1, catalog["signal_conditioning"]["seed"], True)
                self.assertNotEqual(current_state["rng"].getstate(), power_state["rng"].getstate())
        self.assertEqual(noisy[-1]["measurements"]["CR-101"]["CR-101.main_motor.power_kw"], 0)
        self.assertEqual(noisy[-1]["measurements"]["CF-301"]["CF-301.fan_drive.power_kw"], 0)
