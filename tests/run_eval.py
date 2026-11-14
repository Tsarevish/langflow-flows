"""Integration eval of supplied specs. --check-only is offline; --live mutates a test stand."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import validate_spec as V
from langflow_client import Client
from probe_stand import read_env

CASES = ROOT / "tests" / "eval" / "cases"
MANIFEST = ROOT / "tests" / "eval" / "cases.json"


def answer_text(run: dict) -> str:
    parts = []
    for group in run.get("outputs") or []:
        for output in group.get("outputs") or []:
            for value in (output.get("results") or {}).values():
                if isinstance(value, dict):
                    text = value.get("text") or (value.get("data") or {}).get("text")
                    if text:
                        parts.append(str(text))
    return "\n".join(parts)


def tool_called(document, pattern: str) -> bool:
    """Require a completed successful execution, not a model's request to call a tool."""
    if isinstance(document, list):
        return any(tool_called(item, pattern) for item in document)
    if not isinstance(document, dict):
        return False
    event = document.get("event") or document.get("type")
    if event in {"on_tool_end", "tool_end", "tool_use", "tool_result"}:
        payload = document.get("data") if isinstance(document.get("data"), dict) else document
        output = document.get("output", payload.get("output"))
        name = document.get("name") or payload.get("name") or document.get("tool_name")
        if isinstance(output, dict):
            name = name or output.get("name")
            succeeded = output.get("status") == "success" and not output.get("error")
            if re.search(pattern, str(name or ""), re.I) and succeeded and not document.get("error"):
                return True
    return any(tool_called(v, pattern) for k, v in document.items()
               if k not in {"inputs", "input", "template", "config", "text", "prompt", "tool_calls"})


def matched(text: str, step: dict) -> bool:
    if not text.strip():
        return False
    positive = step.get("expect") in text if "expect" in step else bool(re.search(step.get("expect_regex", r"\S"), text))
    return positive and not (step.get("reject_regex") and re.search(step["reject_regex"], text))


def branch_observed(run: dict, alias: str) -> bool:
    """Each router output uses an explicit sender marker in its ChatOutput config."""
    markers = []
    for group in run.get("outputs") or []:
        for output in group.get("outputs") or []:
            for value in (output.get("results") or {}).values():
                if isinstance(value, dict):
                    body = value.get("data") if isinstance(value.get("data"), dict) else value
                    if body.get("text"):
                        markers.append(body.get("sender_name"))
    return markers == ["EVAL_" + alias]


def passed(row: dict) -> bool:
    return (row.get("errors") == 0 and row.get("created") is True
            and row.get("updated", True) is True and row.get("ran") is True
            and row.get("match") is True and row.get("evidence", True) is True
            and row.get("cleaned") is True)


def run_failed(value, *, root=True) -> bool:
    if value is False:
        return root
    if isinstance(value, list):
        return any(run_failed(item, root=False) for item in value)
    if not isinstance(value, dict):
        return False
    if value.get("success") is False or value.get("valid") is False or value.get("error") or value.get("errors"):
        return True
    return any(run_failed(item, root=False) for key, item in value.items() if key not in {"inputs", "input", "text"})


