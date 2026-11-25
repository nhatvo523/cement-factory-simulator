import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from factory_sim.core.config import load_plant, load_scenario
from factory_sim.core.engine import simulate
from factory_sim.server import ExplorerHandler, LiveOperation, live_sensor_frame


ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "configs" / "model_types"


class SimulationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plant, cls.assets = load_plant(MODELS, ROOT / "configs/plants/bulk_material_line.json")

    def run_case(self, name, operating_profile=False):
        scenario = load_scenario(ROOT / f"configs/scenarios/{name}.json", self.assets)
        if not operating_profile:
            scenario.pop("profile", None)
        return list(simulate(self.plant, self.assets, scenario))

    def test_operating_profile_for_all_scenarios(self):
        baseline = self.run_case("baseline", operating_profile=True)
        self.assertEqual(baseline, self.run_case("baseline", operating_profile=True))
        self.assertGreater(len({f["equipment"]["crusher"]["outlet_tph"] for f in baseline}), 1)
        for case in ("baseline", "crusher_stop", "fan_derate", "downstream_feed_stop"):
            frames = self.run_case(case, operating_profile=True)
            for frame in frames:
                self.assertEqual(len(frame["measurements"]), 11)
                self.assertAlmostEqual(frame["balance"]["dry_residual_t"], 0)
                self.assertAlmostEqual(frame["balance"]["water_residual_t"], 0)
            self.assertEqual(frames[:10], baseline[:10])
            fault = frames[10]
            if case == "crusher_stop":
                self.assertEqual(fault["equipment"]["crusher"]["outlet_tph"], 0)
                self.assertEqual(fault["measurements"]["crusher"]["outlet_tph"], 0)
            elif case == "fan_derate":
                self.assertAlmostEqual(fault["equipment"]["process_fan"]["nominal_airflow_m3_s"], 28)
                self.assertLess(fault["equipment"]["drying_mill"]["fresh_inlet_tph"],
                                baseline[10]["equipment"]["drying_mill"]["fresh_inlet_tph"])
            elif case == "downstream_feed_stop":
                self.assertEqual(fault["equipment"]["downstream_feeder"]["outlet_tph"], 0)
                self.assertAlmostEqual(frames[-1]["equipment"]["product_silo"]["inventory_t"], 55)

    def test_baseline_is_balanced_and_reproducible(self):
        frames = self.run_case("baseline")
        self.assertEqual(frames, self.run_case("baseline"))
        for frame in frames:
            self.assertAlmostEqual(frame["equipment"]["product_silo"]["inventory_t"], 35)
            self.assertAlmostEqual(frame["balance"]["dry_residual_t"], 0)
            self.assertAlmostEqual(frame["balance"]["water_residual_t"], 0)
            mill, separator = (frame["equipment"][key] for key in ("drying_mill", "separator"))
            self.assertAlmostEqual(mill["outlet_tph"], separator["inlet_tph"])
            self.assertAlmostEqual(mill["recycle_tph"], separator["recycle_tph"])

    def test_crusher_stop_propagates_after_buffers_deplete(self):
        frames = self.run_case("crusher_stop")
        by_time = {frame["time_s"]: frame["equipment"] for frame in frames}
        self.assertEqual(by_time[660]["crusher"]["outlet_tph"], 0)
        self.assertAlmostEqual(by_time[660]["weigh_feeder"]["outlet_tph"], 100)
        self.assertAlmostEqual(by_time[660]["downstream_feeder"]["outlet_tph"], by_time[600]["downstream_feeder"]["outlet_tph"])
        self.assertEqual(frames[-1]["equipment"]["downstream_feeder"]["outlet_tph"], 0)

    def test_crusher_combines_component_faults_and_latches_trip(self):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        faults = ["crusher_rotor_jam@600", "crusher_vibration_signal_loss@600"]
        frames = handler.operation({"fault": faults})["frames"]
        reversed_frames = handler.operation({"fault": faults[::-1]})["frames"]
        normal, jam, tripped = (frames[i]["equipment"]["crusher"] for i in (9, 10, 11))
        self.assertGreater(jam["components"]["main_motor"]["current_a"],
                           normal["components"]["main_motor"]["current_a"])
        self.assertGreater(jam["outlet_tph"], 0)
        self.assertLess(jam["outlet_tph"], normal["outlet_tph"])
        self.assertEqual({fault["component"] for fault in jam["active_faults"]},
                         {"rotor", "vibration_sensor"})
        self.assertIsNone(jam["components"]["vibration_sensor"]["vibration_mm_s"])
        self.assertEqual(tripped["operating_state"], "TRIPPED")
        self.assertEqual(tripped["trip_reason"], "motor_overcurrent")
        for index, frame in enumerate(frames[11:], start=11):
            self.assertEqual(frame["equipment"]["crusher"]["outlet_tph"], 0)
            self.assertEqual(reversed_frames[index]["equipment"]["crusher"]["outlet_tph"], 0)
            self.assertAlmostEqual(frame["balance"]["dry_residual_t"], 0)

    def test_crusher_sensor_loss_preserves_physical_flow(self):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        normal = handler.operation({})["frames"][10]["equipment"]["crusher"]
        faulty = handler.operation({"fault": ["crusher_vibration_signal_loss@600"]})["frames"][10]["equipment"]["crusher"]
        self.assertEqual(faulty["outlet_tph"], normal["outlet_tph"])
        self.assertEqual(faulty["operating_state"], "RUNNING")
        self.assertEqual(faulty["components"]["vibration_sensor"]["signal_quality"], "BAD")

    def test_live_operation_uses_elapsed_seconds_and_continues_past_ninety_minutes(self):
        with patch("factory_sim.server.monotonic", return_value=100) as clock:
            operation = LiveOperation()
            self.assertEqual(operation.read([])["frame"]["time_s"], 1)
            clock.return_value += 1
            self.assertEqual(operation.read(["crusher_rotor_jam"])["frame"]["time_s"], 2)
            clock.return_value += 1
            jam = operation.read([])["frame"]
            self.assertEqual(jam["time_s"], 3)
            self.assertGreater(jam["equipment"]["crusher"]["outlet_tph"], 0)
            clock.return_value = 5501
            continued = operation.read([])["frame"]
            self.assertEqual(continued["time_s"], 5402)
            self.assertEqual(continued["equipment"]["crusher"]["operating_state"], "TRIPPED")
            self.assertEqual(continued["equipment"]["crusher"]["outlet_tph"], 0)

    def test_line_one_sensor_faults_preserve_inventory_and_distinguish_interlock(self):
        with patch("factory_sim.server.monotonic", return_value=100) as clock:
            normal = LiveOperation()
            faulty = LiveOperation()
            faulty.read(["conveyor_scale_signal_loss", "feed_bin_level_signal_loss"])
            clock.return_value = 101
            reference = normal.read([])["frame"]
            actual = faulty.read(["stockpile_level_false_high"])["frame"]
            for asset in ("transfer_conveyor", "feed_bin"):
                self.assertEqual(actual["equipment"][asset]["outlet_tph"],
                                 reference["equipment"][asset]["outlet_tph"])
            self.assertIsNone(actual["measurements"]["transfer_conveyor"]["outlet_tph"])
            self.assertIsNone(actual["measurements"]["feed_bin"]["level_fraction"])
            clock.return_value = 102
            frame = faulty.read([])["frame"]
            stockpile = frame["equipment"]["stockpile"]
            self.assertEqual(stockpile["inlet_tph"], 0)
            self.assertGreater(stockpile["outlet_tph"], 0)
            self.assertLess(stockpile["level_fraction"], 1)
            self.assertEqual(frame["measurements"]["stockpile"]["level_fraction"], 1)

    def test_live_scada_uses_sampled_component_and_equipment_signals(self):
        with patch("factory_sim.server.monotonic", return_value=100) as clock:
            operation = LiveOperation()
            physical = operation.frame["equipment"]
            scada = live_sensor_frame(operation.frame)
            readings = scada["measurements"]
            for asset in ("crusher", "transfer_conveyor", "stockpile", "reclaimer", "feed_bin"):
                self.assertIn("outlet_tph", readings[asset])
                self.assertNotIn("outlet_tph", scada["equipment"][asset])
                self.assertNotIn("components", scada["equipment"][asset])
            self.assertNotEqual(readings["crusher"]["outlet_tph"], physical["crusher"]["outlet_tph"])
            self.assertNotEqual(readings["crusher"]["components"]["rotor"]["speed_rpm"],
                                physical["crusher"]["components"]["rotor"]["speed_rpm"])
            self.assertNotIn("tool_wear_fraction", readings["crusher"]["components"]["rotor"])
            operation.read(["conveyor_scale_signal_loss", "feed_bin_level_signal_loss",
                            "crusher_vibration_signal_loss", "stockpile_level_false_high"])
            clock.return_value += 1
            readings = live_sensor_frame(operation.read([])["frame"])["measurements"]
            self.assertIsNone(readings["transfer_conveyor"]["outlet_tph"])
            self.assertIsNone(readings["feed_bin"]["level_fraction"])
            self.assertIsNone(readings["crusher"]["components"]["vibration_sensor"]["vibration_mm_s"])
            self.assertEqual(readings["stockpile"]["level_fraction"], 1)
            self.assertLess(readings["stockpile"]["inventory_t"], 40)

    def test_line_one_combined_faults_limit_the_right_material_paths(self):
        with patch("factory_sim.server.monotonic", return_value=100) as clock:
            operation = LiveOperation()
            operation.read(["conveyor_belt_slip", "conveyor_belt_misalignment",
                            "reclaimer_mechanism_jam", "feed_bin_outlet_bridging"])
            clock.return_value = 101
            before_trip = operation.read([])["frame"]["equipment"]
            self.assertGreater(before_trip["feed_bin"]["inventory_t"], 0)
            self.assertEqual(before_trip["feed_bin"]["outlet_tph"], 0)
            self.assertEqual(before_trip["weigh_feeder"]["outlet_tph"], 0)
            self.assertGreater(before_trip["downstream_feeder"]["outlet_tph"], 0)
            self.assertAlmostEqual(before_trip["transfer_conveyor"]["outlet_tph"], 55)
            self.assertGreater(before_trip["reclaimer"]["outlet_tph"], 0)
            clock.return_value = 131
            frame = operation.read([])["frame"]
            for asset in ("transfer_conveyor", "reclaimer"):
                self.assertEqual(frame["equipment"][asset]["operating_state"], "TRIPPED")
                self.assertEqual(frame["equipment"][asset]["outlet_tph"], 0)
            self.assertAlmostEqual(frame["balance"]["dry_residual_t"], 0)
            self.assertAlmostEqual(frame["balance"]["water_residual_t"], 0)

    def test_fan_derate_limits_drying_before_downstream_feed(self):
        frames = self.run_case("fan_derate")
        normal, fault = (frames[i]["equipment"] for i in (9, 10))
        self.assertLess(fault["process_fan"]["airflow_m3_s"], normal["process_fan"]["airflow_m3_s"])
        self.assertLess(fault["drying_mill"]["fresh_inlet_tph"], normal["drying_mill"]["fresh_inlet_tph"])
        self.assertAlmostEqual(fault["separator"]["outlet_moisture_fraction"], 0.005)
        self.assertAlmostEqual(fault["downstream_feeder"]["outlet_tph"], normal["downstream_feeder"]["outlet_tph"])
        self.assertLess(frames[-1]["equipment"]["downstream_feeder"]["outlet_tph"], normal["downstream_feeder"]["outlet_tph"])

    def test_downstream_feed_stop_limits_upstream_when_silo_fills(self):
        frames = self.run_case("downstream_feed_stop")
        before, stopped = (frames[i]["equipment"] for i in (9, 10))
        self.assertEqual(stopped["downstream_feeder"]["outlet_tph"], 0)
        self.assertGreater(stopped["product_silo"]["inventory_t"], before["product_silo"]["inventory_t"])
        self.assertAlmostEqual(stopped["separator"]["outlet_tph"], before["separator"]["outlet_tph"])
        final = frames[-1]["equipment"]
        self.assertAlmostEqual(final["product_silo"]["inventory_t"], 55)
        self.assertAlmostEqual(final["weigh_feeder"]["outlet_tph"], 0)

    def test_reuse_storage_model_with_other_ids_and_parameters(self):
        alternate = {
            "id": "test_bulk_transfer", "step_s": 60, "feeds": {"BUFFER": {
                "flow_tph": 12, "moisture_fraction": 0.02}},
            "equipment": [
                {"id": "BUFFER", "model_type": "bulk_storage_v1", "parameters": {
                    "capacity_t": 9, "initial_t": 2, "initial_moisture_fraction": 0.02}},
                {"id": "DISCHARGE", "model_type": "bulk_throughput_v1", "parameters": {
                    "capacity_tph": 6}},
            ],
            "connections": [{"from": "BUFFER.outlet", "to": "DISCHARGE.inlet", "kind": "material"}],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plant.json"
            path.write_text(json.dumps(alternate), encoding="utf-8")
            plant, assets = load_plant(MODELS, path)
            first, = simulate(plant, assets, {"duration_s": 60, "events": []})
        self.assertAlmostEqual(first["equipment"]["BUFFER"]["inventory_t"], 2.1)
        self.assertAlmostEqual(first["equipment"]["DISCHARGE"]["outlet_tph"], 6)


if __name__ == "__main__":
    unittest.main()
