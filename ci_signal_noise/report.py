"""Format scoring results as a compact terminal report."""

from .scorer import grade_score, top_noise_sources


def format_report(run_info: dict, job_scores: dict[str, dict], overall: dict, log_lines: list[str] | None = None) -> str:
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

    grade, label = grade_score(overall["signal_pct"])
    lines.append(
        f"  Overall: {overall['signal_pct']:.1f}% signal  [Grade: {grade}]"
        f"  ({overall['signal']} signal / {overall['noise']} noise / {overall['neutral']} neutral"
        f" / {overall['total']} total)"
    )
    lines.append(f"  {label}")

    if log_lines:
        noise_sources = top_noise_sources(log_lines)
        if noise_sources:
            lines.append("")
            lines.append("  Top noise sources (suppress to improve signal):")
            for category, count in noise_sources:
                lines.append(f"    - {category}: {count} lines")

    return "\n".join(lines)


def format_multi_run_summary(run_reports: list[tuple[dict, dict]]) -> str:
    """Summary across multiple runs. Each item is (run_info, overall_score)."""
    if not run_reports:
        return "No runs to report."

    lines = ["", "=== Summary across runs ===", ""]
    lines.append(f"  {'Run ID':<12} {'Signal%':>8}  {'Grade':<7} {'Conclusion':<12}  Title")
    lines.append(f"  {'-' * 12} {'-' * 8}  {'-' * 7} {'-' * 12}  -----")

    for run_info, overall in run_reports:
        run_id = str(run_info.get("databaseId", "?"))
        pct = f"{overall['signal_pct']:.1f}%"
        grade, _ = grade_score(overall["signal_pct"])
        conclusion = run_info.get("conclusion", "?") or "?"
        title = run_info.get("displayTitle", "")[:60]
        lines.append(f"  {run_id:<12} {pct:>8}  {grade:<7} {conclusion:<12}  {title}")

    return "\n".join(lines)
