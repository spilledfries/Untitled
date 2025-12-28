import json
import re
import types
import subprocess
import importlib.util
import sys
from pathlib import Path

# Dynamically import the script from project root as a module
MODULE_NAME = "dmn_security_lab"
SCRIPT_PATH = Path(__file__).resolve().parents[1] / f"{MODULE_NAME}.py"
spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = mod
spec.loader.exec_module(mod)  # type: ignore


def test_compute_dmn_proxy_idle_only():
    s, reasons = mod.compute_dmn_proxy(text=None, latency=600, output_wpm=None, input_wpm=None, integrity=None, marker=None)
    assert 0.39 <= s <= 0.41  # 0.5 * 0.8 = 0.4
    assert any(r.startswith("idle:") for r in reasons)


def test_compute_dmn_proxy_text_signals():
    s, reasons = mod.compute_dmn_proxy(
        text="I'm just checking, maybe later?", latency=0, output_wpm=10, input_wpm=40, integrity=79, marker="star"
    )
    # procrastination (0.3) + dither (0.15) + question (0.05) + low o/i (0.2) + low integrity (0.2) + marker (0.05)
    # total 0.95 clamped to 0-1
    assert 0.9 <= s <= 1.0
    assert "text:procrastination" in reasons
    assert any(r.startswith("low-integrity") for r in reasons)


def test_policy_active_breach_threshold():
    policy, reasons = mod.apply_policy("active", dmn_proxy=0.61, text="work", integrity=100)
    assert policy == "breach"
    assert "dmn>=0.6" in reasons


def test_policy_active_breach_text_and_integrity():
    policy, reasons = mod.apply_policy("active", dmn_proxy=0.2, text="just scrolling", integrity=60)
    assert policy == "breach"
    assert "text:procrastination" in reasons and "low-integrity" in reasons


def test_policy_play_never_breaches():
    policy, reasons = mod.apply_policy("play", dmn_proxy=0.99, text="just scrolling", integrity=10)
    assert policy == "ok"


def test_analyze_json_flag(tmp_path, monkeypatch, capsys):
    # Write a tiny JSONL log
    log_path = tmp_path / mod.LOG_JSONL
    data = [
        {"ts": "2025-01-01T00:00:00.000Z", "type": "start"},
        {"ts": "2025-01-01T00:05:00.000Z", "type": "log", "mode": "active", "dmn_proxy": 0.7, "policy": "breach", "reasons": ["dmn>=0.6"], "text": "just checking"},
        {"ts": "2025-01-01T00:06:00.000Z", "type": "stop"},
    ]
    tmp_path.joinpath(mod.LOG_JSONL).write_text("\n".join(json.dumps(x) for x in data), encoding="utf-8")

    # Monkeypatch tail_jsonl to read from our tmp file
    def fake_tail(limit):
        return json.loads("[" + ",".join(json.dumps(x) for x in data[-limit:]) + "]")

    monkeypatch.setattr(mod, "tail_jsonl", fake_tail)

    # Run analyze with --json
    mod.cmd_analyze(types.SimpleNamespace(limit=50, json=True))
    out = capsys.readouterr().out
    summary = json.loads(out)
    assert summary["events"] == 3
    assert summary["breaches"] == 1
    assert summary["mean_dmn"] >= 0.7


import pytest

@pytest.mark.parametrize("lat,expected", [
    (0, 0.0),
    (300, 0.3),
    (600, 0.4),
    (1200, 0.5),
])
def test_compute_dmn_proxy_latency_curve(lat, expected):
    s, _ = mod.compute_dmn_proxy(text=None, latency=lat, output_wpm=None, input_wpm=None, integrity=None, marker=None)
    assert abs(s - expected) < 0.01


def test_cli_e2e(tmp_path):
    script = SCRIPT_PATH
    # Start session
    subprocess.run([
        "python",
        str(script),
        "start",
        "--intent",
        "test",
        "--artifact",
        "demo",
        "--mode",
        "active",
    ], cwd=tmp_path, check=True, text=True, capture_output=True)

    # Log entry
    subprocess.run([
        "python",
        str(script),
        "log",
        "--text",
        "maybe",
        "--latency",
        "1200",
    ], cwd=tmp_path, check=True, text=True, capture_output=True)

    # Stop session
    subprocess.run([
        "python",
        str(script),
        "stop",
    ], cwd=tmp_path, check=True, text=True, capture_output=True)

    csv_path = tmp_path / mod.LOG_CSV
    jsonl_path = tmp_path / mod.LOG_JSONL
    assert csv_path.exists()
    assert jsonl_path.exists()

    lines = jsonl_path.read_text().strip().splitlines()
    assert len(lines) == 3
    entries = [json.loads(l) for l in lines]
    assert [e["type"] for e in entries] == ["start", "log", "stop"]
