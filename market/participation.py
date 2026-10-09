"""Draft CHU admission layered onto the existing conserved sandbox market.

This is a trusted local-process model, NOT remote authentication or hardware
permission. Actor strings, rights-review hashes and reachability observations
are local attestations. It neither mints assets nor calls an external service.
"""
import copy
import re

from .contracts import MarketError, digest, identifier, integer, require
from .core import Market, TERMINAL


PROFILE = "chu-participation-local/v1"
APPROVALS = {"LICENSE", "ACCESS", "OPERATOR"}
MAX_TERM_MS = 3_600_000  # Deliberately shorter than MHL's fourteen-day ceiling.
OBSERVATION_TTL_MS = 30_000


def sha256(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value),
            "SHA-256 required")
    return value


class ParticipationMarket(Market):
    def bootstrap(self, balances, *, operators):
        require(isinstance(operators, list) and operators, "configured operators required")
        for actor in operators:
            identifier(actor)
        require(len(operators) == len(set(operators)), "duplicate operator")
        super().bootstrap(balances)
        with self.transaction() as (s, now):
            s["participation"] = {"profile": PROFILE, "operators": sorted(operators),
                                  "agreements": {}, "observation_ids": []}
            self.event(s, now, "local-operator", "PARTICIPATION_PROFILE", PROFILE,
                       {"operators": sorted(operators), "authentication": "TRUSTED_LOCAL_PROCESS",
                        "actual_remote_access_granted": False})

    @staticmethod
    def profile(s):
        p = s.get("participation")
        require(isinstance(p, dict) and p.get("profile") == PROFILE,
                "participation profile not initialized")
        return p

    @classmethod
    def agreement(cls, s, agreement_id):
        p = cls.profile(s)
        require(agreement_id in p["agreements"], "unknown agreement")
        return p["agreements"][agreement_id]

    def grant(self, *args, **kwargs):
        raise MarketError("use separate LICENSE, ACCESS and OPERATOR approvals plus observation")

    def _quote(self, s, now, requester, offer_id, task, limits, memory_mib, wall_ms):
        require(now >= s["last_time"], "clock moved backwards")
        require(offer_id in s["offers"], "unknown offer")
        # A fresh reachability observation cannot renew an old price commitment.
        require(now + wall_ms < s["offers"][offer_id]["terms"]["expires_at_ms"],
                "offer expired or too close to expiry; publish a fresh offer")
        return super()._quote(s, now, requester, offer_id, task, limits, memory_mib, wall_ms)

    def register_resource(self, actor, resource_id, *, slots, memory_mib, usl_resource_id):
        for value in (actor, resource_id, usl_resource_id):
            identifier(value)
        integer(slots, "slots", 1, 32); integer(memory_mib, "memory MiB", 64, 16384)
        with self.transaction() as (s, now):
            self.profile(s)
            require(actor in s["balances"] and resource_id not in s["resources"], "unknown owner or duplicate resource")
            require(all(r["usl_resource_id"] != usl_resource_id for r in s["resources"].values()),
                    "USL resource alias already registered")
            s["resources"][resource_id] = {"owner": actor, "slots": slots, "memory_mib": memory_mib,
                                         "usl_resource_id": usl_resource_id, "quarantined": False,
                                         "observation_status": "OPERATOR_DECLARED_LOCAL_POOL"}
            self.event(s, now, actor, "REGISTER", resource_id, copy.deepcopy(s["resources"][resource_id]))

    def propose(self, actor, agreement_id, resource_id, *, operator, purpose,
                expires_at_ms, terms_sha256, rights_review_sha256):
        for item in (actor, agreement_id, resource_id, operator, purpose):
            identifier(item)
        integer(expires_at_ms, "expiry")
        sha256(terms_sha256); sha256(rights_review_sha256)
        with self.transaction() as (s, now):
            p = self.profile(s)
            require(operator in p["operators"], "operator is not configured")
            require(resource_id in s["resources"] and
                    s["resources"][resource_id]["owner"] == actor, "resource owner required")
            require(agreement_id not in p["agreements"] and agreement_id not in s["grants"],
                    "agreement ID already used")
            require(now < expires_at_ms <= now + MAX_TERM_MS, "term exceeds local one-hour cap")
            terms = {"owner": actor, "resource_id": resource_id, "operator": operator,
                     "purpose": purpose, "starts_at_ms": now, "expires_at_ms": expires_at_ms,
                     "terms_sha256": terms_sha256, "rights_review_sha256": rights_review_sha256,
                     "resource_limits": {k: s["resources"][resource_id][k] for k in ("slots", "memory_mib")},
                     "profile": PROFILE, "actual_remote_access_granted": False}
            agreement = {"terms": terms, "sha256": digest(terms), "approvals": {},
                         "revoked": False, "observation": None}
            p["agreements"][agreement_id] = agreement
            self.event(s, now, actor, "PROPOSE_PARTICIPATION", agreement_id, copy.deepcopy(agreement))
            return agreement["sha256"]

    def approve(self, actor, agreement_id, kind, *, agreement_sha256):
        require(kind in APPROVALS, "unknown approval kind")
        with self.transaction() as (s, now):
            a = self.agreement(s, agreement_id); terms = a["terms"]
            require(not a["revoked"] and now < terms["expires_at_ms"], "agreement revoked or expired")
            require(agreement_sha256 == a["sha256"], "approval does not bind exact terms")
            expected = terms["operator"] if kind == "OPERATOR" else terms["owner"]
            require(actor == expected, "wrong approving party")
            # Identical approvals are idempotent; they do not refresh the term.
            if kind not in a["approvals"]:
                a["approvals"][kind] = {"actor": actor, "at_ms": now, "sha256": a["sha256"]}
                self.event(s, now, actor, "APPROVE_" + kind, agreement_id, copy.deepcopy(a["approvals"][kind]))

    def _stop_orders(self, s, now, agreement_id, reason):
        for oid, order in s["orders"].items():
            if order["grant_id"] != agreement_id or order["state"] in TERMINAL:
                continue
            if order["state"] == "RESERVED":
                self._close(s, now, oid, "CANCELLED", 0, reason)
            else:
                order["state"] = "STOP_REQUESTED"

    def observe(self, actor, agreement_id, *, reachable, observation_id):
        """Record a local test attestation; never performs a network probe."""
        identifier(observation_id)
        require(type(reachable) is bool, "reachable must be boolean")
        with self.transaction() as (s, now):
            p = self.profile(s); a = self.agreement(s, agreement_id); terms = a["terms"]
            require(actor == terms["operator"] and actor in p["operators"], "configured operator required")
            require(not a["revoked"] and now < terms["expires_at_ms"], "agreement revoked or expired")
            require(set(a["approvals"]) == APPROVALS, "three distinct approvals required")
            require(observation_id not in p["observation_ids"], "observation replay")
            # A single registered resource cannot be pledged twice concurrently.
            if reachable:
                for gid, grant in s["grants"].items():
                    require(not (gid != agreement_id and grant["resource_id"] == terms["resource_id"]
                                 and grant["state"] == "ACTIVE" and now < grant["expires_at_ms"]),
                            "resource already has an active agreement")
                require(not s["resources"][terms["resource_id"]]["quarantined"], "resource quarantined")
            a["observation"] = {"id": observation_id, "at_ms": now, "reachable": reachable,
                                "authority": "LOCAL_OPERATOR_ATTESTATION_NOT_REMOTE_PROOF",
                                "fresh_until_ms": min(now + OBSERVATION_TTL_MS, terms["expires_at_ms"])}
            p["observation_ids"].append(observation_id)
            s["grants"][agreement_id] = {
                "owner": terms["owner"], "provider": terms["owner"],
                "resource_id": terms["resource_id"], "purpose": terms["purpose"],
                "state": "ACTIVE" if reachable else "SUSPENDED",
                "expires_at_ms": a["observation"]["fresh_until_ms"],
                "agreement_sha256": a["sha256"]}
            if not reachable:
                self._stop_orders(s, now, agreement_id, "participation unreachable")
            self.event(s, now, actor, "OBSERVE_PARTICIPATION", agreement_id, copy.deepcopy(a["observation"]))

    @classmethod
    def active_grant(cls, s, grant_id, now):
        grant = super().active_grant(s, grant_id, now)
        a = cls.agreement(s, grant_id)
        require(not a["revoked"] and now < a["terms"]["expires_at_ms"]
                and set(a["approvals"]) == APPROVALS
                and grant["agreement_sha256"] == a["sha256"], "participation inactive")
        return grant

    def revoke(self, actor, grant_id):
        with self.transaction() as (s, now):
            a = self.agreement(s, grant_id)
            require(actor == a["terms"]["owner"], "resource owner required")
            if a["revoked"]:
                return
            a["revoked"] = True
            if grant_id in s["grants"]:
                s["grants"][grant_id]["state"] = "REVOKED"
            self._stop_orders(s, now, grant_id, "participation revoked")
            self.event(s, now, actor, "REVOKE_PARTICIPATION", grant_id, {})

    def participation_status(self, agreement_id):
        s = self.snapshot(); a = self.agreement(s, agreement_id); now = integer(self.clock(), "clock")
        require(now >= s["last_time"], "clock moved backwards")
        if a["revoked"]:
            return "REVOKED"
        if now >= a["terms"]["expires_at_ms"]:
            return "EXPIRED"
        if set(a["approvals"]) != APPROVALS:
            return "PENDING_APPROVALS"
        obs = a["observation"]
        if obs is None:
            return "PENDING_OBSERVATION"
        if not obs["reachable"] or now >= obs["fresh_until_ms"]:
            return "UNREACHABLE"
        if s["resources"][a["terms"]["resource_id"]]["quarantined"]:
            return "QUARANTINED"
        return "ACTIVE"

    @staticmethod
    def invariants(s):
        Market.invariants(s)
        if "participation" not in s:  # Base bootstrap transaction only.
            return
        p = ParticipationMarket.profile(s)
        for gid, a in p["agreements"].items():
            require(digest(a["terms"]) == a["sha256"], "participation terms changed")
            for kind, approval in a["approvals"].items():
                expected = a["terms"]["operator"] if kind == "OPERATOR" else a["terms"]["owner"]
                require(kind in APPROVALS and approval["actor"] == expected
                        and approval["sha256"] == a["sha256"], "approval mismatch")
            if gid in s["grants"]:
                g = s["grants"][gid]
                require(g["agreement_sha256"] == a["sha256"] and
                        g["expires_at_ms"] <= a["terms"]["expires_at_ms"], "grant exceeds agreement")
                require(not a["revoked"] or g["state"] == "REVOKED", "revoked grant restored")
