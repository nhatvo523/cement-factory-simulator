"""Serve the local engineering explorer and its Python simulation API."""

import argparse
import json
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from time import monotonic
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from factory_sim.core.config import load_plant, load_scenario
from factory_sim.core.engine import simulate
from factory_sim.core.results import build_result
from factory_sim.core.telemetry import load_tag_config, public_frames


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = (
    "baseline", "crusher_stop", "fan_derate", "downstream_feed_stop",
    "crusher_rotor_jam", "crusher_tool_wear", "crusher_motor_cooling_loss",
    "crusher_bearing_friction", "crusher_oil_pressure_loss", "crusher_vibration_signal_loss",
    "conveyor_belt_slip", "conveyor_belt_misalignment", "conveyor_chute_blockage", "conveyor_scale_signal_loss",
    "stockpile_level_false_high", "stockpile_stacker_failure", "reclaimer_mechanism_jam",
    "reclaimer_bridge_stall", "reclaimer_harrow_encoder_loss",
    "feed_bin_outlet_bridging", "feed_bin_level_signal_loss",
    "feeder_drive_jam", "feeder_scale_bias", "feeder_scale_loss",
    "mill_roller_wear", "mill_roller_imbalance", "mill_hydraulic_loss", "mill_vibration_signal_loss",
    "separator_underspeed", "separator_drive_trip",
    "fan_impeller_degradation", "fan_damper_stuck", "fan_bearing_overheat",
    "raw_silo_outlet_blockage", "raw_silo_level_signal_loss", "kiln_feeder_jam",
    "preheater_cyclone_blockage", "calciner_fuel_loss", "kiln_drive_trip", "kiln_burner_fuel_loss",
    "cooler_airflow_loss", "cooler_grate_jam", "kiln_id_fan_trip", "kiln_id_fan_derate",
    "clinker_silo_outlet_blockage", "clinker_silo_level_signal_loss",
    "cement_mill_a_trip", "cement_mill_b_trip", "bag_packer_jam", "bulk_loading_stop",
    "cement_feeder_a_jam", "cement_feeder_b_jam", "cement_mill_a_wear",
    "cement_mill_b_wear", "cement_separator_a_trip", "cement_separator_b_trip",
    "cement_fan_a_trip", "cement_fan_b_trip", "cement_silo_gate_blockage",
    "cement_silo_level_loss", "bag_feeder_jam", "bag_conveyor_trip",
    "bag_loader_stop", "bulk_feeder_jam", "truck_scale_signal_loss",
)
CONFIGS = ROOT / "configs"
PAGES = {
    "/": ("UI/Explorer.html", "text/html; charset=utf-8"),
    "/UI/Explorer.html": ("UI/Explorer.html", "text/html; charset=utf-8"),
    "/Specification.md": ("Specification.md", "text/plain; charset=utf-8"),
}


class LiveOperation:
    def __init__(self, thermal_coupling=None, conditioning_enabled=None):
        plant, self.assets = load_plant(
            CONFIGS / "model_types", CONFIGS / "plants/bulk_material_line.json",
        )
        if thermal_coupling is not None:
            plant["thermal_coupling"]["enabled"] = thermal_coupling
        baseline = load_scenario(CONFIGS / "scenarios/baseline.json", self.assets)
        self.pending = []
        self.tag_config = load_tag_config(CONFIGS / "model_types", self.assets, plant, conditioning_enabled)
        raw_frames = simulate({**plant, "step_s": 1}, self.assets, baseline, self.pending)

        def track_frames():
            for frame in raw_frames:
                self.frame = frame
                yield frame

        self.frames = public_frames(track_frames(), self.tag_config["tags"], plant, self.assets, True,
                                    self.tag_config.get("signal_conditioning"))
        self.public_frame = next(self.frames)
        self.started = monotonic()
        self.faults = set()
        self.lock = Lock()

    def read(self, faults, ground_truth=None):
        with self.lock:
            target = int(monotonic() - self.started) + 1
            reports = {}
            while self.frame["time_s"] < target:
                self.public_frame = next(self.frames)
                for device, channels in self.public_frame.get("lab", {}).items():
                    for tag, samples in channels.items():
                        reports.setdefault(device, {}).setdefault(tag, []).extend(samples)
            for name in faults:
                if name not in self.faults:
                    scenario = load_scenario(CONFIGS / "scenarios" / f"{name}.json", self.assets)
                    self.pending.extend(scenario["events"])
                    self.faults.add(name)
            if ground_truth is None:
                ground_truth = self.tag_config.get("ground_truth_default", False)
            frame = {key: value for key, value in self.public_frame.items()
                     if key != "ground_truth" or ground_truth}
            if reports:
                frame["lab"] = reports
            return {"frame": frame, "tags": self.tag_config["tags"]}


