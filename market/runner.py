"""Linux local worker supervision, plus explicitly simulated HSWM fixtures."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from .contracts import MarketError, canonical, digest, normalize_hswm, require
from .core import Market


def hswm_fixture(offer, output, prompt=100, completion=20):
    """Native-compatible example data, never a call to HSWM or an LLM."""
    text = canonical(output)
    sha = hashlib.sha256(text.encode()).hexdigest()
    return {"status": "SUCCEEDED", "success": None, "durationSeconds": 0,
            "output": text, "outputDigest": sha,
            "metadata": {"execution_observation_v1": {
                "schema_version": "hswm-adaptive-execution-observation/v1",
                "executor_schema": "hswm-adaptive-executor/v1", "kind": "llm",
                "cell_id": offer["cell_id"], "configured_model": offer["model"],
                "configuration_sha256": offer["configuration_sha256"], "output_digest": sha,
                "provider_usage": {"status": "REPORTED", "prompt_tokens": prompt,
                                   "completion_tokens": completion, "total_tokens": prompt + completion,
                                   "reported_model": offer["model"]}}}}


def live_hswm_status():
    # A caller-supplied boolean or a token balance cannot manufacture admission.
    return {"status": "NOT_READY", "reason": "No owner-authorized registered HSWM transport is installed",
            "required": ["USL resource/workspace mapping", "owner-selected scope and recipient",
                         "expiry and revocation", "bounded authorized reachability check",
                         "HSWM runtime-owned execution/admission capability"]}


def run(market, provider, order_id):
    require(sys.platform.startswith("linux"), "bounded local worker requires Linux")
    order = market.claim(provider, order_id)
    process = None
    result = None
    try:
        # Cancellation may have arrived between claim and launch.
        latest = market.snapshot()["orders"][order_id]
        if latest["state"] == "STOP_REQUESTED":
            return market.finish(order_id, order["lease"], output=None, usage=None, evidence=None, process_stopped=True)
        with tempfile.TemporaryDirectory(prefix="mh-market-work-") as directory:
            with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
                process = subprocess.Popen([sys.executable, "-I", str(Path(__file__).with_name("worker.py"))],
                    stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, cwd=directory,
                    start_new_session=True, env={"LANG": "C.UTF-8"})
                process.stdin.write(canonical(order["terms"]).encode())
                process.stdin.close()
                while process.poll() is None:
                    current = market.snapshot()
                    row = current["orders"][order_id]
                    grant = current["grants"][row["grant_id"]]
                    if (row["state"] == "STOP_REQUESTED" or grant["state"] != "ACTIVE"
                            or market.clock() >= min(order["deadline_ms"], grant["expires_at_ms"])):
                        _stop(process)
                        break
                    time.sleep(0.01)
                process.wait(timeout=2)
                stdout.seek(0)
                raw = stdout.read(4097)
                if process.returncode == 0 and len(raw) <= 4096:
                    try:
                        result = json.loads(raw)
                    except (ValueError, UnicodeError):
                        result = None
    except (OSError, subprocess.SubprocessError, BrokenPipeError):
        result = None
    finally:
        if process is not None and process.poll() is None:
            _stop(process)
        if process is not None:
            process.wait(timeout=2)
    if result is None:
        return market.finish(order_id, order["lease"], output=None, usage=None, evidence=None, process_stopped=True)
    usage = {"input_tokens": 0, "output_tokens": 0, "cpu_ms": result["cpu_ms"],
             "memory_mib_ms": result["peak_rss_mib"] * result["wall_ms"]}
    evidence = {"mode": "LOCAL_BUILTIN_EXECUTION", "worker_source_sha256": hashlib.sha256(Path(__file__).with_name("worker.py").read_bytes()).hexdigest(),
                "meter": "process_time_ns+ru_maxrss/v1", "wall_ms": result["wall_ms"],
                "peak_rss_mib": result["peak_rss_mib"], "model_calls": 0}
    if order["offer_terms"]["backend"] == "fixture-hswm":
        native = hswm_fixture(order["offer_terms"], result["output"])
        adapted = normalize_hswm(native, model=order["offer_terms"]["model"],
                                cell_id=order["offer_terms"]["cell_id"],
                                configuration_sha256=order["offer_terms"]["configuration_sha256"])
        usage.update({u: adapted[u] for u in ("input_tokens", "output_tokens")})
        evidence.update({"mode": "LOCAL_COMPUTE_WITH_SIMULATED_HSWM_USAGE", "hswm": adapted,
                         "hswm_execution": native, "request_sha256": digest(order["terms"]["task"]),
                         "order_id": order_id, "inference_token_origin": "FIXTURE_NOT_MODEL_RUN"})
    return market.finish(order_id, order["lease"], output=result["output"], usage=usage,
                         evidence=evidence, process_stopped=True)


def _stop(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=0.2)
    except ProcessLookupError:
        pass
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)
