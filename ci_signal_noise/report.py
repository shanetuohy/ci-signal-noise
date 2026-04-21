"""Format scoring results as a compact terminal report."""


def format_report(run_info: dict, job_scores: dict[str, dict], overall: dict) -> str:
    """Produce a compact terminal report for a single run."""
    lines = []

    title = run_info.get("displayTitle", "unknown")
    run_id = run_info.get("databaseId", "?")
    conclusion = run_info.get("conclusion", "?")
    workflow = run_info.get("workflowName", "")

    lines.append(f"Run #{run_id}: {title}")
    if workflow:
        lines.append(f"  Workflow: {workflow}  |  Conclusion: {conclusion}")
    lines.append("")

    # Per-job scores
    name_width = max((len(n) for n in job_scores), default=10)
    name_width = min(name_width, 50)

    lines.append(f"  {'Job':<{name_width}}  Signal%  Signal  Noise  Neutral  Total")
    lines.append(f"  {'-' * name_width}  -------  ------  -----  -------  -----")

    for job_name, scores in sorted(job_scores.items()):
        truncated = job_name[:name_width]
        lines.append(
            f"  {truncated:<{name_width}}"
            f"  {scores['signal_pct']:6.1f}%"
            f"  {scores['signal']:>6}"
            f"  {scores['noise']:>5}"
            f"  {scores['neutral']:>7}"
            f"  {scores['total']:>5}"
        )

    lines.append("")
    lines.append(
        f"  Overall: {overall['signal_pct']:.1f}% signal"
        f"  ({overall['signal']} signal / {overall['noise']} noise / {overall['neutral']} neutral"
        f" / {overall['total']} total)"
    )

    return "\n".join(lines)


def format_multi_run_summary(run_reports: list[tuple[dict, dict]]) -> str:
    """Summary across multiple runs. Each item is (run_info, overall_score)."""
    if not run_reports:
        return "No runs to report."

    lines = ["", "=== Summary across runs ===", ""]
    lines.append(f"  {'Run ID':<12} {'Signal%':>8}  {'Conclusion':<12}  Title")
    lines.append(f"  {'-' * 12} {'-' * 8}  {'-' * 12}  -----")

    for run_info, overall in run_reports:
        run_id = str(run_info.get("databaseId", "?"))
        pct = f"{overall['signal_pct']:.1f}%"
        conclusion = run_info.get("conclusion", "?") or "?"
        title = run_info.get("displayTitle", "")[:60]
        lines.append(f"  {run_id:<12} {pct:>8}  {conclusion:<12}  {title}")

    return "\n".join(lines)
