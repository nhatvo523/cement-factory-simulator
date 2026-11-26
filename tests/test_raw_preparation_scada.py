import unittest
from copy import deepcopy

from factory_sim.core.config import load_plant, load_scenario
from factory_sim.core.engine import simulate
from factory_sim.core.telemetry import load_tag_config, public_frames
from factory_sim.server import CONFIGS


class RawPreparationScadaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plant, cls.assets = load_plant(CONFIGS / "model_types", CONFIGS / "plants/bulk_material_line.json")
        cls.catalog = load_tag_config(CONFIGS / "model_types", cls.assets, cls.plant)
        cls.tags = {tag["tag_id"]: tag for tag in cls.catalog["tags"]}
        cls.baseline = cls.run_scenario()

    @classmethod
    def run_scenario(cls, case="baseline", step_s=60, duration_s=None, events=None):
        scenario = load_scenario(CONFIGS / "scenarios" / f"{case}.json", cls.assets)
        if duration_s is not None:
            scenario["duration_s"] = duration_s
        if events is not None:
            scenario["events"] = events
        return list(simulate({**cls.plant, "step_s": step_s}, cls.assets, scenario))

    def project(self, frames, noise=False):
        return list(public_frames(frames, self.catalog["tags"], self.plant, self.assets,
                                  signal_conditioning={**self.catalog["signal_conditioning"], "noise_enabled": noise}))

    @staticmethod
    def get(frame, tag, channel="measurements"):
        return frame[channel][tag.split(".")[0]][tag]

    def test_z01_catalog_counts_and_temperature_and_vibration_thresholds(self):
        zone = [tag for tag in self.tags.values() if tag["device_id"].endswith(("-101", "-201"))]
        self.assertEqual(sum(not tag.get("channel") for tag in zone), 73)
        self.assertEqual(sum(tag.get("channel") == "alarm" for tag in zone), 47)
        for point, alarm in (("inlet", 400), ("outlet", 120)):
            tag = self.tags[f"RM-201.gas_{point}_temperature_c.alarm_H"]
            self.assertEqual(tag["rule"]["by_mode"], {"RUNNING": alarm})
            self.assertTrue(tag["assumed"])
            self.assertGreater(tag["rule"]["debounce_on_s"], 5)
        for suffix, expected in (("H", [4.48, 4.25, 3.6]), ("HH", [6.58, 6.5, 5.8])):
            points = ("CR-101.vibration_sensor", "RM-201.mill_vibration_sensor", "FN-201.fan_bearing")
            for point, value in zip(points, expected, strict=True):
                rule = self.tags[f"{point}.vibration_mm_s.alarm_{suffix}"]["rule"]
                limit = rule["by_mode"]["RUNNING"]
                self.assertAlmostEqual(limit["reference"] * limit["multiplier"], value)
        steady = self.project(self.baseline)[9]
        self.assertTrue(80 <= self.get(steady, "RM-201.gas_outlet_temperature_c") <= 100)
        self.assertFalse(self.get(steady, "RM-201.gas_outlet_temperature_c.alarm_H", "alarms"))

    def test_current_uses_physical_load_and_dp_depends_on_gas_and_feed(self):
        baseline = self.project(self.baseline)
        biased = self.run_scenario("feeder_scale_bias")
        changed = self.project(biased)
        source = biased[10]["equipment"]["weigh_feeder"]["outlet_tph"]
        self.assertAlmostEqual(self.get(changed[10], "WF-201.feeder_drive.current_a"), 3 + 12 * source / 100,
                               delta=0.06)
        self.assertLess(self.get(changed[10], "WF-201.feeder_drive.current_a"),
                        self.get(baseline[10], "WF-201.feeder_drive.current_a"))
        fan_loss = self.project(self.run_scenario("fan_derate"))
        for case in (changed, fan_loss):
            self.assertLess(self.get(case[10], "RM-201.mill.differential_pressure_pa"),
                            self.get(baseline[10], "RM-201.mill.differential_pressure_pa"))
        self.assertTrue(self.get(fan_loss[10], "RM-201.mill.differential_pressure_pa.alarm_L", "alarms"))
        self.assertTrue(self.get(fan_loss[10], "RM-201.gas_outlet_temperature_c.alarm_H", "alarms"))
        self.assertIn("RC-101.reclaim_belt_scale.flow_tph", baseline[10]["measurements"]["RC-101"])

    def test_ph_cf_and_fn_pressure_reconcile_during_bypass_and_return(self):
        fault = "drying_mill.hydraulic_unit.pressure_loss"
        raw = self.run_scenario(events=[{"at_s": 600, "target": fault, "value": 1},
                                       {"at_s": 900, "target": fault, "value": 0, "clear": True}])
        frames = self.project(raw)
        local_residual = []
        for truth, frame in zip(raw[9:20], frames[9:20], strict=True):
            bypass = truth["equipment"]["drying_mill"]["bypass_position_fraction"]
            fn_flow = self.get(frame, "FN-201.airflow_m3_s")
            fn = self.get(frame, "FN-201.inlet.gauge_pressure_pa")
            ph = self.get(frame, "PH-301.cyclone_4.gauge_pressure_pa")
            cf = self.get(frame, "CF-301.draft_gauge_pa")
            self.assertTrue(all(pressure < 0 for pressure in (fn, ph, cf)))
            local = -1500 * (fn_flow / 80) ** 2
            expected = local + (1 - bypass) * (0.10 * ph + 0.16 * cf)
            self.assertAlmostEqual(fn, expected, delta=35)
            local_residual.append(fn - local)
        self.assertLess(local_residual[0], local_residual[1])
        self.assertLess(local_residual[1], local_residual[2])
        self.assertLess(local_residual[8], local_residual[7])
        self.assertLess(local_residual[9], local_residual[8])

    def test_bin_level_tracks_net_material_flow_with_conditioning(self):
        frames = self.project(self.baseline, noise=True)
        self.assertEqual(frames, self.project(self.baseline, noise=True))
        capacity = self.assets["feed_bin"]["parameters"]["capacity_t"]
        for old, new, measured in zip(self.baseline, self.baseline[1:], frames[1:]):
            before, after = (frame["equipment"]["feed_bin"] for frame in (old, new))
            self.assertAlmostEqual(after["inventory_t"] - before["inventory_t"],
                                   (after["inlet_tph"] - after["outlet_tph"]) / 60)
            level = self.get(measured, "BN-101.level_sensor.measured_level_fraction")
            self.assertAlmostEqual(capacity * level / 100, after["inventory_t"], delta=0.5)

    def test_trip_feedback_order_and_thermal_alarm_after_stop(self):
        event = {"at_s": 70, "target": "crusher.rotor.jam", "value": 1}
        frames = self.run_scenario(step_s=1, duration_s=110, events=[event])
        for frame in frames:
            frame["measurements"]["crusher"]["components"]["main_motor"]["winding_temperature_c"] = 106
        public = self.project(frames)
        self.assertTrue(self.get(public[70], "CR-101.run_feedback"))
        self.assertTrue(self.get(public[70], "CR-101.trip_feedback"))
        self.assertEqual(self.get(public[71], "CR-101.main_motor.current_a"), 0)
        self.assertTrue(self.get(public[71], "CR-101.run_feedback"))
        self.assertFalse(self.get(public[72], "CR-101.run_feedback"))
        self.assertTrue(self.get(public[72], "CR-101.main_motor.winding_temperature_c.alarm_HH", "alarms"))
        real = self.project(self.run_scenario(step_s=1, duration_s=110, events=[event]))
        temperature = "CR-101.main_motor.winding_temperature_c"
        self.assertGreater(self.get(real[72], temperature) - self.get(real[-1], temperature), 0)
        self.assertFalse(self.get(public[72], "CR-101.lubrication.pressure_bar.alarm_LL", "alarms"))

    def test_bad_quality_suppresses_process_alarm_and_reports_instrument_alarm(self):
        frames = [deepcopy(self.baseline[0]) for _ in range(18)]
        for i, frame in enumerate(frames, 1):
            frame["time_s"] = i
            sensor = frame["measurements"]["crusher"]["components"]["vibration_sensor"]
            sensor["vibration_mm_s"] = 8
            sensor["signal_quality"] = "BAD" if i >= 10 else "GOOD"
        frames = self.project(frames)
        process = "CR-101.vibration_sensor.vibration_mm_s.alarm_HH"
        instrument = "CR-101.vibration_sensor.signal_quality.alarm_BAD"
        self.assertTrue(self.get(frames[8], process, "alarms"))
        self.assertFalse(self.get(frames[9], process, "alarms"))
        self.assertTrue(self.get(frames[13], instrument, "alarms"))

    def test_starting_masks_motor_and_hydraulic_alarm_and_bad_level_still_annunciates(self):
        frames = [deepcopy(self.baseline[0]) for _ in range(150)]
        for i, frame in enumerate(frames, 1):
            frame["time_s"] = i
            mill = frame["equipment"]["drying_mill"]
            mill["operating_state"] = "STOPPED" if i <= 10 else "RUNNING"
            components = frame["measurements"]["drying_mill"]["components"]
            components["main_motor"]["current_a"] = 390
            components["hydraulic_unit"]["pressure_bar"] = 65
            sensor = frame["measurements"]["feed_bin"]["components"]["level_sensor"]
            sensor["measured_level_fraction"] = 0
            sensor["signal_quality"] = "BAD"
        frames = self.project(frames)
        for tag in ("RM-201.main_motor.current_a.alarm_H", "RM-201.hydraulic_unit.pressure_bar.alarm_L"):
            self.assertFalse(self.get(frames[30], tag, "alarms"))
            self.assertTrue(self.get(frames[-1], tag, "alarms"))
        self.assertTrue(self.get(frames[-1], "BN-101.level_sensor.signal_quality.alarm_BAD", "alarms"))
        self.assertFalse(self.get(frames[-1], "BN-101.level_sensor.measured_level_fraction.alarm_LL", "alarms"))
