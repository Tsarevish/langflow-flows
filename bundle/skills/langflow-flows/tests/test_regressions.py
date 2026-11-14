"""Behavioral regressions; synthetic schemas and mocked HTTP, no live credentials."""
from __future__ import annotations

import copy
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import validate_spec as V
import probe_stand as P
import dump_schema as D
from schema_snapshot import extract_components
from langflow_client import messages, normalize
import run_eval as E

FIXTURE = ROOT / "tests" / "fixtures" / "components.json"


def findings(text, snap=None):
    result = []
    spec = V.parse_spec(text, result)
    return spec, result + V.validate(spec, snap or V.load_snapshot(FIXTURE))


def codes(text, snap=None):
    return {f.code for f in findings(text, snap)[1]}


ECHO = "nodes:\n  A: ChatInput\n  O: ChatOutput\nedges:\n  A.message -> O.input_value\n"


class ValidatorTests(unittest.TestCase):
    def test_type_mismatch(self):
        text = "nodes:\n  A: ChatInput\n  G: Agent\n  O: ChatOutput\nedges:\n  A.message -> G.model\n  G.response -> O.input_value"
        self.assertIn("E012", codes(text))

    def test_good_types(self):
        self.assertFalse([f for f in findings(ECHO)[1] if f.severity == "error"])

    def test_unknown_field_is_error(self):
        fs = findings(ECHO + "config:\n  A.typo: value")[1]
        self.assertEqual([f.severity for f in fs if f.code == "E009"], ["error"])

    def test_multiline_section_words(self):
        text = "nodes:\n  P: Prompt Template\nconfig:\n  P.template: |\n    nodes:\n    edges:\n    config:\n      example\n  P.use_double_brackets: false"
        spec, fs = findings(text)
        self.assertEqual(spec.config["P"]["template"], "nodes:\nedges:\nconfig:\n  example")
        self.assertNotIn("E002", {f.code for f in fs})
        self.assertEqual(len(spec.nodes), 1)

    def test_empty_config_value_preserved(self):
        self.assertEqual(findings(ECHO + "config:\n  A.input_value:")[0].config["A"]["input_value"], "")

    def test_duplicate_unknown_id(self):
        self.assertIn("E003", codes("nodes:\n  A: Missing\n  A: Missing"))

    def test_unused_input_path(self):
        text = "nodes:\n  A: ChatInput\n  X: TextInput\n  O: ChatOutput\nedges:\n  X.text -> O.input_value"
        self.assertIn("W013", codes(text))

    def test_each_input_path_checked(self):
        self.assertIn("W013", codes(ECHO.replace("  O: ChatOutput", "  X: TextInput\n  O: ChatOutput")))

    def test_secret_in_password_field(self):
        text = "nodes:\n  M: ext:openai:OpenAIModelComponent@official\nconfig:\n  M.api_key: sk-FAKE_TEST_KEY_123456789"
        self.assertIn("W006", codes(text))

    def test_prompt_config_variable(self):
        text = "nodes:\n  P: Prompt Template\nconfig:\n  P.template: Hi {who}\n  P.who: user"
        result = codes(text)
        self.assertNotIn("E009", result)
        self.assertNotIn("W001", result)

    def test_double_brackets(self):
        text = "nodes:\n  A: ChatInput\n  P: Prompt Template\nedges:\n  A.message -> P.who\nconfig:\n  P.template: Hi {{who}}\n  P.use_double_brackets: true"
        self.assertNotIn("E011", codes(text))
        self.assertNotIn("W001", codes(text))

    def test_required_without_default(self):
        snap = V.load_snapshot(FIXTURE)
        snap["components"]["ChatInput"]["fields"]["required_setting"] = {"required": True, "has_default": False}
        self.assertIn("E013", codes(ECHO, snap))

    def test_required_default_respected(self):
        snap = V.load_snapshot(FIXTURE)
        snap["components"]["ChatInput"]["fields"]["required_setting"] = {"required": True, "has_default": True}
        self.assertNotIn("E013", codes(ECHO, snap))

    def test_required_value_respected(self):
        snap = V.load_snapshot(FIXTURE)
        snap["components"]["ChatInput"]["fields"]["required_setting"] = {"required": True, "has_default": False}
        self.assertNotIn("E013", codes(ECHO + "config:\n  A.required_setting: 0", snap))

    def test_explicit_runtime_binding_satisfies_required_field(self):
        snap = V.load_snapshot(FIXTURE)
        snap["components"]["ChatInput"]["fields"]["required_setting"] = {"required": True, "has_default": False}
        spec = V.parse_spec(ECHO, [])
        result = V.validate(spec, snap, external_fields={("A", "required_setting")})
        self.assertNotIn("E013", {f.code for f in result})
        self.assertNotIn("required_setting", spec.config.get("A", {}))

    def test_bound_credential_is_not_missing_field_error(self):
        snap = V.load_snapshot(FIXTURE)
        snap["components"]["ChatInput"]["fields"]["credential"] = {"required": True, "has_default": False, "load_from_db": True}
        result = codes(ECHO, snap)
        self.assertIn("W012", result)
        self.assertNotIn("E013", result)

    def test_old_snapshot_does_not_invent_missing_defaults(self):
        snap = V.load_snapshot(FIXTURE)
        snap["components"]["ChatInput"]["fields"]["required_setting"] = {"required": True}
        self.assertNotIn("E013", codes(ECHO, snap))

    def test_invalid_snapshot_exit_two_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec, snap = Path(tmp) / "flow.spec", Path(tmp) / "snapshot.json"
            spec.write_text(ECHO, encoding="utf-8")
            snap.write_text("not json", encoding="utf-8")
            proc = subprocess.run([sys.executable, "-X", "utf8", "-B", str(ROOT / "scripts/validate_spec.py"), str(spec), "--snapshot", str(snap), "--format", "json"], capture_output=True, encoding="utf-8")
            self.assertEqual(proc.returncode, 2)
            self.assertIs(json.loads(proc.stdout)["ok"], False)

    def test_strict_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "flow.spec"
            spec.write_text("nodes:\n  A: ChatInput", encoding="utf-8")
            proc = subprocess.run([sys.executable, "-X", "utf8", "-B", str(ROOT / "scripts/validate_spec.py"), str(spec), "--snapshot", str(FIXTURE), "--strict", "--format", "json"], capture_output=True, encoding="utf-8")
            self.assertEqual(proc.returncode, 1)
            self.assertFalse(json.loads(proc.stdout)["ok"])


