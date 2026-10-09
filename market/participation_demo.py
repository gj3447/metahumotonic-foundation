"""Run a draft CHU admission/accounting example with fictional local parties.

Usage: python3 -m market.participation_demo
No registration, network connection, credential creation or actual MHC issuance.
"""
import json
from pathlib import Path
import tempfile

from .contracts import MarketError, digest, require
from .participation import ParticipationMarket
from .projection import verify_snapshot


def build_demo(path):
    market = ParticipationMarket(path, clock=lambda: 1000)
    market.bootstrap({"sponsor": 1000, "alice": 0, "bob": 0}, operators=["demo-operator"])
    rates = {"input_tokens": [0, 1], "output_tokens": [0, 1],
             "cpu_ms": [1, 1], "memory_mib_ms": [0, 1]}
    for owner in ("alice", "bob"):
        market.register_resource(owner, owner + ":cpu", slots=1, memory_mib=256,
                                 usl_resource_id="usl:fictional-demo:" + owner)
        sha = market.propose(owner, owner + ":grant", owner + ":cpu", operator="demo-operator",
                             purpose="local-accounting-fixture", expires_at_ms=61000,
                             terms_sha256=digest({"fixture": "not-a-license-acceptance"}),
                             rights_review_sha256=digest({"fixture": "not-a-rights-review"}))
        for actor, kind in [(owner, "LICENSE"), (owner, "ACCESS"), ("demo-operator", "OPERATOR")]:
            market.approve(actor, owner + ":grant", kind, agreement_sha256=sha)
        market.observe("demo-operator", owner + ":grant", reachable=True,
                       observation_id=owner + ":reachability-fixture")
        market.publish(owner, owner + ":offer", owner + ":grant", rates=rates)

    def quote(buyer, provider, cap):
        return market.quote(buyer, provider + ":offer", task={"kind": "sum", "n": 10, "delay_ms": 0},
                            limits={"input_tokens": 0, "output_tokens": 0,
                                    "cpu_ms": cap, "memory_mib_ms": 128000})

    def settle_fixture(buyer, provider, oid, cap, used):
        market.reserve(buyer, oid, quote(buyer, provider, cap), max_budget=cap)
        lease = market.claim(provider, oid)["lease"]
        return market.finish(oid, lease, output={"sum": 55},
                             usage={"input_tokens": 0, "output_tokens": 0,
                                    "cpu_ms": used, "memory_mib_ms": 128000},
                             evidence={"mode": "TRUSTED_LOCAL_TEST_FIXTURE_NOT_HARDWARE_PROOF"},
                             process_stopped=True)

    membership_balance = market.snapshot()["balances"]["alice"]
    try:
        market.reserve("alice", "unfunded", quote("alice", "bob", 10), max_budget=10)
    except MarketError:
        unfunded_rejected = True
    else:
        raise AssertionError("membership unexpectedly creates spending power")
    earned = settle_fixture("sponsor", "alice", "earn", 100, 10)
    purchased = settle_fixture("alice", "bob", "buy", 10, 4)
    market.reserve("sponsor", "outage", quote("sponsor", "alice", 100), max_budget=100)
    market.observe("demo-operator", "alice:grant", reachable=False, observation_id="outage-fixture")
    market.revoke("alice", "alice:grant")
    snapshot = market.snapshot()
    verify_snapshot(snapshot)
    require(snapshot["balances"] == {"sponsor": 990, "alice": 6, "bob": 4}, "unexpected balances")
    return market, {"schema": "chu-participation-demo/v1", "mode": "LOCAL_SANDBOX",
                    "authority": "SECONDARY_AI_DESIGN_PROPOSAL_NOT_RATIFIED",
                    "actual_remote_access_granted": False, "model_calls": 0,
                    "metering": "SYNTHETIC_FIXTURE_NOT_MEASURED_COMPUTE",
                    "rights_review": "FIXTURE_NOT_LEGAL_CLEARANCE",
                    "asset": snapshot["asset"], "initial_supply_atoms": 1000,
                    "membership_balance_atoms": membership_balance,
                    "unfunded_purchase_rejected": unfunded_rejected,
                    "earned_atoms": earned["paid_atoms"], "purchased_atoms": purchased["paid_atoms"],
                    "final_balances": snapshot["balances"],
                    "outage_order": snapshot["receipts"]["outage"]["state"],
                    "alice_participation": market.participation_status("alice:grant"),
                    "accounting_replay": "PASS", "new_assets_minted": 0}


def main():
    with tempfile.TemporaryDirectory(prefix="mh-participation-") as directory:
        _, report = build_demo(Path(directory) / "market.sqlite3")
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
