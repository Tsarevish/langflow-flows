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
import os
from schema_snapshot import SCHEMA_VERSION, compact, extract_components
from probe_stand import atomic_write

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "profiles" / "current" / "components.json"
ENV = Path.home() / ".langflow" / "env"

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


def main() -> int:
    ap = argparse.ArgumentParser(description="Снапшот схем компонентов Langflow")
    ap.add_argument("--url", default=None)
    ap.add_argument("--key", default=None)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    cfg = read_env()
    url = args.url or os.environ.get("LANGFLOW_URL") or os.environ.get("LANGFLOW_SERVER_URL") or cfg.get("LANGFLOW_URL")
    key = args.key if args.key is not None else os.environ.get("LANGFLOW_API_KEY", cfg.get("LANGFLOW_API_KEY", ""))
    if not url:
        print("не задан URL: укажи --url или LANGFLOW_URL в ~/.langflow/env", file=sys.stderr)
        return 2

    version = "?"
    try:
        version = fetch(url, key, "/api/v1/version").get("version", "?")
    except Exception as e:  # noqa: BLE001
        print("version unavailable; previous snapshot preserved", file=sys.stderr)
        return 1

    if version == "?":
        print("version unavailable; previous snapshot preserved", file=sys.stderr)
        return 1

    try:
        allc = fetch(url, key, "/api/v1/all")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} на /api/v1/all", file=sys.stderr)
        return 1

    try:
        components = extract_components(allc)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    doc = {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "langflow_version": version,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": url,
            "component_count": len(components),
        },
        "components": components,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(out, json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True))
    size = out.stat().st_size
    print(f"записано: {out} ({len(components)} типов, {size/1024:.0f} КБ)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