RAW = {"component_display_names": {"chatinput": {"ru": "input"}}, "io": {
    "Plain": {"template": {"text": {"type": "str", "value": "", "tool_mode": False}}, "outputs": [{"name": "text", "types": ["Message"], "tool_mode": True}]},
    "Tool": {"template": {"question": {"type": "str", "tool_mode": True, "required": True}, "secret": {"password": True, "value": "NEVER_PERSIST_THIS", "load_from_db": True}}, "outputs": [{"name": "answer", "types": ["Message"]}]}}}


class SchemaTests(unittest.TestCase):
    def test_translations_skipped(self):
        self.assertEqual(set(extract_components(RAW)), {"Plain", "Tool"})

    def test_output_flag_not_tool_capability(self):
        self.assertNotIn("component_as_tool", {o["name"] for o in extract_components(RAW)["Plain"]["outputs"]})

    def test_input_tool_flag_is_marked_inferred(self):
        tool = extract_components(RAW)["Tool"]
        self.assertEqual(tool["tool_capability"], "inferred")
        self.assertEqual(tool["outputs"][-1]["provenance"], "inferred_tool_mode")

    def test_secret_defaults_not_persisted(self):
        self.assertNotIn("NEVER_PERSIST_THIS", json.dumps(extract_components(RAW)))

    def test_both_collectors_share_extractor(self):
        self.assertIs(P.extract_components, D.extract_components)
        self.assertIs(P.compact, D.compact)

    def test_empty_response_rejected(self):
        with self.assertRaises(ValueError):
            extract_components({"detail": "forbidden"})

    def test_declared_tool_not_duplicated(self):
        raw = copy.deepcopy(RAW)
        raw["io"]["Tool"]["outputs"].append({"name": "component_as_tool", "types": ["Tool"]})
        outputs = extract_components(raw)["Tool"]["outputs"]
        self.assertEqual(sum(o["name"] == "component_as_tool" for o in outputs), 1)


