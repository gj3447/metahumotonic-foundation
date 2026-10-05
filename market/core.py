"""SQLite-serialized local market with standing offers and conserved escrow.

Actor names are roles in a trusted operator process, not remote authentication.
Only sandbox asset atoms exist here. The database owner is the trust boundary.
"""
from contextlib import closing, contextmanager
import copy
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from .contracts import (ASSET, MarketError, canonical, correct_result, digest,
                        identifier, integer, invoice, job, prices, quantities, require)


TERMINAL = {"SETTLED", "REFUNDED", "CANCELLED", "EXPIRED", "REJECTED"}


class Market:
    def __init__(self, path, clock=None):
        self.path = str(Path(path).resolve())
        self.clock = clock or (lambda: int(time.time() * 1000))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)")
        os.chmod(self.path, 0o600)

    def bootstrap(self, balances):
        require(isinstance(balances, dict) and balances, "initial balances required")
        for actor, amount in balances.items():
            identifier(actor)
            integer(amount, "initial atoms")
        integer(sum(balances.values()), "initial supply")
        with closing(sqlite3.connect(self.path, timeout=10, isolation_level=None)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            require(db.execute("SELECT 1 FROM state").fetchone() is None, "already initialized")
            state = {"schema": "metahumotonic-market/v1", "mode": "LOCAL_SANDBOX", "asset": ASSET,
                     "initial_balances": balances, "balances": balances, "supply": sum(balances.values()),
                     "resources": {}, "grants": {}, "offers": {}, "orders": {}, "receipts": {},
                     "events": [], "last_time": integer(self.clock(), "clock")}
            db.execute("INSERT INTO state VALUES (1,?)", (canonical(state),))
            db.commit()

    @contextmanager
    def transaction(self):
        with closing(sqlite3.connect(self.path, timeout=10, isolation_level=None)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT data FROM state WHERE id=1").fetchone()
            require(row is not None, "market is not initialized")
            state = json.loads(row[0])
            now = integer(self.clock(), "clock")
            require(now >= state["last_time"], "clock moved backwards")
            state["last_time"] = now
            try:
                yield state, now
                self.invariants(state)
                db.execute("UPDATE state SET data=? WHERE id=1", (canonical(state),))
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def snapshot(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            row = db.execute("SELECT data FROM state WHERE id=1").fetchone()
        require(row is not None, "market is not initialized")
        return json.loads(row[0])

    @staticmethod
    def event(state, now, actor, action, subject, data):
        previous = state["events"][-1]["sha256"] if state["events"] else "0" * 64
        event = {"sequence": len(state["events"]) + 1, "at_ms": now, "actor": actor,
                 "action": action, "subject": subject, "data": data, "previous_sha256": previous}
        event["sha256"] = digest(event)
        state["events"].append(event)

    @staticmethod
    def invariants(state):
        held = sum(o["escrow"] for o in state["orders"].values())
        require(all(type(v) is int and v >= 0 for v in state["balances"].values()), "invalid balance")
        require(held + sum(state["balances"].values()) == state["supply"], "asset conservation failed")
        for order in state["orders"].values():
            require(order["escrow"] >= 0, "negative escrow")
            require(order["state"] not in TERMINAL or order["escrow"] == 0, "closed escrow remains")
        for rid, resource in state["resources"].items():
            reserved = [o for o in state["orders"].values() if o["resource_id"] == rid and o["state"] not in TERMINAL]
            require(len(reserved) <= resource["slots"], "resource overbooked")
            require(sum(o["terms"]["memory_mib"] for o in reserved) <= resource["memory_mib"], "memory overbooked")

    def register_resource(self, actor, resource_id, *, slots, memory_mib, usl_resource_id):
        identifier(actor); identifier(resource_id); identifier(usl_resource_id)
        integer(slots, "slots", 1, 32); integer(memory_mib, "memory MiB", 64, 16384)
        with self.transaction() as (s, now):
            require(actor in s["balances"] and resource_id not in s["resources"], "unknown owner or duplicate resource")
            s["resources"][resource_id] = {"owner": actor, "slots": slots, "memory_mib": memory_mib,
                                         "usl_resource_id": usl_resource_id,
                                         "quarantined": False,
                                         "observation_status": "OPERATOR_DECLARED_LOCAL_POOL"}
            self.event(s, now, actor, "REGISTER", resource_id, copy.deepcopy(s["resources"][resource_id]))

    def grant(self, actor, grant_id, resource_id, *, provider, expires_at_ms):
        identifier(grant_id); identifier(provider); integer(expires_at_ms, "expiry")
        with self.transaction() as (s, now):
            require(resource_id in s["resources"] and s["resources"][resource_id]["owner"] == actor, "resource owner required")
            require(provider in s["balances"] and grant_id not in s["grants"], "invalid provider or duplicate grant")
            require(now < expires_at_ms <= now + 3_600_000, "grant must expire within one hour")
            s["grants"][grant_id] = {"owner": actor, "provider": provider, "resource_id": resource_id,
                                      "expires_at_ms": expires_at_ms, "state": "ACTIVE", "purpose": "bounded-local-market-test"}
            self.event(s, now, actor, "GRANT", grant_id, copy.deepcopy(s["grants"][grant_id]))

    @staticmethod
    def active_grant(s, grant_id, now):
        require(grant_id in s["grants"], "unknown grant")
        grant = s["grants"][grant_id]
        require(grant["state"] == "ACTIVE" and now < grant["expires_at_ms"], "grant revoked or expired")
        return grant

    def publish(self, actor, offer_id, grant_id, *, rates, backend="local-sum", model=None, tokenizer=None,
                cell_id=None, configuration_sha256=None):
        identifier(offer_id); prices(rates)
        require(backend in {"local-sum", "fixture-hswm"}, "live HSWM is NOT_READY; no authorized transport configured")
        if backend == "fixture-hswm":
            for value in (model, tokenizer, cell_id): identifier(value)
            require(isinstance(configuration_sha256, str) and len(configuration_sha256) == 64
                    and all(c in '0123456789abcdef' for c in configuration_sha256), "configuration digest required")
        else:
            require(all(x is None for x in (model, tokenizer, cell_id, configuration_sha256)), "local compute has no AI model")
            require(rates["input_tokens"][0] == rates["output_tokens"][0] == 0, "local compute cannot sell inference tokens")
        with self.transaction() as (s, now):
            grant = self.active_grant(s, grant_id, now)
            require(grant["provider"] == actor and offer_id not in s["offers"], "provider required or duplicate offer")
            terms = {"provider": actor, "grant_id": grant_id, "resource_id": grant["resource_id"],
                     "rates": rates, "asset": ASSET, "backend": backend, "model": model, "tokenizer": tokenizer,
                     "cell_id": cell_id, "configuration_sha256": configuration_sha256,
                     "rounding": "CEIL_TOTAL_ONCE", "failure_policy": "NO_VALID_RESULT_FULL_REFUND",
                     "memory_meter": "PEAK_RSS_MIB_TIMES_WALL_MS", "expires_at_ms": grant["expires_at_ms"]}
            s["offers"][offer_id] = {"terms": terms, "terms_sha256": digest(terms), "state": "OPEN"}
            self.event(s, now, actor, "PUBLISH", offer_id, copy.deepcopy(s["offers"][offer_id]))
            return digest(terms)

    def withdraw(self, actor, offer_id):
        with self.transaction() as (s, now):
            offer = s["offers"][offer_id]
            require(offer["terms"]["provider"] == actor, "provider required")
            offer["state"] = "WITHDRAWN"
            self.event(s, now, actor, "WITHDRAW", offer_id, {})

    def quote(self, requester, offer_id, *, task, limits, memory_mib=128, wall_ms=1000):
        identifier(requester); job(task); quantities(limits)
        integer(memory_mib, "memory cap", 64, 512); integer(wall_ms, "wall cap", 50, 5000)
        integer(limits["cpu_ms"], "CPU cap", 1, 10_000)
        require(limits["memory_mib_ms"] >= memory_mib * wall_ms, "memory-time cap must cover reservation")
        s = self.snapshot(); now = integer(self.clock(), "clock")
        return self._quote(s, now, requester, offer_id, task, limits, memory_mib, wall_ms)

    def _quote(self, s, now, requester, offer_id, task, limits, memory_mib, wall_ms):
        require(requester in s["balances"] and offer_id in s["offers"], "unknown requester or offer")
        offer = s["offers"][offer_id]; terms = offer["terms"]
        require(offer["state"] == "OPEN" and requester != terms["provider"], "offer unavailable or self trade")
        grant = self.active_grant(s, terms["grant_id"], now)
        require(grant["expires_at_ms"] > now + wall_ms + 1000, "grant too close to expiry")
        resource = s["resources"][terms["resource_id"]]
        require(not resource["quarantined"], "resource awaits stop reconciliation")
        active = [o for o in s["orders"].values() if o["resource_id"] == terms["resource_id"] and o["state"] not in TERMINAL]
        require(len(active) < resource["slots"] and sum(o["terms"]["memory_mib"] for o in active) + memory_mib <= resource["memory_mib"], "resource fully reserved")
        if terms["backend"] == "local-sum":
            require(limits["input_tokens"] == limits["output_tokens"] == 0, "local compute has no token usage")
        quote = {"requester": requester, "offer_id": offer_id, "offer_sha256": offer["terms_sha256"],
                 "task": task, "limits": limits, "memory_mib": memory_mib, "wall_ms": wall_ms,
                 "expires_at_ms": min(now + 30_000, grant["expires_at_ms"] - wall_ms - 1000),
                 "maximum_charge": invoice(terms["rates"], limits)}
        quote["sha256"] = digest(quote)
        return quote

    def discover(self, requester, *, task, limits, backend, model=None, tokenizer=None, memory_mib=128, wall_ms=1000):
        matches = []
        for offer_id, offer in self.snapshot()["offers"].items():
            terms = offer["terms"]
            if (terms["backend"], terms["model"], terms["tokenizer"]) != (backend, model, tokenizer): continue
            try:
                matches.append(self.quote(requester, offer_id, task=task, limits=limits, memory_mib=memory_mib, wall_ms=wall_ms))
            except MarketError:
                continue
        return sorted(matches, key=lambda q: (q["maximum_charge"]["atoms"], q["offer_id"]))

    def reserve(self, requester, order_id, quote, *, max_budget):
        identifier(order_id); integer(max_budget, "budget")
        # Validate the entire quote again; never trust a caller's maximum price.
        require(isinstance(quote, dict) and set(quote) == {"requester", "offer_id", "offer_sha256", "task", "limits",
                    "memory_mib", "wall_ms", "expires_at_ms", "maximum_charge", "sha256"}, "invalid quote fields")
        job(quote["task"]); quantities(quote["limits"])
        integer(quote["memory_mib"], "memory cap", 64, 512); integer(quote["wall_ms"], "wall cap", 50, 5000)
        integer(quote["limits"]["cpu_ms"], "CPU cap", 1, 10000)
        require(quote["limits"]["memory_mib_ms"] >= quote["memory_mib"] * quote["wall_ms"], "memory-time cap too low")
        with self.transaction() as (s, now):
            require(order_id not in s["orders"], "order ID already used")
            require(quote["requester"] == requester and now < quote["expires_at_ms"] <= now + 30_000, "quote expired or wrong requester")
            rebuilt = self._quote(s, now, requester, quote["offer_id"], quote["task"], quote["limits"], quote["memory_mib"], quote["wall_ms"])
            rebuilt["expires_at_ms"] = quote["expires_at_ms"]
            rebuilt.pop("sha256"); rebuilt["sha256"] = digest(rebuilt)
            require(canonical(quote) == canonical(rebuilt), "quote was altered")
            offered = s["offers"][quote["offer_id"]]["terms"]
            resource = s["resources"][offered["resource_id"]]
            active = [o for o in s["orders"].values() if o["resource_id"] == offered["resource_id"] and o["state"] not in TERMINAL]
            require(len(active) < resource["slots"] and sum(o["terms"]["memory_mib"] for o in active) + quote["memory_mib"] <= resource["memory_mib"], "resource fully reserved")
            amount = quote["maximum_charge"]["atoms"]
            require(amount <= max_budget and amount <= s["balances"][requester], "insufficient budget or balance")
            s["balances"][requester] -= amount
            s["orders"][order_id] = {"terms": copy.deepcopy(quote), "offer_terms": copy.deepcopy(offered),
                "provider": offered["provider"], "requester": requester, "resource_id": offered["resource_id"],
                "grant_id": offered["grant_id"], "state": "RESERVED", "escrow": amount,
                "created_at_ms": now, "lease": None, "deadline_ms": None, "usage": None, "evidence": None}
            self.event(s, now, requester, "RESERVE", order_id, {"quote_sha256": quote["sha256"], "atoms": amount})

    def _close(self, s, now, order_id, state, amount, reason):
        order = s["orders"][order_id]
        if order["state"] in TERMINAL: return copy.deepcopy(s["receipts"][order_id])
        held = order["escrow"]
        require(0 <= amount <= held, "payment exceeds escrow")
        s["balances"][order["provider"]] += amount
        s["balances"][order["requester"]] += held - amount
        order["escrow"] = 0; order["state"] = state
        receipt = {"order_id": order_id, "asset": ASSET, "state": state, "paid_atoms": amount,
                   "refund_atoms": held - amount, "reserved_atoms": held, "reason": reason,
                   "quote_sha256": order["terms"]["sha256"], "offer_sha256": order["terms"]["offer_sha256"],
                   "usage": order["usage"], "evidence": order["evidence"],
                   "invoice": invoice(order["offer_terms"]["rates"], order["usage"]) if order["usage"] else None,
                   "settlement": "LOCAL_SANDBOX_ONLY", "at_ms": now}
        receipt["sha256"] = digest(receipt); s["receipts"][order_id] = receipt
        self.event(s, now, "local-operator", state, order_id, {"receipt_sha256": receipt["sha256"]})
        return copy.deepcopy(receipt)

    def cancel(self, actor, order_id):
        with self.transaction() as (s, now):
            order = s["orders"][order_id]
            require(actor in {order["requester"], order["provider"]}, "order party required")
            if order["state"] in TERMINAL: return copy.deepcopy(s["receipts"][order_id])
            if order["state"] == "RESERVED": return self._close(s, now, order_id, "CANCELLED", 0, "before execution")
            order["state"] = "STOP_REQUESTED"
            self.event(s, now, actor, "STOP_REQUESTED", order_id, {})

    def revoke(self, actor, grant_id):
        with self.transaction() as (s, now):
            grant = s["grants"][grant_id]
            require(actor == grant["owner"], "resource owner required")
            grant["state"] = "REVOKED"
            for oid, order in s["orders"].items():
                if order["grant_id"] != grant_id or order["state"] in TERMINAL: continue
                if order["state"] == "RESERVED": self._close(s, now, oid, "CANCELLED", 0, "grant revoked")
                else: order["state"] = "STOP_REQUESTED"
            self.event(s, now, actor, "REVOKE", grant_id, {})

    def claim(self, provider, order_id):
        with self.transaction() as (s, now):
            order = s["orders"][order_id]
            require(provider == order["provider"] and order["state"] == "RESERVED", "order cannot start")
            grant = self.active_grant(s, order["grant_id"], now)
            require(not s["resources"][order["resource_id"]]["quarantined"], "resource quarantined")
            require(now < order["terms"]["expires_at_ms"], "reservation expired")
            order["deadline_ms"] = min(now + order["terms"]["wall_ms"], grant["expires_at_ms"])
            order["lease"] = uuid.uuid4().hex; order["state"] = "RUNNING"
            self.event(s, now, provider, "START", order_id, {"deadline_ms": order["deadline_ms"]})
            return copy.deepcopy(order)

    def finish(self, order_id, lease, *, output, usage, evidence, process_stopped):
        require(process_stopped is True, "worker stop acknowledgement required")
        with self.transaction() as (s, now):
            order = s["orders"][order_id]
            require(order["lease"] == lease and lease is not None, "wrong execution lease")
            if order["state"] in TERMINAL: return copy.deepcopy(s["receipts"][order_id])
            grant = s["grants"][order["grant_id"]]
            if (order["state"] == "STOP_REQUESTED" or grant["state"] != "ACTIVE"
                    or now >= grant["expires_at_ms"]):
                return self._close(s, now, order_id, "CANCELLED", 0, "execution stopped after cancellation/revocation")
            if now >= order["deadline_ms"]:
                return self._close(s, now, order_id, "EXPIRED", 0, "execution deadline reached")
            if usage is None or output is None:
                return self._close(s, now, order_id, "REFUNDED", 0, "worker failed; no verified result")
            quantities(usage)
            if any(usage[u] > order["terms"]["limits"][u] for u in usage):
                return self._close(s, now, order_id, "REJECTED", 0, "reported usage exceeds contract")
            require(isinstance(evidence, dict), "evidence required")
            order["usage"] = copy.deepcopy(usage); order["evidence"] = copy.deepcopy(evidence)
            if not correct_result(order["terms"]["task"], output):
                return self._close(s, now, order_id, "REJECTED", 0, "independent sum verifier rejected output")
            order["evidence"].update({"output_sha256": digest(output), "verifier": "sum-closed-form/v1",
                                       "result_status": "VERIFIED_FOR_SUM_ONLY"})
            amount = invoice(order["offer_terms"]["rates"], usage)["atoms"]
            return self._close(s, now, order_id, "SETTLED", amount, "verified bounded workload")

    def sweep(self):
        """Release expired funds; quarantine capacity if supervisor stop is unknown."""
        with self.transaction() as (s, now):
            for oid, order in s["orders"].items():
                if order["state"] in TERMINAL: continue
                grant = s["grants"][order["grant_id"]]
                expired = now >= grant["expires_at_ms"] or grant["state"] != "ACTIVE"
                if order["state"] == "RESERVED" and (expired or now >= order["terms"]["expires_at_ms"]):
                    self._close(s, now, oid, "EXPIRED", 0, "reservation/grant expired before execution")
                elif order["state"] in {"RUNNING", "STOP_REQUESTED"}:
                    if now >= order["deadline_ms"] + 1000:
                        s["resources"][order["resource_id"]]["quarantined"] = True
                        self._close(s, now, oid, "EXPIRED", 0, "stop unconfirmed; capacity quarantined")
                    elif expired or now >= order["deadline_ms"]:
                        order["state"] = "STOP_REQUESTED"

    def reconcile_stopped_resource(self, actor, resource_id, *, evidence_reference):
        identifier(evidence_reference)
        with self.transaction() as (s, now):
            resource = s["resources"][resource_id]
            require(resource["owner"] == actor, "resource owner required")
            require(not any(o["resource_id"] == resource_id and o["state"] not in TERMINAL
                            for o in s["orders"].values()), "active reservations remain")
            resource["quarantined"] = False
            self.event(s, now, actor, "OWNER_STOP_RECONCILIATION", resource_id,
                       {"evidence_reference": evidence_reference, "authority": "LOCAL_OPERATOR_ATTESTATION"})

    def available(self):
        s = self.snapshot(); now = self.clock(); result = {}
        for rid, resource in s["resources"].items():
            grants = [g for g in s["grants"].values() if g["resource_id"] == rid and g["state"] == "ACTIVE" and now < g["expires_at_ms"]]
            orders = [o for o in s["orders"].values() if o["resource_id"] == rid and o["state"] not in TERMINAL]
            enabled = bool(grants) and not resource["quarantined"]
            result[rid] = {"free_slots": resource["slots"] - len(orders) if enabled else 0,
                           "free_memory_mib": resource["memory_mib"] - sum(o["terms"]["memory_mib"] for o in orders) if enabled else 0,
                           "quarantined": resource["quarantined"],
                           "observation_status": resource["observation_status"]}
        return result
