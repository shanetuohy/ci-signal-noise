# ci-signal-noise

Score CI signal vs noise ratio from GitHub Actions logs.

**Signal** = lines containing actionable info (test failures, errors, build failures, assertion output).
**Noise** = boilerplate (dependency downloads, progress bars, setup steps, blank lines, repeated separators).

## Requirements

- Python 3.10+
- `gh` CLI authenticated with GitHub

## Usage

```bash
# Analyze last 3 runs for a repo
python -m ci_signal_noise owner/repo

# Analyze a specific run
python -m ci_signal_noise owner/repo --run-id 12345

# Analyze last 5 runs
python -m ci_signal_noise owner/repo --runs 5
```

## Output

Per-job and overall signal percentage (0-100), where signal% = signal / (signal + noise).

## Running tests

```bash
python -m pytest tests/ -v
```
