"""Audit this version's built artifacts without uploading or printing secrets."""

import argparse
from email.parser import BytesParser
import hashlib
from pathlib import Path, PurePosixPath
import tarfile
import tomllib
import zipfile


def audit_members(names):
    forbidden = {".env", ".env.example", ".DS_Store", ".git", ".venv", "node_modules", "__pycache__", "data", "assets", "apps"}
    for name in names:
        parts = PurePosixPath(name).parts
        if any(part in forbidden or part.startswith(".env.") for part in parts):
            raise ValueError(f"Unexpected private/deployment file in release: {name}")
        if name.endswith((".pyc", ".pyo", ".db", ".sqlite3", ".log")):
            raise ValueError(f"Unexpected generated file in release: {name}")


def check(directory: Path, root: Path):
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    version = project["version"]
    stem = project["name"].replace("-", "_") + "-" + version
    wheel = directory / f"{stem}-py3-none-any.whl"
    source = directory / f"{stem}.tar.gz"
    for artifact in (wheel, source):
        if not artifact.is_file():
            raise ValueError(f"Missing artifact: {artifact.name}. Run python -m build first.")
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        audit_members(names)
        required = {f"discord_bot_maker/{module}" for module in (
            "__init__.py", "dbot.py", "features.py", "responses.py", "interactions.py",
            "storage.py", "reminders.py", "definition.py", "engine.py", "flow.py",
            "cli.py", "example.py", "py.typed",
        )}
        if not required <= set(names):
            raise ValueError("Wheel is missing public modules or its type marker.")
        metadata = BytesParser().parsebytes(archive.read(f"{stem}.dist-info/METADATA"))
        if metadata["Name"] != project["name"] or metadata["Version"] != version:
            raise ValueError("Wheel metadata disagrees with pyproject.toml.")
        if metadata["Requires-Python"] != project["requires-python"]:
            raise ValueError("Python requirement disagrees with project metadata.")
        if metadata["License-Expression"] != "MIT":
            raise ValueError("Missing MIT license expression.")
        dependencies = metadata.get_all("Requires-Dist", [])
        if not any(value.startswith("discord.py") for value in dependencies) or not any(value.startswith("pydantic") for value in dependencies):
            raise ValueError("Core runtime dependencies are missing.")
        entrypoints = archive.read(f"{stem}.dist-info/entry_points.txt").decode()
        if "discord-bot-maker = discord_bot_maker.cli:main" not in entrypoints:
            raise ValueError("CLI entry point is missing.")
    with tarfile.open(source, "r:gz") as archive:
        names = archive.getnames()
        audit_members(names)
        required = {f"{stem}/{file}" for file in ("pyproject.toml", "README.md", "LICENSE", "CHANGELOG.md", "llms.txt", "docs/authoring.md", "docs/releasing.md", "examples/sponge.py", "src/discord_bot_maker/py.typed")}
        if not required <= set(names):
            raise ValueError("Source archive is missing documentation or example source.")
        if any(member.issym() or member.islnk() for member in archive.getmembers()):
            raise ValueError("Release source should not contain symlinks.")
    for artifact in (wheel, source):
        print(f"{artifact.name}  sha256={hashlib.sha256(artifact.read_bytes()).hexdigest()}")
    print(f"Release {version} passed artifact checks. Nothing was uploaded.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        check(args.dist, root)
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, tarfile.TarError) as error:
        parser.exit(1, f"Release check failed: {error}\n")


if __name__ == "__main__":
    main()
