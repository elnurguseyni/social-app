import os
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "app-control.sh"


@pytest.mark.parametrize("arguments", [[], ["restart"]])
def test_rejects_invalid_arguments(arguments):
    result = subprocess.run(
        ["bash", str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode == 1
    assert "Usage:" in result.stderr


@pytest.mark.parametrize(
    "workflow_status,expected_exit",
    [("FAILED", 1), ("SUCCEEDED", 0)],
)
def test_reports_workflow_result(
    tmp_path, monkeypatch, workflow_status, expected_exit
):
    fake_aws = tmp_path / "aws"
    fake_aws.write_text(
        """#!/bin/bash
case "$*" in
  "stepfunctions start-execution "*)
    echo "mock-execution-arn"
    ;;
  "stepfunctions describe-execution "*)
    if [[ "$*" == *"--query status"* ]]; then
      echo "$MOCK_WORKFLOW_STATUS"
    else
      echo '{"error":"PracticeError","cause":"Simulated failure"}'
    fi
    ;;
  *)
    echo "Unexpected mock command" >&2
    exit 2
    ;;
esac
"""
    )
    fake_aws.chmod(0o755)

    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("MOCK_WORKFLOW_STATUS", workflow_status)

    result = subprocess.run(
        ["bash", str(SCRIPT), "start"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode == expected_exit
    assert f"Current status: {workflow_status}" in result.stdout

    if workflow_status == "FAILED":
        assert "PracticeError" in result.stderr
        assert "Simulated failure" in result.stderr
    else:
        assert "App start workflow completed." in result.stdout
        assert result.stderr == ""