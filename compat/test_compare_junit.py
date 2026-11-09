"""Tests for compare_junit, using JUnit XML that pytest itself produced."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_junit as cj  # noqa: E402

SUITE = textwrap.dedent(
    """
    import os, pytest

    JIT = os.environ.get("FAKE_JIT") == "1"
    RUN = int(os.environ.get("FAKE_RUN", "1"))

    def test_always_passes():
        assert 1 + 1 == 2

    def test_pre_existing():
        assert False, "broken on both arms"

    def test_masked():
        if JIT:
            raise RuntimeError("different failure at 0xdeadbeef")
        assert False, "broken on both arms"

    def test_candidate():
        assert not JIT, "fails only with JIT"

    def test_intermittent():
        assert not (JIT and RUN % 2 == 0), "fails on even JIT runs"

    def test_anomaly():
        assert JIT, "fails only without JIT"

    @pytest.mark.skipif(not os.environ.get("FAKE_JIT") == "1", reason="only on jit")
    def test_skip_differs():
        pass

    @pytest.mark.skip(reason="always")
    def test_skipped():
        pass

    class TestClass:
        def test_method(self):
            assert True
    """
)


def run_suite(tmp_path: Path, jit: str, run: int, out: Path) -> None:
    (tmp_path / "test_fake.py").write_text(SUITE)
    env = {**__import__("os").environ, "FAKE_JIT": jit, "FAKE_RUN": str(run)}
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         f"--junitxml={out}", str(tmp_path / "test_fake.py")],
        cwd=tmp_path, env=env, capture_output=True, check=False,
    )
    assert out.exists(), "pytest did not write junit xml"


@pytest.fixture
def arms(tmp_path: Path) -> tuple[list[Path], list[Path]]:
    off = [tmp_path / f"junit-off-{i}.xml" for i in (1, 2)]
    on = [tmp_path / f"junit-on-{i}.xml" for i in (1, 2)]
    for i, p in enumerate(off, 1):
        run_suite(tmp_path, "0", i, p)
    for i, p in enumerate(on, 1):
        run_suite(tmp_path, "1", i, p)
    return off, on


def test_parse_outcomes(arms):
    off, _ = arms
    parsed = cj.parse_junit(off[0])
    assert parsed["test_fake::test_always_passes"].outcome == "passed"
    assert parsed["test_fake::test_pre_existing"].outcome == "failed"
    assert parsed["test_fake::test_skipped"].outcome == "skipped"
    assert "test_fake.TestClass::test_method" in parsed
    assert parsed["test_fake::test_pre_existing"].signature.startswith("AssertionError")


def test_classes(arms):
    off, on = arms
    rows = cj.compare_package("fake", cj.load_arm(off), cj.load_arm(on))
    by_name = {r["test_id"].split("::")[-1]: r["class"] for r in rows}
    assert by_name == {
        "test_always_passes": "no_differential_failure",
        "test_method": "no_differential_failure",
        "test_pre_existing": "pre_existing",
        "test_masked": "masked_candidate",
        "test_candidate": "candidate",
        "test_intermittent": "intermittent_candidate",
        "test_anomaly": "anomaly",
        "test_skip_differs": "skip_differs",
        "test_skipped": "skipped",
    }


def test_intermittent_counts(arms):
    off, on = arms
    rows = {r["test_id"]: r for r in cj.compare_package("fake", cj.load_arm(off), cj.load_arm(on))}
    r = rows["test_fake::test_intermittent"]
    assert (r["n_off"], r["off_fail"], r["n_on"], r["on_fail"]) == (2, 0, 2, 1)


def test_signature_normalises_addresses(arms):
    _, on = arms
    sig = cj.parse_junit(on[0])["test_fake::test_masked"].signature
    assert "0xdeadbeef" not in sig and "0xADDR" in sig


def test_truncated_on_arm_is_only_in_off(arms, tmp_path):
    off, on = arms
    tree = __import__("xml.etree.ElementTree", fromlist=["x"]).parse(on[0])
    suite = tree.getroot().find("testsuite")
    for case in list(suite.findall("testcase"))[3:]:
        suite.remove(case)
    truncated = tmp_path / "junit-on-trunc.xml"
    tree.write(truncated)
    rows = cj.compare_package("fake", cj.load_arm(off), cj.load_arm([truncated]))
    assert sum(1 for r in rows if r["class"] == "only_in_off") == 6


def test_cli_discovery(arms, tmp_path):
    off, on = arms
    repos = tmp_path / "repos" / "fake"
    repos.mkdir(parents=True)
    for p in off + on:
        p.rename(repos / p.name)
    out = tmp_path / "out"
    assert cj.main([str(tmp_path / "repos"), "--out", str(out)]) == 0
    summary = (out / "summary.csv").read_text().splitlines()
    assert summary[0].startswith("package,off_files,on_files,tests_off,tests_on,")
    assert summary[1].startswith("fake,2,2,9,9,2,1,1,1,1,0,1,1,1,0,0")
    assert (out / "per_test.csv").read_text().count("\n") == 10  # header + 9 tests
