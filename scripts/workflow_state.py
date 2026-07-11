#!/usr/bin/env python3
"""Preflight/gate/record workflow stage transitions and downstream invalidation.

Reads the canonical stage DAG from workflow-contract.json and tracks per-stage
status in a case's stock-meta.json under `stage_records`. `preflight`, `gate`,
and `status` are read-only; `record` is the only command that writes.
"""

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_contract import atomic_write_json  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = REPO_ROOT / "workflow-contract.json"


def load_contract(path=None):
    path = Path(path) if path else CONTRACT_PATH
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _stages_by_id(contract):
    return {stage["id"]: stage for stage in contract["stages"]}


def hash_file(path):
    path = Path(path)
    if not path.exists():
        return None
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _embedded_status(path):
    path = Path(path)
    if path.suffix != ".json":
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    metadata = payload.get("metadata") if isinstance(payload, dict) else None
    if isinstance(metadata, dict):
        return metadata.get("status")
    return None


def _load_meta(case_dir):
    meta_path = Path(case_dir) / "stock-meta.json"
    with open(meta_path, encoding="utf-8") as handle:
        return json.load(handle)


def _iso_utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _latest_source_as_of(case_dir, filenames):
    dates = []
    for filename in filenames:
        path = Path(case_dir) / filename
        if path.suffix != ".json" or not path.exists():
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        metadata = payload.get("metadata") if isinstance(payload, dict) else None
        source_as_of = metadata.get("source_as_of") if isinstance(metadata, dict) else None
        if source_as_of:
            dates.append(source_as_of)
    return max(dates) if dates else None


def gate_stage(case_dir, stage_id, contract, as_of):
    case_dir = Path(case_dir)
    stage = _stages_by_id(contract)[stage_id]
    meta = _load_meta(case_dir)
    stage_records = meta.get("stage_records", {})
    consumable = set(contract["consumable_statuses"])

    blocking_reasons = []

    for dep_id in stage["depends_on"]:
        dep_record = stage_records.get(dep_id)
        if dep_record is None:
            blocking_reasons.append(f"upstream stage not yet recorded: {dep_id}")
            continue
        if dep_record["status"] not in consumable:
            blocking_reasons.append(f"upstream stage {dep_id} is {dep_record['status']}")
            continue
        for filename, recorded_hash in dep_record.get("output_hashes", {}).items():
            current_hash = hash_file(case_dir / filename)
            if current_hash != recorded_hash:
                blocking_reasons.append(
                    f"upstream stage {dep_id} output hash changed: {filename}"
                )
        for filename, recorded_hash in dep_record.get("input_hashes", {}).items():
            # stock-meta.json contains the stage records themselves, so every
            # successful record operation intentionally changes its hash.
            if filename == "stock-meta.json":
                continue
            current_hash = hash_file(case_dir / filename)
            if current_hash != recorded_hash:
                blocking_reasons.append(
                    f"upstream stage {dep_id} input hash changed: {filename}"
                )

    for filename in stage["required_inputs"]:
        path = case_dir / filename
        if not path.exists():
            blocking_reasons.append(f"required input missing: {filename}")
            continue
        embedded_status = _embedded_status(path)
        if embedded_status is not None and embedded_status not in consumable:
            blocking_reasons.append(f"required input {filename} has status {embedded_status}")

    as_of_str = as_of.isoformat() if hasattr(as_of, "isoformat") else as_of

    return {
        "stage_id": stage_id,
        "ready": not blocking_reasons,
        "evaluated_as_of": as_of_str,
        "blocking_reasons": blocking_reasons,
    }


def invalidate_downstream(meta, changed_stage, contract):
    consumers = {}
    for stage in contract["stages"]:
        for dep in stage["depends_on"]:
            consumers.setdefault(dep, []).append(stage["id"])

    stage_records = meta.setdefault("stage_records", {})
    visited = set()
    stack = [changed_stage]
    invalidated = []
    while stack:
        current = stack.pop()
        for consumer in consumers.get(current, []):
            if consumer in visited:
                continue
            visited.add(consumer)
            record = stage_records.get(consumer)
            if record is not None and record.get("status") != "stale":
                record["status"] = "stale"
                invalidated.append(consumer)
            stack.append(consumer)
    return invalidated


