#!/usr/bin/env python3
"""Static checks for at_account_accountant, for when no Odoo runtime is around.

Catches the mistakes that otherwise only surface as an install failure:
missing data files, dangling xmlids, report actions pointing at templates that
do not exist, and report_type values with no action behind them.

    python3 tools/validate_module.py
"""
import ast
import glob
import os
import py_compile
import re
import sys
import xml.etree.ElementTree as ET

MODULE = "at_account_accountant"


def main():
    root = os.path.join(os.path.dirname(__file__), os.pardir, MODULE)
    os.chdir(os.path.abspath(root))
    problems = []

    manifest = ast.literal_eval(open("__manifest__.py").read())
    for data_file in manifest["data"]:
        if not os.path.exists(data_file):
            problems.append(f"manifest data file missing: {data_file}")

    xml_files = glob.glob("**/*.xml", recursive=True)

    defined = set()
    for path in xml_files:
        for el in ET.parse(path).getroot().iter():
            if el.tag in ("record", "template", "menuitem") and el.get("id"):
                defined.add(f"{MODULE}.{el.get('id')}")

    for path in xml_files:
        text = open(path).read()
        refs = set(re.findall(rf't-call="({MODULE}\.[\w.]+)"', text))
        for el in ET.parse(path).getroot().iter():
            for attr in ("parent", "action", "ref"):
                value = el.get(attr)
                if value and value.startswith(f"{MODULE}."):
                    refs.add(value)
        for ref in sorted(refs):
            if ref not in defined:
                problems.append(f"{path}: unresolved xmlid {ref}")

    for path in xml_files:
        for record in ET.parse(path).getroot().iter("record"):
            if record.get("model") != "ir.actions.report":
                continue
            for field in record.findall("field"):
                if field.get("name") == "report_name" and field.text not in defined:
                    problems.append(f"{path}: report_name has no template {field.text}")

    for path in glob.glob("**/*.py", recursive=True):
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as err:
            problems.append(f"{path}: {err}")

    for path in glob.glob("report/*.py"):
        for name in re.findall(r'_name = "report\.([\w.]+)"', open(path).read()):
            if name not in defined:
                problems.append(f"{path}: no template for report model {name}")

    wizard = open("wizard/financial_report_wizard.py").read()
    selection_block = wizard.split('string="Report"')[0]
    report_types = set(re.findall(r'\("(\w+)",', selection_block))
    actions = dict(re.findall(rf'"(\w+)": "({MODULE}\.[\w.]+)",', wizard))
    for report_type in sorted(report_types):
        if report_type not in actions:
            problems.append(f"report_type {report_type!r} missing from REPORT_ACTIONS")
    for report_type, action in sorted(actions.items()):
        if action not in defined:
            problems.append(f"REPORT_ACTIONS[{report_type!r}] -> undefined {action}")

    print(f"{len(defined)} xmlids, {len(report_types)} report types")
    if problems:
        print("FAILED")
        for problem in problems:
            print("  !", problem)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
