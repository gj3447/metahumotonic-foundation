"""Bounded agent-first economic experiment; no network, model calls or real funds.

Run: python3 -m economy.agent_native --help
All prices, demand, resource units and policies are explicit experimental inputs.
The existing bilateral escrow machine handles every modeled payment.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
import random

from .artifacts import canonical, digest, bundle, verify_bundle
from .simulator import EconomySimulator, SimulationError

ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATHS = ("economy/agent_native.py", "economy/simulator.py",
                "economy/artifacts.py", "economy/scenarios.py")


@dataclass(frozen=True)
class Config:
    rounds: int = 12
    seed: int = 1
    bootstrap_rounds: int = 3
    external_jobs: int = 6
    subsidy_jobs: int = 2
    customer_budget: int = 1000
    sponsor_budget: int = 100
    reward: int = 6
    compute_price: int = 3
    energy_cost: int = 1
    upkeep_per_slot: int = 1
    investment_cost: int = 12
    provider_reserve: int = 4
    outside_margin: int = 1
    worker_budget: int = 12
    worker_reserve: int = 2
    worker_max_spend: int = 4
    worker_min_margin: int = 1
    cost_shock_round: int = 0
    shocked_energy_cost: int = 5
    faulty_provider: bool = False

    def validate(self):
        for key, value in asdict(self).items():
            if key == "faulty_provider":
                if type(value) is not bool:
                    raise SimulationError("faulty_provider must be boolean")
            elif type(value) is not int or not 0 <= value <= 10000:
                raise SimulationError(f"invalid nonnegative integer: {key}")
        if not 1 <= self.rounds <= 30 or self.external_jobs + self.subsidy_jobs > 20:
            raise SimulationError("experiment exceeds round/job limits")
        if not self.compute_price or not self.reward or not self.investment_cost:
            raise SimulationError("prices must be positive")
        return self


class World:
    """Finite-budget customer, solver and hardware-controller agents.

    Local actor IDs are simulation principals, not authenticated identities.
    Policies assent to immutable terms automatically inside their modeled budget.
    """
    def __init__(self, config: Config):
        self.config = config.validate()
        self.rng = random.Random(config.seed)
        self.workers = [f"agent:solver-{i}" for i in range(3)]
        self.providers = [f"agent:hardware-{i}" for i in range(2)]
        self.initial = {"agent:customer": str(config.customer_budget),
                        "agent:sponsor": str(config.sponsor_budget),
                        "agent:physical-supplier": "0",
                        **{a: str(config.worker_budget) for a in self.workers},
                        **{a: "8" for a in self.providers}}
        self.wallet = {a: int(v) for a, v in self.initial.items()}
        self.ledger = EconomySimulator(self.initial)
        self.commands = []
        self.decisions = []
        self.jobs = []
        self.capacity = {a: 2 for a in self.providers}
        self.blocked = {a: set() for a in self.workers}
        self.payments = Counter()
        self.completed_by_worker = Counter()
        self.completed_by_provider = Counter()
        self.reinvestment_earnings = Counter()

    def call(self, action, *args):
        result = getattr(self.ledger, action)(*args)
        self.commands.append({"action": action, "args": list(args)})
        return result

    def reserve(self, key, buyer, seller, amount, unit):
        terms = self.call("propose", key, buyer, seller, unit, str(amount), "1")
        self.call("assent", key, buyer, terms)
        self.call("assent", key, seller, terms)
        self.call("fund", key, buyer)
        self.wallet[buyer] -= amount
        return (key, buyer, seller, amount)

    def finish(self, contract, evidence, valid=True):
        key, buyer, seller, amount = contract
        self.call("start", key, seller)
        self.call("submit", key, seller, "1", "sim:usage/" + key, evidence)
        if valid:
            self.call("accept", key, buyer)
            self.call("settle", key, buyer, "settle:" + key)
            self.wallet[seller] += amount
        else:
            # An explicit cooperative-refund policy, NOT an adversarial judge.
            self.call("dispute", key, buyer, "bounded sum verifier rejected output")
            h = self.call("propose_resolution", key, buyer, "0", "preconfigured cooperative refund")
            for actor in (buyer, seller):
                self.call("assent_resolution", key, actor, h)
            self.call("resolve", key, buyer, "refund:" + key)
            self.wallet[buyer] += amount

    def expense(self, key, actor, amount, kind):
        if amount == 0:
            return
        if self.wallet[actor] < amount:
            raise SimulationError("unfunded physical expense")
        c = self.reserve(key, actor, "agent:physical-supplier", amount, "modeled-" + kind)
        self.finish(c, "sim:assumed-delivery/" + key)
        self.payments[kind] += amount

    def decision(self, tick, actor, action, reason, **details):
        self.decisions.append({"round": tick, "actor": actor, "action": action,
                               "reason": reason, **details})

    def execute(self):
        cfg = self.config
        history = []
        for tick in range(1, cfg.rounds + 1):
            energy = cfg.shocked_energy_cost if cfg.cost_shock_round and tick >= cfg.cost_shock_round else cfg.energy_cost
            requests = ["agent:customer"] * cfg.external_jobs
            if tick <= cfg.bootstrap_rounds:
                requests += ["agent:sponsor"] * cfg.subsidy_jobs
            self.rng.shuffle(requests)
            funded_demand = any(self.wallet[a] >= cfg.reward for a in requests)
            offers = {}
            for provider in self.providers:
                maintenance = self.capacity[provider] * cfg.upkeep_per_slot
                reason = ("NO_FUNDED_DEMAND" if not funded_demand else
                          "OUTSIDE_OPTION" if cfg.compute_price - energy < cfg.outside_margin else
                          "OPERATING_BUDGET" if self.wallet[provider] < maintenance + energy else "QUOTE")
                if reason != "QUOTE":
                    self.decision(tick, provider, "WITHDRAW", reason)
                    continue
                self.expense(f"r{tick}:{provider}:upkeep", provider, maintenance, "upkeep")
                offers[provider] = self.capacity[provider]
                self.decision(tick, provider, "OFFER", "COST_PLUS_OUTSIDE_OPTION",
                              price=cfg.compute_price, slots=self.capacity[provider])
            start_capacity = sum(offers.values())
            used = Counter()
            succeeded = Counter()
            round_paid = Counter()
            for index, payer in enumerate(requests):
                key = f"r{tick}:job{index}"
                if self.wallet[payer] < cfg.reward:
                    self.decision(tick, payer, "REFUSE", "CUSTOMER_BUDGET", job=key)
                    continue
                workers = self.workers[:]
                self.rng.shuffle(workers)
                chosen = None
                for worker in workers:
                    if cfg.compute_price > cfg.worker_max_spend or cfg.reward - cfg.compute_price < cfg.worker_min_margin:
                        self.decision(tick, worker, "REFUSE", "PRICE_OR_MARGIN", job=key)
                        continue
                    if self.wallet[worker] - cfg.compute_price < cfg.worker_reserve:
                        self.decision(tick, worker, "REFUSE", "WORKING_CAPITAL", job=key)
                        continue
                    candidates = [p for p, slots in offers.items() if used[p] < slots
                                  and p not in self.blocked[worker] and self.wallet[p] >= energy]
                    if candidates:
                        # Equal disclosed prices here; shuffle removes fixed ID priority.
                        chosen = (worker, self.rng.choice(candidates))
                        break
                if chosen is None:
                    self.decision(tick, payer, "REFUSE", "NO_ACCEPTABLE_OFFER", job=key)
                    continue
                worker, provider = chosen
                self.decision(tick, worker, "ACCEPT", "FUNDED_JOB_POSITIVE_MARGIN", job=key,
                              provider=provider, spend=cfg.compute_price, reward=cfg.reward)
                customer_contract = self.reserve(key + ":output", payer, worker, cfg.reward, "verified-sum-result")
                compute_contract = self.reserve(key + ":compute", worker, provider, cfg.compute_price, "toy-sum-v1")
                self.expense(key + ":energy", provider, energy, "energy")
                used[provider] += 1
                n = self.rng.randint(10, 100)
                output = sum(range(1, n + 1))
                if cfg.faulty_provider and provider == self.providers[0]:
                    output += 1
                valid = output == n * (n + 1) // 2
                evidence = "sim:result/" + digest({"n": n, "output": output})
                self.finish(compute_contract, evidence, valid)
                self.finish(customer_contract, evidence, valid)
                self.jobs.append({"id": key, "round": tick, "payer": payer, "solver": worker,
                                  "provider": provider, "n": n, "output": output, "verified": valid,
                                  "compute_agreement": compute_contract[0], "output_agreement": customer_contract[0]})
                if valid:
                    self.completed_by_worker[worker] += 1
                    self.completed_by_provider[provider] += 1
                    succeeded[provider] += 1
                    round_paid[payer] += cfg.reward
                    self.payments[payer] += cfg.reward
                else:
                    self.blocked[worker].add(provider)
                    self.decision(tick, worker, "CHANGE_PROVIDER", "INVALID_RESULT", provider=provider, job=key)
            for provider, slots in offers.items():
                surplus = succeeded[provider] * cfg.compute_price - used[provider] * energy - slots * cfg.upkeep_per_slot
                self.reinvestment_earnings[provider] += surplus
                if (used[provider] == slots and succeeded[provider] == slots and surplus > 0
                        and self.reinvestment_earnings[provider] >= cfg.investment_cost
                        and self.wallet[provider] >= cfg.investment_cost + cfg.provider_reserve):
                    self.expense(f"r{tick}:{provider}:invest", provider, cfg.investment_cost, "investment")
                    self.capacity[provider] += 1
                    self.reinvestment_earnings[provider] -= cfg.investment_cost
                    self.decision(tick, provider, "REINVEST", "FULL_UTILIZATION_AND_FUNDED_SURPLUS", slots_added=1)
            snapshot = self.ledger.snapshot()
            if {a: int(v) for a, v in snapshot["balances"].items()} != self.wallet or snapshot["escrow_total"] != "0":
                raise SimulationError("wallet/escrow projection mismatch")
            history.append({"round": tick, "offered_capacity": start_capacity,
                            "installed_capacity": sum(self.capacity.values()),
                            "completed": sum(succeeded.values()), "attempted": sum(used.values()),
                            "external_paid": round_paid["agent:customer"],
                            "subsidy_paid": round_paid["agent:sponsor"],
                            "worker_balances": {a: self.wallet[a] for a in self.workers},
                            "provider_balances": {a: self.wallet[a] for a in self.providers}})
        snapshot = self.ledger.snapshot()
        total = sum(self.completed_by_provider.values())
        post = [r for r in history if r["round"] > cfg.bootstrap_rounds]
        summary = {"completed": total, "failed": len(self.jobs) - total,
                   "initial_capacity": 4, "final_installed_capacity": sum(self.capacity.values()),
                   "final_offered_capacity": history[-1]["offered_capacity"],
                   "post_bootstrap_completed": sum(r["completed"] for r in post),
                   "external_paid": self.payments["agent:customer"], "subsidy_paid": self.payments["agent:sponsor"],
                   "energy_paid": self.payments["energy"], "upkeep_paid": self.payments["upkeep"],
                   "investment_paid": self.payments["investment"],
                   "repeat_solvers": sum(n > 1 for n in self.completed_by_worker.values()),
                   "provider_hhi": (sum(n*n for n in self.completed_by_provider.values()) / (total*total)) if total else None,
                   "money_conserved": sum(self.wallet.values()) == sum(int(v) for v in self.initial.values()),
                   "escrow": snapshot["escrow_total"], "model_calls": 0,
                   "real_resource_growth_measured": False, "safety_evaluated": False}
        return {"config": asdict(cfg), "summary": summary, "rounds": history,
                "decisions": self.decisions, "jobs": self.jobs,
                "ledger": bundle(self.ledger, self.initial, self.commands)}


def source_digests():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCE_PATHS}


def run(config=Config()):
    result = World(config).execute()
    result.update(format="metahumotonic-agent-experiment/v1", mode="LOCAL_SIMULATION",
                  authority="SECONDARY_AI", source_sha256=source_digests())
    result["sha256"] = digest(result)
    return result


def verify(document):
    if not isinstance(document, dict) or document.get("source_sha256") != source_digests():
        raise SimulationError("agent experiment source mismatch")
    if document.get("sha256") != digest({k: v for k, v in document.items() if k != "sha256"}):
        raise SimulationError("agent experiment digest mismatch")
    verify_bundle(document["ledger"])
    if canonical(document) != canonical(run(Config(**document["config"]))):
        raise SimulationError("agent decisions/outcomes differ from policy replay")
    return document["summary"]


def suite():
    """Paired seeds; scenarios are interventions, not forecasts or calibration."""
    cases = {"paid_demand": {}, "subsidy_only": {"external_jobs": 0},
             "cost_shock": {"cost_shock_round": 4}, "faulty_provider": {"faulty_provider": True}}
    rows = []
    for name, changes in cases.items():
        for seed in (1, 2, 3):
            result = run(replace(Config(), seed=seed, **changes))
            rows.append({"scenario": name, "config": result["config"], "summary": result["summary"],
                         "rounds": result["rounds"], "run_sha256": result["sha256"]})
    return {"format": "metahumotonic-agent-suite/v1", "mode": "LOCAL_SIMULATION",
            "source_sha256": source_digests(), "runs": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    single = commands.add_parser("run", help="run one bounded model and export a replayable bundle")
    single.add_argument("--config", type=Path, help="JSON Config object; defaults are illustrative")
    single.add_argument("--output", type=Path, required=True)
    sweep = commands.add_parser("suite", help="four scenarios, three paired seeds; summary evidence")
    sweep.add_argument("--output", type=Path, required=True)
    replay = commands.add_parser("verify", help="replay a run or suite and compare all fields")
    replay.add_argument("path", type=Path)
    args = parser.parse_args()
    from .__main__ import write_json, unique_keys
    try:
        if args.command == "verify":
            doc = json.loads(args.path.read_text(), object_pairs_hook=unique_keys)
            if doc.get("format") == "metahumotonic-agent-suite/v1":
                if canonical(doc) != canonical(suite()):
                    raise SimulationError("suite differs from replay")
                print(json.dumps({"replay": "PASS", "runs": len(doc["runs"])}))
            else:
                print(json.dumps({"replay": "PASS", "summary": verify(doc)}))
            return
        if args.command == "suite":
            result = suite()
            view = [{"scenario": r["scenario"], "seed": r["config"]["seed"], **r["summary"]} for r in result["runs"]]
        else:
            config = Config(**json.loads(args.config.read_text(), object_pairs_hook=unique_keys)) if args.config else Config()
            result = run(config)
            view = result["summary"]
        write_json(args.output, result)
        print(json.dumps(view, ensure_ascii=False, indent=2))
    except (ValueError, TypeError, KeyError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
