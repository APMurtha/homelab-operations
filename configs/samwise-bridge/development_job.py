"""Trusted program streamed into the pinned container. No repository imports."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request

TARGET = "samwise_even.py"
TEMPLATE = "add-parity-helper"
EXPRESSIONS = ("value % 2 == 0", "(value & 1) == 0")
MODEL = "qwen3:4b-instruct-2507-q4_K_M"
CASES = [-3, -2, -1, 0, 1, 2, 3, 2**64]
TEST = "integer-parity-v1"


def source(expression):
    if expression not in EXPRESSIONS:
        raise ValueError("unexpected implementation")
    return f"def is_even(value: int) -> bool:\n    return {expression}\n"


def validate(result):
    if (not isinstance(result, dict) or set(result) != {"source", "test"}
            or result["source"] not in tuple(map(source, EXPRESSIONS)) or result["test"] != TEST):
        raise ValueError("unexpected development result")
    return result


def run():
    with tempfile.TemporaryDirectory(dir="/tmp") as directory:
        root = Path(directory)
        checkout = root / "checkout"
        checkout.mkdir()  # Sparse projection: the sole authorized path is a verified addition.
        os.chdir(root)
        home = root / "home"
        (home / ".codex").mkdir(parents=True)
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(home),
               "CODEX_HOME": str(home / ".codex"), "OLLAMA_NO_CLOUD": "1",
               "OLLAMA_MODELS": "/opt/samwise/models", "OLLAMA_HOST": "127.0.0.1:11434",
               "OLLAMA_CONTEXT_LENGTH": "4096", "OLLAMA_NUM_PARALLEL": "1",
               "CODEX_OSS_BASE_URL": "http://127.0.0.1:11434/v1"}
        schema = root / "schema"
        schema.write_text(json.dumps({"type": "object", "additionalProperties": False,
                                     "required": ["expression"], "properties": {"expression": {
                                         "type": "string", "enum": EXPRESSIONS}}}))
        prompt = ("Implement is_even(value: int) -> bool. Choose a readable return expression "
                  "from the schema that handles signed integers and zero.")
        quiet = dict(env=env, cwd=home, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with subprocess.Popen(["/usr/local/bin/ollama", "serve"], stdin=subprocess.DEVNULL,
                              **quiet) as server:
            try:
                for _ in range(40):
                    try:
                        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1):
                            break
                    except OSError:
                        if server.poll() is not None:
                            raise RuntimeError("local model server exited")
                        time.sleep(0.25)
                else:
                    raise RuntimeError("local model server timed out")
                args = ["/usr/local/bin/codex", "--ask-for-approval", "never", "exec", "--oss",
                        "--local-provider", "ollama", "--model", MODEL, "--sandbox", "read-only",
                        "--ephemeral", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check",
                        "--enable", "skip_host_skill_discovery", "-c", 'web_search="disabled"',
                        "-c", "model_context_window=4096"]
                for feature in ("shell_tool", "shell_snapshot", "plugins", "hooks", "multi_agent", "apps"):
                    args.extend(["--disable", feature])
                answer = root / "answer"
                args.extend(["--output-schema", str(schema), "--output-last-message", str(answer), "-"])
                subprocess.run(args, input=prompt.encode(), check=True, timeout=145, **quiet)
            finally:
                if server.poll() is None:
                    server.kill()
        with answer.open("rb") as stream:
            raw = stream.read(257)
        if len(raw) > 256:
            raise ValueError("oversized answer")
        data = json.loads(raw)
        if not isinstance(data, dict) or set(data) != {"expression"}:
            raise ValueError("unexpected answer")
        module = source(data["expression"])
        target = checkout / TARGET
        target.write_text(module)
        # Run the fixed tests against the exact staged file, only after validating the grammar.
        harness = ('import runpy,sys\nf=runpy.run_path(sys.argv[1])["is_even"]\n'
                   f'assert all(f(i) is (i % 2 == 0) for i in {CASES!r})')
        subprocess.run([sys.executable, "-I", "-S", "-c", harness, str(target)],
                       stdin=subprocess.DEVNULL, check=True, timeout=3, **quiet)
        print(json.dumps(validate({"source": target.read_text(), "test": TEST})))


if __name__ == "__main__":
    run()
