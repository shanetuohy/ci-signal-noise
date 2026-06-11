"""CLI entrypoint for ci-signal-noise."""

import argparse
import json
import sys

from .flaky import detect_flaky_tests, extract_test_results
from .flaky_report import format_flaky_report
from .gh_client import download_run_logs, list_runs
from .report import format_multi_run_summary, format_report
from .scorer import grade_score, score_lines, top_noise_sources


def main():
    parser = argparse.ArgumentParser(
        prog="ci-signal-noise",
        description="Score CI signal vs noise ratio from GitHub Actions logs",
    )
    parser.add_argument("repo", help="GitHub repo (owner/name)")
    parser.add_argument("--run-id", type=int, help="Specific run ID to analyze")
    parser.add_argument("--runs", type=int, default=3, help="Number of recent runs to analyze (default: 3)")
    parser.add_argument("--flaky", action="store_true", help="Detect flaky tests across multiple runs")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output results as JSON for CI pipeline integration")

    args = parser.parse_args()

    if args.run_id:
        run_ids = [args.run_id]
        runs_by_id = {args.run_id: {"databaseId": args.run_id, "displayTitle": "", "conclusion": ""}}
    else:
        runs = list_runs(args.repo, limit=args.runs)
        if not runs:
            print(
                f"No runs found for '{args.repo}'. "
                "Verify the repo exists and you have access (gh auth status).",
                file=sys.stderr,
            )
            sys.exit(1)
        run_ids = [r["databaseId"] for r in runs]
        runs_by_id = {r["databaseId"]: r for r in runs}

    summaries: list[tuple[dict, dict]] = []
    json_runs: list[dict] = []
    runs_test_results: list[list] = []

    for run_id in run_ids:
        run_info = runs_by_id[run_id]
        try:
            logs = download_run_logs(args.repo, run_id)
        except RuntimeError as e:
            print(f"Skipping run {run_id}: {e}", file=sys.stderr)
            continue

        if not logs:
            print(
                f"No logs for run {run_id} in '{args.repo}'. "
                "The run may still be queued or in progress.",
                file=sys.stderr,
            )
            continue

        all_lines = []
        job_scores = {}
        for job_name, lines in logs.items():
            job_scores[job_name] = score_lines(lines)
            all_lines.extend(lines)

        if args.flaky:
            runs_test_results.append(extract_test_results(all_lines))

        overall = score_lines(all_lines)
        grade, label = grade_score(overall["signal_pct"])
        noise_sources = top_noise_sources(all_lines)

        if args.json_output:
            json_runs.append({
                "run_id": run_info.get("databaseId"),
                "title": run_info.get("displayTitle", ""),
                "conclusion": run_info.get("conclusion", ""),
                "workflow": run_info.get("workflowName", ""),
                "overall": overall,
                "grade": grade,
                "grade_label": label,
                "top_noise_sources": [
                    {"category": cat, "count": cnt} for cat, cnt in noise_sources
                ],
                "jobs": {name: scores for name, scores in sorted(job_scores.items())},
            })
        else:
            print(format_report(run_info, job_scores, overall, log_lines=all_lines))
            print()

        summaries.append((run_info, overall))

    if args.json_output:
        print(json.dumps({"runs": json_runs}, indent=2))
    else:
        if len(summaries) > 1:
            print(format_multi_run_summary(summaries))

        if args.flaky:
            if len(runs_test_results) < 2:
                print(
                    f"\nFlaky detection requires at least 2 runs with logs, "
                    f"but only {len(runs_test_results)} had downloadable logs. "
                    "Try increasing --runs or check that recent runs have completed.",
                    file=sys.stderr,
                )
            else:
                flaky_reports = detect_flaky_tests(runs_test_results)
                print()
                print(format_flaky_report(flaky_reports, total_runs=len(runs_test_results)))


if __name__ == "__main__":
    main()
