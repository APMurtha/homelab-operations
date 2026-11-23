"""Fetch and verify pinned inputs in an external, disposable build context."""
import argparse
from hashlib import file_digest
import json
from pathlib import Path
import shutil
import tarfile
import urllib.request

CODEX = (
    "https://github.com/openai/codex/releases/download/rust-v0.170.0/"
    "codex-x86_64-unknown-linux-musl.tar.gz"
)
CODEX_SHA = "d054916ccd28a53820376b8d2f7c875184ca8f40fcd44bbabeb8ee240ce247f5"
REGISTRY = "registry.ollama.ai"
MODEL = "4b-instruct-2507-q4_K_M"
MANIFEST_SHA = "0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0"


def fetch(url, path, digest):
    with urllib.request.urlopen(url, timeout=60) as response, path.open("xb") as target:
        shutil.copyfileobj(response, target)
    with path.open("rb") as source:
        if file_digest(source, "sha256").hexdigest() != digest:
            raise ValueError(f"Digest mismatch for {url}")
    path.chmod(0o644)


def stage(context):
    context.mkdir()
    source = Path(__file__).resolve().parent
    for name in ("Containerfile", "offline.py"):
        shutil.copyfile(source / name, context / name)
        (context / name).chmod(0o644)
    package = context / "codex.tar.gz"
    fetch(CODEX, package, CODEX_SHA)
    with tarfile.open(package) as archive:
        member = archive.getmember("codex-x86_64-unknown-linux-musl")
        if not member.isfile():
            raise ValueError("Expected a regular Codex binary")
        with archive.extractfile(member) as binary, (context / "codex").open("xb") as target:
            shutil.copyfileobj(binary, target)
    (context / "codex").chmod(0o555)
    package.unlink()

    models = context / "models"
    manifest = models / "manifests" / REGISTRY / "library/qwen3" / MODEL
    manifest.parent.mkdir(parents=True)
    blobs = models / "blobs"
    blobs.mkdir()
    endpoint = f"https://{REGISTRY}/v2/library/qwen3"
    fetch(f"{endpoint}/manifests/{MODEL}", manifest, MANIFEST_SHA)
    spec = json.loads(manifest.read_bytes())
    for dependency in [spec["config"], *spec["layers"]]:
        digest = dependency["digest"]
        path = blobs / digest.replace(":", "-")
        fetch(f"{endpoint}/blobs/{digest}", path, digest.removeprefix("sha256:"))
        if path.stat().st_size != dependency["size"]:
            raise ValueError(f"Unexpected blob size for {digest}")
    for directory in models.rglob("*"):
        if directory.is_dir():
            directory.chmod(0o755)
    models.chmod(0o755)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("context", type=Path, help="New directory for verified build inputs")
    stage(parser.parse_args().context)
