# 2.0.0 stable release and web validation

Validation date: 2026-10-17. No PyPI upload or web deployment performed.

- Python 3.15.0: 51 repository tests passed, including streaming limits, production
  configuration, ownership, CSRF, credential encryption and disabled hosting.
- Web: type checking and a fresh production build passed. Ten browser checks
  passed against both development and the actual generated production server.
  They cover editing, conditions, saving/reloading, exports/imports, mobile,
  minimap bounds, link metadata, HTML escaping, security headers and throttling.
- The build now waits for Bun's SvelteKit analysis workers and verifies regenerated
  adapter output. PUBLIC_ORIGIN is supplied at web build time for SvelteKit 3.
- Stable wheel/sdist metadata, AGENTS.md/CLAUDE.md inclusion, Twine strict validation
  and configured-secret/token-format archive scans passed.
- Bun and pip-audit found no known advisories for checked locked dependencies.
- GitHub CI includes Python 3.10/3.12/3.15, production browser checks and container
  builds. Local Docker/PostgreSQL, live OAuth and backup restore remain unverified.

Historical prerelease validation follows for context.

## 2.0.0a1 validation record

Release preparation date: 2026-10-17. No upload is performed by these checks.

## Python package

- Full repository suite: 47 tests passed on Python 3.15.0.
- Built wheel installed into fresh virtual environments outside the checkout:
  41 library tests passed on each of Python 3.10.22, 3.12.15 and 3.15.0.
- Installed-package smoke checks: imports, version/CLI, command option metadata,
  scoped SQLite persistence, portable graph export and preview, and py.typed.
- Core-only installations did not require FastAPI, PostgreSQL or frontend tools.
- Source distribution built; its wheel rebuilt from the source archive.
- Twine strict checks passed for the wheel and source archive.
- Artifact audit verifies expected modules, MIT metadata, runtime requirements,
  entry point, examples/docs, type marker and absence of deployment/private files.
- Repository dependency consistency and whitespace checks passed.

The temporary checks included repeated 3.10/3.12 runs where uv provided both a
versioned path and an alias; these are the same interpreter versions, not broader
platform coverage. Testing was local macOS. Linux CI is configured but has not yet
run on GitHub. Upstream Discord/Python deprecation warnings remain visible.

## Live Discord

The original three-command bot was confirmed working by the user. Expanded Sponge
also connected and synchronized its command set. This is not equivalent to a full
live smoke test of buttons, polls, reminders, administrative permissions and
restart behavior. Automated interaction/storage tests cover these features offline.

## Separate repository work

Web development resumed after the prerelease upload. Seven browser tests passed, including minimap bounds in both themes.
Type checking and production
compilation pass. Browser tests exercise build/preview/export/save/reload, both
condition branches, mobile list editing without horizontal overflow, palette
drag/drop, undo/redo, local restoration, imports and invalid-flow feedback.
Desktop and mobile screenshots were inspected. Production PostgreSQL behavior,
runner recovery, container execution/deployment and backup restoration remain
unverified. These services are excluded from PyPI artifacts and are not part of
the prerelease's production-readiness claim.

## Secrets and publication

Local .env, bot data, virtual environments and generated output are ignored.
Release archives are checked against the configured local secret values without
printing those values, as well as common token/key patterns. The staged commit is
reviewed separately before committing. Publication remains a manual user action;
see releasing.md for the exact artifact-specific command.
