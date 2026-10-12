#!/usr/bin/env python3
"""Check registered explanation structure, never truth or human comprehension."""
import argparse
import json
import re
import sys
from pathlib import Path


def lint(data, strict=False):
    issues = []

    def issue(path, rule, evidence, repair, level="error"):
        issues.append({"location": path, "requirement": rule,
                       "evidence": str(evidence), "impact": "登记结构或对应关系需核对",
                       "severity": level, "repair": repair})

    def obj(value, path):
        if not isinstance(value, dict):
            issue(path, "必须为对象", type(value).__name__, "提供 JSON 对象")
            return {}
        return value

    def array(value, path):
        if not isinstance(value, list):
            issue(path, "必须为数组", type(value).__name__, "提供数组，无内容时用 []")
            return []
        return value

    def string(value, path, empty=False):
        if not isinstance(value, str) or (not empty and not value.strip()):
            issue(path, "必须为" + ("字符串" if empty else "非空字符串"), repr(value), "补充真实内容")
            return ""
        return value

    def strings(value, path, nonempty=False):
        result = array(value, path)
        if nonempty and not result:
            issue(path, "至少一项", result, "登记必要内容")
        return [string(v, f"{path}[{i}]") for i, v in enumerate(result)]

    def records(value, path):
        rows = [obj(v, f"{path}[{i}]") for i, v in enumerate(array(value, path))]
        seen = set()
        for i, row in enumerate(rows):
            ident = string(row.get("id"), f"{path}[{i}].id")
            if ident in seen:
                issue(f"{path}[{i}].id", "ID 唯一", ident, "使用唯一 ID 并同步引用")
            seen.add(ident)
        return rows, seen

    root = obj(data, "$")
    if root.get("version") != 1 or isinstance(root.get("version"), bool):
        issue("version", "版本为 1", root.get("version"), "使用 version: 1")
    phase = root.get("phase")
    if phase not in ("plan", "draft"):
        issue("phase", "阶段为 plan 或 draft", phase, "填写实际阶段")
    task = obj(root.get("task"), "task")
    string(task.get("question"), "task.question")
    for key in ("constraints", "additions", "prerequisites", "must_preserve"):
        strings(task.get(key), "task." + key)
    for key in ("understood", "confused"):
        for i, value in enumerate(array(task.get(key), "task." + key)):
            row = obj(value, f"task.{key}[{i}]")
            for field in ("content", "evidence"):
                string(row.get(field), f"task.{key}[{i}].{field}")

    sources, source_ids = records(root.get("sources"), "sources")
    for i, row in enumerate(sources):
        for key in ("locator", "support_scope"):
            string(row.get(key), f"sources[{i}].{key}")
        if row.get("status") not in ("provided", "verified", "unverified"):
            issue(f"sources[{i}].status", "有效来源状态", row.get("status"), "声明 provided/verified/unverified")

    def refs(value, path, registered):
        for ref in strings(value, path):
            if ref not in registered:
                issue(path, "引用必须已登记", ref, "补登记或修正错误 ID")

    units, _ = records(root.get("units"), "units")
    if not units:
        issue("units", "至少一个讲解单元", units, "登记需要讲解的内容；简单事实无需生成记录")
    preceding = set()
    steps, texts = [], []
    for i, row in enumerate(units):
        path = f"units[{i}]"
        for key in ("question", "claim", "selection_basis"):
            string(row.get(key), path + "." + key)
        chosen = strings(row.get("selected_by"), path + ".selected_by", True)
        for reason in chosen:
            if reason not in ("answer", "prerequisite", "misuse-risk"):
                issue(path + ".selected_by", "有效入选类别", reason, "使用 answer/prerequisite/misuse-risk")
        refs(row.get("depends_on"), path + ".depends_on", preceding)
        preceding.add(row.get("id") if isinstance(row.get("id"), str) else "")
        strings(row.get("must_keep"), path + ".must_keep", True)
        refs(row.get("evidence_ids"), path + ".evidence_ids", source_ids)
        string(row.get("gap"), path + ".gap", True)
        if phase != "draft":
            continue
        full_text = string(row.get("text"), path + ".text")
        texts.append((path + ".text", full_text))
        local_steps = array(row.get("steps"), path + ".steps")
        if not local_steps:
            issue(path + ".steps", "至少一个正式展开步骤", local_steps, "登记实际定义、推导、操作或证据")
        local_ids = set()
        previous_position = -1
        for j, value in enumerate(local_steps):
            step_path = f"{path}.steps[{j}]"
            step = obj(value, step_path)
            ident = string(step.get("id"), step_path + ".id")
            local_ids.add(ident)
            text = string(step.get("text"), step_path + ".text")
            if text and text not in full_text:
                issue(step_path + ".text", "登记步骤须实际存在于正文", text, "同步登记文本与正文")
            position = full_text.find(text) if text else -1
            if position >= 0:
                if position < previous_position:
                    issue(step_path + ".text", "登记步骤顺序须与正文一致", text, "同步步骤顺序，检查定义是否早于使用")
                previous_position = position
            refs(step.get("source_ids"), step_path + ".source_ids", source_ids)
            steps.append((step_path, step))
        local_entries = array(row.get("entry"), path + ".entry")
        if not local_entries:
            issue(path + ".entry", "登记具体入口", local_entries, "登记实际入口，语义是否具体另行审核")
        for j, value in enumerate(local_entries):
            entry_path = f"{path}.entry[{j}]"
            entry = obj(value, entry_path)
            text = string(entry.get("text"), entry_path + ".text")
            if text and text not in full_text:
                issue(entry_path + ".text", "入口须实际存在于正文", text, "同步入口与正文")
            refs(entry.get("step_ids"), entry_path + ".step_ids", local_ids)
            if entry.get("step_ids") == []:
                issue(entry_path + ".step_ids", "入口须对应正式步骤", [], "登记至少一个实际对应步骤")

    step_order = {}
    for index, (path, step) in enumerate(steps):
        ident = step.get("id") if isinstance(step.get("id"), str) else ""
        if ident in step_order:
            issue(path + ".id", "步骤 ID 全局唯一", ident, "改用唯一 ID 并同步引用")
        step_order[ident] = index
    if phase == "draft":
        symbols, symbol_ids = records(root.get("symbols"), "symbols")
        symbol_defs = {}
        for i, symbol in enumerate(symbols):
            for key in ("notation", "meaning", "scope", "defined_in"):
                string(symbol.get(key), f"symbols[{i}].{key}")
            defined = symbol.get("defined_in")
            if not isinstance(defined, str) or defined not in step_order:
                issue(f"symbols[{i}].defined_in", "定义步骤存在", defined, "登记实际定义位置")
            ident = symbol.get("id")
            if isinstance(ident, str):
                symbol_defs[ident] = step_order.get(defined) if isinstance(defined, str) else None
        for index, (path, step) in enumerate(steps):
            refs(step.get("uses_symbols"), path + ".uses_symbols", symbol_ids)
            for ident in strings(step.get("uses_symbols"), path + ".uses_symbols"):
                defined_at = symbol_defs.get(ident)
                if defined_at is not None and defined_at > index:
                    issue(path + ".uses_symbols", "登记符号先定义后使用", ident, "在首次使用前补定义")

    seen_text = {}
    for path, text in texts:
        for paragraph in re.split(r"\n\s*\n", text):
            normalized = re.sub(r"\s+", "", paragraph)
            if len(normalized) < 20:
                continue
            if normalized in seen_text:
                issue(path, "明显重复需核对", paragraph[:180],
                      "检查与 " + seen_text[normalized] + " 是否重复；只删无新增信息部分", "warning")
            seen_text[normalized] = path

    defects, _ = records(root.get("defects", []), "defects")
    for i, defect in enumerate(defects):
        for key in ("location", "requirement", "evidence", "impact", "repair"):
            string(defect.get(key), f"defects[{i}].{key}")
        if defect.get("severity") not in ("blocker", "major", "minor"):
            issue(f"defects[{i}].severity", "有效严重度", defect.get("severity"), "使用 blocker/major/minor")
        if defect.get("status") not in ("open", "repaired", "unverified"):
            issue(f"defects[{i}].status", "有效修复状态", defect.get("status"), "使用 open/repaired/unverified")
        if strict and defect.get("severity") in ("blocker", "major") and defect.get("status") != "repaired":
            issue(f"defects[{i}]", "已登记主要缺陷尚未修复", defect.get("evidence"), defect.get("repair", "补证或修复"))
    return {"ok": not any(x["severity"] == "error" for x in issues),
            "scope": "仅结构与已登记对应；未验证语义、事实、数学或人的理解", "issues": issues}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--strict", action="store_true", help="Fail on registered unresolved major/blocker defects")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.record.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    result = lint(data, args.strict)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