class ProfileTests(unittest.TestCase):
    def probe(self, target, fail=False):
        def call(api, path, *args, **kwargs):
            value = {"/api/v1/version": {"version": "test-v2"}, "/api/v1/users/whoami": {"username": "test"},
                     "/api/v1/all": RAW, "/api/v1/config": {}, "/api/v1/models": [], "/api/v1/variables/": []}.get(path, [])
            return (403, '{}') if fail and path == "/api/v1/all" else (200, json.dumps(value))
        with patch.object(P.Api, "call", call), patch.object(P, "mcp_tools", return_value={"available": False}), patch.dict(os.environ, {"LANGFLOW_URL": "http://test.invalid:7860"}), contextlib.redirect_stdout(io.StringIO()):
            return P.main(["--out", str(target), "--env", str(target / "absent.env")])

    def test_manual_profile_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / "profile.md").write_text("MANUAL MODEL AND LIMITS", encoding="utf-8")
            (target / "profile.json").write_text(json.dumps({"limits": {"timeout": 42}, "quirks": ["manual"], "model": "chosen"}), encoding="utf-8")
            self.assertEqual(self.probe(target), 0)
            self.assertEqual((target / "profile.md").read_text(), "MANUAL MODEL AND LIMITS")
            data = json.loads((target / "profile.json").read_text(encoding="utf-8"))
            self.assertEqual(data["limits"], {"timeout": 42})
            self.assertEqual(data["quirks"], ["manual"])
            self.assertEqual(data["model"], "chosen")
            self.assertEqual(data["meta"]["url"], "http://test.invalid:7860")
            self.assertIn("http://test.invalid:7860", (target / "profile.auto.md").read_text(encoding="utf-8"))

    def test_failed_schema_preserves_all_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            for name in ("profile.md", "profile.json", "components.json"):
                (target / name).write_text("OLD", encoding="utf-8")
            self.assertEqual(self.probe(target, fail=True), 1)
            self.assertTrue(all(p.read_text() == "OLD" for p in target.iterdir()))

    def test_first_probe_creates_manual_and_auto(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            self.assertEqual(self.probe(target), 0)
            self.assertTrue((target / "profile.md").exists())
            self.assertTrue((target / "profile.auto.md").exists())
            self.assertEqual(json.loads((target / "components.json").read_text())["meta"]["schema_version"], 2)


def response(text, marker=None):
    return {"outputs": [{"outputs": [{"results": {"message": {"text": text, "sender_name": marker}}}]}]}


class EvalTests(unittest.TestCase):
    def test_nested_execution_error(self):
        run = response("42")
        run["outputs"][0]["outputs"][0]["results"]["message"]["error"] = True
        self.assertTrue(E.run_failed(run))
        self.assertTrue(E.run_failed(False))
        self.assertFalse(E.run_failed(response("42")))
        metadata = response("42")
        metadata.update(edited=False, streaming=False)
        self.assertFalse(E.run_failed(metadata))

    def test_false_mcp_result_fails(self):
        for result in ({"content": [{"type": "text", "text": "False"}]}, {"structuredContent": False}, {"structuredContent": {"success": False}}):
            self.assertTrue(normalize(result)["isError"])

    def test_mcp_multiline_sse(self):
        body = 'data: {"id": 1,\ndata: "result": {}}\n\n'
        self.assertEqual(messages(body), [{"id": 1, "result": {}}])

    def test_bare_json_event_stream(self):
        self.assertEqual(messages('{"event":"token"}\n\n{"event":"end"}\n'),
                         [{"event": "token"}, {"event": "end"}])

    def test_artifact_redaction(self):
        value = {"api_key": "provider-secret", "password": "db-secret", "text": "test transport-secret"}
        redacted = E.redact_artifact(value, ["transport-secret"])
        self.assertNotIn("secret", json.dumps(redacted))

    def test_calculator_trace_name(self):
        trace = {"type": "tool_use", "name": "evaluate_expression", "output": {"artifact": {"result": "391"}, "status": "success"}}
        self.assertTrue(E.tool_called(trace, r"^evaluate_expression$"))

    def test_answer_shapes(self):
        self.assertEqual(E.answer_text(response("answer")), "answer")
        nested = {"outputs": [{"outputs": [{"results": {"message": {"data": {"text": "nested"}}}}]}]}
        self.assertEqual(E.answer_text(nested), "nested")

    def test_tool_name_in_prose_not_evidence(self):
        self.assertFalse(E.tool_called(response("I used calculate and got 391"), "calculate"))
        self.assertFalse(E.tool_called({"inputs": {"tool_calls": [{"name": "calculate"}]}}, "calculate"))

    def test_structured_tool_call(self):
        self.assertFalse(E.tool_called({"tool_calls": [{"function": {"name": "calculate"}}]}, "calculate"))

    def test_failed_tool_execution_not_evidence(self):
        trace = {"type": "tool_use", "name": "calculate", "output": {"status": "error", "content": "failed"}}
        self.assertFalse(E.tool_called(trace, "calculate"))

    def test_wrong_tool_not_evidence(self):
        self.assertFalse(E.tool_called({"tool_calls": [{"name": "search"}]}, "calculate"))

    def test_branch_identity(self):
        self.assertTrue(E.branch_observed(response("yes", "EVAL_Da"), "Da"))
        self.assertFalse(E.branch_observed(response("yes", "EVAL_Net"), "Da"))

    def test_success_requires_all_stages(self):
        good = dict(errors=0, created=True, updated=True, ran=True, match=True, evidence=True, cleaned=True)
        self.assertTrue(E.passed(good))
        for key in ("created", "updated", "ran", "match", "evidence", "cleaned"):
            self.assertFalse(E.passed({**good, key: False}), key)

    def test_recall_isolation_assertion(self):
        self.assertFalse(E.matched("НЕИЗВЕСТНО ЛИМОН-58317", {"expect_regex": "НЕИЗВЕСТНО", "reject_regex": "58317"}))

    def test_missing_model_configuration_fails_before_network(self):
        with self.assertRaises(ValueError):
            E.prepare(CASES_PATH("02-chat-model.spec"), {})

    def test_cleanup_after_failed_run(self):
        class Fake:
            def __init__(self):
                self.deleted = []
            def tool(self, name, args):
                return {"isError": False, "data": {"id": "test-created-id"}}
            def request(self, path, method="GET", body=None):
                if method == "DELETE":
                    self.deleted.append(path)
                elif method == "POST":
                    raise RuntimeError("run failed")
                else:
                    return {"data": {"nodes": []}}
        fake = Fake()
        row = E.evaluate({"id": "test", "title": "test", "input": "hello", "expect": "hello"}, ECHO, None, V.load_snapshot(FIXTURE), fake, {})
        self.assertEqual(fake.deleted, ["/api/v1/flows/test-created-id"])
        self.assertFalse(row["passed"])
        self.assertTrue(row["cleaned"])

    def test_multiturn_session_ids(self):
        class Fake:
            def __init__(self):
                self.sessions = []
            def tool(self, name, args):
                return {"isError": False, "data": {"id": "disposable"}}
            def request(self, path, method="GET", body=None):
                if method == "POST":
                    self.sessions.append(body["session_id"])
                    return response("OK")
                return {"data": {"nodes": []}}
        case = {"id": "memory", "title": "memory", "steps": [
            {"input": "remember", "expect": "OK"}, {"input": "recall", "expect": "OK"},
            {"input": "isolated", "expect": "OK", "session": "isolated"}]}
        fake = Fake()
        row = E.evaluate(case, ECHO, None, V.load_snapshot(FIXTURE), fake, {})
        self.assertTrue(row["passed"])
        self.assertEqual(fake.sessions[0], fake.sessions[1])
        self.assertNotEqual(fake.sessions[0], fake.sessions[2])
        other = Fake()
        E.evaluate(case, ECHO, None, V.load_snapshot(FIXTURE), other, {})
        self.assertNotEqual(fake.sessions[0], other.sessions[0])

    def test_stale_tool_trace_is_not_success(self):
        class Fake:
            def tool(self, name, args):
                if name == "create_flow_from_spec":
                    return {"isError": False, "data": {"id": "disposable"}}
                return {"isError": False, "data": {"run_id": "old-run", "tool_calls": [{"name": "calculate"}]}}
            def request(self, path, method="GET", body=None):
                if method == "POST":
                    return {**response("391"), "run_id": "current-run"}
                return {"data": {"nodes": []}}
        row = E.evaluate({"id": "tool", "title": "tool", "input": "17*23", "expect": "391", "require_tool": "calculate"}, ECHO, None, V.load_snapshot(FIXTURE), Fake(), {})
        self.assertTrue(row["match"])
        self.assertFalse(row["evidence"])
        self.assertFalse(row["passed"])

    def test_failed_update_cannot_pass(self):
        class Fake:
            def __init__(self):
                self.deleted = False
            def tool(self, name, args):
                return {"isError": name == "update_flow_from_spec", "data": {"id": "disposable"}}
            def request(self, path, method="GET", body=None):
                self.deleted = method == "DELETE"
                return None
        fake = Fake()
        row = E.evaluate({"id": "edit", "title": "edit"}, ECHO, ECHO, V.load_snapshot(FIXTURE), fake, {})
        self.assertFalse(row["passed"])
        self.assertFalse(row["updated"])
        self.assertTrue(fake.deleted)


def CASES_PATH(name):
    return ROOT / "tests" / "eval" / "cases" / name


if __name__ == "__main__":
    unittest.main()
