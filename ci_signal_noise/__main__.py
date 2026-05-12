"""CLI entrypoint for ci-signal-noise."""

import argparse
import sys

from .flaky import detect_flaky_tests, extract_test_results
from .flaky_report import format_flaky_report
from .gh_client import download_run_logs, list_runs
from .report import format_multi_run_summary, format_report
from .scorer import score_lines


def main():
    parser = argparse.ArgumentParser(
        prog="ci-signal-noise",
        description="Score CI signal vs noise ratio from GitHub Actions logs",
    )
    parser.add_argument("repo", help="GitHub repo (owner/name)")
    parser.add_argument("--run-id", type=int, help="Specific run ID to analyze")
    parser.add_argument("--runs", type=int, default=3, help="Number of recent runs to analyze (default: 3)")
    parser.add_argument("--flaky", action="store_true", help="Detect flaky tests across multiple runs")

    args = parser.parse_args()

    if args.run_id:
        run_ids = [args.run_id]
        runs_by_id = {args.run_id: {"databaseId": args.run_id, "displayTitle": "", "conclusion": ""}}
    else:
        runs = list_runs(args.repo, limit=args.runs)
        if not runs:
            print("No runs found.", file=sys.stderr)
            sys.exit(1)
        run_ids = [r["databaseId"] for r in runs]
        runs_by_id = {r["databaseId"]: r for r in runs}

    summaries: list[tuple[dict, dict]] = []
    runs_test_results: list[list] = []

    for run_id in run_ids:
        run_info = runs_by_id[run_id]
        try:
            logs = download_run_logs(args.repo, run_id)
        except RuntimeError as e:
            print(f"Skipping run {run_id}: {e}", file=sys.stderr)
            continue

        if not logs:
            print(f"No logs for run {run_id}", file=sys.stderr)
            continue

        all_lines = []
        job_scores = {}
        for job_name, lines in logs.items():
            job_scores[job_name] = score_lines(lines)
            all_lines.extend(lines)

        if args.flaky:
            runs_test_results.append(extract_test_results(all_lines))

        overall = score_lines(all_lines)
        print(format_report(run_info, job_scores, overall))
        print()
        summaries.append((run_info, overall))

    if len(summaries) > 1:
        print(format_multi_run_summary(summaries))

    if args.flaky:
        if len(runs_test_results) < 2:
            print("\nFlaky detection requires at least 2 runs.", file=sys.stderr)
        else:
            flaky_reports = detect_flaky_tests(runs_test_results)
            print()
            print(format_flaky_report(flaky_reports, total_runs=len(runs_test_results)))


if __name__ == "__main__":
    main()
