"""CLI entrypoint for ci-signal-noise."""

import argparse
import sys

from .gh_client import download_run_logs, list_runs
from .report import format_multi_run_summary, format_report
from .scorer import score_lines


def main():
    parser = argparse.ArgumentParser(
        prog="ci-signal-noise",
        description="Measure how much actionable signal vs boilerplate noise appears in your GitHub Actions logs.",
    )
    parser.add_argument("repo", help="GitHub repo in owner/name format (e.g. acme/web-app)")
    parser.add_argument("--run-id", type=int, help="Analyze a specific workflow run by its numeric ID")
    parser.add_argument("--runs", type=int, default=3, help="Number of latest completed runs to analyze (default: 3)")

    args = parser.parse_args()

    if args.run_id:
        run_ids = [args.run_id]
        runs_by_id = {args.run_id: {"databaseId": args.run_id, "displayTitle": "", "conclusion": ""}}
    else:
        runs = list_runs(args.repo, limit=args.runs)
        if not runs:
            print(
                f"No workflow runs found for '{args.repo}'. "
                "Check that the repo name is correct and that it has at least one completed workflow run.",
                file=sys.stderr,
            )
            sys.exit(1)
        run_ids = [r["databaseId"] for r in runs]
        runs_by_id = {r["databaseId"]: r for r in runs}

    summaries: list[tuple[dict, dict]] = []

    for run_id in run_ids:
        run_info = runs_by_id[run_id]
        try:
            logs = download_run_logs(args.repo, run_id)
        except RuntimeError as e:
            print(f"Could not fetch logs for run {run_id} ({e}); continuing with remaining runs.", file=sys.stderr)
            continue

        if not logs:
            print(
                f"No logs available for run {run_id} — the run may still be in progress or its logs may have expired.",
                file=sys.stderr,
            )
            continue

        job_scores = {}
        all_lines = []
        for job_name, lines in logs.items():
            job_scores[job_name] = score_lines(lines)
            all_lines.extend(lines)

        overall = score_lines(all_lines)
        print(format_report(run_info, job_scores, overall))
        print()
        summaries.append((run_info, overall))

    if len(summaries) > 1:
        print(format_multi_run_summary(summaries))


if __name__ == "__main__":
    main()
