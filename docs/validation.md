# 2.0.0a1 validation record

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

The web app previously passed type checking and production compilation. Initial
browser tests failed, then web work was paused. Production PostgreSQL behavior,
runner recovery, container execution/deployment and backup restoration remain
unverified. These services are excluded from PyPI artifacts and are not part of
the prerelease's production-readiness claim.

## Secrets and publication

Local .env, bot data, virtual environments and generated output are ignored.
Release archives are checked against the configured local secret values without
printing those values, as well as common token/key patterns. The staged commit is
reviewed separately before committing. Publication remains a manual user action;
see releasing.md for the exact artifact-specific command.
