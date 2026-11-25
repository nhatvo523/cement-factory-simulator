"""Apply instrument behavior to published readings only."""

from collections import deque
from hashlib import sha256
from math import expm1
from random import Random


def debounce(state, target, time_s, changed_at, on_s, off_s, initial=None):
    if "value" not in state:
        state["value"] = target if initial is None else initial
    if target == state["value"]:
        state.pop("pending", None)
    else:
        pending, since = state.get("pending", (None, changed_at))
        if pending != target:
            since = changed_at
            state["pending"] = (target, since)
        if time_s - since >= (on_s if target else off_s):
            state["value"] = target
            state.pop("pending", None)
    return state["value"]


def conditioned_value(raw, tag, state, time_s, step_s, seed, noise_enabled):
    cfg = tag["conditioning"]
    start = time_s - step_s
    if not state:
        state.update(target=raw, last_input=raw, change_at=start, pending=deque(),
                     filtered=raw, published=raw, sample_at=time_s)
    elif raw != state["last_input"]:
        state["pending"].append((start + cfg["transport_delay_s"], raw))
        state["last_input"] = raw

    def advance(t0, t1):
        target, current = state["target"], state["filtered"]
        tau = cfg.get("time_constant_s", 0)
        state["filtered"] = (current + (target - current) * -expm1(-(t1 - t0) / tau)
                             if tau and target is not None and current is not None else target)

    cursor = start
    while state["pending"] and state["pending"][0][0] <= time_s:
        changed_at, delayed = state["pending"].popleft()
        if cfg["kind"] == "analog":
            advance(cursor, changed_at)
        cursor = changed_at
        state.update(target=delayed, change_at=changed_at)

    if cfg["kind"] in {"discrete", "status"}:
        target = state["target"]
        if target is None:
            state.pop("debounce", None)
            return None
        return debounce(state.setdefault("debounce", {}), target, time_s, state["change_at"],
                        cfg["debounce_on_s"], cfg["debounce_off_s"])
    advance(cursor, time_s)
    if time_s < state["sample_at"]:
        return state["published"]
    period = cfg["sample_period_s"]
    elapsed = time_s - state["sample_at"]
    state["sample_at"] = state["sample_at"] + (elapsed // period + 1) * period if period else time_s
    value = state["filtered"]
    if value is not None:
        low, high, resolution = (cfg[key] for key in ("range_min", "range_max", "resolution"))
        settled_zero = cfg.get("preserve_zero") and state["target"] == 0 and abs(value) < resolution / 2
        if settled_zero:
            value = 0
        elif noise_enabled and cfg["noise_pct_of_span"]:
            if "rng" not in state:
                digest = sha256(f"{seed}:{tag['tag_id']}".encode()).digest()
                state["rng"] = Random(int.from_bytes(digest, "big"))
            value += state["rng"].uniform(-1, 1) * (high - low) * cfg["noise_pct_of_span"] / 100
        value = min(high, max(low, value))
        value = min(high, max(low, low + round((value - low) / resolution) * resolution))
    state["published"] = value
    return value


def alarm_value(value, rule, state, mode, time_s, step_s):
    limit = rule["by_mode"].get(mode, rule["by_mode"].get("ALL"))
    if value is None or limit is None:
        state.clear()
        return False
    if rule["severity"] == "BAD":
        target = value == limit
    else:
        if isinstance(limit, dict):
            limit = limit["reference"] * limit["multiplier"]
        high = rule["severity"].startswith("H")
        active = state.get("value", False)
        band = rule["deadband"] if active else 0
        target = value >= limit - band if high else value <= limit + band
    return debounce(state, target, time_s, time_s - step_s, rule["debounce_on_s"],
                    rule["debounce_off_s"], initial=False)