class ExplorerHandler(BaseHTTPRequestHandler):
    live_sessions = OrderedDict()
    live_lock = Lock()

    def send_content(self, status, content, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, status, value):
        content = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        self.send_content(status, content, "application/json; charset=utf-8")

    def simulation(self, scenario, faults=(), ground_truth=None, thermal_coupling=None,
                   conditioning_enabled=None):
        return build_result(
            CONFIGS / "model_types", CONFIGS / "plants/bulk_material_line.json",
            CONFIGS / "scenarios" / f"{scenario}.json", faults, ground_truth, thermal_coupling, conditioning_enabled,
        )

    def fault_schedule(self, query):
        faults = {}
        for entry in query.get("fault", []):
            name, _, at_s = entry.partition("@")
            if name not in SCENARIOS[1:] or name in faults or not at_s.isascii() or not at_s.isdecimal():
                raise ValueError("Invalid fault selection")
            faults[name] = int(at_s)
        return [
            (CONFIGS / "scenarios" / f"{name}.json", at_s) for name, at_s in faults.items()
        ]

    def operation(self, query, ground_truth=None):
        return self.simulation("baseline", self.fault_schedule(query), ground_truth)

    def do_POST(self):
        if self.path != "/api/live-operation":
            self.send_json(404, {"error": "Not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                raise ValueError
            request = json.loads(self.rfile.read(size))
            session = request["session"]
            faults = request["faults"]
            reset = request["reset"]
            ground_truth = request.get("ground_truth")
            if ((session is not None and not isinstance(session, str)) or type(reset) is not bool
                    or (ground_truth is not None and type(ground_truth) is not bool)
                    or not isinstance(faults, list) or any(name not in SCENARIOS[1:] for name in faults)):
                raise ValueError
        except (ValueError, TypeError, KeyError):
            self.send_json(400, {"error": "Invalid live operation request"})
            return
        with self.live_lock:
            operation = self.live_sessions.get(session)
            if operation is None or reset:
                if operation is not None:
                    del self.live_sessions[session]
                session = uuid4().hex
                operation = LiveOperation()
                self.live_sessions[session] = operation
                if len(self.live_sessions) > 32:
                    self.live_sessions.popitem(last=False)
            else:
                self.live_sessions.move_to_end(session)
        result = operation.read(faults, ground_truth)
        self.send_json(200, {"session": session, **result})

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path in PAGES:
            path, content_type = PAGES[url.path]
            self.send_content(200, (ROOT / path).read_bytes(), content_type)
        elif url.path in ("/api/simulation", "/api/operation"):
            query = parse_qs(url.query, keep_blank_values=True)
            scenario = query.get("scenario", ["baseline"])[0]
            if scenario not in SCENARIOS:
                self.send_json(400, {"error": "Unknown scenario"})
                return
            try:
                flag = query.get("ground_truth", [])
                if flag and flag not in (["true"], ["false"]):
                    raise ValueError("Invalid ground_truth flag")
                ground_truth = flag == ["true"] if flag else None
                result = (self.operation(query, ground_truth) if url.path == "/api/operation"
                          else self.simulation(scenario, ground_truth=ground_truth))
                self.send_json(200, result)
            except ValueError:
                self.send_json(400, {"error": "Invalid simulation parameters"})
            except (OSError, KeyError, RuntimeError) as error:
                self.log_error("Simulation failed: %s", error)
                self.send_json(500, {"error": "Simulation failed"})
        else:
            self.send_json(404, {"error": "Not found"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", args.port), ExplorerHandler) as server:
        print(f"Explorer: http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
