"""Обновить только снапшот схем компонентов (без полного профиля стенда).

Запуск (нужен доступ к инстансу и ключ в ~/.langflow/env):

    python scripts/dump_schema.py [--url URL] [--out PATH]

Обычно не нужен: `probe_stand.py` снимает и профиль, и снапшот сразу.
Этот скрипт полезен, когда профиль есть, а версия Langflow сменилась
и надо перегенерировать только схемы.

Снапшот намеренно урезан: только то, что нужно валидатору — выходы, входы, поля.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "profiles" / "current" / "components.json"
ENV = Path.home() / ".langflow" / "env"

# У этих узлов нет режима «инструмент»: они сами вход/выход флоу.
NON_TOOL = {"ChatInput", "ChatOutput", "TextInput", "TextOutput", "Webhook", "Note"}


def read_env() -> dict[str, str]:
    cfg: dict[str, str] = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg


def fetch(url: str, key: str, path: str, timeout: int = 120):
    req = urllib.request.Request(url.rstrip("/") + path, method="GET")
    req.add_header("accept", "application/json")
    req.add_header("accept-encoding", "gzip")
    if key:
        req.add_header("x-api-key", key)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if (r.headers.get("content-encoding") or "") == "gzip":
            import gzip

            raw = gzip.decompress(raw)
        return json.loads(raw)


def compact(template: dict) -> tuple[list[dict], list[dict], dict[str, dict]]:
    """(порты-выходы, порты-входы, поля) из одного компонента."""
    outputs = []
    for o in template.get("outputs") or []:
        if not isinstance(o, dict):
            continue
        outputs.append({
            "name": o.get("name"),
            "types": o.get("types") or [],
            "group": bool(o.get("group_outputs")),
        })

    fields = template.get("template") or {}
    inputs = []
    plain_fields = {}
    for name, f in fields.items():
        if not isinstance(f, dict):
            continue
        plain_fields[name] = {
            "type": f.get("type"),
            "required": bool(f.get("required")),
            "password": bool(f.get("password")),
            "options": len(f["options"]) if isinstance(f.get("options"), list) else 0,
        }
        itypes = f.get("input_types")
        if itypes:
            inputs.append({
                "name": name,
                "input_types": itypes,
                "type": f.get("type"),
                "required": bool(f.get("required")),
            })
    return outputs, inputs, plain_fields


def main() -> int:
    ap = argparse.ArgumentParser(description="Снапшот схем компонентов Langflow")
    ap.add_argument("--url", default=None)
    ap.add_argument("--key", default=None)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    cfg = read_env()
    url = args.url or cfg.get("LANGFLOW_URL")
    key = args.key or cfg.get("LANGFLOW_API_KEY", "")
    if not url:
        print("не задан URL: укажи --url или LANGFLOW_URL в ~/.langflow/env", file=sys.stderr)
        return 2

    version = "?"
    try:
        version = fetch(url, key, "/api/v1/version").get("version", "?")
    except Exception as e:  # noqa: BLE001
        print(f"версия недоступна: {e}", file=sys.stderr)

    try:
        allc = fetch(url, key, "/api/v1/all")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} на /api/v1/all", file=sys.stderr)
        return 1

    components = {}
    for category, types in allc.items():
        if not isinstance(types, dict):
            continue
        for ctype, spec in types.items():
            if not isinstance(spec, dict):
                continue
            outputs, inputs, fields = compact(spec)
            # В сыром шаблоне нет порта component_as_tool: он появляется в режиме
            # инструмента (MCP-описание его показывает). Добавляем синтетически,
            # иначе валидатор будет отвергать корректную связь с Agent.tools.
            if ctype not in NON_TOOL and outputs:
                outputs.append({"name": "component_as_tool", "types": ["Tool"], "group": False})
            components[ctype] = {
                "category": category,
                "display_name": spec.get("display_name"),
                "tool_mode": bool(spec.get("tool_mode")),
                "outputs": outputs,
                "inputs": inputs,
                "fields": fields,
            }

    doc = {
        "meta": {
            "langflow_version": version,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": url,
            "component_count": len(components),
        },
        "components": components,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    size = out.stat().st_size
    print(f"записано: {out} ({len(components)} типов, {size/1024:.0f} КБ)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
