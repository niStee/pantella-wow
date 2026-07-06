import contextlib
import os
import subprocess
import sys
import time

# Run Pantella bootstrap with piped input for non-interactive testing
ROOT = r"D:\repos\Pantella"
PYTHON = r"D:\repos\Pantella-Launcher\Pantella_Launcher\python-3.10.11-embed\python.exe"
BOOTSTRAP = os.path.join(ROOT, "pantella_wow_bootstrap.py")
LOG_DIR = os.path.join(ROOT, "logs")
STDOUT_LOG = os.path.join(LOG_DIR, "backend_stdout.txt")
STDERR_LOG = os.path.join(LOG_DIR, "backend_stderr.txt")

os.makedirs(LOG_DIR, exist_ok=True)

for path in (STDOUT_LOG, STDERR_LOG):
    if os.path.exists(path):
        os.remove(path)

inputs = ["hello", "how are you", "goodbye"]

with open(STDOUT_LOG, "wb") as out, open(STDERR_LOG, "wb") as err:
    proc = subprocess.Popen(
        [PYTHON, BOOTSTRAP],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=out,
        stderr=err,
        text=True,
        bufsize=1,
    )

    print(f"PID={proc.pid}", flush=True)

    started = False
    for _ in range(900):
        time.sleep(1)
        try:
            with open(STDOUT_LOG, encoding="utf-8", errors="replace") as f:
                content = f.read()
            if "Starting Conversation Loop" in content or "WoW: Step" in content:
                started = True
                print("CONVERSATION_LOOP_STARTED", flush=True)
                break
        except Exception:
            pass

    if not started:
        print("TIMEOUT_WAITING_FOR_LOOP", flush=True)
        proc.terminate()
        time.sleep(2)
        proc.kill()
        sys.exit(1)

    # Feed each input line with a delay
    for line in inputs:
        print(f"SENDING: {line}", flush=True)
        proc.stdin.write(line + "\n")
        proc.stdin.flush()
        time.sleep(30)  # Give LLM time to respond

    # Let it finish and capture any trailing output
    time.sleep(5)
    proc.terminate()
    time.sleep(2)
    with contextlib.suppress(Exception):
        proc.kill()

print("DONE", flush=True)
