# CI

Every pull request against `main` runs the pipeline in `.github/workflows/ci.yml`.
Nothing deploys — the pipeline's only job is to prove a change is safe before a
human merges it.

## Jobs

| Job | What it does | Blocking |
|---|---|---|
| `lint` | `ruff check` + `ruff format --check` | yes |
| `unit` | `pytest -m unit` on Python 3.11, 3.12, 3.13 | yes |
| `integration` | `pytest -m integration`, after `unit` passes | yes |
| `coverage` | Full suite with `--cov-fail-under=80`; posts a summary and uploads an HTML report | yes |
| `security` | `pip-audit` against `laundry_app/requirements.txt` | yes |
| `ci-required` | Aggregates all of the above into one check | yes |

## Why a single `ci-required` check

Matrix jobs report one check per combination (`unit (3.11)`, `unit (3.12)`, …).
If branch protection named those directly, adding or dropping a Python version
would silently stop enforcing the check — the ruleset would still be waiting on
a context that no longer exists. `ci-required` depends on every other job and
fails if any of them failed, was cancelled, or was skipped. Protection names
only that one context, so the matrix can change freely.

## Running the same checks locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r laundry_app/requirements.txt pytest pytest-cov ruff pip-audit

.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest -m unit
.venv/bin/python -m pytest -m integration
.venv/bin/python -m pytest --cov=laundry_app --cov-fail-under=80
.venv/bin/pip-audit -r laundry_app/requirements.txt
```

## Branch protection

Import `.github/rulesets/main-protection.json` via
**Settings → Rules → Rulesets → New ruleset → Import a ruleset**.

It applies to the default branch and:

- requires a pull request (no direct pushes to `main`)
- requires the `ci-required` status check to pass
- requires branches to be up to date before merging
  (`strict_required_status_checks_policy`)
- requires all review threads resolved
- blocks force-pushes and branch deletion
- restricts merges to squash or rebase

`required_approving_review_count` is set to `0`. GitHub does not let a pull
request author approve their own pull request, so on a single-maintainer repo a
value of `1` makes every PR unmergeable. With `0`, CI still gates the merge and
the merge button is still yours to click. Raise it to `1` as soon as a second
maintainer exists.
