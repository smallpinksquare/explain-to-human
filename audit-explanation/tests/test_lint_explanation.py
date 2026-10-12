"""Behavioral invariants of the optional structural linter (stdlib only)."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "lint_explanation.py"
SPEC = importlib.util.spec_from_file_location("explanation_lint", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def example():
    intro = "把每项非负分数除以总分，就能得到总和为一的份额。"
    define = "令 a、b 是非负实数且 a+b>0。"
    operation = "份额为 a/(a+b) 与 b/(a+b)，两者之和为 (a+b)/(a+b)=1。"
    return {
        "version": 1, "phase": "draft",
        "task": {"question": "怎样将两个分数变成份额？", "constraints": [],
                 "additions": ["归一化"], "prerequisites": ["加法与除法"],
                 "understood": [], "confused": [], "must_preserve": ["总分大于零"]},
        "sources": [],
        "symbols": [
            {"id": name, "notation": name, "meaning": "输入分数", "scope": "非负且总和大于零", "defined_in": "define"}
            for name in ("a", "b")],
        "units": [{"id": "normalize", "question": "怎样计算份额？", "claim": "除以总分后和为一",
                   "selected_by": ["answer"], "selection_basis": "给出问题所要求的计算",
                   "depends_on": [], "must_keep": ["总分非零"], "evidence_ids": [], "gap": "",
                   "text": "\n\n".join((intro, define, operation)),
                   "entry": [{"text": intro, "step_ids": ["operation"]}],
                   "steps": [{"id": "define", "text": define, "uses_symbols": [], "source_ids": []},
                             {"id": "operation", "text": operation, "uses_symbols": ["a", "b"], "source_ids": []}]}],
        "defects": []}


class LintTests(unittest.TestCase):
    def test_valid_draft(self):
        self.assertTrue(MODULE.lint(example())["ok"])

    def test_plan_needs_no_draft_fields(self):
        data = example()
        data["phase"] = "plan"
        del data["symbols"]
        for key in ("text", "entry", "steps"):
            del data["units"][0][key]
        self.assertTrue(MODULE.lint(data)["ok"])

    def test_missing_question_rejected(self):
        data = example()
        del data["task"]["question"]
        self.assertFalse(MODULE.lint(data)["ok"])

    def test_claimed_understanding_needs_feedback_evidence(self):
        data = example()
        data["task"]["understood"] = [{"content": "归一化"}]
        self.assertFalse(MODULE.lint(data)["ok"])

    def test_unregistered_source_rejected(self):
        data = example()
        data["units"][0]["steps"][1]["source_ids"] = ["missing"]
        self.assertFalse(MODULE.lint(data)["ok"])

    def test_unregistered_symbol_rejected(self):
        data = example()
        data["units"][0]["steps"][1]["uses_symbols"].append("z")
        self.assertFalse(MODULE.lint(data)["ok"])

    def test_late_definition_rejected(self):
        data = example()
        data["units"][0]["steps"].reverse()
        self.assertFalse(MODULE.lint(data)["ok"])

    def test_registry_cannot_hide_reversed_text_order(self):
        data = example()
        unit = data["units"][0]
        unit["text"] = "\n\n".join((unit["entry"][0]["text"], unit["steps"][1]["text"], unit["steps"][0]["text"]))
        self.assertFalse(MODULE.lint(data)["ok"])

    def test_self_and_forward_dependencies_rejected(self):
        for dep in ("normalize", "future"):
            data = example()
            data["units"][0]["depends_on"] = [dep]
            self.assertFalse(MODULE.lint(data)["ok"])

    def test_missing_entry_mapping_rejected(self):
        data = example()
        data["units"][0]["entry"][0]["step_ids"] = ["absent"]
        self.assertFalse(MODULE.lint(data)["ok"])

    def test_phantom_paragraph_rejected(self):
        data = example()
        data["units"][0]["steps"][1]["text"] = "正文里没有这一步"
        self.assertFalse(MODULE.lint(data)["ok"])

    def test_duplicate_ids_rejected(self):
        data = example()
        data["units"].append(copy.deepcopy(data["units"][0]))
        self.assertFalse(MODULE.lint(data)["ok"])

    def test_obvious_repetition_is_warning_only(self):
        data = example()
        data["units"][0]["text"] += "\n\n" + data["units"][0]["entry"][0]["text"]
        result = MODULE.lint(data)
        self.assertTrue(result["ok"])
        self.assertTrue(any(x["severity"] == "warning" for x in result["issues"]))

    def test_strict_unresolved_defect_fails_and_repaired_passes(self):
        data = example()
        defect = {"id": "D1", "location": "第一步", "requirement": "条件齐全",
                  "evidence": "示意缺陷记录", "impact": "可能除零", "severity": "blocker",
                  "repair": "补总分非零条件", "status": "unverified"}
        data["defects"] = [defect]
        self.assertTrue(MODULE.lint(data)["ok"])
        self.assertFalse(MODULE.lint(data, strict=True)["ok"])
        defect["status"] = "repaired"
        self.assertTrue(MODULE.lint(data, strict=True)["ok"])

    def test_malformed_inputs_report_without_crashing(self):
        for data in (None, [], {"version": True, "phase": [], "units": [None]}, {"task": "invalid"}):
            with self.subTest(data=data):
                self.assertFalse(MODULE.lint(data)["ok"])

    def test_semantic_falsehood_not_certified(self):
        data = example()
        data["units"][0]["claim"] = "任意负数相除都能得到概率"
        result = MODULE.lint(data)
        self.assertTrue(result["ok"])
        self.assertIn("未验证", result["scope"])

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            for data, expected in ((example(), 0), ({}, 1)):
                path.write_text(json.dumps(data), encoding="utf-8")
                run = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
                self.assertEqual(run.returncode, expected)
                self.assertIn("ok", json.loads(run.stdout))
            path.write_text("{invalid", encoding="utf-8")
            run = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
