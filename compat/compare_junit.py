"""Per-test differential comparison of pytest JUnit XML files, JIT off versus on.

labeille's `run` records one status per package (pass, fail, crash, timeout,
install_error) and keeps only a 2,000-character stderr tail, so it cannot tell
a pre-existing failure from a JIT-specific one, nor two different failures in
the same test. This script does, from pytest's own JUnit XML.

Producing the files: run both arms with persistent work dirs so each package
is cloned once and both arms test the same checkout, and give each arm its
own JUnit file name (tests run with the repo clone as cwd):

    labeille run --top 25 --work-dir /work --env PYTHON_JIT=0 \
        --test-command-suffix "--junitxml=junit-off.xml" --results-dir results/off
    labeille run --top 25 --work-dir /work --env PYTHON_JIT=1 \
        --test-command-suffix "--junitxml=junit-on.xml"  --results-dir results/on

Reruns of the on arm (3 of 3 for a deterministic candidate, 10 and 10 for an
intermittent one) append more files: junit-on-2.xml, junit-off-2.xml, ...

    python compat/compare_junit.py /work/repos --out results/<run>/compat
    python compat/compare_junit.py --package requests \
        --off a/junit-off.xml --on b/junit-on.xml --on c/junit-on-2.xml --out out/

Output: `<out>/per_test.csv` (one row per package and test id), `<out>/summary.csv`
(one row per package with the evidence-level counts) and a short text summary
on stdout.

Classes, per test (`off_fail` / `on_fail` are counts over the files given;
`n_off` / `n_on` are the number of files):

    no_differential_failure   passed in every run of both arms
    pre_existing              failed in both arms with the same signature
    masked_candidate          failed in both arms with different signatures
    candidate                 passed in every off run, failed in every on run
    intermittent_candidate    passed in every off run, failed in some on runs
    flaky_both                failed in some runs of both arms
    anomaly                   failed in some off run, passed in every on run
    skipped                   skipped in every run of both arms
    skip_differs              skipped in one arm and not the other
    only_in_off / only_in_on  collected in one arm only (a crash truncates the
                              on arm's file; pytest writes it on exit only)

A signature is the failure's type plus the first line of its message, with
hex addresses, memory sizes, durations and temp paths normalised away.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

OFF_GLOB = "junit-off*.xml"
ON_GLOB = "junit-on*.xml"

_NORMALISERS = [
    (re.compile(r"0x[0-9a-fA-F]+"), "0xADDR"),
    (re.compile(r"/tmp/[^\s'\"]+"), "/tmp/PATH"),
    (re.compile(r"\b\d+(\.\d+)?\s*(s|ms|us|µs|ns|KiB|MiB|GiB|KB|MB|GB|bytes)\b"), "N UNIT"),
    (re.compile(r"\bat line \d+\b"), "at line N"),
    (re.compile(r":\d+:"), ":N:"),
]


@dataclass
class TestOutcome:
    outcome: str  # passed | failed | skipped
    signature: str = ""


@dataclass
class ArmResult:
    """All test outcomes for one package in one arm, over one or more runs."""

    files: list[Path] = field(default_factory=list)
    runs: list[dict[str, TestOutcome]] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.runs)

    def test_ids(self) -> set[str]:
        ids: set[str] = set()
        for run in self.runs:
            ids |= run.keys()
        return ids


def normalise(text: str) -> str:
    line = text.strip().splitlines()[0] if text.strip() else ""
    for pattern, repl in _NORMALISERS:
        line = pattern.sub(repl, line)
    return line[:200]


def parse_junit(path: Path) -> dict[str, TestOutcome]:
    """Return {test_id: TestOutcome} from one pytest JUnit XML file.

    Test id is `classname::name`, which is stable across runs for pytest.
    `error` (setup/teardown) counts as failed. A testcase with no child passed.
    """
    root = ET.parse(path).getroot()
    out: dict[str, TestOutcome] = {}
    for case in root.iter("testcase"):
        test_id = f"{case.get('classname', '')}::{case.get('name', '')}"
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        if failure is not None or error is not None:
            # pytest puts "ExcType: message" in `message` and sets no `type`;
            # other producers set `type` instead. Use whichever carries the class.
            node = failure if failure is not None else error
            kind = node.get("type") or ""
            msg = normalise(node.get("message") or (node.text or ""))
            if kind and not msg.startswith(kind):
                msg = f"{kind}: {msg}"
            if node.tag == "error":  # setup or teardown failure
                msg = f"error: {msg}"
            out[test_id] = TestOutcome("failed", msg)
        elif skipped is not None:
            out[test_id] = TestOutcome("skipped")
        else:
            out[test_id] = TestOutcome("passed")
    return out


def load_arm(files: list[Path]) -> ArmResult:
    arm = ArmResult(files=list(files))
    for f in files:
        arm.runs.append(parse_junit(f))
    return arm


def classify(test_id: str, off: ArmResult, on: ArmResult) -> dict[str, object]:
    off_outcomes = [run[test_id] for run in off.runs if test_id in run]
    on_outcomes = [run[test_id] for run in on.runs if test_id in run]

    def count(outcomes: list[TestOutcome], kind: str) -> int:
        return sum(1 for o in outcomes if o.outcome == kind)

    off_fail, on_fail = count(off_outcomes, "failed"), count(on_outcomes, "failed")
    off_skip, on_skip = count(off_outcomes, "skipped"), count(on_outcomes, "skipped")
    off_sigs = sorted({o.signature for o in off_outcomes if o.outcome == "failed"})
    on_sigs = sorted({o.signature for o in on_outcomes if o.outcome == "failed"})

    if not off_outcomes:
        cls = "only_in_on"
    elif not on_outcomes:
        cls = "only_in_off"
    elif off_skip == len(off_outcomes) and on_skip == len(on_outcomes):
        cls = "skipped"
    elif (off_skip > 0) != (on_skip > 0):
        cls = "skip_differs"
    elif off_fail == 0 and on_fail == 0:
        cls = "no_differential_failure"
    elif off_fail > 0 and on_fail > 0:
        if off_sigs == on_sigs:
            cls = "pre_existing"
        elif off_fail == len(off_outcomes) and on_fail == len(on_outcomes):
            cls = "masked_candidate"
        else:
            cls = "flaky_both"
    elif off_fail == 0:
        cls = "candidate" if on_fail == len(on_outcomes) else "intermittent_candidate"
    else:
        cls = "anomaly"

    return {
        "test_id": test_id,
        "class": cls,
        "n_off": len(off_outcomes),
        "off_fail": off_fail,
        "n_on": len(on_outcomes),
        "on_fail": on_fail,
        "off_signature": " | ".join(off_sigs),
        "on_signature": " | ".join(on_sigs),
    }


def compare_package(package: str, off: ArmResult, on: ArmResult) -> list[dict[str, object]]:
    rows = []
    for test_id in sorted(off.test_ids() | on.test_ids()):
        row = classify(test_id, off, on)
        row = {"package": package, **row}
        rows.append(row)
    return rows


def summarise(package: str, off: ArmResult, on: ArmResult, rows: list[dict[str, object]]) -> dict:
    classes = Counter(str(r["class"]) for r in rows)
    return {
        "package": package,
        "off_files": len(off.files),
        "on_files": len(on.files),
        "tests_off": len(off.test_ids()),
        "tests_on": len(on.test_ids()),
        **{c: classes.get(c, 0) for c in CLASS_ORDER},
    }


CLASS_ORDER = [
    "no_differential_failure",
    "pre_existing",
    "masked_candidate",
    "candidate",
    "intermittent_candidate",
    "flaky_both",
    "anomaly",
    "skipped",
    "skip_differs",
    "only_in_off",
    "only_in_on",
]


def discover(repos_dir: Path) -> dict[str, tuple[list[Path], list[Path]]]:
    """Map package dir name -> (off files, on files) under a labeille work dir."""
    found: dict[str, tuple[list[Path], list[Path]]] = {}
    for pkg_dir in sorted(p for p in repos_dir.iterdir() if p.is_dir()):
        off = sorted(pkg_dir.glob(OFF_GLOB))
        on = sorted(pkg_dir.glob(ON_GLOB))
        if off or on:
            found[pkg_dir.name] = (off, on)
    return found


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("repos_dir", nargs="?", type=Path, help="labeille --work-dir/repos")
    parser.add_argument("--package", help="single package name (with --off and --on)")
    parser.add_argument("--off", type=Path, action="append", default=[])
    parser.add_argument("--on", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.package:
        targets = {args.package: (args.off, args.on)}
    elif args.repos_dir:
        targets = discover(args.repos_dir)
    else:
        parser.error("give a repos_dir or --package with --off/--on")

    per_test: list[dict] = []
    summary: list[dict] = []
    for package, (off_files, on_files) in targets.items():
        if not off_files or not on_files:
            summary.append(
                {"package": package, "off_files": len(off_files), "on_files": len(on_files)}
            )
            continue
        off, on = load_arm(off_files), load_arm(on_files)
        rows = compare_package(package, off, on)
        per_test.extend(rows)
        summary.append(summarise(package, off, on, rows))

    write_csv(
        args.out / "per_test.csv",
        per_test,
        ["package", "test_id", "class", "n_off", "off_fail", "n_on", "on_fail",
         "off_signature", "on_signature"],
    )
    write_csv(
        args.out / "summary.csv",
        summary,
        ["package", "off_files", "on_files", "tests_off", "tests_on", *CLASS_ORDER],
    )

    for s in summary:
        if "tests_off" not in s:
            print(f"{s['package']}: missing an arm (off={s['off_files']}, on={s['on_files']})")
            continue
        interesting = {c: s[c] for c in CLASS_ORDER if s[c] and c not in
                       ("no_differential_failure", "skipped")}
        print(f"{s['package']}: {s['tests_off']} tests off, {s['tests_on']} on, "
              f"{s['no_differential_failure']} no differential failure"
              + (f", {interesting}" if interesting else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
