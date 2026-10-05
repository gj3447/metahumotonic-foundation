"""Run a local market demo, inspect its ledger or export portable receipts."""
import argparse
import json
from pathlib import Path
import tempfile

from .contracts import MarketError, require, read_json, quote_hswm_observation
from .core import Market
from .demo import build_demo


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="fresh sandbox ledger and bounded local compute; no network/model calls")
    demo.add_argument("--output-dir", type=Path)
    native = commands.add_parser("quote-hswm", help="price a supplied native observation; no execution/payment")
    native.add_argument("--execution", type=Path, required=True)
    native.add_argument("--offer", type=Path, required=True, help="immutable offer terms JSON")
    for name in ("status", "sweep", "export"):
        sub = commands.add_parser(name)
        sub.add_argument("--db", type=Path, required=True)
        if name == "export": sub.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "quote-hswm":
            for path in (args.execution, args.offer):
                require(path.stat().st_size <= 1_048_576, "input exceeds one MiB")
            print(json.dumps(quote_hswm_observation(read_json(args.execution.read_text(encoding="utf-8")),
                                                  read_json(args.offer.read_text(encoding="utf-8"))), ensure_ascii=False, indent=2))
            return
        if args.command == "demo":
            directory = args.output_dir or Path(tempfile.mkdtemp(prefix="metahumotonic-market-demo-"))
            directory.mkdir(parents=True, exist_ok=True)
            require(not (directory / "market.sqlite3").exists(), "demo requires a fresh directory")
            market, report = build_demo(directory / "market.sqlite3")
            save(directory / "demo.json", report)
        else:
            require(args.db.is_file(), "existing market database required")
            market = Market(args.db)
            if args.command == "sweep": market.sweep()
            directory = args.output_dir if args.command == "export" else None
        state = market.snapshot()
        if directory:
            from .projection import project
            directory.mkdir(parents=True, exist_ok=True)
            save(directory / "market.json", state)
            save(directory / "market.jsonld", project(state))
        print(json.dumps({"mode": state["mode"], "asset": state["asset"], "balances": state["balances"],
                          "escrow_atoms": sum(o["escrow"] for o in state["orders"].values()),
                          "orders": {key: o["state"] for key, o in state["orders"].items()},
                          "available": market.available(), "output_dir": str(directory) if directory else None},
                         ensure_ascii=False, indent=2))
    except (MarketError, KeyError, OSError, UnicodeError, json.JSONDecodeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
