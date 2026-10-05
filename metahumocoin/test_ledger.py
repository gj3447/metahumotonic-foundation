import concurrent.futures
import tempfile
import unittest
from pathlib import Path

from .ledger import Ledger, Rejected, run_reference


class ClaimsTest(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger()
        self.sid = self.ledger.apply("create", "create", 0, start=0, end=100)
        self.ledger.apply("cap", "capacity", 0, sid=self.sid, lot="a", slot="device", quantity=100, fresh_until=90)

    def tearDown(self):
        self.ledger.close()

    def mint(self, quantity=80):
        return self.ledger.apply("mint", "mint", 0, sid=self.sid, account="alice", quantity=quantity)

    def lock(self, quantity=10):
        return self.ledger.apply("lock", "lock", 1, sid=self.sid, account="alice", claim="job", quantity=quantity)

    def test_real_work_redeems_only_after_verification(self):
        self.mint()
        self.lock()
        self.assertEqual(self.ledger.report(self.sid, 1)["liability"], 80)
        self.assertEqual(self.ledger.apply("done", "finish", 2, claim="job", result=run_reference(10)), "ACCEPTED")
        self.assertEqual(self.ledger.report(self.sid, 2), {
            "physical_remaining": 90, "covered": 72, "liability": 70,
            "deficit": 0, "headroom": 2, "status": "COVERED"})

    def test_overmint_rolls_back(self):
        self.mint()
        before = self.ledger.snapshot()
        with self.assertRaisesRegex(Rejected, "unbacked"):
            self.ledger.apply("extra", "mint", 1, sid=self.sid, account="alice", quantity=1)
        self.assertEqual(before, self.ledger.snapshot())

    def test_duplicate_capacity_and_overlapping_series(self):
        other = self.ledger.apply("other", "create", 0, start=0, end=200)
        for sid, lot, slot in [(self.sid, "a", "other-device"), (other, "b", "device")]:
            with self.assertRaises(Rejected):
                self.ledger.apply("dup", "capacity", 0, sid=sid, lot=lot, slot=slot, quantity=100, fresh_until=90)

    def test_nonoverlapping_capacity_periods_are_separate(self):
        other = self.ledger.apply("next", "create", 0, start=100, end=200)
        self.ledger.apply("cap-next", "capacity", 0, sid=other, lot="b", slot="device", quantity=100, fresh_until=200)
        self.assertEqual(self.ledger.report(other, 0)["covered"], 0)
        self.assertEqual(self.ledger.report(other, 100)["covered"], 80)

    def test_fee_is_transfer_not_new_supply(self):
        self.mint()
        self.ledger.apply("fee", "transfer", 1, sid=self.sid, sender="alice", recipient="foundation", quantity=2)
        self.assertEqual(self.ledger.report(self.sid, 1)["liability"], 80)
        self.assertEqual(self.ledger.snapshot()["series"][self.sid]["balances"], {"alice": 78, "foundation": 2})

    def test_transfer_failure_is_atomic(self):
        self.mint()
        before = self.ledger.snapshot()
        with self.assertRaises(Rejected):
            self.ledger.apply("fee", "transfer", 1, sid=self.sid, sender="alice", recipient="bad name", quantity=2)
        self.assertEqual(before, self.ledger.snapshot())

    def test_locked_claim_cannot_be_spent_twice(self):
        self.mint()
        self.lock(80)
        with self.assertRaises(Rejected):
            self.ledger.apply("double", "transfer", 1, sid=self.sid, sender="alice", recipient="bob", quantity=1)
        with self.assertRaises(Rejected):
            self.ledger.apply("double-lock", "lock", 1, sid=self.sid, account="alice", claim="job-2", quantity=1)

    def test_failed_work_spends_capacity_but_preserves_debt(self):
        self.mint()
        self.lock()
        self.assertEqual(self.ledger.apply("bad", "finish", 2, claim="job", result=0), "FAILED")
        report = self.ledger.report(self.sid, 2)
        self.assertEqual((report["physical_remaining"], report["liability"], report["deficit"]), (90, 80, 8))
        with self.assertRaises(Rejected):
            self.ledger.apply("run", "lock", 2, sid=self.sid, account="alice", claim="new", quantity=1)

    def test_revocation_freezes_mint_and_new_redemption(self):
        self.mint()
        self.ledger.apply("revoke", "revoke", 1, lot="a")
        self.assertEqual(self.ledger.report(self.sid, 1)["deficit"], 80)
        with self.assertRaises(Rejected):
            self.ledger.apply("extra", "mint", 1, sid=self.sid, account="alice", quantity=1)
        with self.assertRaises(Rejected):
            self.lock()

    def test_expiry_preserves_locked_liability_and_releases_claim(self):
        self.mint()
        self.lock()
        self.assertEqual(self.ledger.report(self.sid, 100)["liability"], 80)
        with self.assertRaises(Rejected):
            self.ledger.apply("late", "finish", 100, claim="job", result=run_reference(10))
        self.ledger.apply("release", "release", 100, claim="job")
        self.assertEqual(self.ledger.snapshot()["series"][self.sid]["balances"]["alice"], 80)
        self.assertEqual(self.ledger.report(self.sid, 100)["status"], "EXPIRED")

    def test_stale_capacity_is_not_backing(self):
        self.mint()
        self.assertEqual(self.ledger.report(self.sid, 89)["covered"], 80)
        self.assertEqual(self.ledger.report(self.sid, 90)["deficit"], 80)

    def test_uncertain_outcome_does_not_restore_used_capacity(self):
        self.mint()
        self.lock()
        self.ledger.apply("release", "release", 2, claim="job")
        self.assertEqual(self.ledger.report(self.sid, 2)["physical_remaining"], 90)
        for action in ["release", "finish"]:
            with self.assertRaises(Rejected):
                self.ledger.apply("again", action, 2, claim="job", **({"result": 5005000} if action == "finish" else {}))

    def test_idempotent_retry_and_conflicting_replay(self):
        self.assertEqual(self.mint(), self.mint())
        self.assertEqual(self.ledger.report(self.sid, 0)["liability"], 80)
        with self.assertRaisesRegex(Rejected, "replay"):
            self.mint(79)

    def test_integer_units_and_bounded_execution(self):
        for amount in [True, 1.5, "1", -1, 0, 1_000_001]:
            with self.assertRaises(Rejected):
                self.mint(amount)
        with self.assertRaises(Rejected):
            run_reference(101)

    def test_series_balance_cannot_pay_other_window(self):
        self.mint()
        other = self.ledger.apply("other", "create", 0, start=0, end=200)
        with self.assertRaises(Rejected):
            self.ledger.apply("wrong", "transfer", 1, sid=other, sender="alice", recipient="bob", quantity=1)

    def test_clock_cannot_restore_expired_capacity(self):
        self.mint()
        self.ledger.apply("revoke", "revoke", 100, lot="a")
        with self.assertRaisesRegex(Rejected, "clock rollback"):
            self.ledger.apply("extra", "mint", 0, sid=self.sid, account="alice", quantity=1)

    def test_replenishment_requires_new_unpledged_capacity(self):
        self.mint()
        self.ledger.apply("revoke", "revoke", 1, lot="a")
        self.ledger.apply("replacement", "capacity", 1, sid=self.sid, lot="b", slot="device-2", quantity=100, fresh_until=100)
        self.assertEqual(self.ledger.report(self.sid, 1)["deficit"], 0)


class PersistenceTest(unittest.TestCase):
    def test_two_connections_cannot_overissue_and_replay_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.sqlite"
            ledger = Ledger(path)
            sid = ledger.apply("create", "create", 0, start=0, end=100)
            ledger.apply("cap", "capacity", 0, sid=sid, lot="a", slot="device", quantity=100, fresh_until=100)
            ledger.close()

            def issue(account):
                instance = Ledger(path)
                try:
                    instance.apply(account, "mint", 1, sid=sid, account=account, quantity=60)
                    return account
                except Rejected:
                    return None
                finally:
                    instance.close()

            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                winners = [x for x in pool.map(issue, ["alice", "bob"]) if x]
            self.assertEqual(len(winners), 1)
            ledger = Ledger(path)
            try:
                self.assertEqual(ledger.report(sid, 1)["liability"], 60)
                self.assertEqual(ledger.apply(winners[0], "mint", 1, sid=sid, account=winners[0], quantity=60), 60)
                self.assertEqual(ledger.report(sid, 1)["liability"], 60)
            finally:
                ledger.close()


if __name__ == "__main__":
    unittest.main()
