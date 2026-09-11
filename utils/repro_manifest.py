"""Record input checksums, parameters, and the runtime without user identity."""
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import platform


def sha256_file(filename):
    digest = hashlib.sha256()
    with Path(filename).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(input_files, random_seed, key_parameters,
                   reproduce_command, dependencies):
    versions = {}
    for package in dependencies:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not installed"
    return {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "random_seed": random_seed,
        # reproduce.write_manifest converts these to project-relative paths.
        "input_files": [{"path": str(Path(filename).resolve()),
                         "sha256": sha256_file(filename)}
                        for filename in input_files],
        "runtime": {"name": "python", "version": platform.python_version(),
                    "platform": platform.platform(), "dependencies": versions},
        "key_parameters": key_parameters,
        "reproduce_command": reproduce_command,
    }
