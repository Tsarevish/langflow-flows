"""Снять профиль стенда Langflow: что за версия, что доступно, какие ограничения видны.

    python scripts/probe_stand.py                 # URL и ключ из ~/.langflow/env
    python scripts/probe_stand.py --url URL --key KEY
    python scripts/probe_stand.py --out profiles/my-stand

Пишет в каталог профиля:
  profile.md        — ручная карточка (сохраняется при обновлении)
  profile.auto.md   — измеренные сведения последней разведки
  profile.json      — те же данные машинно
  components.json   — снапшот схем компонентов (для validate_spec.py)

Что НЕ определяется автоматически (записывается как «требует проверки»):
лимит времени на запуск, число параллельных запросов к модели, политика записи
файлов, поддержка xlsx/docx/картинок. Их уточняют у эксплуатации или проверяют
опытом — см. references/recon.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ENV = Path.home() / ".langflow" / "env"
from schema_snapshot import SCHEMA_VERSION, compact, extract_components


# ------------------------------------------------------------------ транспорт


def read_env(path: Path | None = None) -> dict[str, str]:
    path = path or ENV
    cfg: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg


class Api:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.key = key

    def call(self, path: str, method: str = "GET", body=None, headers=None, timeout: int = 120):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.url + path, data=data, method=method)
        req.add_header("accept", "application/json, text/event-stream")
        req.add_header("accept-encoding", "gzip")
        if data is not None:
            req.add_header("content-type", "application/json")
        if self.key:
            req.add_header("x-api-key", self.key)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if (r.headers.get("content-encoding") or "") == "gzip":
                    import gzip

                    raw = gzip.decompress(raw)
                return r.status, raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            raw = e.read()
            return e.code, raw.decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            return None, repr(e)


# ------------------------------------------------------------------ компоненты


def mcp_tools(api: Api) -> dict:
    """Список инструментов встроенного MCP-сервера, если он есть."""
    status, body = api.call("/api/v1/agentic/mcp", "POST", {
        "jsonrpc": "2.0", "id": 1, "method": "tools/list",
    }, headers={"accept": "application/json, text/event-stream"})
    if status != 200:
        return {"available": False, "status": status, "detail": body[:160]}
    msgs = []
    for line in body.splitlines():
        if line.startswith("data:"):
            try:
                msgs.append(json.loads(line[5:].strip()))
            except Exception:  # noqa: BLE001
                pass
    if not msgs:
        try:
            msgs = [json.loads(body)]
        except Exception:  # noqa: BLE001
            msgs = []
    for m in msgs:
        tools = (m.get("result") or {}).get("tools")
        if tools is not None:
            return {"available": True, "count": len(tools),
                    "names": sorted(t.get("name") for t in tools)}
    return {"available": False, "detail": body[:160]}


# ------------------------------------------------------------------ вывод


def slugify(url: str) -> str:
    host = re.sub(r"^https?://", "", url).rstrip("/")
    host = re.sub(r"[^A-Za-z0-9._-]+", "-", host)
    return f"stand-{host}"


def atomic_write(path: Path, text: str) -> None:
    import tempfile
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Профиль стенда Langflow")
    ap.add_argument("--url", default=None, help="адрес стенда; по умолчанию из --env")
    ap.add_argument("--key", default=None, help="API-ключ; по умолчанию из --env")
    ap.add_argument("--env", default=str(ENV), help="файл с LANGFLOW_URL и LANGFLOW_API_KEY")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    cfg = read_env(Path(args.env))
    url = args.url or os.environ.get("LANGFLOW_URL") or os.environ.get("LANGFLOW_SERVER_URL") or cfg.get("LANGFLOW_URL")
    key = args.key if args.key is not None else os.environ.get("LANGFLOW_API_KEY", cfg.get("LANGFLOW_API_KEY", ""))

    if not url:
        print(f"нет URL: задай --url или положи LANGFLOW_URL в {args.env}")
        return 2

    api = Api(url, key)
    out_dir = Path(args.out) if args.out else SKILL / "profiles" / slugify(url)

    def get_json(path: str):
        st, body = api.call(path)
        try:
            return st, json.loads(body)
        except Exception:  # noqa: BLE001
            return st, {"_raw": body[:200]}

    st_version, version = get_json("/api/v1/version")
    st_cfg, config = get_json("/api/v1/config")
    st_me, me = get_json("/api/v1/users/whoami")
    st_models, models = get_json("/api/v1/models")
    st_vars, variables = get_json("/api/v1/variables/")
    st_flows, flows = get_json("/api/v1/flows/?page=1&size=100")
    st_all, allc = get_json("/api/v1/all")
    tools = mcp_tools(api)

    authed = st_me == 200 and isinstance(me, dict) and bool(me.get("username"))
    if not authed:
        print(f"ключ не принят: {str(me)[:200]}")
        print("нужен API-ключ Langflow: интерфейс → аватар → Settings → Langflow API → Add New")
        print("локально: с версии 1.5 авто-логин не заменяет ключ для API")
        return 1
    providers = []
    if isinstance(models, list):
        for m in models:
            providers.append({
                "id": m.get("provider_id"),
                "vars": [(v.get("variable_key"), bool(v.get("required"))) for v in (m.get("variables") or [])],
            })

    if st_all != 200 or st_version != 200 or not isinstance(version, dict) or not version.get("version"):
        print(f"profile not updated: version HTTP {st_version}, components HTTP {st_all}")
        return 1
    try:
        comps = extract_components(allc)
    except ValueError as exc:
        print(f"profile not updated: {exc}")
        return 1

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    name = (me or {}).get("username") if isinstance(me, dict) else None
    data = {
        "meta": {"probed_at": now, "url": url, "probe_version": 2},
        "access": {"authenticated": bool(authed), "username": name,
                   "superuser": bool((me or {}).get("is_superuser")) if isinstance(me, dict) else None},
        "version": version if st_version == 200 else {"status": st_version},
        "config": config if st_cfg == 200 else {"status": st_cfg},
        "providers": providers,
        "variables": [{"name": v.get("name"), "type": v.get("type"), "has_value": v.get("has_value")}
                      for v in (variables if isinstance(variables, list) else [])],
        "mcp": tools,
        "flows_count": len(flows) if isinstance(flows, list) else None,
        "components_count": len(comps),
        "custom_components": sorted(t for t, c in comps.items() if c["category"] == "custom_component"),
        "component_list": sorted(comps),
        "limits": {},      # заполняется человеком/опытом
        "quirks": [],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    previous_path = out_dir / "profile.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {}
    # Preserve manual and installation-specific additions; refresh only measured fields.
    data["limits"] = previous.get("limits", {})
    data["quirks"] = previous.get("quirks", [])
    data = {**previous, **data}
    atomic_write(previous_path, json.dumps(data, ensure_ascii=False, indent=1))
    atomic_write(out_dir / "components.json", json.dumps(
        {"meta": {"schema_version": SCHEMA_VERSION, "probed_at": now, "url": url,
                  "langflow_version": (version or {}).get("version", "?") if isinstance(version, dict) else "?",
                  "component_count": len(comps)},
         "components": comps}, ensure_ascii=False, indent=1, sort_keys=True))

    ver = (version or {}).get("version", "?") if isinstance(version, dict) else "?"
    md = f"""# Стенд {url}