def record_stage(case_dir, stage_id, contract, as_of=None):
    case_dir = Path(case_dir)
    stage = _stages_by_id(contract)[stage_id]
    meta = _load_meta(case_dir)
    consumable = set(contract["consumable_statuses"])

    input_hashes = {}
    gate = gate_stage(case_dir, stage_id, contract, as_of or date.today())
    issues = list(gate["blocking_reasons"])
    for filename in stage["required_inputs"]:
        path = case_dir / filename
        file_hash = hash_file(path)
        input_hashes[filename] = file_hash
        if file_hash is None:
            issues.append(f"missing required input: {filename}")
            continue
        embedded_status = _embedded_status(path)
        if embedded_status is not None and embedded_status not in consumable:
            issues.append(f"required input {filename} has status {embedded_status}")

    output_hashes = {}
    own_statuses = []
    for filename in stage["outputs"]:
        path = case_dir / filename
        file_hash = hash_file(path)
        output_hashes[filename] = file_hash
        if file_hash is None:
            issues.append(f"missing output: {filename}")
        else:
            embedded_status = _embedded_status(path)
            if embedded_status is not None:
                own_statuses.append(embedded_status)

    if issues:
        status = "blocked"
    elif own_statuses:
        status_rank = {"pass": 0, "degraded": 1, "stale": 2, "blocked": 3, "failed": 4}
        status = max(own_statuses, key=lambda value: status_rank.get(value, 99))
    else:
        status = "pass"

    previous_record = meta.get("stage_records", {}).get(stage_id)
    previous_output_hashes = (previous_record or {}).get("output_hashes", {})
    output_changed = bool(previous_output_hashes) and previous_output_hashes != output_hashes

    record = {
        "status": status,
        "checked_at": _iso_utc_now(),
        "source_as_of": _latest_source_as_of(case_dir, stage["required_inputs"]),
        "input_hashes": input_hashes,
        "output_hashes": output_hashes,
        "issues": issues,
    }

    meta.setdefault("stage_records", {})[stage_id] = record

    invalidated = []
    if output_changed:
        invalidated = invalidate_downstream(meta, stage_id, contract)

    atomic_write_json(case_dir / "stock-meta.json", meta)

    result = dict(record)
    result["invalidated_downstream"] = invalidated
    return result


def preflight(case_dir, contract):
    return {
        stage["id"]: gate_stage(case_dir, stage["id"], contract, date.today())
        for stage in contract["stages"]
    }


def status(case_dir, contract):
    meta = _load_meta(case_dir)
    stage_records = meta.get("stage_records", {})
    terminal_stage = contract["terminal_stage"]
    terminal_record = stage_records.get(terminal_stage)
    complete = terminal_record is not None and terminal_record["status"] in contract["consumable_statuses"]
    return {
        "complete": complete,
        "terminal_stage": terminal_stage,
        "stage_records": stage_records,
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("case_dir")
    preflight_parser.add_argument("--json", action="store_true")

    gate_parser = subparsers.add_parser("gate")
    gate_parser.add_argument("case_dir")
    gate_parser.add_argument("stage_id")
    gate_parser.add_argument("--as-of")
    gate_parser.add_argument("--json", action="store_true")

    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("case_dir")
    record_parser.add_argument("stage_id")
    record_parser.add_argument("--json", action="store_true")

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("case_dir")
    status_parser.add_argument("--json", action="store_true")

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    contract = load_contract()

    if args.command == "preflight":
        result = preflight(args.case_dir, contract)
    elif args.command == "gate":
        as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
        result = gate_stage(args.case_dir, args.stage_id, contract, as_of)
    elif args.command == "record":
        result = record_stage(args.case_dir, args.stage_id, contract)
    elif args.command == "status":
        result = status(args.case_dir, contract)
    else:
        raise ValueError(f"unknown command: {args.command}")

    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
