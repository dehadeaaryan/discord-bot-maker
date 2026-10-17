"""Check distributions or staged blobs without printing configured secret values."""

import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import zipfile

SECRET_NAME = re.compile(r"TOKEN|SECRET|PASSWORD|API_KEY|PRIVATE_KEY", re.I)
PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|pypi-[A-Za-z0-9_-]{50,}|mfa\.[A-Za-z0-9_-]{50,})\b"),
    re.compile(rb"\b[A-Za-z0-9_-]{23,28}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,}\b"),
]


def configured_secrets(root):
    values = [value.encode() for key, value in os.environ.items() if SECRET_NAME.search(key) and len(value) >= 12]
    env = root / ".env"
    if env.is_file():
        for line in env.read_text().splitlines():
            key, separator, value = line.strip().partition("=")
            if separator and SECRET_NAME.search(key):
                try:
                    parsed = shlex.split(value, comments=True)
                except ValueError:
                    raise ValueError("Cannot parse a local secret setting; fix .env quoting before scanning.") from None
                if len(parsed) == 1 and len(parsed[0]) >= 12:
                    values.append(parsed[0].encode())
    return set(values)


def inspect_bytes(label, data, secrets):
    if any(secret in data for secret in secrets) or any(pattern.search(data) for pattern in PATTERNS):
        raise ValueError(f"Possible credential detected in {label}; content withheld.")


def inspect_archive(path, secrets):
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            for member in archive.namelist():
                inspect_bytes(f"{path.name}:{member}", archive.read(member), secrets)
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            for member in archive.getmembers():
                if member.isfile():
                    with archive.extractfile(member) as content:
                        inspect_bytes(f"{path.name}:{member.name}", content.read(), secrets)
    else:
        raise ValueError("Provide wheel or tar.gz distributions.")


def inspect_staged(root, secrets):
    names = subprocess.check_output(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"], cwd=root).decode().split("\0")
    count = 0
    for name in filter(None, names):
        parts = Path(name).parts
        if any(part in {".env", ".pypirc", "node_modules", ".venv", "__pycache__"} or (part.startswith(".env.") and part != ".env.example") for part in parts):
            raise ValueError(f"Private/generated file staged: {name}")
        data = subprocess.check_output(["git", "show", f":{name}"], cwd=root)
        inspect_bytes(f"staged:{name}", data, secrets)
        count += 1
    print(f"Checked {count} staged files.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="*", type=Path)
    parser.add_argument("--staged", action="store_true")
    args = parser.parse_args()
    if not args.artifacts and not args.staged:
        parser.error("Provide distribution paths or --staged.")
    root = Path(__file__).resolve().parents[1]
    try:
        secrets = configured_secrets(root)
        for artifact in args.artifacts:
            inspect_archive(artifact, secrets)
            print(f"Credential scan passed: {artifact.name}")
        if args.staged:
            inspect_staged(root, secrets)
        print(f"Compared against {len(secrets)} configured secret value(s), plus token/key patterns. Values were not printed.")
    except (ValueError, OSError, subprocess.CalledProcessError, tarfile.TarError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Secret check failed: {error}\n")


if __name__ == "__main__":
    main()
