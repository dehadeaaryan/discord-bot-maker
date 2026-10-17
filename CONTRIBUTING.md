# Contributing

Start with [development setup](docs/development.md) and [authoring API](docs/authoring.md).
Keep the library reusable: Sponge-specific behavior belongs in examples/sponge.py.
Use typed, explicit public APIs and give invalid configurations useful early errors.

Use Bun for frontend dependencies and commit bun.lock. Use the user's configured
Git author/committer identity. Keep secrets, bot data, build output, virtual
environments and platform metadata out of commits and release archives.

The Python package and standalone examples are the current priority. Web work is
paused. Keep experimental code's status explicit; passing library tests does not
establish production readiness for hosted services.

Run the relevant tests and the release checks before proposing a package release.
Include a changelog entry for behavior changes and update the authoring guide and
llms.txt when changing the public API. Preserve documented DBot compatibility or
record the migration clearly. See docs/releasing.md for building and publishing.
