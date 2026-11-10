"""Spec-driven development gate: every requirement is verified, and tests only cite real requirements."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"
REQ_ID = re.compile(r"REQ-[A-Z]+-\d+")


def defined_requirements() -> set[str]:
    ids = set()
    for line in (SPECS / "requirements.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(REQ-[A-Z]+-\d+)\s*\|", line)
        if m:
            assert m.group(1) not in ids, f"duplicate requirement {m.group(1)}"
            ids.add(m.group(1))
    return ids


def automated_coverage() -> set[str]:
    ids = set()
    for path in (ROOT / "tests").glob("test_*.py"):
        for args in re.findall(r"pytest\.mark\.req\(([^)]*)\)", path.read_text(encoding="utf-8")):
            ids.update(REQ_ID.findall(args))
    return ids


def manual_coverage() -> set[str]:
    ids = set()
    for line in (SPECS / "manual-tests.md").read_text(encoding="utf-8").splitlines():
        if re.match(r"\|\s*S-\d+\s*\|", line):
            ids.update(REQ_ID.findall(line.rstrip(" |").rsplit("|", 1)[-1]))
    return ids


def test_requirements_are_defined():
    assert len(defined_requirements()) > 20


def test_every_requirement_is_verified():
    missing = defined_requirements() - automated_coverage() - manual_coverage()
    assert not missing, f"requirements with no automated or manual test: {sorted(missing)}"


def test_tests_cite_only_existing_requirements():
    unknown = (automated_coverage() | manual_coverage()) - defined_requirements()
    assert not unknown, f"tests cite requirements not in specs/requirements.md: {sorted(unknown)}"
