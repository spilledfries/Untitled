"""
Security Systems — Python Lab (DMN monitor + policy engine)
Run: python dmn_security_lab.py --help

Artifacts:
- dmn_log.csv   (UTF-8 CSV)
- dmn_log.jsonl (JSON Lines)
- dmn_state.json
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
from dataclasses import dataclass, asdict, field
from datetime import datetime
import json
import os
import re
import sys
import uuid
from typing import List, Optional, Dict, Any, Tuple

LOG_CSV = "dmn_log.csv"
LOG_JSONL = "dmn_log.jsonl"
STATE_FILE = "dmn_state.json"

ISO = "%Y-%m-%dT%H:%M:%S.%fZ"

# Precompile lightweight text signals. Kept short to avoid false positives.
PROCRAST_PHRASES = [
    r"\bscroll(ing)?\b",
    r"\bmaybe later\b",
    r"\bjust check(ing)?\b",
    r"\bafter this\b",
    r"\bone more\b",
    r"\b procrastinat(ing|e|ion)\b",
    r"\b tomorrow\b",
    r"\b later\b",
    r"\b idk\b",
    r"\b not now\b",
]
PROCRAST_RE = re.compile("|".join(PROCRAST_PHRASES), re.IGNORECASE)
# Why: tests expect "maybe" alone to count as dithering.
DITHER_RE = re.compile(r"\b(I\s*(might|could|should|maybe)|not\s*sure|maybe)\b", re.IGNORECASE)
QMARK_RE = re.compile(r"\?")

@dataclass
class Event:
    ts: str
    session_id: str
    type: str
    mode: str
    intent: Optional[str] = None
    artifact: Optional[str] = None
    text: Optional[str] = None
    latency: Optional[int] = None          # seconds idle/latency
    output_wpm: Optional[int] = None
    input_wpm: Optional[int] = None
    bpm: Optional[int] = None
    integrity: Optional[int] = None        # 0-100 self-rated
    marker: Optional[str] = None
    dmn_proxy: Optional[float] = None      # 0.0-1.0
    policy: Optional[str] = None           # "ok"|"breach"
    reasons: List[str] = field(default_factory=list)
    notes: Optional[str] = None

# I/O

def now_utc_iso() -> str:
    return datetime.utcnow().strftime(ISO)

def read_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def write_state(state: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def clear_state() -> None:
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

def append_jsonl(event: Event) -> None:
    with open(LOG_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

def append_csv(event: Event) -> None:
    row = asdict(event)
    header = list(row.keys())
    file_exists = os.path.exists(LOG_CSV)
    with open(LOG_CSV, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        if not file_exists:
            w.writeheader()
        w.writerow(row)

def save_event(event: Event) -> None:
    append_csv(event)
    append_jsonl(event)

# Scoring

def compute_dmn_proxy(
    text: Optional[str],
    latency: Optional[int],
    output_wpm: Optional[int],
    input_wpm: Optional[int],
    integrity: Optional[int],
    marker: Optional[str],
) -> Tuple[float, List[str]]:
    score = 0.0
    reasons: List[str] = []

    # Idle/latency: 0 at 0s, 0.6 at 5 min, 0.8 at 10 min, 1.0 at 20+ min.
    if isinstance(latency, int) and latency >= 0:
        if latency >= 1200:
            s = 1.0
        elif latency >= 600:
            s = 0.8 + 0.2 * (latency - 600) / 600
        elif latency >= 300:
            s = 0.6 + 0.2 * (latency - 300) / 300
        else:
            s = 0.6 * (latency / 300)
        score += 0.5 * s
        if latency >= 60:
            reasons.append(f"idle:{latency}s")

    # Text signals
    if text:
        if PROCRAST_RE.search(text):
            score += 0.3
            reasons.append("text:procrastination")
        if DITHER_RE.search(text):
            score += 0.15
            reasons.append("text:dither")
        if QMARK_RE.search(text):
            score += 0.05
            reasons.append("text:questioning")

    # Output/Input dynamics
    if isinstance(output_wpm, int) and isinstance(input_wpm, int) and input_wpm > 0:
        ratio = output_wpm / max(1, input_wpm)
        if ratio < 0.5 and output_wpm < 20:
            score += 0.2
            reasons.append(f"low-o/i:{ratio:.2f}")

    # Integrity penalty
    if isinstance(integrity, int):
        if integrity < 80:
            score += 0.2
            reasons.append(f"low-integrity:{integrity}")

    # Marker nudge
    if marker:
        if marker.lower() in {"star", "!", "flag"}:
            score += 0.05
            reasons.append("marker:nudge")

    # Clamp
    score = max(0.0, min(1.0, score))
    return score, reasons

def apply_policy(mode: str, dmn_proxy: float, text: Optional[str], integrity: Optional[int]) -> Tuple[str, List[str]]:
    reasons: List[str] = []
    breach = False
    if mode.lower() == "active":
        if dmn_proxy >= 0.6:
            breach = True
            reasons.append("dmn>=0.6")
        if text and PROCRAST_RE.search(text):
            breach = True
            reasons.append("text:procrastination")
        if isinstance(integrity, int) and integrity < 80:
            breach = True
            reasons.append("low-integrity")
    # play mode never breaches
    return ("breach" if breach else "ok"), reasons

# Commands

def cmd_start(args: argparse.Namespace) -> None:
    state = read_state()
    if state.get("session_id"):
        print("Error: session already active. Use 'stop' first.", file=sys.stderr)
        sys.exit(2)
    session_id = str(uuid.uuid4())
    state = {
        "session_id": session_id,
        "mode": args.mode.lower(),
        "intent": args.intent,
        "artifact": args.artifact,
        "started_at": now_utc_iso(),
    }
    write_state(state)

    event = Event(
        ts=state["started_at"],
        session_id=session_id,
        type="start",
        mode=state["mode"],
        intent=state["intent"],
        artifact=state["artifact"],
    )
    save_event(event)
    print(f"started {session_id} mode={state['mode']} intent={state['intent']} artifact={state['artifact']}")

def require_state() -> Dict[str, Any]:
    state = read_state()
    if not state.get("session_id"):
        print("Error: no active session. Use 'start' first.", file=sys.stderr)
        sys.exit(2)
    return state

def cmd_log(args: argparse.Namespace) -> None:
    state = require_state()

    dmn_val, dmn_reasons = compute_dmn_proxy(
        text=args.text,
        latency=args.latency,
        output_wpm=args.output_wpm,
        input_wpm=args.input_wpm,
        integrity=args.integrity,
        marker=args.marker,
    )
    policy, pol_reasons = apply_policy(state["mode"], dmn_val, args.text, args.integrity)

    event = Event(
        ts=now_utc_iso(),
        session_id=state["session_id"],
        type="log",
        mode=state["mode"],
        intent=state["intent"],
        artifact=state["artifact"],
        text=args.text,
        latency=args.latency,
        output_wpm=args.output_wpm,
        input_wpm=args.input_wpm,
        bpm=args.bpm,
        integrity=args.integrity,
        marker=args.marker,
        dmn_proxy=round(dmn_val, 3),
        policy=policy,
        reasons=list(dict.fromkeys(dmn_reasons + pol_reasons)),
    )
    save_event(event)
    print(f"log dmn={event.dmn_proxy} policy={policy} reasons={';'.join(event.reasons) if event.reasons else 'none'}")

def cmd_stop(args: argparse.Namespace) -> None:
    state = require_state()
    event = Event(
        ts=now_utc_iso(),
        session_id=state["session_id"],
        type="stop",
        mode=state["mode"],
        intent=state["intent"],
        artifact=state["artifact"],
        notes=args.notes,
    )
    save_event(event)
    clear_state()
    print("stopped")

# Analysis

def tail_jsonl(limit: int) -> List[Dict[str, Any]]:
    if not os.path.exists(LOG_JSONL):
        return []
    out: List[Dict[str, Any]] = []
    # Simple read-all for small files; fine for a lab scaffold.
    with open(LOG_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out[-limit:] if limit > 0 else out


def fmt_pct(n: int, d: int) -> str:
    return "0.0%" if d == 0 else f"{(100.0 * n / d):.1f}%"


def percentile(nums: List[int], p: int) -> float:
    if not nums:
        return 0.0
    nums = sorted(nums)
    k = (len(nums) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(nums) - 1)
    if f == c:
        return float(nums[f])
    return nums[f] + (nums[c] - nums[f]) * (k - f)


def build_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    logs = [r for r in rows if r.get("type") == "log"]
    breaches = [r for r in logs if r.get("policy") == "breach"]
    dmn_vals = [float(r.get("dmn_proxy", 0.0)) for r in logs if r.get("dmn_proxy") is not None]
    lat_vals = [int(r.get("latency", 0)) for r in logs if r.get("latency") is not None]

    def mean(nums: List[float]) -> float:
        return 0.0 if not nums else sum(nums) / len(nums)

    # reasons histogram
    reason_counts: Dict[str, int] = {}
    for r in logs:
        for reason in r.get("reasons") or []:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    # top terms
    texts = [r.get("text", "") or "" for r in logs]
    tokens: Dict[str, int] = {}
    for t in texts:
        for m in re.findall(r"\b[a-z]{3,}\b", t.lower()):
            if m in {"the", "and", "for", "this", "that", "with", "just", "later", "maybe"}:
                continue
            tokens[m] = tokens.get(m, 0) + 1
    top_tokens = sorted(tokens.items(), key=lambda kv: kv[1], reverse=True)[:8]

    summary = {
        "events": total,
        "logs": len(logs),
        "breaches": len(breaches),
        "breach_rate": 0.0 if len(logs) == 0 else round(100.0 * len(breaches) / len(logs), 1),
        "mean_dmn": round(mean(dmn_vals), 3),
        "max_dmn": round(max(dmn_vals), 3) if dmn_vals else 0.0,
        "mean_latency": round(mean(lat_vals), 1) if lat_vals else 0.0,
        "p95_latency": round(percentile(lat_vals, 95), 0) if lat_vals else 0.0,
        "top_terms": top_tokens,
        "top_reasons": sorted(reason_counts.items(), key=lambda kv: kv[1], reverse=True)[:8],
    }
    return summary


def cmd_analyze(args: argparse.Namespace) -> None:
    rows = tail_jsonl(args.limit)
    if args.json:
        print(json.dumps(build_summary(rows), ensure_ascii=False, indent=2))
        return
    if not rows:
        print("no data")
        return

    # human-readable
    total = len(rows)
    logs = [r for r in rows if r.get("type") == "log"]
    breaches = [r for r in logs if r.get("policy") == "breach"]
    active = [r for r in logs if r.get("mode") == "active"]
    play = [r for r in logs if r.get("mode") == "play"]
    dmn_vals = [float(r.get("dmn_proxy", 0.0)) for r in logs if r.get("dmn_proxy") is not None]
    lat_vals = [int(r.get("latency", 0)) for r in logs if r.get("latency") is not None]

    def mean(nums: List[float]) -> float:
        return 0.0 if not nums else sum(nums) / len(nums)

    # Top textual signals
    texts = [r.get("text", "") or "" for r in logs]
    tokens: Dict[str, int] = {}
    for t in texts:
        for m in re.findall(r"\b[a-z]{3,}\b", t.lower()):
            if m in {"the", "and", "for", "this", "that", "with", "just", "later", "maybe"}:
                continue
            tokens[m] = tokens.get(m, 0) + 1
    top_tokens = sorted(tokens.items(), key=lambda kv: kv[1], reverse=True)[:8]

    print("=== DMN Security Lab Analysis ===")
    print(f"events: {total}  logs:{len(logs)}  breaches:{len(breaches)} ({0.0 if len(logs)==0 else (100.0*len(breaches)/len(logs)):.1f}%)")
    print(f"active logs:{len(active)}  play logs:{len(play)}")
    print(f"mean dmn: {mean(dmn_vals):.3f}  max dmn: {max(dmn_vals) if dmn_vals else 0.0:.3f}")
    if lat_vals:
        print(f"mean latency: {mean(lat_vals):.1f}s  p95 latency: {percentile(lat_vals, 95):.0f}s")
    if top_tokens:
        print("top terms:", ", ".join([f"{w}({c})" for w, c in top_tokens]))
    # reasons histogram
    reason_counts: Dict[str, int] = {}
    for r in logs:
        for reason in (r.get("reasons") or []):
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    if reason_counts:
        top_reasons = sorted(reason_counts.items(), key=lambda kv: kv[1], reverse=True)[:8]
        print("top reasons:", ", ".join([f"{k}({v})" for k, v in top_reasons]))

    # Timeline preview
    preview = rows[-10:]
    print("\n--- last 10 events ---")
    for r in preview:
        ts = r.get("ts")
        et = r.get("type")
        md = r.get("mode", "-")
        dp = r.get("dmn_proxy")
        pol = r.get("policy", "-")
        txt = (r.get("text") or "")[:60]
        if txt and len(r.get("text") or "") > 60:
            txt += "…"
        print(f"{ts}  {et:5}  mode={md:6}  dmn={dp if dp is not None else '-'}  policy={pol:6}  {txt}")

# CLI

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dmn_security_lab.py", description="DMN monitor + focus policy engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("start", help="start a session")
    sp.add_argument("--intent", required=True)
    sp.add_argument("--artifact", required=True)
    sp.add_argument("--mode", choices=["active", "play"], required=True)
    sp.set_defaults(func=cmd_start)

    lp = sub.add_parser("log", help="append a log entry")
    lp.add_argument("--text", required=False, default=None)
    lp.add_argument("--latency", type=int, required=False, default=None)
    lp.add_argument("--output-wpm", type=int, required=False, default=None)
    lp.add_argument("--input-wpm", type=int, required=False, default=None)
    lp.add_argument("--bpm", type=int, required=False, default=None)
    lp.add_argument("--integrity", type=int, required=False, default=None)
    lp.add_argument("--marker", required=False, default=None)
    lp.set_defaults(func=cmd_log)

    tp = sub.add_parser("stop", help="stop current session")
    tp.add_argument("--notes", required=False, default=None)
    tp.set_defaults(func=cmd_stop)

    ap = sub.add_parser("analyze", help="analyze recent entries")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON summary")
    ap.set_defaults(func=cmd_analyze)

    return p


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
