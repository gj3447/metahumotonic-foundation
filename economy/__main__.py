"""Run and replay the local economy demo without network access."""
import argparse
import json
import os
from pathlib import Path
import tempfile

from .artifacts import bundle, to_jsonld, verify_bundle
from .scenarios import demo
from .simulator import SimulationError


def write_json(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".simulation-", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(document, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SimulationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("demo", help="run settlement, cancellation and dispute examples")
    run.add_argument("--output-dir", type=Path, help="write simulation.json and simulation.jsonld here")
    verify = commands.add_parser("verify", help="verify source hashes and replay a saved simulation bundle")
    verify.add_argument("bundle", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "demo":
            simulator, initial, inputs = demo()
            document = bundle(simulator, initial, inputs)
            verify_bundle(document)
            if args.output_dir:
                graph = to_jsonld(document)
                write_json(args.output_dir / "simulation.json", document)
                write_json(args.output_dir / "simulation.jsonld", graph)
            snapshot = simulator.snapshot()
        else:
            document = json.loads(args.bundle.read_text(encoding="utf-8"), object_pairs_hook=unique_keys)
            snapshot = verify_bundle(document).snapshot()
        print(json.dumps({
            "mode": snapshot["mode"], "currency": snapshot["currency"],
            "balances": snapshot["balances"], "escrow_total": snapshot["escrow_total"],
            "total_units": snapshot["total_units"],
            "agreements": {key: value["status"] for key, value in snapshot["agreements"].items()},
            "receipts": len(snapshot["receipts"]), "events": len(document["events"]),
            "bundle_sha256": document["bundle_sha256"], "replay": "PASS",
        }, ensure_ascii=False, indent=2))
    except (SimulationError, ValueError, TypeError, KeyError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
