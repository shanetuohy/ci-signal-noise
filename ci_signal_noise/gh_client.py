"""Wrapper around the `gh` CLI to fetch GitHub Actions logs."""

import json
import re
import subprocess


def _run_gh(*args: str, timeout: int = 120) -> str:
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"gh {' '.join(args)} timed out after {timeout}s. "
            "The operation may be fetching a large amount of data, or GitHub may be slow. "
            "Try again or increase the timeout."
        )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        hint = ""
        if "auth" in stderr.lower() or "401" in stderr or "403" in stderr:
            hint = " Check your auth with: gh auth status"
        elif "not found" in stderr.lower() or "404" in stderr:
            hint = " Verify the repo name is correct (owner/repo format)."
        elif "timeout" in stderr.lower() or "connection" in stderr.lower():
            hint = " Check your network connection and try again."
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
