"""Classify CI log lines as signal or noise and compute scores."""

import re
from collections import Counter

# Signal patterns: lines containing actionable information
SIGNAL_PATTERNS = [
    # Test failures and errors
    re.compile(r"(?i)\bfail(ed|ure|ing)?\b"),
    re.compile(r"(?i)\berror\b"),
    re.compile(r"(?i)exception\b"),
    re.compile(r"(?i)\btraceback\b"),
    re.compile(r"(?i)\bassert(ion)?\s*(error|fail)", re.IGNORECASE),
    re.compile(r"(?i)\bpanic\b"),
    re.compile(r"(?i)\bfatal\b"),
    # Test result summaries
    re.compile(r"\d+\s+(passed|failed|error|skipped)"),
    re.compile(r"(?i)FAIL\s+\S+"),
    re.compile(r"(?i)^(FAILED|PASSED|ERROR)\s"),
    # Build failures
    re.compile(r"(?i)\bbuild\s+fail"),
    re.compile(r"(?i)\bcompil(e|ation)\s+(error|fail)"),
    re.compile(r"(?i)\bundefined\s+reference"),
    re.compile(r"(?i)\bsyntax\s*error"),
    re.compile(r"(?i)\btype\s+error"),
    re.compile(r"(?i)\bname\s*error"),
    re.compile(r"(?i)\bimport\s*error"),
    re.compile(r"(?i)\bmodule\s+not\s+found"),
    # Lint / static analysis
    re.compile(r"(?i)\bwarning\b.*\b(unused|deprecated|shadow)"),
    re.compile(r"(?i)\blint(er)?\s*(error|fail|warning)"),
    # Exit codes
    re.compile(r"(?i)\bexit\s+code\s+[1-9]"),
    re.compile(r"(?i)\bprocess\s+completed\s+with\s+exit\s+code\s+[1-9]"),
    # Diff / change markers in test output
    re.compile(r"^[-+]{3}\s"),
    re.compile(r"^@@\s"),
]

# Noise patterns: boilerplate lines with no actionable content
NOISE_PATTERNS = [
    # Blank or whitespace-only lines
    re.compile(r"^\s*$"),
    # Repeated separators
    re.compile(r"^[-=*#]{3,}\s*$"),
    # Download / fetch progress
    re.compile(r"(?i)\bdownload(ing|ed)?\b.*\b\d+(\.\d+)?\s*(kb|mb|gb|bytes|%)", re.IGNORECASE),
    re.compile(r"(?i)\bfetch(ing|ed)?\b.*\b(package|module|depend)"),
    re.compile(r"\d+%\|[#=\-\s\u2588\u2591]*\|"),  # progress bars
    re.compile(r"(?i)^\s*\d+(\.\d+)?\s*(kb|mb|gb)\s"),
    # Dependency resolution
    re.compile(r"(?i)\bresolving\s+(depend|package|module)"),
    re.compile(r"(?i)\binstalling\s+(depend|package|module|collect)"),
    re.compile(r"(?i)\bcollecting\s+\S+"),
    re.compile(r"(?i)\balready\s+(satisfied|installed|up.to.date)"),
    re.compile(r"(?i)\busing\s+cached\b"),
    # Setup / boilerplate
    re.compile(r"(?i)^\s*\$\s"),  # shell prompt echoes
    re.compile(r"(?i)^run\s+"),  # GitHub Actions "Run" prefix
    re.compile(r"(?i)^##\["),  # GitHub Actions workflow commands
    re.compile(r"(?i)^\s*>+\s*$"),  # empty quote lines
    # Timing lines
    re.compile(r"(?i)^\s*real\s+\d+m"),
    re.compile(r"(?i)^\s*user\s+\d+m"),
    re.compile(r"(?i)^\s*sys\s+\d+m"),
    # Verbose npm/pip/apt output
    re.compile(r"(?i)^npm\s+(warn|notice)\b"),
    re.compile(r"(?i)^\s*added\s+\d+\s+packages?\s+in\s+"),
    re.compile(r"(?i)^\s*up\s+to\s+date"),
]

# Map each noise pattern index to a human-readable category for top_noise_sources().
_NOISE_CATEGORIES = {
    0: "blank lines",
    1: "separator lines",
    2: "download progress", 3: "download progress", 4: "progress bars", 5: "download progress",
    6: "dependency resolution", 7: "dependency resolution", 8: "dependency resolution",
    9: "dependency resolution", 10: "dependency resolution",
    11: "setup boilerplate", 12: "setup boilerplate", 13: "setup boilerplate", 14: "setup boilerplate",
    15: "timing lines", 16: "timing lines", 17: "timing lines",
    18: "package manager output", 19: "package manager output", 20: "package manager output",
}


def classify_line(line: str) -> str:
    """Classify a single log line as 'signal', 'noise', or 'neutral'.

    Signal takes priority: if a line matches both signal and noise patterns,
    it is classified as signal (e.g. "error downloading package").
    """
    stripped = line.rstrip("\n")

    for pat in SIGNAL_PATTERNS:
        if pat.search(stripped):
            return "signal"

    for pat in NOISE_PATTERNS:
        if pat.search(stripped):
            return "noise"

    return "neutral"


def score_lines(lines: list[str]) -> dict:
    """Score a list of log lines and return classification counts + signal percentage."""
    counts = {"signal": 0, "noise": 0, "neutral": 0}
    for line in lines:
        counts[classify_line(line)] += 1

    total = len(lines)
    if total == 0:
        return {**counts, "total": 0, "signal_pct": 0.0}

    # Signal percentage: signal / (signal + noise), ignoring neutral lines.
    # If all lines are neutral, score is 50 (no clear signal or noise).
    classified = counts["signal"] + counts["noise"]
    if classified == 0:
        signal_pct = 50.0
    else:
        signal_pct = round(counts["signal"] / classified * 100, 1)

    return {**counts, "total": total, "signal_pct": signal_pct}


def grade_score(signal_pct: float) -> tuple[str, str]:
    """Map a signal percentage to a letter grade and short label.

    Returns (grade, label) e.g. ("A", "Excellent").
    """
    if signal_pct >= 80:
        return ("A", "Excellent — logs are highly actionable")
    if signal_pct >= 60:
        return ("B", "Good — most output is useful")
    if signal_pct >= 40:
        return ("C", "Fair — significant noise present")
    if signal_pct >= 20:
        return ("D", "Poor — noise dominates signal")
    return ("F", "Failing — logs are nearly all noise")


def _classify_noise_category(line: str) -> str | None:
    """Return the noise category for a line, or None if it's not noise."""
    stripped = line.rstrip("\n")
    # Signal takes priority
    for pat in SIGNAL_PATTERNS:
        if pat.search(stripped):
            return None
    for idx, pat in enumerate(NOISE_PATTERNS):
        if pat.search(stripped):
            return _NOISE_CATEGORIES.get(idx, "other noise")
    return None


def top_noise_sources(lines: list[str], limit: int = 5) -> list[tuple[str, int]]:
    """Identify the most common noise pattern categories in the log.

    Returns a list of (category_name, count) sorted by count descending,
    up to *limit* entries.
    """
    cats = Counter()
    for line in lines:
        cat = _classify_noise_category(line)
        if cat is not None:
            cats[cat] += 1
    return cats.most_common(limit)
