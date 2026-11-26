import math
import unittest

from factory_sim.server import ExplorerHandler


def reading(frame, device, field):
    return frame["measurements"][device][f"{device}.{field}"]


class KilnScadaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        cases = ("baseline", "kiln_id_fan_derate", "kiln_id_fan_trip", "cooler_grate_jam",
                 "kiln_feeder_jam", "cooler_airflow_loss")
        cls.results = {name: handler.simulation(name, thermal_coupling=False, conditioning_enabled=False) for name in cases}

    def frames(self, name):
        return self.results[name]["frames"]

    def test_phase_a_tags_have_assumed_metadata_and_replay_deterministically(self):
        baseline = self.results["baseline"]
        tags = [tag for tag in baseline["tags"] if tag["device_id"].endswith("-301") and "normal" in tag]
        self.assertGreaterEqual(len(tags), 22)
        for tag in tags:
            self.assertTrue({"unit", "range", "normal", "assumed"} <= tag.keys())
            self.assertTrue(tag["assumed"])
            if tag["unit"] == "°C":
                self.assertGreater(tag["time_constant_s"], 0)
            for frame in baseline["frames"]:
                self.assertIn(tag["tag_id"], frame["measurements"][tag["device_id"]])
        replay = ExplorerHandler.__new__(ExplorerHandler).simulation("baseline", thermal_coupling=False, conditioning_enabled=False)
        self.assertEqual(replay["frames"], baseline["frames"])

    def test_cyclone_order_pressure_law_and_thermal_step_response(self):
        before, after, later = self.frames("kiln_id_fan_derate")[9:12]
        for frame in (before, after, later):
            temperatures = [reading(frame, "PH-301", f"cyclone_{i}.gas_temperature_c") for i in range(1, 5)]
            pressures = [reading(frame, "PH-301", f"cyclone_{i}.gauge_pressure_pa") for i in range(1, 5)]
            self.assertTrue(temperatures[0] > temperatures[1] > temperatures[2] > temperatures[3])
            self.assertTrue(0 > pressures[0] > pressures[1] > pressures[2] > pressures[3])
        pressure = "cyclone_4.gauge_pressure_pa"
        temperature = "cyclone_1.gas_temperature_c"
        self.assertAlmostEqual(reading(after, "PH-301", pressure), 0.4**2 * reading(before, "PH-301", pressure))
        self.assertEqual(reading(after, "PH-301", pressure), reading(later, "PH-301", pressure))
        initial = reading(before, "PH-301", temperature)
        target = 25 + (initial - 25) * 0.4
        self.assertAlmostEqual(reading(after, "PH-301", temperature), target + (initial - target) * math.exp(-60 / 180))
        self.assertGreater(reading(after, "PH-301", temperature), reading(later, "PH-301", temperature))

    def test_calciner_pressure_and_air_follow_draft(self):
        fields = ("calciner_outlet.gauge_pressure_pa", "chamber.differential_pressure_pa", "tertiary_air.flow_m3_s")
        normal = [reading(self.frames("baseline")[9], "PC-301", field) for field in fields]
        derated = [reading(self.frames("kiln_id_fan_derate")[10], "PC-301", field) for field in fields]
        self.assertEqual(normal, [-1200, 650, 35])
        self.assertGreater(derated[0], normal[0])
        self.assertLess(derated[1], normal[1])
        self.assertLess(derated[2], normal[2])
        handler = ExplorerHandler.__new__(ExplorerHandler)
        tripped = handler.simulation("kiln_id_fan_trip")["frames"][10]
        self.assertFalse(tripped["alarms"]["PC-301"]["PC-301.tertiary_air.flow_m3_s.alarm_L"])

    def test_drive_current_and_cooler_temperature_follow_load(self):
        before, loaded = self.frames("kiln_id_fan_derate")[9:11]
        self.assertLess(reading(loaded, "KL-301", "kiln_drive.current_a"),
                        reading(before, "KL-301", "kiln_drive.current_a"))
        self.assertGreater(reading(loaded, "KL-301", "kiln_drive.current_a"), 0)
        self.assertLess(reading(loaded, "CL-301", "cooler_outlet.temperature_c"),
                        reading(before, "CL-301", "cooler_outlet.temperature_c"))
        before, reduced, later = self.frames("cooler_airflow_loss")[9:12]
        self.assertLess(reading(reduced, "CL-301", "grate.undergrate_pressure_pa"),
                        reading(before, "CL-301", "grate.undergrate_pressure_pa"))
        self.assertLess(reading(before, "CL-301", "cooler_outlet.temperature_c"),
                        reading(reduced, "CL-301", "cooler_outlet.temperature_c"))
        self.assertLess(reading(reduced, "CL-301", "cooler_outlet.temperature_c"),
                        reading(later, "CL-301", "cooler_outlet.temperature_c"))

    def test_stops_distinguish_immediate_feedback_from_residual_heat(self):
        for scenario in ("kiln_id_fan_trip", "cooler_grate_jam", "kiln_feeder_jam"):
            with self.subTest(scenario=scenario):
                before, stopped, later = self.frames(scenario)[9:12]
                self.assertFalse(reading(stopped, "KF-301", "run_feedback"))
                self.assertEqual(reading(stopped, "KF-301", "outlet_tph"), 0)
                self.assertEqual(reading(stopped, "KF-301", "feeder_drive.current_a"), 0)
                self.assertEqual(reading(stopped, "KL-301", "kiln_drive.current_a"), 0)
                self.assertEqual(reading(stopped, "CL-301", "grate_drive.speed_m_s"), 0)
                for device, field in (("PC-301", "tertiary_air.temperature_c"),
                                      ("KL-301", "kiln_inlet.gas_temperature_c"),
                                      ("CL-301", "cooler_outlet.temperature_c")):
                    self.assertGreater(reading(before, device, field), reading(stopped, device, field))
                    self.assertGreater(reading(stopped, device, field), reading(later, device, field))
                    self.assertGreater(reading(later, device, field), 25)
                if scenario == "kiln_id_fan_trip":
                    self.assertTrue(reading(stopped, "CF-301", "trip_feedback"))
                    self.assertEqual(reading(stopped, "CF-301", "fan_drive.current_a"), 0)
                    self.assertEqual(reading(stopped, "PH-301", "cyclone_4.gauge_pressure_pa"), 0)
                else:
                    self.assertTrue(reading(stopped, "CF-301", "run_feedback"))
                    self.assertEqual(reading(stopped, "PH-301", "cyclone_4.gauge_pressure_pa"),
                                     reading(before, "PH-301", "cyclone_4.gauge_pressure_pa"))
                    self.assertEqual(reading(stopped, "PH-301", "cyclone_1.gas_temperature_c"),
                                     reading(before, "PH-301", "cyclone_1.gas_temperature_c"))
                    self.assertTrue(reading(stopped, "CL-301", "trip_feedback") if scenario == "cooler_grate_jam"
                                    else reading(stopped, "KF-301", "trip_feedback"))
