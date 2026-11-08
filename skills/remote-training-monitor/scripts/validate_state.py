#!/usr/bin/env python3
"""Validate a monitor's state.json against state.schema.json.

Standard library only. Supports the subset of JSON Schema the state file uses:
type (including lists and "null"), enum, required, properties,
additionalProperties (false or a schema), pattern, minLength, maxLength,
minimum and items.

Usage:
    validate_state.py <path/to/state.json> [--schema <path>]

Exit 0 when valid. Exit 1 with one line per violation otherwise.
"""

import json
import re
import sys
from pathlib import Path

TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def type_ok(value, names):
    for name in names:
        if name == "integer" and isinstance(value, bool):
            continue
        if name == "number" and isinstance(value, bool):
            continue
        if isinstance(value, TYPES[name]):
            return True
    return False


def check(value, schema, path, errors):
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not one of {schema['enum']}")
        return
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not type_ok(value, names):
            errors.append(f"{path}: expected {'/'.join(names)}, got {type(value).__name__}")
            return
    if value is None:
        return
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']} characters; ids stay short, prose goes to History")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} is below {schema['minimum']}")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required field {key!r}")
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in props:
                check(item, props[key], f"{path}.{key}", errors)
            elif extra is False:
                errors.append(f"{path}: unknown field {key!r}")
            elif isinstance(extra, dict):
                check(item, extra, f"{path}.{key}", errors)
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            check(item, schema["items"], f"{path}[{i}]", errors)


def semantic(state, errors):
    """Cross-field rules the schema cannot express."""
    if state.get("run_state") != "RUNNING" and state.get("health") is not None:
        errors.append("health: must be null unless run_state is RUNNING")
    monitor = state.get("monitor") or {}
    if monitor.get("state") == "WATCHING" and state.get("heartbeat") is None:
        errors.append("heartbeat: WATCHING needs a recorded heartbeat")
    if monitor.get("state") in ("WAITING", "OFF") and not monitor.get("reason"):
        errors.append(f"monitor.reason: required when monitor.state is {monitor.get('state')}")
    hb = state.get("heartbeat") or {}
    if hb.get("mode") == "interval" and not hb.get("interval_min"):
        errors.append("heartbeat.interval_min: required for an interval heartbeat")
    if hb.get("mode") == "completion" and hb.get("interval_min"):
        errors.append("heartbeat.interval_min: a completion waiter has no interval")
    if state.get("run_state") in ("QUEUED", "RUNNING", "PASSED", "FAILED", "CANCELLED") and not state.get("current_attempt"):
        errors.append("current_attempt: required once anything is submitted")


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 2
    state_path = Path(argv[1])
    schema_path = Path(__file__).resolve().parent.parent / "state.schema.json"
    if "--schema" in argv:
        schema_path = Path(argv[argv.index("--schema") + 1])
    try:
        state = json.loads(state_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"{state_path}: cannot read as JSON: {exc}")
        return 1
    schema = json.loads(schema_path.read_text())
    errors = []
    check(state, schema, "state", errors)
    if not errors:
        semantic(state, errors)
    if errors:
        for line in errors:
            print(f"{state_path}: {line}")
        return 1
    print(f"{state_path}: valid")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
