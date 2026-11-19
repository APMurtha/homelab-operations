"""Entrypoint baked into the reviewed offline runner image."""
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request

MODEL = "qwen3:4b-instruct-2507-q4_K_M"


def unpack(stream, checkout):
    counts = {}
    with tarfile.open(fileobj=stream, mode="r|") as archive:
        for entry in archive:
            path = PurePosixPath(entry.name)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise ValueError("unsafe archive path")
            if not (entry.isfile() or entry.isdir()):
                raise ValueError("unsupported archive entry")
            archive.extract(entry, checkout, filter="data")
            if entry.isfile():
                suffix = path.suffix.lower()
                if suffix in {".md", ".rst", ".txt"}:
                    category = "documentation"
                elif suffix in {".yaml", ".yml", ".json", ".toml", ".ini", ".conf"}:
                    category = "configuration"
                else:
                    category = "code"
                counts[category] = counts.get(category, 0) + 1
                if sum(counts.values()) > 10000:
                    raise ValueError("too many files")
    if not counts:
        raise ValueError("empty archive")
    return counts


def run():
    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        root = Path(directory)
        checkout = root / "checkout"
        checkout.mkdir()
        counts = unpack(sys.stdin.buffer, checkout)
        home = root / "home"
        codex_home = home / ".codex"
        codex_home.mkdir(parents=True)
        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(home), "LANG": "C.UTF-8",
            "OLLAMA_HOST": "127.0.0.1:11434", "OLLAMA_MODELS": "/opt/samwise/models",
            "OLLAMA_NO_CLOUD": "1", "OLLAMA_CONTEXT_LENGTH": "4096",
            "OLLAMA_NUM_PARALLEL": "1", "OLLAMA_MAX_LOADED_MODELS": "1",
            "CODEX_HOME": str(codex_home),
            "CODEX_OSS_BASE_URL": "http://127.0.0.1:11434/v1",
        }
        answer = root / "answer"
        schema = root / "answer-schema.json"
        schema.write_text(json.dumps({
            "type": "object",
            "properties": {"focus": {"type": "string", "enum": sorted(counts)}},
            "required": ["focus"],
            "additionalProperties": False,
        }), encoding="utf-8")
        # Codex receives aggregate counts from the checkout. Run outside the
        # source tree so repository instructions and config cannot be loaded.
        prompt = (
            "Choose the most useful category to review next for this repository inventory. "
            "Consider only these file counts. Return a JSON object with one key, focus, "
            "whose value is a category from the input.\n"
            + json.dumps(counts, sort_keys=True)
        )
        with subprocess.Popen(["/usr/local/bin/ollama", "serve"], env=env, cwd=home,
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL) as server:
            try:
                for _ in range(40):
                    try:
                        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1) as response:
                            models = json.loads(response.read(65536))["models"]
                        if not any(model["name"] == MODEL for model in models):
                            raise RuntimeError("reviewed local model is missing")
                        break
                    except urllib.error.URLError:
                        if server.poll() is not None:
                            raise RuntimeError("local inference server stopped")
                        time.sleep(0.25)
                else:
                    raise RuntimeError("local inference server unavailable")
                subprocess.run([
                    "/usr/local/bin/codex", "--ask-for-approval", "never", "exec",
                    "--oss", "--local-provider", "ollama", "--model", MODEL,
                    "--sandbox", "read-only", "--ephemeral", "--ignore-user-config",
                    "--ignore-rules", "--skip-git-repo-check", "--disable", "shell_tool",
                    "--disable", "plugins", "--disable", "hooks", "--disable", "multi_agent",
                    "--disable", "apps", "--disable", "shell_snapshot",
                    "--enable", "skip_host_skill_discovery", "-c", 'web_search="disabled"',
                    "-c", "model_context_window=4096", "--output-schema", str(schema),
                    "--output-last-message", str(answer), "-",
                ], env=env, cwd=home, input=prompt.encode(), timeout=145, check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                with answer.open("rb") as result:
                    response = result.read(257)
                if len(response) > 256:
                    raise ValueError("oversized Codex answer")
                data = json.loads(response)
                if (not isinstance(data, dict) or set(data) != {"focus"}
                        or not isinstance(data["focus"], str) or data["focus"] not in counts):
                    raise ValueError("unexpected Codex answer")
                print(json.dumps({"files": sum(counts.values()), "focus": data["focus"]}))
            finally:
                if server.poll() is None:
                    server.kill()
                    server.wait()


if __name__ == "__main__":
    run()
