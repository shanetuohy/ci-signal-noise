"""Wrapper around the `gh` CLI to fetch GitHub Actions logs."""

import json
import re
import subprocess


def _run_gh(*args: str, timeout: int = 120) -> str:
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        hint = ""
        if "auth login" in stderr or "authentication" in stderr.lower():
            hint = " Hint: run 'gh auth login' to authenticate."
        elif "Could not resolve" in stderr or "repository not found" in stderr.lower():
            hint = " Hint: check that the repo name is correct and that you have access."
        raise RuntimeError(f"gh {' '.join(args)} failed: {stderr}{hint}")
    return result.stdout


# gh run view --log output format: "job-name\tstep-name\tlog-line"
_LOG_LINE_RE = re.compile(r"^(.+?)\t(.+?)\t(.*)$")


def list_runs(repo: str, limit: int = 5) -> list[dict]:
    """List recent workflow runs for a repo."""
    raw = _run_gh(
        "run", "list",
        "--repo", repo,
        "--limit", str(limit),
        "--json", "databaseId,displayTitle,conclusion,status,event,headBranch,workflowName",
    )
    return json.loads(raw)


def download_run_logs(repo: str, run_id: int) -> dict[str, list[str]]:
    """Fetch logs for a run via `gh run view --log`. Returns {job_name: [lines]}."""
    raw = _run_gh(
        "run", "view", str(run_id),
        "--repo", repo,
        "--log",
        timeout=120,
    )

    logs: dict[str, list[str]] = {}
    for line in raw.splitlines():
        m = _LOG_LINE_RE.match(line)
        if m:
            job_name = m.group(1)
            log_line = m.group(3)
            if job_name not in logs:
                logs[job_name] = []
            logs[job_name].append(log_line)
        else:
            # Fallback: line without tab structure goes to "unknown"
            logs.setdefault("unknown", []).append(line)

    return logs
