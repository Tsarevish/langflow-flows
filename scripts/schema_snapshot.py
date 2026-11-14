"""Shared, conservative extraction of /api/v1/all. Never persist credential values."""
from __future__ import annotations

SCHEMA_VERSION = 2
SKIP_CATEGORIES = {"component_display_names"}


def compact(spec: dict) -> tuple[list[dict], list[dict], dict]:
    outputs = [{"name": o["name"], "types": o.get("types") or [],
                "group": bool(o.get("group_outputs")), "provenance": "declared"}
               for o in spec.get("outputs") or [] if isinstance(o, dict) and o.get("name")]
    inputs, fields = [], {}
    for name, f in (spec.get("template") or {}).items():
        if not isinstance(f, dict):
            continue
        # Presence is enough for required-field checks; values may be sensitive.
        meta = {k: f[k] for k in ("type", "required", "password", "load_from_db",
                                 "tool_mode", "dynamic", "real_time_refresh", "list") if k in f}
        meta["has_default"] = "value" in f and f["value"] is not None and f["value"] != ""
        if isinstance(f.get("options"), list) and not f.get("password"):
            meta["options"] = f["options"]
        fields[name] = meta
        if f.get("input_types"):
            inputs.append({"name": name, "input_types": f["input_types"], **meta})
    # Output-level tool_mode is NOT evidence of tool capability.
    supports_tool = any(f.get("tool_mode") is True for f in fields.values()) or spec.get("add_tool_output") is True
    if supports_tool and not any(o["name"] == "component_as_tool" for o in outputs):
        outputs.append({"name": "component_as_tool", "types": ["Tool"], "group": False,
                        "provenance": "inferred_tool_mode"})
    return outputs, inputs, fields


def extract_components(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("/api/v1/all must return an object")
    result = {}
    for category, types in raw.items():
        if category in SKIP_CATEGORIES or not isinstance(types, dict):
            continue
        for name, spec in types.items():
            if not isinstance(spec, dict) or not isinstance(spec.get("template"), dict):
                continue
            outputs, inputs, fields = compact(spec)
            result[name] = {"category": category, "display_name": spec.get("display_name"),
                            "outputs": outputs, "inputs": inputs, "fields": fields,
                            "tool_capability": "declared" if any(o["name"] == "component_as_tool" and o["provenance"] == "declared" for o in outputs)
                            else "inferred" if any(o["name"] == "component_as_tool" for o in outputs) else "unknown"}
    if not result:
        raise ValueError("empty component schema; previous snapshot was not replaced")
    return result
