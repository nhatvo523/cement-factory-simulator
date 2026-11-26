import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import Request, urlopen

from factory_sim.core.config import load_plant, load_scenario, read_json
from factory_sim.core.engine import simulate
from factory_sim.core.telemetry import load_tag_config
from factory_sim.server import CONFIGS, ROOT, SCENARIOS, ExplorerHandler
from solver_fingerprint import release_stockpile_assets


class ScadaContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plant, cls.assets = load_plant(CONFIGS / "model_types", CONFIGS / "plants/bulk_material_line.json")
        cls.tags = load_tag_config(CONFIGS / "model_types", cls.assets, cls.plant)["tags"]
        cls.allowed = {}
        for tag in cls.tags:
            if tag.get("channel"):
                continue
            cls.allowed.setdefault(tag["device_id"], set()).add(tag["tag_id"])

    def assert_public_frame(self, frame):
        self.assertEqual(set(frame) - {"lab", "alarms"}, {"time_s", "measurements"})
        lab_tags = {(tag["device_id"], tag["tag_id"]) for tag in self.tags if tag.get("channel") == "lab"}
        for device, readings in frame.get("lab", {}).items():
            for tag, samples in readings.items():
                self.assertIn((device, tag), lab_tags)
                for sample in samples:
                    self.assertEqual(set(sample), {"sampled_at_s", "reported_at_s", "value"})
        allowed_alarms = {(tag["device_id"], tag["tag_id"]) for tag in self.tags if tag.get("channel") == "alarm"}
        actual_alarms = {(device, tag) for device, values in frame.get("alarms", {}).items()
                         for tag, value in values.items() if type(value) is bool}
        self.assertEqual(actual_alarms, allowed_alarms)
        actual = {device: set(values) for device, values in frame["measurements"].items()}
        self.assertEqual(actual, self.allowed)
        for readings in frame["measurements"].values():
            self.assertTrue(all(value is None or type(value) in (str, int, float, bool)
                                for value in readings.values()))

    def test_http_and_cli_share_catalog_and_hide_truth_by_default(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), ExplorerHandler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"

            def get(path, data=None):
                request = Request(base + path, None if data is None else json.dumps(data).encode(),
                                  {"Content-Type": "application/json"})
                with urlopen(request, timeout=15) as response:
                    return json.load(response)

            try:
                baseline = get("/api/simulation")
                operation = get("/api/operation?fault=kiln_id_fan_trip@600")
                live_request = {"session": None, "faults": [], "reset": False}
                live = get("/api/live-operation", live_request)
                self.assertEqual(set(live), {"session", "tags", "frame"})
                self.assertEqual(live["tags"], self.tags)
                self.assert_public_frame(live["frame"])
                for payload in (baseline, operation):
                    self.assertEqual(payload["tags"], self.tags)
                    for frame in payload["frames"]:
                        self.assert_public_frame(frame)
                self.assertEqual(get("/api/simulation"), baseline)
                truth = get("/api/operation?fault=kiln_id_fan_trip@600&ground_truth=true")
                event_frame = truth["frames"][10]
                diagnostics = event_frame["ground_truth"]
                self.assertEqual(diagnostics["events"][0]["target"], "kiln_id_fan.fan_drive.trip")
                self.assertTrue(diagnostics["equipment"]["kiln_id_fan"]["trip_reason"])
                self.assertNotIn("ground_truth", operation["frames"][10])
                self.assertIn("ground_truth", get("/api/live-operation", {
                    **live_request, "session": live["session"], "ground_truth": True,
                })["frame"])
            finally:
                server.shutdown()
                thread.join()

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "scada.json"
            subprocess.run([sys.executable, "-m", "factory_sim", "configs/scenarios/baseline.json",
                            "--output", str(output)], cwd=ROOT, check=True, capture_output=True)
            export = read_json(output)
        self.assertEqual(export, baseline)

    def test_three_point_changes_and_removed_heat_proxy(self):
        handler = ExplorerHandler.__new__(ExplorerHandler)
        frames = handler.operation({"fault": ["kiln_id_fan_trip@600", "bag_packer_jam@600"]})["frames"]
        normal, fault = (frames[i]["measurements"] for i in (9, 10))
        self.assertLess(normal["CF-301"]["CF-301.draft_gauge_pa"], 0)
        self.assertEqual(fault["CF-301"]["CF-301.draft_gauge_pa"], 0)
        self.assertTrue(fault["CF-301"]["CF-301.trip_feedback"])
        self.assertGreater(normal["PK-501"]["PK-501.bags_count"], 0)
        self.assertEqual(normal["PK-501"]["PK-501.bags_count"], fault["PK-501"]["PK-501.bags_count"])
        self.assertEqual(fault["PK-501"]["PK-501.bags_per_min"], 0)
        for cell in ("A", "B"):
            self.assertGreater(normal["SL-401"][f"SL-401.cell_{cell}.measured_level_fraction"], 0)
        self.assertNotIn("grades", normal["SL-401"])
        self.assertNotIn("RM-201.mill_hot_gas.heat_fraction", normal["RM-201"])

    def test_all_65_scenarios_match_pre_step_one_solver(self):
        expected = read_json(Path(__file__).with_name("step1_solver_baseline.json"))
        self.assertEqual(set(expected), set(SCENARIOS))
        self.assertEqual(len(expected), 65)
        legacy_plant = {**self.plant, "thermal_coupling": {**self.plant["thermal_coupling"], "enabled": False}}
        assets = release_stockpile_assets(self.assets)
        for name in SCENARIOS:
            with self.subTest(scenario=name):
                scenario = load_scenario(CONFIGS / "scenarios" / f"{name}.json", assets)
                physical = [{key: frame[key] for key in ("time_s", "equipment", "balance", "events")}
                            for frame in simulate(legacy_plant, assets, scenario)]
                encoded = json.dumps(physical, sort_keys=True, separators=(",", ":")).encode()
                self.assertEqual(hashlib.sha256(encoded).hexdigest(), expected[name])
