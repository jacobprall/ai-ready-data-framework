"""End-to-end tests: full CLI pipeline via subprocess."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.e2e

REPO_ROOT = Path(__file__).parent.parent.parent
AGENT_DIR = REPO_ROOT / "agent"


@pytest.fixture(scope="module")
def fixture_db_path(tmp_path_factory):
    """Create fixture DB for e2e tests."""
    from tests.fixtures.create_fixture import create_fixture
    db_dir = tmp_path_factory.mktemp("e2e_fixture")
    return create_fixture(str(db_dir / "sample.duckdb"))


def _run_cli(*args, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
    """Run the CLI as a subprocess."""
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    cmd = [sys.executable, "-m", "agent.cli"] + list(args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=60,
    )


class TestCliAssess:

    def test_no_connection_exits_with_error(self):
        result = _run_cli("assess")
        assert result.returncode != 0

    def test_assess_with_duckdb(self, fixture_db_path, tmp_path):
        report_path = str(tmp_path / "report.json")
        result = _run_cli(
            "assess",
            "--connection", f"duckdb://{fixture_db_path}",
            "--output", f"json:{report_path}",
            "--schema", "analytics",
            "--no-save",
        )
        assert result.returncode == 0, f"STDERR: {result.stderr}"
        assert Path(report_path).exists()
        report = json.loads(Path(report_path).read_text())
        assert "assessment_id" in report
        assert "summary" in report
        assert "tests" in report
        assert len(report["tests"]) > 0

    def test_assess_dry_run(self, fixture_db_path):
        result = _run_cli(
            "assess",
            "--connection", f"duckdb://{fixture_db_path}",
            "--schema", "analytics",
            "--dry-run",
            "--no-save",
        )
        assert result.returncode == 0, f"STDERR: {result.stderr}"
        assert "Dry Run Preview" in result.stdout or "Dry run complete" in result.stdout

    def test_assess_with_context(self, fixture_db_path, tmp_path):
        # Create a context file
        context_path = tmp_path / "ctx.yaml"
        context_path.write_text(
            "target_level: L2\n"
            "excluded_schemas:\n"
            "  - staging\n"
            "  - _scratch\n"
        )
        report_path = str(tmp_path / "report.json")
        result = _run_cli(
            "assess",
            "--connection", f"duckdb://{fixture_db_path}",
            "--output", f"json:{report_path}",
            "--context", str(context_path),
            "--no-save",
        )
        assert result.returncode == 0, f"STDERR: {result.stderr}"
        report = json.loads(Path(report_path).read_text())
        # Context should be reflected in the report
        if "user_context" in report:
            assert report["user_context"]["target_level"] == "L2"

    def test_assess_interactive_outputs_questions(self, fixture_db_path):
        result = _run_cli(
            "assess",
            "--connection", f"duckdb://{fixture_db_path}",
            "--schema", "analytics",
            "--interactive",
            "--no-save",
            "--output", "stdout",
        )
        assert result.returncode == 0, f"STDERR: {result.stderr}"
        assert "Phase 1" in result.stdout
        assert "Phase 2" in result.stdout

    def test_assess_markdown_output(self, fixture_db_path):
        result = _run_cli(
            "assess",
            "--connection", f"duckdb://{fixture_db_path}",
            "--schema", "analytics",
            "--no-save",
            "--output", "markdown",
        )
        assert result.returncode == 0, f"STDERR: {result.stderr}"
        assert "AI-Ready Data Assessment Report" in result.stdout


class TestCliHistory:

    def test_empty_history(self):
        result = _run_cli(
            "history",
            env_overrides={"AIRD_DB_PATH": "/tmp/aird_test_empty.db"},
        )
        assert result.returncode == 0
        assert "No assessments found" in result.stdout


class TestCliDiff:

    def test_diff_needs_two_assessments(self):
        result = _run_cli(
            "diff",
            env_overrides={"AIRD_DB_PATH": "/tmp/aird_test_empty_diff.db"},
        )
        assert result.returncode == 0
        assert "No assessments found" in result.stdout or "Need at least two" in result.stdout


class TestCliSuites:

    def test_lists_suites(self):
        result = _run_cli("suites")
        assert result.returncode == 0
        assert "common" in result.stdout


class TestCliHelp:

    def test_no_args_shows_help(self):
        result = _run_cli()
        # Exits with 1 but prints help
        assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower() or result.returncode == 1
