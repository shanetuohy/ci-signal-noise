"""Format flaky test analysis as a compact terminal report."""

from .flaky import FlakeReport


def format_flaky_report(reports: list[FlakeReport], total_runs: int) -> str:
    """Produce a compact terminal report of flaky tests."""
    lines: list[str] = []

    lines.append(f"=== Flaky Test Report ({total_runs} runs analyzed) ===")
    lines.append("")

    if not reports:
        lines.append("  No flaky tests detected.")
        return "\n".join(lines)

    lines.append(f"  Found {len(reports)} flaky test(s):")
    lines.append("")

    name_width = min(max(len(r.test_name) for r in reports), 60)
    lines.append(
        f"  {'Test':<{name_width}}  Flake%  Pass  Fail  Seen In"
    )
    lines.append(
        f"  {'-' * name_width}  ------  ----  ----  -------"
    )

    for r in reports:
        truncated = r.test_name[:name_width]
        pct = f"{r.flake_rate * 100:.0f}%"
        lines.append(
            f"  {truncated:<{name_width}}"
            f"  {pct:>5}"
            f"  {r.pass_count:>5}"
            f"  {r.fail_count:>4}"
            f"  {r.total_runs:>3}/{total_runs} runs"
        )

    lines.append("")

    # Suggested actions
    high_flake = [r for r in reports if r.flake_rate >= 0.3]
    if high_flake:
        lines.append("  Suggested actions:")
        for r in high_flake[:5]:
            lines.append(f"    - Investigate: {r.test_name} (flake rate {r.flake_rate * 100:.0f}%)")
    else:
        lines.append("  All flaky tests have low flake rates — monitor but no urgent action needed.")

    return "\n".join(lines)
