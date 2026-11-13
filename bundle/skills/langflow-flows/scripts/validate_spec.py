"""Офлайн-проверка спеки Langflow. Без сети: работает по снапшоту схем.

    python scripts/validate_spec.py flow.spec
    python scripts/validate_spec.py flow.spec --strict
    python scripts/validate_spec.py flow.spec --format json
    python scripts/validate_spec.py flow.spec --profile profiles/stand-x

Снапшот берётся из профиля стенда (`profiles/*/components.json`). Если профиля нет —
сначала `python scripts/probe_stand.py`.

Коды: E* — сборка/запуск упадут почти наверняка. W* — сработает, но поведение
скорее всего не то, что задумано.

Код возврата: 0 — чисто, 1 — есть ошибки (в --strict и предупреждения), 2 — не смог
прочитать спеку или снапшот.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
PROFILES = SKILL / "profiles"

ENTRY_TYPES = {"ChatInput", "TextInput", "Webhook"}
OUTPUT_TYPES = {"ChatOutput", "TextOutput"}
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{12,}|postgres(?:ql)?://[^\s@]+:[^\s@]+@|"
                       r"mysql://[^\s@]+:[^\s@]+@|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,})")
VAR_RE = re.compile(r"(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)\}(?!\})")
VAR_NAME_RE = re.compile(r"[A-Z0-9_]{3,}")


@dataclass
class Finding:
    code: str
    severity: str  # error | warning
    message: str
    where: str = ""

    def as_dict(self) -> dict:
        return {"code": self.code, "severity": self.severity, "message": self.message, "where": self.where}


@dataclass
class Spec:
    name: str = ""
    description: str = ""
    nodes: list[tuple[str, str]] = field(default_factory=list)
    edges: list[tuple[str, str, str, str]] = field(default_factory=list)  # src, out, dst, in
    config: dict[str, dict[str, str]] = field(default_factory=dict)


# ---------------------------------------------------------------- профиль


def find_snapshot(explicit: str | None = None) -> Path:
    """Снапшот из профиля: явный путь, переменная окружения, единственный профиль."""
    if explicit:
        return Path(explicit)
    env = os.environ.get("LANGFLOW_PROFILE")
    if env:
        return Path(env) / "components.json"
    if not PROFILES.exists():
        raise SystemExit("нет каталога profiles/: сначала `python scripts/probe_stand.py`")
    found = sorted(PROFILES.glob("*/components.json"))
    if not found:
        raise SystemExit("нет ни одного профиля стенда: `python scripts/probe_stand.py`")
    if len(found) > 1:
        names = ", ".join(str(p.parent.name) for p in found)
        raise SystemExit(
            f"профилей несколько ({names}).\n"
            f"укажи --profile <каталог> или задай LANGFLOW_PROFILE"
        )
    return found[0]


# ---------------------------------------------------------------- парсер


def parse_spec(text: str, findings: list[Finding]) -> Spec:
    """Повторяет поведение lfx/graph/flow_builder/spec.py, но собирает проблемы."""
    spec = Spec()
    text = text.lstrip("\ufeff")  # BOM от Windows-редакторов
    section = None
    key = None
    buf: list[str] = []
    multiline = False
    key_indent = None

    def flush() -> None:
        nonlocal key, buf, multiline
        if key and buf:
            node, fld = key.split(".", 1)
            spec.config.setdefault(node, {})[fld] = "\n".join(buf).strip()
        key, buf, multiline = None, [], False

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            if section == "config" and key:
                buf.append("")
            continue

        if line in ("nodes:", "edges:", "config:"):
            flush()
            section = line[:-1]
            continue

        if section is None:
            if line.startswith("name:"):
                spec.name = line[5:].strip()
            elif line.startswith("description:"):
                spec.description = line[12:].strip()
            else:
                findings.append(Finding("E002", "error",
                                        f"непонятная строка до первого раздела: {line[:60]!r}",
                                        f"строка {lineno}"))
            continue

        if section == "nodes":
            if ":" not in line:
                findings.append(Finding("E002", "error",
                                        f"узел должен быть 'ID: Тип', получено {line[:60]!r}",
                                        f"строка {lineno}"))
                continue
            nid, ntype = line.split(":", 1)
            spec.nodes.append((nid.strip(), ntype.strip()))

        elif section == "edges":
            if " -> " not in line:
                findings.append(Finding("E002", "error",
                                        f"связь должна быть 'ID.выход -> ID.вход', получено {line[:60]!r}",
                                        f"строка {lineno}"))
                continue
            left, right = line.split(" -> ", 1)
            if "." not in left or "." not in right:
                findings.append(Finding("E002", "error", f"обе стороны связи должны быть 'ID.порт': {line[:60]!r}",
                                        f"строка {lineno}"))
                continue
            s, so = left.strip().split(".", 1)
            d, di = right.strip().split(".", 1)
            spec.edges.append((s.strip(), so.strip(), d.strip(), di.strip()))

        else:  # config
            indent = len(raw) - len(raw.lstrip())
            continuation = multiline and key_indent is not None and indent > key_indent
            if not continuation:
                m = re.match(r"^(\w+\.\w+):\s*(.*)$", line)
                if m:
                    flush()
                    if key_indent is None:
                        key_indent = indent
                    key = m.group(1)
                    val = m.group(2)
                    if val == "|":
                        multiline = True
                    elif val:
                        buf.append(val)
                    continue
                if not key:
                    findings.append(Finding("E002", "error",
                                            f"в config ожидалось 'ID.поле: значение', получено {line[:50]!r}",
                                            f"строка {lineno}"))
                    continue
            if key:
                stripped = raw
                for _ in range(4):
                    stripped = stripped.removeprefix(" ")
                buf.append(stripped)

    flush()
    return spec


# ---------------------------------------------------------------- правила


def load_snapshot(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"нет снапшота схем: {path}\nсгенерируй: python scripts/probe_stand.py")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if "components" not in doc:
        raise SystemExit(f"снапшот повреждён: {path}")
    return doc


def closest(word: str, candidates, n: int = 3) -> list[str]:
    return difflib.get_close_matches(word, list(candidates), n=n, cutoff=0.6)


def validate(spec: Spec, snap: dict) -> list[Finding]:
    out: list[Finding] = []
    comps: dict = snap["components"]

    if not spec.nodes:
        out.append(Finding("E001", "error", "в спеке нет ни одного узла"))
        return out

    # --- узлы
    types: dict[str, str] = {}
    unknown: set[str] = set()
    for nid, ntype in spec.nodes:
        if nid in types:
            out.append(Finding("E003", "error", f"узел '{nid}' объявлен дважды", nid))
            continue
        if ntype not in comps:
            hint = closest(ntype, comps)
            msg = f"неизвестный тип компонента '{ntype}'"
            if hint:
                msg += "; похоже на: " + ", ".join(f"'{h}'" for h in hint)
            out.append(Finding("E004", "error", msg, nid))
            unknown.add(nid)
            continue
        types[nid] = ntype

    # --- связи
    linked_in: dict[str, set[str]] = {n: set() for n in types}
    linked_out: dict[str, set[str]] = {n: set() for n in types}
    graph: dict[str, set[str]] = {n: set() for n in types}
    mentioned: set[str] = set()

    for src, sop, dst, dip in spec.edges:
        mentioned.update((src, dst))
        ok = True
        for side, nid in (("источник", src), ("приёмник", dst)):
            if nid in unknown:
                ok = False  # про этот узел уже сказано в E004
            elif nid not in types:
                out.append(Finding("E005", "error", f"связь ссылается на неизвестный узел '{nid}' ({side})"))
                ok = False
        if not ok:
            continue

        outs = [o["name"] for o in comps[types[src]]["outputs"]]
        ins = [i["name"] for i in comps[types[dst]]["inputs"]]

        if sop not in outs:
            if sop in [i["name"] for i in comps[types[src]]["inputs"]]:
                out.append(Finding("E006", "error",
                                   f"'{sop}' у {types[src]} — это вход, а не выход; "
                                   f"похоже, стороны связи перепутаны", f"{src}.{sop}"))
            else:
                hint = closest(sop, outs)
                msg = f"у {types[src]} нет выхода '{sop}'"
                msg += f"; есть: {', '.join(outs[:6])}" if outs else "; выходов нет"
                if hint:
                    msg += f"; похоже на: {', '.join(hint)}"
                out.append(Finding("E006", "error", msg, f"{src}.{sop}"))

        if dip not in ins:
            if types[dst] == "Prompt Template":
                pass  # про несовпадение переменной скажет E011
            elif dip in [o["name"] for o in comps[types[dst]]["outputs"]]:
                out.append(Finding("E007", "error",
                                   f"'{dip}' у {types[dst]} — это выход; стороны связи перепутаны",
                                   f"{dst}.{dip}"))
            else:
                hint = closest(dip, ins)
                msg = f"у {types[dst]} нет входа '{dip}'"
                msg += f"; входы: {', '.join(ins[:6])}" if ins else "; входов нет (только поля)"
                if hint:
                    msg += f"; похоже на: {', '.join(hint)}"
                out.append(Finding("E007", "error", msg, f"{dst}.{dip}"))

        linked_out[src].add(sop)
        linked_in[dst].add(dip)
        graph[src].add(dst)

    # --- config
    for nid, fields in spec.config.items():
        if nid not in types:
            out.append(Finding("E008", "error", f"config ссылается на неизвестный узел '{nid}'"))
            continue
        known = comps[types[nid]]["fields"]
        for fname, value in fields.items():
            if fname not in known:
                hint = closest(fname, known)
                msg = f"у {types[nid]} нет поля '{fname}'"
                if hint:
                    msg += f"; похоже на: {', '.join(hint)}"
                out.append(Finding("E009", "warning", msg, f"{nid}.{fname}"))
                continue
            meta = known[fname] or {}
            val = str(value).strip()
            if meta.get("password") and VAR_NAME_RE.fullmatch(val):
                out.append(Finding("E010", "error",
                                   f"'{fname}' у {types[nid]} — поле, привязанное к переменной. "
                                   f"Запись значения в спеку снимает привязку (load_from_db) и ломает "
                                   f"авторизацию. Убери строку из config: привязка уже стоит по умолчанию.",
                                   f"{nid}.{fname}"))
            elif not meta.get("password") and SECRET_RE.search(val):
                out.append(Finding("W006", "warning",
                                   f"в поле '{fname}' секрет в открытом виде — вынеси в переменную",
                                   f"{nid}.{fname}"))

    # --- переменные промпта против связей
    for nid, ntype in types.items():
        if ntype != "Prompt Template":
            continue
        tpl = (spec.config.get(nid) or {}).get("template", "")
        declared = set(VAR_RE.findall(tpl))
        for port in linked_in[nid] - declared:
            out.append(Finding("E011", "error",
                               f"в {nid} соединено в порт '{port}', но переменной {{{port}}} в template "
                               f"нет — такого входа не существует", f"{nid}.{port}"))
        for var in declared - linked_in[nid]:
            out.append(Finding("W001", "warning",
                               f"переменная {{{var}}} в шаблоне {nid} ни к чему не подключена — "
                               f"останется пустой", f"{nid}.{var}"))

    # --- агент без модели
    for nid, ntype in types.items():
        if ntype == "Agent" and "model" not in linked_in[nid]:
            out.append(Finding("W003", "warning", f"у агента {nid} не подключена модель (вход 'model')", nid))

    # --- ветвление: оба выхода
    for nid, ntype in types.items():
        if ntype != "ConditionalRouter":
            continue
        for branch in ("true_result", "false_result"):
            if branch not in linked_out[nid]:
                out.append(Finding("W004", "warning",
                                   f"у {nid} не подключён выход '{branch}' — эта ветка молча исчезнет", nid))

    # --- секреты, которые нельзя задать в спеке
    for nid, ntype in types.items():
        if ntype == "SQLComponent" and "database_url" not in linked_in[nid]:
            if "database_url" not in (spec.config.get(nid) or {}):
                out.append(Finding("W009", "warning",
                                   f"у {nid} не задана строка подключения — поле защищённое, "
                                   f"её придётся прописать в самом флоу после создания", nid))

    # --- выход
    if not any(t in OUTPUT_TYPES for t in types.values()):
        out.append(Finding("W005", "warning",
                           "в спеке нет ChatOutput/TextOutput — результат будет некуда выводить"))

    # --- изолированные узлы и путь до выхода
    for nid in types:
        if not linked_in[nid] and not linked_out[nid] and len(types) > 1 and nid not in mentioned:
            out.append(Finding("W007", "warning", f"узел {nid} ни с чем не соединён — в запуске не участвует", nid))

    roots = [n for n in types if not linked_in[n]]
    seen, stack = set(roots), list(roots)
    while stack:
        cur = stack.pop()
        for nxt in graph[cur]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    if not any(t in OUTPUT_TYPES for n, t in types.items() if n in seen):
        out.append(Finding("W008", "warning", "от входов нет пути до ChatOutput — цепочка обрывается"))

    return out


# ---------------------------------------------------------------- вывод


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Офлайн-проверка спеки Langflow")
    ap.add_argument("spec", help="путь к .spec")
    ap.add_argument("--profile", default=None, help="каталог профиля стенда")
    ap.add_argument("--snapshot", default=None, help="путь к components.json напрямую")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--strict", action="store_true", help="предупреждения считать ошибками")
    ap.add_argument("--quiet", action="store_true", help="только итог")
    args = ap.parse_args(argv)

    path = Path(args.spec)
    if not path.exists():
        print(f"нет файла: {path}", file=sys.stderr)
        return 2

    if args.snapshot:
        snap_path = Path(args.snapshot)
    elif args.profile:
        snap_path = Path(args.profile) / "components.json"
    else:
        snap_path = find_snapshot()

    snap = load_snapshot(snap_path)
    findings: list[Finding] = []
    spec = parse_spec(path.read_text(encoding="utf-8"), findings)
    findings.extend(validate(spec, snap))

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    failed = bool(errors) or (args.strict and bool(warnings))

    if args.format == "json":
        print(json.dumps({
            "spec": str(path),
            "profile": str(snap_path.parent.name),
            "snapshot_version": snap.get("meta", {}).get("langflow_version"),
            "nodes": len(spec.nodes),
            "edges": len(spec.edges),
            "errors": len(errors),
            "warnings": len(warnings),
            "ok": not failed,
            "findings": [f.as_dict() for f in findings],
        }, ensure_ascii=False, indent=1))
        return 1 if failed else 0

    if not args.quiet:
        for f in findings:
            mark = "ОШИБКА  " if f.severity == "error" else "предупр."
            where = f"  [{f.where}]" if f.where else ""
            print(f"{mark} {f.code}  {f.message}{where}")

    print(f"\n{path.name}: узлов {len(spec.nodes)}, связей {len(spec.edges)}; "
          f"ошибок {len(errors)}, предупреждений {len(warnings)}")
    print("РЕЗУЛЬТАТ: не пройдено" if failed else "РЕЗУЛЬТАТ: чисто")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
