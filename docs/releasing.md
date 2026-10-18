# Publishing Discord Bot Maker to PyPI

## This release

- Existing project: https://pypi.org/project/discord-bot-maker/
- Latest published version reported by the user: **2.0.0a1**.
- Prepared next release: **2.1.1**, the unified-authoring Python package (unreleased).
- Distribution: `discord-bot-maker`; import: `discord_bot_maker`.
- Artifacts: `discord_bot_maker-2.1.1-py3-none-any.whl` and
  `discord_bot_maker-2.1.1.tar.gz`.

This stable release is for the standalone Python package. It can be installed
without `--pre`. The web app and experimental hosted runner are separate repository
services and are excluded from the Python distributions. Preparing artifacts does
not upload a release; run the explicit upload command only after checks pass.

## Prepare and check

From the repository root, using its .venv:

```sh
uv pip install -r requirements.lock
uv pip install -e '.[release]'
.venv/bin/python -m pytest -q
.venv/bin/python -m build
.venv/bin/python scripts/check_release.py
.venv/bin/python scripts/check_secrets.py dist/discord_bot_maker-2.1.1-py3-none-any.whl dist/discord_bot_maker-2.1.1.tar.gz
.venv/bin/python -m twine check --strict dist/discord_bot_maker-2.1.1-py3-none-any.whl dist/discord_bot_maker-2.1.1.tar.gz
```

For a locked publishing-tool install, use `uv pip install -r requirements-release.lock`.
Push the release commit before uploading so the README's GitHub documentation
links point to the matching published source.

The checker verifies metadata, version alignment, expected modules and type marker,
source documentation/examples, secrets/artifact exclusion, and SHA-256 digests.
It checks only this version's exact filenames. Older files in dist/ are never
implicitly selected for upload. `python -m build` also rebuilds the wheel from
its source distribution to check the source manifest.

The separate secret scanner compares archive contents against configured local
secret values and common credential formats without printing the values. Run
`python scripts/check_secrets.py --staged` before committing as well. These checks
complement the manifest exclusions; they cannot prove absence of every possible
unknown credential format. Never put credentials in source or examples.

Use fresh environments to test installation and CLI outside the checkout. Test
supported Python versions in CI before moving from alpha to stable. Library
checks do not certify the repository's optional hosted service for production.

## Upload this version

```sh
.venv/bin/python -m twine upload --repository pypi dist/discord_bot_maker-2.1.1-py3-none-any.whl dist/discord_bot_maker-2.1.1.tar.gz
```

Twine uses supported PyPI credentials from its environment/keyring or prompts for
your **PyPI API token** with hidden input. This is not the Discord bot token.
Create a token scoped to the existing discord-bot-maker project in PyPI account
settings if needed. Do not put it in source, a shell command, or this repository's
.env file. Older Twine versions may request a username: use the literal `__token__`.

Optional rehearsal against TestPyPI uses the same exact artifacts:

```sh
.venv/bin/python -m twine upload --repository testpypi dist/discord_bot_maker-2.1.1-py3-none-any.whl dist/discord_bot_maker-2.1.1.tar.gz
```

TestPyPI is a separate account/project registry with separate credentials. For a
real dependency/install smoke test, prefer a fresh environment and the built wheel;
TestPyPI may not contain dependencies.

## Upgrade after upload

For a consumer's active virtual environment:

```sh
python -m pip install --upgrade 'discord-bot-maker==2.1.1'
```

Or follow the newest stable release:

```sh
python -m pip install --upgrade discord-bot-maker
```

Check the installed version with `discord-bot-maker --version` or
`python -c 'import discord_bot_maker; print(discord_bot_maker.__version__)'`.
An editable checkout still imports local source, so use a fresh environment to
verify what PyPI actually serves.

## Future releases

Change version in pyproject.toml, update CHANGELOG.md and release instructions,
run the checks, commit, and build fresh artifacts. PyPI versions/files are
immutable: if 2.1.1 has already been uploaded, fix forward as 2.1.2 rather than
trying to overwrite it. The release checker derives filenames from metadata.
Do not use `--skip-existing` to hide an accidental version collision.

The manual GitHub publishing workflow is .github/workflows/publish.yml. Configure
PyPI Trusted Publishing for the exact repository, workflow `publish.yml`, and
GitHub environment `pypi`. Then invoke it manually from the committed revision.
The protected environment is the appropriate place for any desired approval rule.
It uses short-lived OIDC credentials; no PyPI API token belongs in GitHub source.
After a successful publish, tag the actual release commit and push that tag when
you intend to announce the release. No tag is created during local preparation.
