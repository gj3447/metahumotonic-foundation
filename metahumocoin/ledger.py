"""Atomic, single-operator research ledger for dated compute claims.

Capacity entries and clock values are trusted test inputs, NOT capacity proofs.
The SQLite file is the authority boundary; this is not a public financial API.
All amounts are integer reference jobs, never USD, FLOPs or arbitrary LLM tokens.
"""
import hashlib
import json
import sqlite3

PROFILE = {"version": "sum-v1", "n": 1000, "unit": "one-correct-sum-job",
           "quality": "exact integer result", "scope": "LOCAL_REFERENCE_ONLY"}
MAX = 1_000_000


class Rejected(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Rejected(message)


def integer(value, minimum=1):
    require(type(value) is int and minimum <= value <= MAX, "invalid integer")
    return value


def name(value):
    require(isinstance(value, str) and 0 < len(value) <= 128
            and all(c.isalnum() or c in "-_:./" for c in value), "invalid identifier")
    return value


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def run_reference(quantity):
    """Bounded actual local work; result verification uses the closed formula."""
    integer(quantity)
    require(quantity <= 100, "local execution cap is 100 jobs")
    return sum(sum(range(1, PROFILE["n"] + 1)) for _ in range(quantity))


class Ledger:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path, isolation_level=None, timeout=5)
        self.db.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)")
        self.db.execute("INSERT OR IGNORE INTO state VALUES (1, ?)", (encode({
            "clock": 0, "series": {}, "lots": {}, "claims": {}, "events": {}}),))

    def close(self):
        self.db.close()

    def snapshot(self):
        return json.loads(self.db.execute("SELECT body FROM state WHERE id=1").fetchone()[0])

    @staticmethod
    def eligible(state, lot, now):
        series = state["series"][lot["series"]]
        return (lot["active"] and series["start"] <= now < series["end"]
                and now < lot["fresh_until"])

    @classmethod
    def coverage(cls, state, sid, now):
        series = state["series"][sid]
        remaining = sum(lot["quantity"] - lot["spent"] for lot in state["lots"].values()
                        if lot["series"] == sid and cls.eligible(state, lot, now))
        # 20% illustrative reserve margin; not calibrated from provider data.
        covered = remaining * 4 // 5
        liability = series["minted"] - series["burned"]
        return {"physical_remaining": remaining, "covered": covered,
                "liability": liability, "deficit": max(0, liability - covered),
                "headroom": max(0, covered - liability),
                "status": "EXPIRED" if now >= series["end"] else
                          "SHORTFALL" if covered < liability else "COVERED"}

    def report(self, sid, now):
        integer(now, 0)
        state = self.snapshot()
        require(now >= state["clock"], "clock rollback")
        return self.coverage(state, sid, now)

    @staticmethod
    def credit(series, account, amount):
        name(account)
        balance = series["balances"].get(account, 0) + amount
        require(balance >= 0, "insufficient balance")
        series["balances"][account] = balance

    @classmethod
    def invariant(cls, state):
        for sid, series in state["series"].items():
            require(series["profile"] == PROFILE, "profile version mismatch")
            locked = sum(c["quantity"] for c in state["claims"].values()
                         if c["series"] == sid and c["status"] == "LOCKED")
            require(sum(series["balances"].values()) + locked ==
                    series["minted"] - series["burned"], "liability conservation")
        for lid, lot in state["lots"].items():
            locked = sum(c["allocation"].get(lid, 0) for c in state["claims"].values()
                         if c["status"] == "LOCKED")
            require(0 <= lot["spent"] + locked <= lot["quantity"], "capacity conservation")

    def apply(self, event, action, now, **args):
        """All mutations commit together; exact event retries return the old result."""
        name(event)
        integer(now, 0)
        request = encode({"action": action, "now": now, "args": args})
        self.db.execute("BEGIN IMMEDIATE")
        try:
            state = self.snapshot()
            if event in state["events"]:
                old = state["events"][event]
                require(old["request"] == request, "event replay with different request")
                self.db.execute("COMMIT")
                return old["result"]
            require(now >= state["clock"], "clock rollback")
            self.invariant(state)
            require(action in {"create", "capacity", "revoke", "mint", "transfer", "lock", "finish", "release"},
                    "unknown action")
            result = getattr(self, "_" + action)(state, now, **args)
            state["clock"] = now
            self.invariant(state)
            state["events"][event] = {"request": request, "result": result}
            self.db.execute("UPDATE state SET body=? WHERE id=1", (encode(state),))
            self.db.execute("COMMIT")
            return result
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def _create(self, state, now, start, end):
        integer(start, 0)
        integer(end)
        require(now <= start < end, "invalid service window")
        sid = "SIM-MHC-CU:" + hashlib.sha256(encode([PROFILE, start, end]).encode()).hexdigest()[:24]
        require(sid not in state["series"], "series already exists")
        state["series"][sid] = {"profile": PROFILE.copy(), "start": start, "end": end,
                               "minted": 0, "burned": 0, "balances": {}}
        return sid

    def _capacity(self, state, now, sid, lot, slot, quantity, fresh_until):
        name(lot)
        name(slot)
        integer(quantity)
        integer(fresh_until)
        series = state["series"][sid]
        require(lot not in state["lots"], "duplicate capacity lot")
        require(now < fresh_until <= series["end"], "invalid capacity freshness")
        for old in state["lots"].values():
            other = state["series"][old["series"]]
            overlap = max(series["start"], other["start"]) < min(series["end"], other["end"])
            require(not (slot == old["slot"] and overlap), "capacity slot pledged twice")
        state["lots"][lot] = {"series": sid, "slot": slot, "quantity": quantity,
                              "fresh_until": fresh_until, "spent": 0, "active": True}
        return lot

    def _revoke(self, state, now, lot):
        state["lots"][lot]["active"] = False
        return "REVOKED"

    def _mint(self, state, now, sid, account, quantity):
        integer(quantity)
        require(quantity <= self.coverage(state, sid, now)["headroom"], "unbacked mint")
        series = state["series"][sid]
        self.credit(series, account, quantity)
        series["minted"] += quantity
        return quantity

    def _transfer(self, state, now, sid, sender, recipient, quantity):
        integer(quantity)
        series = state["series"][sid]
        require(series["start"] <= now < series["end"], "inactive series")
        self.credit(series, sender, -quantity)
        self.credit(series, recipient, quantity)
        return quantity

    def _lock(self, state, now, sid, account, claim, quantity):
        name(claim)
        integer(quantity)
        require(claim not in state["claims"], "duplicate claim")
        report = self.coverage(state, sid, now)
        require(report["status"] == "COVERED" and report["physical_remaining"] > 0,
                "redemption frozen: expired, stale or shortfall")
        self.credit(state["series"][sid], account, -quantity)
        allocation, needed = {}, quantity
        for lid, lot in sorted(state["lots"].items()):
            if lot["series"] != sid or not self.eligible(state, lot, now):
                continue
            reserved = sum(c["allocation"].get(lid, 0) for c in state["claims"].values()
                           if c["status"] == "LOCKED")
            take = min(needed, lot["quantity"] - lot["spent"] - reserved)
            if take:
                allocation[lid] = take
                needed -= take
            if not needed:
                break
        require(needed == 0, "capacity already reserved")
        state["claims"][claim] = {"series": sid, "account": account, "quantity": quantity,
                                  "allocation": allocation, "status": "LOCKED"}
        return claim

    def _finish(self, state, now, claim, result):
        record = state["claims"][claim]
        require(record["status"] == "LOCKED", "claim already settled")
        require(type(result) is int, "result must be an integer")
        require(all(self.eligible(state, state["lots"][lid], now) for lid in record["allocation"]),
                "capacity no longer available; release the claim")
        # Both valid and invalid attempts consume the reserved capacity.
        for lid, amount in record["allocation"].items():
            state["lots"][lid]["spent"] += amount
        n = PROFILE["n"]
        accepted = result == record["quantity"] * n * (n + 1) // 2
        record.update(status="ACCEPTED" if accepted else "FAILED", result=result)
        series = state["series"][record["series"]]
        if accepted:
            series["burned"] += record["quantity"]
        else:
            self.credit(series, record["account"], record["quantity"])
        return record["status"]

    def _release(self, state, now, claim):
        """Conservatively spend reserved capacity when an outcome is unknown.

        Claims return to the owner, even after expiry; liabilities never vanish.
        This is not a refund of physical work or a fiat compensation payment.
        """
        record = state["claims"][claim]
        require(record["status"] == "LOCKED", "claim already settled")
        for lid, quantity in record["allocation"].items():
            state["lots"][lid]["spent"] += quantity
        self.credit(state["series"][record["series"]], record["account"], record["quantity"])
        record["status"] = "RELEASED_UNCERTAIN"
        return record["status"]
