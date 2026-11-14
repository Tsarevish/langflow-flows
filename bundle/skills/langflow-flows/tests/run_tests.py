"""Регрессионные тесты валидатора: ожидаемые коды против фактических.

    python tests/run_tests.py

Проверяет два свойства:
  * на каждом «плохом» кейсе находится именно ожидаемый код;
  * на примерах из examples/ нет ни одной ошибки.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "scripts" / "validate_spec.py"

def profile_args() -> list[str]:
    if os.environ.get("LANGFLOW_PROFILE"):
        return ["--profile", os.environ["LANGFLOW_PROFILE"]]
    return ["--snapshot", str(ROOT / "tests" / "fixtures" / "components.json")]

# файл -> минимальный набор кодов, которые обязаны появиться
CASES = {
    "E003-duplicate-id.spec": {"E003"},
    "E004-unknown-type.spec": {"E004"},
    "E005-dangling-edge.spec": {"E005"},
    "E006-bad-port.spec": {"E006"},
    "E010-secret-in-config.spec": {"E010"},
    "E011-prompt-var.spec": {"E011"},
    "W-warnings.spec": {"W003", "W005"},
}


def run(path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-B", str(VALIDATOR), str(path), "--format", "json", *profile_args()],
        capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"validator failed ({proc.returncode}): {proc.stderr}")
    return json.loads(proc.stdout)


def main() -> int:
    failed = 0
    cases_dir = ROOT / "tests" / "cases"

    print("== плохие кейсы")
    for name, expected in sorted(CASES.items()):
        path = cases_dir / name
        if not path.exists():
            print(f"  ПРОПУСК {name}: нет файла")
            failed += 1
            continue
        res = run(path)
        got = {f["code"] for f in res["findings"]}
        missing = expected - got
        if missing:
            failed += 1
            print(f"  ПРОВАЛ {name}: нет кодов {sorted(missing)} (есть {sorted(got)})")
        else:
            print(f"  ok     {name}: {sorted(got)}")

    print("\n== хорошие кейсы")
    for path in sorted((ROOT / "examples").glob("*.spec")):
        res = run(path)
        if res["errors"]:
            failed += 1
            bad = [f["code"] for f in res["findings"] if f["severity"] == "error"]
            print(f"  ПРОВАЛ {path.name}: ошибки {bad}")
        else:
            print(f"  ok     {path.name}: 0 ошибок, {res['warnings']} предупреждений")

    print(f"\nитог: {'всё прошло' if not failed else f'провалов {failed}'}")
    import unittest
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 1 if failed or not result.wasSuccessful() else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
