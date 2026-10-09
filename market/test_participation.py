import copy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from .contracts import MarketError, digest
from .participation import ParticipationMarket, MAX_TERM_MS, OBSERVATION_TTL_MS
from .projection import verify_snapshot
from .runner import run


TASK = {"kind": "sum", "n": 10, "delay_ms": 0}
LIMITS = {"input_tokens": 0, "output_tokens": 0, "cpu_ms": 100, "memory_mib_ms": 128000}
RATES = {"input_tokens": [0, 1], "output_tokens": [0, 1], "cpu_ms": [1, 1], "memory_mib_ms": [0, 1]}


class ParticipationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "market.sqlite3"
        self.now = 1000
        self.m = ParticipationMarket(self.path, clock=lambda: self.now)
        self.m.bootstrap({"sponsor": 1000, "alice": 0, "bob": 0}, operators=["operator"])
        for owner in ("alice", "bob"):
            self.m.register_resource(owner, owner + ":cpu", slots=2 if owner == "bob" else 1, memory_mib=256,
                                     usl_resource_id="usl:test:" + owner)

    def tearDown(self):
        self.directory.cleanup()

    def proposal(self, owner="alice", gid=None, **kw):
        terms = {"operator": "operator", "purpose": "local-sum-test",
                 "expires_at_ms": self.now + 60000, "terms_sha256": digest({"fixture": "terms"}),
                 "rights_review_sha256": digest({"fixture": "rights-not-legal-proof"})}
        terms.update(kw)
        return self.m.propose(owner, gid or owner + ":grant", owner + ":cpu", **terms)

    def approvals(self, owner, gid, sha):
        for actor, kind in [(owner, "LICENSE"), (owner, "ACCESS"), ("operator", "OPERATOR")]:
            self.m.approve(actor, gid, kind, agreement_sha256=sha)

    def activate(self, owner="alice", gid=None):
        gid = gid or owner + ":grant"
        sha = self.proposal(owner, gid)
        self.approvals(owner, gid, sha)
        self.m.observe("operator", gid, reachable=True, observation_id=gid + ":reach")
        return gid

    def offer(self, owner="alice"):
        gid = self.activate(owner)
        self.m.publish(owner, owner + ":offer", gid, rates=copy.deepcopy(RATES))
        return owner + ":offer"

    def quote(self, buyer="sponsor", offer="alice:offer", cpu=100):
        return self.m.quote(buyer, offer, task=TASK, limits={**LIMITS, "cpu_ms": cpu})

    def finish_fixture(self, oid, provider, cpu=10, output=None):
        lease = self.m.claim(provider, oid)["lease"]
        return self.m.finish(oid, lease, output={"sum": 55} if output is None else output,
                             usage={**LIMITS, "cpu_ms": cpu},
                             evidence={"mode": "TRUSTED_LOCAL_TEST_FIXTURE_NOT_HARDWARE_PROOF"},
                             process_stopped=True)

    def test_each_approval_and_observation_is_required(self):
        sha = self.proposal()
        self.assertEqual(self.m.participation_status("alice:grant"), "PENDING_APPROVALS")
        for actor, kind in [("alice", "LICENSE"), ("alice", "ACCESS"), ("operator", "OPERATOR")]:
            with self.assertRaises(MarketError):
                self.m.observe("operator", "alice:grant", reachable=True, observation_id="early")
            self.m.approve(actor, "alice:grant", kind, agreement_sha256=sha)
        self.assertEqual(self.m.participation_status("alice:grant"), "PENDING_OBSERVATION")
        self.m.observe("operator", "alice:grant", reachable=True, observation_id="ready")
        self.assertEqual(self.m.participation_status("alice:grant"), "ACTIVE")
        self.assertEqual(self.m.snapshot()["balances"]["alice"], 0)

    def test_wrong_party_or_changed_terms_cannot_approve(self):
        sha = self.proposal()
        before = self.m.snapshot()
        for actor, kind, binding in [("bob", "ACCESS", sha), ("alice", "OPERATOR", sha),
                                     ("alice", "LICENSE", "f" * 64)]:
            with self.assertRaises(MarketError):
                self.m.approve(actor, "alice:grant", kind, agreement_sha256=binding)
            self.assertEqual(before, self.m.snapshot())

    def test_unknown_operator_and_bad_rights_hash_are_rejected(self):
        for change in ({"operator": "impostor"}, {"rights_review_sha256": "VERIFIED"},
                       {"expires_at_ms": self.now + MAX_TERM_MS + 1}):
            with self.assertRaises(MarketError): self.proposal(**change)

    def test_plain_grant_cannot_skip_admission(self):
        with self.assertRaises(MarketError):
            self.m.grant("alice", "direct", "alice:cpu", provider="alice", expires_at_ms=5000)

    def test_small_membership_does_not_create_buying_power(self):
        self.offer("alice"); self.offer("bob")
        before = self.m.snapshot()
        with self.assertRaises(MarketError):
            self.m.reserve("alice", "free", self.quote("alice", "bob:offer"), max_budget=100)
        self.assertEqual(before, self.m.snapshot())
        self.m.reserve("sponsor", "earned", self.quote(), max_budget=100)
        self.finish_fixture("earned", "alice", cpu=10)
        self.assertEqual(self.m.snapshot()["balances"]["alice"], 10)
        with self.assertRaises(MarketError):
            self.m.reserve("alice", "too-much", self.quote("alice", "bob:offer", cpu=11), max_budget=11)
        self.m.reserve("alice", "spend", self.quote("alice", "bob:offer", cpu=10), max_budget=10)
        self.finish_fixture("spend", "bob", cpu=4)
        self.assertEqual(self.m.snapshot()["balances"], {"sponsor": 990, "alice": 6, "bob": 4})
        verify_snapshot(self.m.snapshot())

    def test_failed_result_cannot_earn_credit(self):
        self.offer(); self.m.reserve("sponsor", "wrong", self.quote(), max_budget=100)
        self.assertEqual(self.finish_fixture("wrong", "alice", output={"sum": 56})["state"], "REJECTED")
        self.assertEqual(self.m.snapshot()["balances"], {"sponsor": 1000, "alice": 0, "bob": 0})

    def test_duplicate_receipt_cannot_pay_twice(self):
        self.offer(); self.m.reserve("sponsor", "once", self.quote(), max_budget=100)
        first = self.finish_fixture("once", "alice")
        s = self.m.snapshot()
        second = self.m.finish("once", s["orders"]["once"]["lease"], output=None, usage=None,
                               evidence=None, process_stopped=True)
        self.assertEqual(first, second); self.assertEqual(s, self.m.snapshot())

    def test_observation_replay_or_wrong_operator_rejected(self):
        gid = self.activate()
        before = self.m.snapshot()
        for actor, oid in [("bob", "new"), ("operator", gid + ":reach")]:
            with self.assertRaises(MarketError):
                self.m.observe(actor, gid, reachable=True, observation_id=oid)
        self.assertEqual(before, self.m.snapshot())

    def test_stale_observation_blocks_new_work_and_recovery_does_not_extend_term(self):
        self.offer(); self.now += OBSERVATION_TTL_MS
        self.assertEqual(self.m.participation_status("alice:grant"), "UNREACHABLE")
        with self.assertRaises(MarketError): self.quote()
        self.m.observe("operator", "alice:grant", reachable=True, observation_id="fresh")
        self.assertEqual(self.m.participation_status("alice:grant"), "ACTIVE")
        self.now = 61000
        self.assertEqual(self.m.participation_status("alice:grant"), "EXPIRED")
        with self.assertRaises(MarketError):
            self.m.observe("operator", "alice:grant", reachable=True, observation_id="renew")
        with self.assertRaises(MarketError):
            self.m.approve("alice", "alice:grant", "ACCESS", agreement_sha256=self.m.snapshot()["participation"]["agreements"]["alice:grant"]["sha256"])

    def test_fresh_observation_does_not_renew_old_price_offer(self):
        self.offer(); self.now += OBSERVATION_TTL_MS
        self.m.observe("operator", "alice:grant", reachable=True, observation_id="fresh-price")
        with self.assertRaises(MarketError): self.quote()
        self.m.publish("alice", "new-offer", "alice:grant", rates=RATES)
        self.assertEqual(self.quote(offer="new-offer")["offer_id"], "new-offer")

    def test_reserved_order_cannot_start_after_observation_expires(self):
        self.offer(); self.m.reserve("sponsor", "late", self.quote(), max_budget=100)
        self.now += OBSERVATION_TTL_MS
        with self.assertRaises(MarketError): self.m.claim("alice", "late")
        self.m.sweep()
        self.assertEqual(self.m.snapshot()["balances"]["sponsor"], 1000)

    def test_real_local_worker_completes_under_participation(self):
        self.offer(); self.m.reserve("sponsor", "real", self.quote(), max_budget=100)
        receipt = run(self.m, "alice", "real")
        self.assertEqual(receipt["state"], "SETTLED")
        self.assertEqual(receipt["evidence"]["mode"], "LOCAL_BUILTIN_EXECUTION")
        self.assertEqual(receipt["evidence"]["model_calls"], 0)
        verify_snapshot(self.m.snapshot())

    def test_real_local_worker_stops_after_owner_revokes(self):
        import subprocess
        self.offer()
        quote = self.m.quote("sponsor", "alice:offer", task={**TASK, "delay_ms": 4000},
                             limits={**LIMITS, "memory_mib_ms": 640000}, wall_ms=5000)
        self.m.reserve("sponsor", "stop-real", quote, max_budget=100)
        started = threading.Event(); processes = []
        original = subprocess.Popen

        def launch(*args, **kwargs):
            process = original(*args, **kwargs)
            processes.append(process); started.set()
            return process

        with patch("market.runner.subprocess.Popen", side_effect=launch):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(run, self.m, "alice", "stop-real")
                try:
                    self.assertTrue(started.wait(10), "worker never started")
                finally:
                    self.m.revoke("alice", "alice:grant")
                receipt = future.result(timeout=10)
        self.assertIsNotNone(processes[0].poll())
        self.assertEqual(receipt["state"], "CANCELLED")
        self.assertEqual(receipt["paid_atoms"], 0)
        self.assertEqual(self.m.snapshot()["balances"]["sponsor"], 1000)

    def test_outage_cancels_reservation_and_refunds(self):
        self.offer(); self.m.reserve("sponsor", "pending", self.quote(), max_budget=100)
        self.m.observe("operator", "alice:grant", reachable=False, observation_id="down")
        self.assertEqual(self.m.snapshot()["orders"]["pending"]["state"], "CANCELLED")
        self.assertEqual(self.m.snapshot()["balances"]["sponsor"], 1000)
        with self.assertRaises(MarketError): self.m.claim("alice", "pending")

    def test_running_revoke_requests_stop_and_does_not_free_capacity_early(self):
        self.offer(); self.m.reserve("sponsor", "running", self.quote(), max_budget=100)
        lease = self.m.claim("alice", "running")["lease"]
        self.m.revoke("alice", "alice:grant")
        s = self.m.snapshot()
        self.assertEqual(s["orders"]["running"]["state"], "STOP_REQUESTED")
        self.assertEqual(s["orders"]["running"]["escrow"], 100)
        with self.assertRaises(MarketError):
            self.m.finish("running", lease, output=None, usage=None, evidence=None, process_stopped=False)
        receipt = self.m.finish("running", lease, output=None, usage=None, evidence=None, process_stopped=True)
        self.assertEqual(receipt["state"], "CANCELLED")
        with self.assertRaises(MarketError):
            self.m.observe("operator", "alice:grant", reachable=True, observation_id="revive")

    def test_pending_revoke_and_no_automatic_reenrollment(self):
        self.proposal(); self.m.revoke("alice", "alice:grant")
        self.assertEqual(self.m.participation_status("alice:grant"), "REVOKED")
        with self.assertRaises(MarketError): self.proposal()
        self.assertNotIn("alice:grant", self.m.snapshot()["grants"])

    def test_duplicate_resource_alias_or_active_pledge_rejected(self):
        self.activate()
        with self.assertRaises(MarketError):
            self.m.register_resource("bob", "alias", slots=1, memory_mib=256, usl_resource_id="usl:test:alice")
        sha = self.proposal(gid="another")
        self.approvals("alice", "another", sha)
        with self.assertRaises(MarketError):
            self.m.observe("operator", "another", reachable=True, observation_id="double")

    def test_concurrent_spend_has_one_winner_and_preserves_supply(self):
        self.offer(); self.m.reserve("sponsor", "income", self.quote(), max_budget=100)
        self.finish_fixture("income", "alice", cpu=10)
        self.offer("bob")
        quote = self.quote("alice", "bob:offer", cpu=10)
        barrier = threading.Barrier(2); outcomes = []
        def spend(i):
            client = ParticipationMarket(self.path, clock=lambda: self.now)
            barrier.wait()
            try:
                client.reserve("alice", "race" + str(i), quote, max_budget=10)
                outcomes.append("OK")
            except MarketError:
                outcomes.append("REJECTED")
        threads = [threading.Thread(target=spend, args=(i,)) for i in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=10)
        self.assertTrue(all(not t.is_alive() for t in threads))
        self.assertEqual(sorted(outcomes), ["OK", "REJECTED"])
        verify_snapshot(self.m.snapshot())

    def test_persistence_and_clock_rollback(self):
        self.activate()
        reopened = ParticipationMarket(self.path, clock=lambda: self.now)
        self.assertEqual(reopened.participation_status("alice:grant"), "ACTIVE")
        self.now -= 1
        with self.assertRaises(MarketError): reopened.participation_status("alice:grant")
        with self.assertRaises(MarketError): reopened.revoke("alice", "alice:grant")


if __name__ == "__main__":
    unittest.main()
