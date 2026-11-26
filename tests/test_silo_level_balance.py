import unittest
from math import expm1

from factory_sim.core.config import load_plant, load_scenario
from factory_sim.core.engine import simulate
from factory_sim.core.telemetry import load_tag_config, public_frames
from factory_sim.server import CONFIGS


class SiloLevelBalanceTest(unittest.TestCase):
    def test_published_levels_follow_independent_mass_balance_and_instrument_error(self):
        plant, assets = load_plant(CONFIGS / "model_types", CONFIGS / "plants/bulk_material_line.json")
        plant["step_s"] = 1
        assets["WS-502"]["parameters"]["truck_target_t"] = 4.5
        scenario = load_scenario(CONFIGS / "scenarios/bag_packer_jam.json", assets)
        unbiased = {"relative_amplitude": 0, "period_s": 1}
        scenario["profile"] = {"measurements": {"SL-401": {"inventory_t": unbiased}}}
        scenario["duration_s"] = 760
        scenario["events"].extend([
            {"at_s": 725, "target": "SL-401.level_sensor.signal_loss", "value": 1},
            {"at_s": 735, "target": "clinker_silo.level_sensor.signal_loss", "value": 1},
        ])
        catalog = load_tag_config(CONFIGS / "model_types", assets, plant)
        raw = list(simulate(plant, assets, scenario))
        public = public_frames(raw, catalog["tags"], plant, assets,
                               signal_conditioning=catalog["signal_conditioning"])
        c = assets["clinker_silo"]["parameters"]
        compartments = {entry["grade"]: entry for entry in plant["cement_dispatch"]["compartments"].values()}
        inventories = [c["initial_t"], *(compartments[g]["initial_t"] for g in "AB")]
        capacities = [c["capacity_t"], *(compartments[g]["capacity_t"] for g in "AB")]
        self.assertEqual(capacities, [450, 90, 90])
        tags = [("SL-302", "SL-302.level_sensor.measured_level_fraction"),
                *(("SL-401", f"SL-401.cell_{g}.measured_level_fraction") for g in "AB")]
        filtered, samples = [None] * 3, [None] * 3
        shipping_b = set()
        for source, measured in zip(raw, public, strict=True):
            eq = source["equipment"]
            t = source["time_s"]
            clinker = eq["clinker_silo"]
            rates = [(clinker["inlet_tph"], clinker["outlet_tph"]),
                     (eq["SP-401A"]["outlet_tph"], eq["FD-501"]["outlet_tph"]),
                     (eq["SP-401B"]["outlet_tph"], eq["FD-502"]["outlet_tph"])]
            shipping_b.add(rates[2][1] > 0)
            stocks = [clinker["inventory_t"], *(eq["SL-401"]["grades"][g] for g in "AB")]
            for i, ((inflow, outflow), stock, (device, tag)) in enumerate(zip(rates, stocks, tags, strict=True)):
                inventories[i] += (inflow - outflow) / 3600
                self.assertAlmostEqual(inventories[i], stock, delta=1e-8)
                observed = measured["measurements"][device][tag]
                bad = t > (735 if i == 0 else 725)
                if bad:
                    quality = f"{device}.level_sensor.signal_quality"
                    self.assertEqual(measured["measurements"][device][quality], "BAD")
                    if t % 2:
                        self.assertIsNone(observed)
                    continue
                level = 100 * inventories[i] / capacities[i]
                if filtered[i] is None:
                    filtered[i] = level
                else:
                    filtered[i] += (level - filtered[i]) * -expm1(-1 / 8)
                if t % 2:
                    samples[i] = filtered[i]
                self.assertAlmostEqual(observed, samples[i], delta=.0650001)
            if 600 < t <= 725:
                self.assertEqual(rates[1][1], 0)
                self.assertGreater(rates[1][0], 0)
        self.assertEqual(shipping_b, {False, True})