Снято автоматически {now}. Ручные модель, ограничения и особенности храни в
`profile.md`, а не в этом перегенерируемом файле. См. `references/recon.md`.

## Доступ

- аутентификация: {"да, " + str(name) if authed else "НЕТ — ключ не принят"}
- суперюзер: {"да" if data["access"]["superuser"] else "нет"}
- ключ: окружение `LANGFLOW_API_KEY` или локальный env-файл, заголовок `x-api-key`

## Версия и флаги

- Langflow: **{ver}**
- `allow_custom_components`: {data["config"].get("allow_custom_components")}
- `authz_enabled`: {data["config"].get("authz_enabled")}
- `event_delivery`: {data["config"].get("event_delivery")}
- максимальный размер загрузки: {data["config"].get("max_file_size_upload")} МБ

## Модели и переменные

Провайдеры-шаблоны: {", ".join(p["id"] or "?" for p in providers) or "нет данных"}

Настроенные переменные: {", ".join(v["name"] or "?" for v in data["variables"]) or "нет"}

**Рабочая модель** (проверить и записать): провайдер, `openai_api_base`, `model_name`,
какая переменная даёт ключ.

## Возможности MCP

- встроенный `/api/v1/agentic/mcp`: {"есть, инструментов " + str(tools.get("count")) if tools.get("available") else "нет (" + str(tools.get("status")) + ")"}
- компонентов в снапшоте: {len(comps)}
- флоу на стенде: {data["flows_count"]}

## Ограничения (заполнить)

- [ ] предел времени одного запуска
- [ ] число параллельных запросов к модели
- [ ] политика записи файлов (можно ли `SaveToFile`)
- [ ] какие форматы читает `File` (xlsx, docx-таблицы, сканы)
- [ ] доступ в интернет с сервера и что блокируется
- [ ] какие модели понимают изображения
- [ ] права на кастомные компоненты

## Особенности (заполнить)

- ...

## Служебное

- снапшот схем: `components.json` (для `validate_spec.py`)
- машинные данные: `profile.json`
"""
    atomic_write(out_dir / "profile.auto.md", md)
    if not (out_dir / "profile.md").exists():
        atomic_write(out_dir / "profile.md", "# Ручные настройки стенда\n\nИзмеренные данные: [profile.auto.md](profile.auto.md).\n\n## Модель\n\n## Ограничения\n\n## Особенности\n")

    print(f"профиль: {out_dir}")
    print(f"  версия {ver} | авторизация {'ок' if authed else 'НЕТ'} | "
          f"компонентов {len(comps)} | MCP {tools.get('count') if tools.get('available') else '—'}")
    return 0 if authed else 1


if __name__ == "__main__":
    raise SystemExit(main())