def redact_artifact(value, secrets=()):
    if isinstance(value, dict):
        return {k: "[REDACTED]" if re.search(r"api.?key|password|authorization|database_url|access.?token", k, re.I)
                else redact_artifact(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_artifact(v, secrets) for v in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
    return value


def prepare(path: Path, settings: dict) -> str:
    text = path.read_text(encoding="utf-8")
    for token, key in (("__MODEL_BASE__", "model_base"), ("__MODEL_NAME__", "model_name")):
        if token in text:
            if not settings.get(key):
                raise ValueError(f"missing {key}; configure eval model explicitly")
            value = settings[key]
            if "\n" in value or "\r" in value:
                raise ValueError(f"invalid {key}")
            text = text.replace(token, value)
    if settings.get("model_type"):
        text = text.replace("ext:openai:OpenAIModelComponent@official", settings["model_type"])
    return text


def offline_check(text: str, snap: dict, settings: dict | None = None) -> tuple[int, int]:
    findings = []
    spec = V.parse_spec(text, findings)
    external = {(nid, "database_url") for nid, ntype in spec.nodes
                if ntype == "SQLComponent" and (settings or {}).get("database_url")}
    findings += V.validate(spec, snap, external_fields=external)
    return (sum(f.severity == "error" for f in findings), sum(f.severity == "warning" for f in findings))


def bind_settings(client: Client, fid: str, settings: dict) -> None:
    flow = client.request(f"/api/v1/flows/{fid}")
    changed = False
    for node in flow["data"]["nodes"]:
        template = (node.get("data") or {}).get("node", {}).get("template") or {}
        model_type = settings.get("model_type") or "ext:openai:OpenAIModelComponent@official"
        if node.get("data", {}).get("type") == model_type and "api_key" in template and settings.get("credential"):
            template["api_key"].update(value=settings["credential"], load_from_db=True)
            changed = True
        if node.get("data", {}).get("type") == "SQLComponent":
            if not settings.get("database_url"):
                raise ValueError("SQL test requires LANGFLOW_EVAL_DATABASE_URL for a dedicated test DB")
            template["database_url"].update(value=settings["database_url"], load_from_db=False)
            changed = True
    if changed:
        client.request(f"/api/v1/flows/{fid}", "PUT", {"name": flow.get("name"), "data": flow["data"]})


def evaluate(case: dict, text: str, update: str | None, snap: dict, client: Client, settings: dict) -> dict:
    row = {"id": case["id"], "title": case["title"], "created": False, "ran": False,
           "match": False, "evidence": True, "cleaned": False, "sessions": []}
    checks = [offline_check(text, snap, settings)] + ([offline_check(update, snap, settings)] if update else [])
    row["errors"], row["warns"] = map(sum, zip(*checks))
    fid = None
    try:
        if row["errors"]:
            return row
        created = client.tool("create_flow_from_spec", {"spec": text, "validate": False})
        data = created.get("data")
        fid = data.get("id") if isinstance(data, dict) else None
        row["created"] = not created["isError"] and bool(fid)
        if not row["created"]:
            return row
        row["flow_id"] = fid
        if update:
            result = client.tool("update_flow_from_spec", {"flow_id": fid, "spec": update})
            row["updated"] = not result["isError"]
            if not row["updated"]:
                return row
        bind_settings(client, fid, settings)
        # Unique sessions prevent accidental reuse of previous eval history.
        prefix = f"eval-{uuid.uuid4().hex}"
        steps = case.get("steps") or [{"input": case["input"], **{k: case[k] for k in ("expect", "expect_regex") if k in case}}]
        outcomes = []
        for index, step in enumerate(steps):
            session_id = prefix + "-" + step.get("session", "main")
            if session_id not in row["sessions"]:
                row["sessions"].append(session_id)
            run = client.request(f"/api/v1/run/{fid}", "POST", {
                "input_value": step["input"], "session_id": session_id,
                "input_type": "chat", "output_type": "chat"})
            if settings.get("artifact_dir"):
                directory = Path(settings["artifact_dir"])
                directory.mkdir(parents=True, exist_ok=True)
                artifact = {"flow_id": fid, "session_id": session_id, "input": step["input"], "response": run}
                (directory / f"{case['id']}-{index}.json").write_text(json.dumps(
                    redact_artifact(artifact, settings.get("redact_values", [])), ensure_ascii=False, indent=2), encoding="utf-8")
            answer = answer_text(run) if isinstance(run, dict) else ""
            ran = isinstance(run, dict) and not run_failed(run) and bool(answer.strip())
            evidence = True
            if step.get("output_alias"):
                evidence = branch_observed(run, step["output_alias"])
            if case.get("require_tool"):
                tool_evidence = tool_called(run, case["require_tool"])
                if not tool_evidence:
                    trace = client.tool("get_build_results", {"flow_id": fid})
                    trace_data = trace.get("data")
                    # A cached result from a previous execution is not evidence.
                    same_run = (isinstance(trace_data, dict) and run.get("run_id")
                                and trace_data.get("run_id") == run["run_id"])
                    tool_evidence = bool(same_run and not trace["isError"] and tool_called(trace_data, case["require_tool"]))
                evidence = evidence and tool_evidence
            outcomes.append({"ran": ran, "match": ran and matched(answer, step), "evidence": evidence,
                             "session_id": session_id, "answer": answer})
        row.update(ran=all(o["ran"] for o in outcomes), match=all(o["match"] for o in outcomes),
                   evidence=all(o["evidence"] for o in outcomes), steps=outcomes)
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        # Don't echo server bodies, model output or connection strings.
        row["note"] = (str(exc) if isinstance(exc, RuntimeError) and str(exc).startswith(("HTTP ", "MCP "))
                       else f"{type(exc).__name__}: test could not complete; inspect stand privately")
    finally:
        if fid:
            try:
                client.request(f"/api/v1/flows/{fid}", "DELETE")
                row["cleaned"] = True
            except (RuntimeError, ValueError):
                row["cleanup_flow_id"] = fid
        else:
            row["cleaned"] = True  # No flow was created, so no deletion is needed.
        row["passed"] = passed(row)
    return row


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="*")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--url")
    parser.add_argument("--env", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--artifact-dir", type=Path, help="write redacted run responses for review")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument("--live", action="store_true", help="create/run/delete disposable test flows")
    args = parser.parse_args(argv)
    try:
        snap = V.load_snapshot(Path(args.profile) / "components.json")
        cfg = read_env(args.env)
        cfg.update(os.environ)
        settings = {name: cfg.get(env, "") for name, env in {
            "model_base": "LANGFLOW_EVAL_MODEL_BASE", "model_name": "LANGFLOW_EVAL_MODEL_NAME",
            "model_type": "LANGFLOW_EVAL_MODEL_TYPE", "credential": "LANGFLOW_EVAL_CREDENTIAL",
            "database_url": "LANGFLOW_EVAL_DATABASE_URL"}.items()}
        settings["artifact_dir"] = args.artifact_dir
        settings["redact_values"] = [cfg.get("LANGFLOW_API_KEY"), settings["database_url"]]
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["cases"]
        selected = [c for c in manifest if not args.ids or c["id"] in args.ids]
        if not selected or set(args.ids) - {c["id"] for c in manifest}:
            raise ValueError("unknown/empty case selection")
        # Validate all inputs before creating anything.
        prepared = [(c, prepare(CASES / c["spec"], settings), prepare(CASES / c["update"], settings) if c.get("update") else None) for c in selected]
        client = None
        if args.live:
            url = args.url or cfg.get("LANGFLOW_URL") or cfg.get("LANGFLOW_SERVER_URL")
            if not url:
                raise ValueError("missing target URL")
            expected = snap.get("meta", {}).get("url") or snap.get("meta", {}).get("source")
            if expected and expected.rstrip("/") != url.rstrip("/"):
                raise ValueError("snapshot belongs to a different stand")
            if any("__MODEL_NAME__" in (CASES / c["spec"]).read_text(encoding="utf-8") for c in selected) and not settings["credential"]:
                raise ValueError("set LANGFLOW_EVAL_CREDENTIAL to a configured variable name")
            if any("SQLComponent" in text for _, text, _ in prepared) and not settings["database_url"]:
                raise ValueError("set LANGFLOW_EVAL_DATABASE_URL to a dedicated test database")
            client = Client(url, cfg.get("LANGFLOW_API_KEY", ""))
            version = client.request("/api/v1/version")
            if version.get("version") != snap.get("meta", {}).get("langflow_version"):
                raise ValueError("snapshot version mismatch; refresh profile")
            if settings["credential"]:
                variables = client.request("/api/v1/variables/")
                if not isinstance(variables, list) or settings["credential"] not in {v.get("name") for v in variables if isinstance(v, dict)}:
                    raise ValueError("configured credential variable not found on the target stand")
        results = []
        for case, text, update in prepared:
            if args.check_only:
                checks = [offline_check(text, snap, settings)] + ([offline_check(update, snap, settings)] if update else [])
                errors, warns = map(sum, zip(*checks))
                results.append({"id": case["id"], "errors": errors, "warns": warns, "offline_ok": errors == 0})
            else:
                results.append(evaluate(case, text, update, snap, client, settings))
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0 if all(r.get("offline_ok") if args.check_only else r.get("passed") for r in results) else 1
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"eval configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
