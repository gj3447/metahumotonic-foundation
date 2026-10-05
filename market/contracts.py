"""Exact units and a narrow adapter for HSWM's existing execution observation."""
import hashlib
import json
import re
from fractions import Fraction


class MarketError(ValueError):
    pass


UNITS = ("input_tokens", "output_tokens", "cpu_ms", "memory_mib_ms")
ASSET = "sandbox:SIM-MHC"
MAX_INTEGER = 10**15


def require(condition, message):
    if not condition:
        raise MarketError(message)


def integer(value, name, minimum=0, maximum=MAX_INTEGER):
    require(type(value) is int and minimum <= value <= maximum, f"invalid {name}")
    return value


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-zA-Z0-9_.:-]{1,160}", value), "invalid ID")
    return value


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def read_json(text):
    """Reject ambiguous duplicate fields and non-JSON numeric constants."""
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, f"duplicate JSON field: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise MarketError(f"invalid JSON number: {value}")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def quantities(value):
    require(isinstance(value, dict) and set(value) == set(UNITS), "all four usage units are required")
    return {unit: integer(value[unit], unit) for unit in UNITS}


def prices(value):
    require(isinstance(value, dict) and set(value) == set(UNITS), "all four unit prices are required")
    for unit, rate in value.items():
        require(isinstance(rate, list) and len(rate) == 2, f"price needs [numerator, denominator]: {unit}")
        integer(rate[0], "price numerator")
        integer(rate[1], "price denominator", 1)
    return value


def invoice(rates, usage):
    prices(rates)
    quantities(usage)
    lines = {u: Fraction(usage[u] * rates[u][0], rates[u][1]) for u in UNITS}
    total = sum(lines.values(), Fraction(0))
    # One final ceiling to asset atoms, disclosed in the immutable offer.
    atoms = (total.numerator + total.denominator - 1) // total.denominator
    integer(atoms, "invoice atoms")
    return {"asset": ASSET, "atoms": atoms, "rounding": "CEIL_TOTAL_ONCE",
            "lines": {u: {"quantity": usage[u], "rate": rates[u],
                           "exact_atoms": [v.numerator, v.denominator]} for u, v in lines.items()}}


def job(value):
    require(isinstance(value, dict) and set(value) == {"kind", "n", "delay_ms"}, "invalid bounded job")
    require(value["kind"] == "sum", "only the built-in sum workload is executable")
    integer(value["n"], "n", 0, 2_000_000)
    integer(value["delay_ms"], "delay_ms", 0, 5000)
    return value


def correct_result(spec, output):
    job(spec)
    n = spec["n"]
    return type(output) is dict and set(output) == {"sum"} and type(output["sum"]) is int and output["sum"] == n * (n + 1) // 2


def normalize_hswm(execution, *, model, cell_id, configuration_sha256):
    """Read existing AdaptiveExecution fields, preserving provider-report status.

    This pure conversion performs no HSWM execution/admission, no HTTP I/O and
    no authentication. Missing token counts stay an error, never become zero.
    """
    require(isinstance(model, str) and bool(model), "configured model required")
    require(isinstance(cell_id, str) and bool(cell_id), "configured cell required")
    require(isinstance(configuration_sha256, str) and re.fullmatch(r"[0-9a-f]{64}", configuration_sha256),
            "configuration digest required")
    require(isinstance(execution, dict), "HSWM execution must be an object")
    require(execution.get("status") == "SUCCEEDED", "HSWM execution did not succeed")
    output = execution.get("output")
    require(isinstance(output, str) and len(output.encode()) <= 64000, "invalid HSWM output")
    output_hash = hashlib.sha256(output.encode()).hexdigest()
    require(execution.get("outputDigest") == output_hash, "HSWM output digest mismatch")
    metadata = execution.get("metadata")
    require(isinstance(metadata, dict), "HSWM metadata unavailable")
    obs = metadata.get("execution_observation_v1")
    require(isinstance(obs, dict), "HSWM execution observation unavailable")
    require(obs.get("schema_version") == "hswm-adaptive-execution-observation/v1"
            and obs.get("executor_schema") == "hswm-adaptive-executor/v1"
            and obs.get("kind") == "llm", "unsupported HSWM observation")
    require(obs.get("cell_id") == cell_id and obs.get("configured_model") == model
            and obs.get("configuration_sha256") == configuration_sha256,
            "HSWM cell/model/configuration mismatch")
    require(obs.get("output_digest") == output_hash, "HSWM observation output mismatch")
    usage = obs.get("provider_usage", {})
    require(isinstance(usage, dict), "HSWM usage must be an object")
    require(usage.get("status") == "REPORTED" and usage.get("reported_model") == model,
            "HSWM token usage unavailable or model mismatch")
    prompt = integer(usage.get("prompt_tokens"), "prompt tokens")
    completion = integer(usage.get("completion_tokens"), "completion tokens")
    total = integer(usage.get("total_tokens"), "total tokens")
    require(total == prompt + completion, "HSWM token total mismatch")
    return {"input_tokens": prompt, "output_tokens": completion,
            "meter_status": "PROVIDER_REPORTED", "source_sha256": digest(execution),
            "model": model, "cell_id": cell_id, "configuration_sha256": configuration_sha256,
            "output": output, "output_sha256": output_hash}


def quote_hswm_observation(execution, offer_terms):
    """Quote supplied native evidence without executing HSWM or moving funds.

    Native usage has no CPU/RAM meter. Reject hardware-priced offers instead of
    inventing physical measurements. Zero below means unbilled, not observed.
    """
    require(isinstance(offer_terms, dict), "offer terms must be an object")
    require(offer_terms.get("asset") == ASSET, "only the local sandbox asset is supported")
    rates = prices(offer_terms.get("rates"))
    require(rates["cpu_ms"][0] == rates["memory_mib_ms"][0] == 0,
            "hardware meter required for hardware-priced HSWM offer")
    observed = normalize_hswm(execution, model=offer_terms.get("model"), cell_id=offer_terms.get("cell_id"),
                              configuration_sha256=offer_terms.get("configuration_sha256"))
    billed = {"input_tokens": observed["input_tokens"], "output_tokens": observed["output_tokens"],
              "cpu_ms": 0, "memory_mib_ms": 0}
    return {"status": "QUOTE_ONLY_PROVIDER_REPORTED", "funds_moved": False,
            "offer_sha256": digest(offer_terms), "execution_sha256": observed["source_sha256"],
            "metered_usage": {**billed, "cpu_ms": None, "memory_mib_ms": None},
            "invoice": invoice(rates, billed)}
