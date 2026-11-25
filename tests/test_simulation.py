import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from factory_sim.core.config import load_plant, load_scenario
from factory_sim.core.engine import simulate
from factory_sim.core.results import solve_result
from factory_sim.server import CONFIGS, ExplorerHandler, LiveOperation


ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "configs" / "model_types"


def read_solver(operation, faults):
    operation.read(faults)
    return operation.frame


def solve_operation(handler, query):
    result, _, _ = solve_result(MODELS, CONFIGS / "plants/bulk_material_line.json",
                                CONFIGS / "scenarios/baseline.json", handler.fault_schedule(query), thermal_coupling=False)
    return result


class SimulationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plant, cls.assets = load_plant(MODELS, ROOT / "configs/plants/bulk_material_line.json")
        cls.plant["thermal_coupling"]["enabled"] = False

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
                self.assertEqual(len(frame["measurements"]), 33)
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
        frames = solve_operation(handler, {"fault": faults})["frames"]
        reversed_frames = solve_operation(handler, {"fault": faults[::-1]})["frames"]
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
        normal = solve_operation(handler, {})["frames"][10]["equipment"]["crusher"]
        faulty = solve_operation(handler, {"fault": ["crusher_vibration_signal_loss@600"]})["frames"][10]["equipment"]["crusher"]
        self.assertEqual(faulty["outlet_tph"], normal["outlet_tph"])
        self.assertEqual(faulty["operating_state"], "RUNNING")
        self.assertEqual(faulty["components"]["vibration_sensor"]["signal_quality"], "BAD")

    def test_live_operation_uses_elapsed_seconds_and_continues_past_ninety_minutes(self):
        with patch("factory_sim.server.monotonic", return_value=100) as clock:
            operation = LiveOperation(thermal_coupling=False)
            self.assertEqual(read_solver(operation, [])["time_s"], 1)
            clock.return_value += 1
            self.assertEqual(read_solver(operation, ["crusher_rotor_jam"])["time_s"], 2)
            clock.return_value += 1
            jam = read_solver(operation, [])
            self.assertEqual(jam["time_s"], 3)
            self.assertGreater(jam["equipment"]["crusher"]["outlet_tph"], 0)
            clock.return_value = 5501
            continued = read_solver(operation, [])
            self.assertEqual(continued["time_s"], 5402)
            self.assertEqual(continued["equipment"]["crusher"]["operating_state"], "TRIPPED")
            self.assertEqual(continued["equipment"]["crusher"]["outlet_tph"], 0)

    def test_line_one_sensor_faults_preserve_inventory_and_distinguish_interlock(self):
        with patch("factory_sim.server.monotonic", return_value=100) as clock:
            normal = LiveOperation(thermal_coupling=False)
            faulty = LiveOperation(thermal_coupling=False)
            faulty.read(["conveyor_scale_signal_loss", "feed_bin_level_signal_loss"])
            clock.return_value = 101
            reference = read_solver(normal, [])
            actual = read_solver(faulty, ["stockpile_level_false_high"])
            for asset in ("transfer_conveyor", "feed_bin"):
                self.assertEqual(actual["equipment"][asset]["outlet_tph"],
                                 reference["equipment"][asset]["outlet_tph"])
            self.assertIsNone(actual["measurements"]["transfer_conveyor"]["outlet_tph"])
            self.assertIsNone(actual["measurements"]["feed_bin"]["level_fraction"])
            clock.return_value = 102
            frame = read_solver(faulty, [])
            stockpile = frame["equipment"]["stockpile"]
            self.assertEqual(stockpile["inlet_tph"], 0)
            self.assertGreater(stockpile["outlet_tph"], 0)
            self.assertLess(stockpile["level_fraction"], 1)
            self.assertEqual(frame["measurements"]["stockpile"]["level_fraction"], 1)

    def test_live_scada_uses_sampled_component_and_equipment_signals(self):
        with patch("factory_sim.server.monotonic", return_value=100) as clock:
            operation = LiveOperation(thermal_coupling=False)
            physical = operation.frame["equipment"]
            readings = operation.read([])["frame"]["measurements"]
            self.assertNotEqual(readings["CR-101"]["CR-101.rotor.speed_rpm"],
                                physical["crusher"]["components"]["rotor"]["speed_rpm"])
            self.assertNotIn("CR-101.rotor.tool_wear_fraction", readings["CR-101"])
            operation.read(["conveyor_scale_signal_loss", "feed_bin_level_signal_loss",
                            "crusher_vibration_signal_loss", "stockpile_level_false_high"])
            clock.return_value += 1
            readings = operation.read([])["frame"]["measurements"]
            self.assertIsNone(readings["BC-101"]["BC-101.belt_scale.measured_flow_tph"])
            self.assertIsNone(readings["BN-101"]["BN-101.level_sensor.measured_level_fraction"])
            self.assertIsNone(readings["CR-101"]["CR-101.vibration_sensor.vibration_mm_s"])
            self.assertEqual(readings["ST-101"]["ST-101.level_sensor.measured_level_fraction"], 100)

    def test_line_one_combined_faults_limit_the_right_material_paths(self):
        with patch("factory_sim.server.monotonic", return_value=100) as clock:
            operation = LiveOperation(thermal_coupling=False)
            operation.read(["conveyor_belt_slip", "conveyor_belt_misalignment",
                            "reclaimer_mechanism_jam", "feed_bin_outlet_bridging"])
            clock.return_value = 101
            before_trip = read_solver(operation, [])["equipment"]
            self.assertGreater(before_trip["feed_bin"]["inventory_t"], 0)
            self.assertEqual(before_trip["feed_bin"]["outlet_tph"], 0)
            self.assertEqual(before_trip["weigh_feeder"]["outlet_tph"], 0)
            self.assertGreater(before_trip["downstream_feeder"]["outlet_tph"], 0)
            self.assertAlmostEqual(before_trip["transfer_conveyor"]["outlet_tph"], 55)
            self.assertGreater(before_trip["reclaimer"]["outlet_tph"], 0)
            clock.return_value = 131
            frame = read_solver(operation, [])
            for asset in ("transfer_conveyor", "reclaimer"):
                self.assertEqual(frame["equipment"][asset]["operating_state"], "TRIPPED")
                self.assertEqual(frame["equipment"][asset]["outlet_tph"], 0)
            self.assertAlmostEqual(frame["balance"]["dry_residual_t"], 0)
            self.assertAlmostEqual(frame["balance"]["water_residual_t"], 0)

    def test_reclaimer_travel_encoder_and_discharge_interlock(self):
        with patch("factory_sim.server.monotonic", return_value=100) as clock:
            operation = LiveOperation(thermal_coupling=False)
            normal = operation.frame["measurements"]["reclaimer"]
            self.assertGreater(normal["components"]["bridge_travel"]["position_m"], 0)
            self.assertGreater(normal["components"]["scraper_chain"]["speed_m_s"], 0)
            operation.read(["reclaimer_harrow_encoder_loss"])
            clock.return_value = 101
            frame = read_solver(operation, [])
            readings = frame["measurements"]["reclaimer"]
            self.assertIsNone(readings["components"]["harrow_encoder"]["position_m"])
            self.assertEqual(readings["components"]["harrow_travel"]["end_limit"], "NORMAL")
            self.assertGreater(readings["reclaimed_total_t"], normal["reclaimed_total_t"])
            self.assertEqual(frame["equipment"]["reclaimer"]["operating_state"], "RUNNING")
            operation.read(["feed_bin_outlet_bridging"])
            clock.return_value = 1400
            frame = read_solver(operation, [])
            self.assertEqual(frame["equipment"]["reclaimer"]["waiting_reason"], "reclaimer_discharge_unavailable")
            self.assertEqual(frame["measurements"]["reclaimer"]["outlet_tph"], 0)

    def test_reclaimer_bridge_stall_stops_travel_and_trips_after_delay(self):
        with patch("factory_sim.server.monotonic", return_value=100) as clock:
            operation = LiveOperation(thermal_coupling=False)
            operation.read(["reclaimer_bridge_stall"])
            clock.return_value = 101
            frame = read_solver(operation, [])
            reclaimer = frame["equipment"]["reclaimer"]
            self.assertEqual(reclaimer["components"]["bridge_travel"]["travel_speed_m_min"], 0)
            self.assertEqual(reclaimer["outlet_tph"], 0)
            self.assertIsNone(reclaimer["trip_reason"])
            clock.return_value = 111
            reclaimer = read_solver(operation, [])["equipment"]["reclaimer"]
            self.assertEqual(reclaimer["operating_state"], "TRIPPED")
            self.assertEqual(reclaimer["trip_reason"], "reclaimer_travel_stall")

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

    def test_weigh_feeder_bias_changes_measurement_and_physical_feed(self):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        baseline = solve_operation(handler, {})["frames"][10]
        frame = solve_operation(handler, {"fault": ["feeder_scale_bias@600"]})["frames"][10]
        physical = frame["equipment"]["weigh_feeder"]["outlet_tph"]
        reported = frame["measurements"]["weigh_feeder"]["outlet_tph"]
        self.assertLess(physical, baseline["equipment"]["weigh_feeder"]["outlet_tph"])
        self.assertGreater(reported, physical * 1.2)
        result = solve_operation(handler, {"fault": ["feeder_scale_loss@600", "feeder_scale_bias@600"]})["frames"][10]
        self.assertIsNone(result["measurements"]["weigh_feeder"]["outlet_tph"])
        self.assertEqual(result["equipment"]["weigh_feeder"]["outlet_tph"], 0)

    def test_separator_component_faults_affect_recycle_and_interlock_mill(self):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        baseline = solve_operation(handler, {})["frames"][10]["equipment"]
        slow = solve_operation(handler, {"fault": ["separator_underspeed@600"]})["frames"][10]["equipment"]
        self.assertLess(slow["separator"]["recycle_tph"], baseline["separator"]["recycle_tph"])
        self.assertAlmostEqual(slow["separator"]["recycle_tph"], slow["drying_mill"]["recycle_tph"])
        frame = solve_operation(handler, {"fault": ["separator_drive_trip@600"]})["frames"][10]
        self.assertEqual(frame["equipment"]["separator"]["operating_state"], "TRIPPED")
        self.assertEqual(frame["equipment"]["drying_mill"]["fresh_inlet_tph"], 0)
        self.assertEqual(frame["equipment"]["drying_mill"]["process_notice"], "mill_separator_unavailable")
        self.assertAlmostEqual(frame["balance"]["dry_residual_t"], 0)

    def test_fan_impeller_fault_reduces_silo_input_before_kiln_feed(self):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        baseline = solve_operation(handler, {})["frames"][10]["equipment"]
        frame = solve_operation(handler, {"fault": ["fan_impeller_degradation@600"]})["frames"][10]
        equipment = frame["equipment"]
        self.assertEqual(equipment["process_fan"]["active_faults"][0]["component"], "impeller")
        self.assertEqual(equipment["drying_mill"]["process_notice"], "mill_low_airflow")
        self.assertLess(equipment["product_silo"]["inlet_tph"], baseline["product_silo"]["inlet_tph"])
        self.assertAlmostEqual(equipment["downstream_feeder"]["outlet_tph"], baseline["downstream_feeder"]["outlet_tph"])
        self.assertAlmostEqual(frame["balance"]["water_residual_t"], 0)

    def test_kiln_line_accounts_for_calcination_and_recovers_cooler_heat(self):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        frame = solve_operation(handler, {})["frames"][10]
        stages = frame["equipment"]
        self.assertAlmostEqual(stages["precalciner"]["outlet_tph"], stages["rotary_kiln"]["inlet_tph"])
        self.assertAlmostEqual(stages["clinker_cooler"]["outlet_tph"], stages["clinker_silo"]["inlet_tph"])
        process_co2_tph = stages["precalciner"]["process_co2_tph"] + stages["rotary_kiln"]["process_co2_tph"]
        self.assertGreater(frame["balance"]["process_co2_t"], 0)
        self.assertAlmostEqual(frame["balance"]["process_co2_t"] * 60, process_co2_tph)
        self.assertGreater(stages["rotary_kiln"]["recovered_heat_kw"], 0)
        self.assertAlmostEqual(frame["balance"]["dry_residual_t"], 0)

    def test_id_fan_trip_blocks_kiln_feed_with_raw_meal_still_in_silo(self):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        frame = solve_operation(handler, {"fault": ["kiln_id_fan_trip@600"]})["frames"][10]
        stages = frame["equipment"]
        self.assertEqual(stages["kiln_id_fan"]["operating_state"], "TRIPPED")
        self.assertEqual(stages["preheater"]["process_notice"], "kiln_low_draft")
        self.assertEqual(stages["downstream_feeder"]["outlet_tph"], 0)
        self.assertGreater(stages["product_silo"]["inventory_t"], 0)
        self.assertEqual(stages["clinker_silo"]["inlet_tph"], 0)
        self.assertGreater(stages["clinker_silo"]["outlet_tph"], 0)

    def test_cooler_derate_and_silo_outlet_blockage_affect_different_flows(self):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        normal = solve_operation(handler, {})["frames"][10]["equipment"]
        frame = solve_operation(handler, {"fault": ["cooler_airflow_loss@600",
                                             "clinker_silo_outlet_blockage@600"]})["frames"][10]
        stages = frame["equipment"]
        cooler = stages["clinker_cooler"]
        self.assertGreater(cooler["components"]["cooler_outlet"]["temperature_c"],
                           normal["clinker_cooler"]["components"]["cooler_outlet"]["temperature_c"])
        self.assertLess(cooler["recovered_heat_kw"], normal["clinker_cooler"]["recovered_heat_kw"])
        self.assertGreater(stages["clinker_silo"]["inlet_tph"], 0)
        self.assertEqual(stages["clinker_silo"]["outlet_tph"], 0)
        self.assertAlmostEqual(frame["balance"]["dry_residual_t"], 0)

    def test_kiln_heat_loss_propagates_to_preheater_and_raw_mill(self):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        baseline = solve_operation(handler, {})["frames"][11]["equipment"]
        trip = solve_operation(handler, {"fault": ["kiln_drive_trip@600"]})["frames"][11]["equipment"]
        derate = solve_operation(handler, {"fault": ["kiln_id_fan_derate@600"]})["frames"][11]["equipment"]
        self.assertLess(trip["drying_mill"]["fresh_inlet_tph"], baseline["drying_mill"]["fresh_inlet_tph"])
        self.assertEqual(trip["drying_mill"]["process_notice"], "mill_kiln_heat_reduced")
        self.assertEqual(trip["drying_mill"]["components"]["mill_hot_gas"]["heat_fraction"], 0)
        self.assertLess(derate["preheater"]["components"]["preheater_outlet"]["temperature_c"],
                        baseline["preheater"]["components"]["preheater_outlet"]["temperature_c"])

    def test_zone_four_stoppage_fills_only_its_grade_and_blocks_its_mill(self):
        scenario = load_scenario(ROOT / "configs/scenarios/bag_packer_jam.json", self.assets)
        scenario["duration_s"] = 10800
        frames = list(simulate(self.plant, self.assets, scenario))
        first = frames[10]["equipment"]
        final = frames[-1]["equipment"]
        self.assertEqual(first["PK-501"]["outlet_tph"], 0)
        self.assertGreater(first["SP-502"]["outlet_tph"], 0)
        self.assertAlmostEqual(final["SL-401"]["grades"]["A"], 90)
        self.assertLess(final["SL-401"]["grades"]["B"], 90)
        self.assertEqual(final["SP-401A"]["outlet_tph"], 0)
        self.assertGreater(final["SP-401B"]["outlet_tph"], 0)
        self.assertGreater(final["clinker_silo"]["inventory_t"], first["clinker_silo"]["inventory_t"])
        for frame in frames:
            self.assertAlmostEqual(frame["balance"]["dry_residual_t"], 0)
            self.assertAlmostEqual(frame["balance"]["water_residual_t"], 0)

    def test_cement_mill_trip_still_allows_dispatch_from_opening_inventory(self):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        frames = solve_operation(handler, {"fault": ["cement_mill_a_trip@600"]})["frames"]
        first = frames[10]["equipment"]
        self.assertEqual(first["CM-401A"]["operating_state"], "TRIPPED")
        self.assertEqual(first["SP-401A"]["outlet_tph"], 0)
        self.assertGreater(first["PK-501"]["outlet_tph"], 0)
        self.assertEqual(frames[-1]["equipment"]["PK-501"]["outlet_tph"], 0)
        self.assertGreater(frames[-1]["equipment"]["SP-502"]["outlet_tph"], 0)

    def test_finish_mill_recycle_and_fan_fault_follow_connected_branch(self):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        frame = solve_operation(handler, {"fault": ["cement_fan_a_trip@600"]})["frames"][10]
        state = frame["equipment"]
        self.assertEqual(state["FN-401A"]["trip_reason"], "fan_drive_trip")
        self.assertEqual(state["SP-401A"]["outlet_tph"], 0)
        self.assertGreater(state["SP-401B"]["outlet_tph"], 0)
        feeder, mill, separator = (state[key] for key in ("WF-401B", "CM-401B", "SP-401B"))
        self.assertAlmostEqual(feeder["outlet_tph"],
                               feeder["clinker_tph"] + feeder["gypsum_tph"] + feeder["additive_tph"])
        self.assertAlmostEqual(mill["outlet_tph"], separator["inlet_tph"])
        self.assertAlmostEqual(separator["inlet_tph"], separator["outlet_tph"] + separator["recycle_tph"])
        self.assertIn("vibration_mm_s", frame["measurements"]["CM-401B"]["components"]["bearing"])

    def test_truck_exchange_stops_bulk_loading_at_target(self):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        frames = solve_operation(handler, {})["frames"]
        for previous, frame in zip(frames, frames[1:]):
            scale = frame["equipment"]["WS-502"]
            self.assertLessEqual(scale["truck_net_t"], 28 + 1e-9)
            if scale.get("waiting_reason") == "truck_exchange":
                self.assertAlmostEqual(previous["equipment"]["WS-502"]["truck_net_t"], 28)
                self.assertEqual(frame["equipment"]["SP-502"]["outlet_tph"], 0)
                self.assertGreater(frame["equipment"]["PK-501"]["outlet_tph"], 0)
                break
        else:
            self.fail("Bulk loading never paused to exchange trucks")

    def test_stacked_dispatch_faults_separate_bad_readings_from_physical_state(self):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        frame = solve_operation(handler, {"fault": ["cement_silo_level_loss@600",
                                             "truck_scale_signal_loss@600"]})["frames"][10]
        self.assertIsNone(frame["measurements"]["SL-401"]["inventory_t"])
        self.assertIsNone(frame["measurements"]["SL-401"]["grades"])
        self.assertGreater(frame["equipment"]["SL-401"]["inventory_t"], 0)
        self.assertEqual(frame["equipment"]["SP-502"]["outlet_tph"], 0)
        self.assertIsNone(frame["measurements"]["WS-502"]["truck_net_t"])
        self.assertGreater(frame["equipment"]["PK-501"]["outlet_tph"], 0)


if __name__ == "__main__":
    unittest.main()
