"""Eval-набор: 12 сценариев против живого Langflow.

    python tests/run_eval.py            # все
    python tests/run_eval.py 05 09      # выборочно
    python tests/run_eval.py --json

Метрики по каждому сценарию:
  errors   — ошибки офлайн-валидатора до отправки (E*)
  warns    — предупреждения валидатора
  created  — удалось ли создать флоу
  ran      — удалось ли получить ответ
  match    — ответ похож на ожидаемый

Печатается сводка: сколько сценариев прошло с первого прохода.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate_spec as V  # noqa: E402

sys.path.insert(0, str(HERE.parent.parent / "tools"))
import lfx_rest as R  # noqa: E402
import mcp_call as M  # noqa: E402

CASES = HERE / "eval" / "cases"
MANIFEST = HERE / "eval" / "cases.json"


def db_url() -> str | None:
    """Строка подключения берётся из рабочего флоу владельца."""
    st, flows = R.json_request("/api/v1/flows/?page=1&size=100")
    for f in flows if isinstance(flows, list) else []:
        if "V3" in str(f.get("name", "")):
            st, flow = R.get_flow(f["id"])
            for n in flow["data"]["nodes"]:
                t = (n.get("data") or {}).get("node", {}).get("template") or {}
                if (n.get("data") or {}).get("type") == "SQLComponent":
                    return t.get("database_url", {}).get("value")
    return None


def _profile() -> str | None:
    """Снапшот для офлайн-проверки: из LANGFLOW_PROFILE или первый профиль по алфавиту."""
    env = os.environ.get("LANGFLOW_PROFILE")
    if env:
        return str(Path(env) / "components.json")
    found = sorted((ROOT / "profiles").glob("*/components.json"))
    return str(found[0]) if found else None


def offline_check(spec_path: Path) -> tuple[int, int]:
    snap = V.load_snapshot(Path(_profile()) if _profile() else V.find_snapshot())
    findings: list[V.Finding] = []
    spec = V.parse_spec(spec_path.read_text(encoding="utf-8"), findings)
    findings.extend(V.validate(spec, snap))
    errs = sum(1 for f in findings if f.severity == "error")
    warns = sum(1 for f in findings if f.severity == "warning")
    return errs, warns


def patch_sql(flow_id: str, url: str) -> None:
    st, flow = R.get_flow(flow_id)
    changed = False
    for n in flow["data"]["nodes"]:
        if (n.get("data") or {}).get("type") == "SQLComponent":
            n["data"]["node"]["template"]["database_url"]["value"] = url
            changed = True
    if changed:
        R.json_request(f"/api/v1/flows/{flow_id}", "PUT",
                       {"name": flow.get("name"), "description": flow.get("description"),
                        "data": flow["data"]})


def answer_text(run: dict) -> str:
    data = run.get("data") or {}
    parts = []
    try:
        for o in data.get("outputs") or []:
            for rr in (o.get("outputs") or []):
                for k, v in (rr.get("results") or {}).items():
                    t = (v.get("data") or {}).get("text")
                    if t:
                        parts.append(str(t))
    except Exception:  # noqa: BLE001
        pass
    return "\n".join(parts) or (run.get("text") or "")


def main(argv: list[str]) -> int:
    only = {a for a in argv if not a.startswith("-")}
    as_json = "--json" in argv
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["cases"]
    db = db_url()

    results = []
    for case in manifest:
        if only and case["id"] not in only:
            continue
        spec_path = CASES / case["spec"]
        row = {"id": case["id"], "title": case["title"], "kind": case["kind"]}
        # для правок оцениваем целевое состояние, а не промежуточное
        check_path = CASES / case["update"] if case["kind"] == "edit" else spec_path
        row["errors"], row["warns"] = offline_check(check_path)
        if row["errors"]:
            row.update(created=False, ran=False, match=False, note="не отправлен: ошибки валидатора")
            results.append(row)
            continue

        r = M.call_tool("create_flow_from_spec",
                        {"spec": spec_path.read_text(encoding="utf-8"), "validate": False})
        row["created"] = not r["isError"]
        if not row["created"]:
            row.update(ran=False, match=False, note=(r.get("text") or "")[:150])
            results.append(row)
            continue
        fid = (r.get("data") or {}).get("id")

        if case["kind"] == "edit":
            upd = (CASES / case["update"]).read_text(encoding="utf-8")
            u = M.call_tool("update_flow_from_spec", {"flow_id": fid, "spec": upd})
            row["updated"] = not u["isError"]
            if u["isError"]:
                row.update(ran=False, match=False, note=("правка: " + (u.get("text") or "")[:120]))
                R.request(f"/api/v1/flows/{fid}", "DELETE")
                results.append(row)
                continue

        if db:
            patch_sql(fid, db)

        run = M.call_tool("run_flow", {"flow_id": fid, "input_value": case["input"]})
        text = answer_text(run)
        row["ran"] = not run["isError"]
        row["answer"] = text.strip().replace("\n", " ")[:160]
        if case.get("expect") is not None:
            row["match"] = case["expect"] in text
        else:
            row["match"] = bool(re.search(case["expect_regex"], text, re.S))
        if not row["ran"]:
            row["note"] = (run.get("text") or "")[:120]
        results.append(row)
        R.request(f"/api/v1/flows/{fid}", "DELETE")

    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    else:
        print(f"{'id':<3} {'созд':<5} {'запуск':<7} {'ответ':<6} {'E/W':<6} сценарий")
        for r in results:
            ok = lambda v: "да" if v else "НЕТ"  # noqa: E731
            print(f"{r['id']:<3} {ok(r['created']):<5} {ok(r['ran']):<7} {ok(r['match']):<6} "
                  f"{r['errors']}/{r['warns']:<4} {r['title']}")
            if not r["ran"] or not r["match"]:
                print(f"     ответ: {r.get('answer','—')}")
                if r.get("note"):
                    print(f"     примечание: {r['note']}")

    total = len(results)
    passed = sum(1 for r in results if r["match"])
    build = [r for r in results if r["kind"] == "build"]
    clean = sum(1 for r in build if r["errors"] == 0 and r["match"])
    summary = (f"итог: {passed}/{total} сценариев с ожидаемым ответом; "
               f"без ошибок валидатора и с ответом: {clean}/{len(build)}")
    if as_json:
        print(summary, file=sys.stderr)
    else:
        print(f"\n{summary}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
