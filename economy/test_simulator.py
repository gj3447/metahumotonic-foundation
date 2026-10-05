"""Behavioural tests for the simulated MetaHumoCoin bilateral economy.

These cases deliberately use only the public simulator API.  The simulation is
an accounting model; no issuance, external wallet, or real transfer is implied.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Context, Decimal, localcontext
import unittest

from economy import EconomySimulator, SimulationError


REQUESTER = "requester"
PROVIDER = "provider"


class EconomySimulatorTests(unittest.TestCase):
    def make_simulator(self, requester="20", provider="5"):
        return EconomySimulator({REQUESTER: requester, PROVIDER: provider})

    def proposed(self, simulator, agreement_id="agreement-1", *, max_units="5", price="2"):
        return simulator.propose(
            agreement_id, REQUESTER, PROVIDER, "compute-hour", price, max_units
        )

    def funded(self, simulator, agreement_id="agreement-1", *, max_units="5", price="2"):
        terms_hash = self.proposed(
            simulator, agreement_id, max_units=max_units, price=price
        )
        simulator.assent(agreement_id, REQUESTER, terms_hash)
        simulator.assent(agreement_id, PROVIDER, terms_hash)
        simulator.fund(agreement_id, REQUESTER)
        return terms_hash

    def accepted_work(self, simulator, agreement_id="agreement-1", *, units="3"):
        self.funded(simulator, agreement_id)
        simulator.start(agreement_id, PROVIDER)
        simulator.submit(agreement_id, PROVIDER, units, "meter:1", "result:1")
        simulator.accept(agreement_id, REQUESTER)

    def test_success_pays_provider_and_refunds_unused_escrow(self):
        simulator = self.make_simulator()
        self.accepted_work(simulator)

        receipt = simulator.settle("agreement-1", REQUESTER, "settle-001")
        snapshot = simulator.snapshot()

        self.assertEqual(receipt["action"], "SETTLE")
        self.assertEqual(receipt["provider_amount"], "6")
        self.assertEqual(receipt["requester_refund"], "4")
        self.assertEqual(receipt["escrow_after"], "0")
        self.assertEqual(snapshot["balances"], {REQUESTER: "14", PROVIDER: "11"})
        self.assertEqual(snapshot["escrow"], {})
        self.assertEqual(snapshot["escrow_total"], "0")
        self.assertEqual(snapshot["total_units"], "25")

    def test_cancel_before_execution_refunds_full_escrow(self):
        simulator = self.make_simulator()
        self.funded(simulator)
        simulator.cancel("agreement-1", REQUESTER)

        snapshot = simulator.snapshot()
        self.assertEqual(snapshot["balances"], {REQUESTER: "20", PROVIDER: "5"})
        self.assertEqual(snapshot["escrow"], {})
        self.assertEqual(snapshot["escrow_total"], "0")
        self.assertEqual(snapshot["agreements"]["agreement-1"]["status"], "CANCELLED")

    def test_dispute_cannot_be_forced_and_requires_matching_mutual_resolution(self):
        simulator = self.make_simulator()
        self.funded(simulator)
        simulator.start("agreement-1", PROVIDER)
        simulator.submit("agreement-1", PROVIDER, "3", "meter:1", "result:1")
        simulator.dispute("agreement-1", REQUESTER, "usage contested")

        with self.assertRaises(SimulationError):
            simulator.resolve("agreement-1", REQUESTER, "resolve-001")

        resolution_hash = simulator.propose_resolution(
            "agreement-1", REQUESTER, "4", "compromise"
        )
        with self.assertRaises(SimulationError):
            simulator.assent_resolution("agreement-1", PROVIDER, "0" * 64)
        with self.assertRaises(SimulationError):
            simulator.resolve("agreement-1", REQUESTER, "resolve-001")

        simulator.assent_resolution("agreement-1", REQUESTER, resolution_hash)
        simulator.assent_resolution("agreement-1", PROVIDER, resolution_hash)
        receipt = simulator.resolve("agreement-1", REQUESTER, "resolve-001")
        self.assertEqual(receipt["action"], "RESOLVE")
        self.assertEqual(receipt["provider_amount"], "4")
        self.assertEqual(receipt["requester_refund"], "6")
        self.assertEqual(simulator.snapshot()["balances"], {REQUESTER: "16", PROVIDER: "9"})

    def test_missing_or_mismatched_terms_assent_cannot_start_or_fund(self):
        simulator = self.make_simulator()
        terms_hash = self.proposed(simulator)

        with self.assertRaises(SimulationError):
            simulator.assent("agreement-1", REQUESTER, "f" * 64)
        simulator.assent("agreement-1", REQUESTER, terms_hash)
        with self.assertRaises(SimulationError):
            simulator.fund("agreement-1", REQUESTER)
        with self.assertRaises(SimulationError):
            simulator.start("agreement-1", PROVIDER)

    def test_only_contract_parties_may_perform_their_roles(self):
        simulator = self.make_simulator()
        terms_hash = self.proposed(simulator)
        for method, args in (
            (simulator.assent, ("agreement-1", "intruder", terms_hash)),
            (simulator.fund, ("agreement-1", PROVIDER)),
            (simulator.cancel, ("agreement-1", "intruder")),
        ):
            with self.subTest(method=method.__name__):
                with self.assertRaises(SimulationError):
                    method(*args)

    def test_amounts_reject_float_nonfinite_negative_and_excess_precision(self):
        invalid = (1.5, "NaN", "Infinity", "-1", "0.0000001")
        for amount in invalid:
            with self.subTest(amount=repr(amount)):
                simulator = self.make_simulator()
                with self.assertRaises(SimulationError):
                    self.proposed(simulator, price=amount)

        for balance in invalid:
            with self.subTest(initial_balance=repr(balance)):
                with self.assertRaises(SimulationError):
                    EconomySimulator({REQUESTER: balance})

    def test_escrow_cannot_overreserve_requester_balance(self):
        simulator = self.make_simulator(requester="10")
        self.funded(simulator, "agreement-1", max_units="4", price="2")
        terms_hash = self.proposed(simulator, "agreement-2", max_units="4", price="2")
        simulator.assent("agreement-2", REQUESTER, terms_hash)
        simulator.assent("agreement-2", PROVIDER, terms_hash)

        with self.assertRaises(SimulationError):
            simulator.fund("agreement-2", REQUESTER)
        snapshot = simulator.snapshot()
        self.assertEqual(snapshot["balances"][REQUESTER], "2")
        self.assertEqual(snapshot["escrow"], {"agreement-1": "8"})
        self.assertEqual(snapshot["escrow_total"], "8")

    def test_usage_may_not_exceed_agreed_cap(self):
        simulator = self.make_simulator()
        self.funded(simulator)
        simulator.start("agreement-1", PROVIDER)

        with self.assertRaises(SimulationError):
            simulator.submit("agreement-1", PROVIDER, "5.000001", "meter:1", "result:1")

    def test_settlement_requires_requester_acceptance(self):
        simulator = self.make_simulator()
        self.funded(simulator)
        simulator.start("agreement-1", PROVIDER)
        simulator.submit("agreement-1", PROVIDER, "3", "meter:1", "result:1")

        with self.assertRaises(SimulationError):
            simulator.settle("agreement-1", REQUESTER, "settle-001")

    def test_exact_operation_retry_is_idempotent_and_reuse_is_forbidden(self):
        simulator = self.make_simulator(requester="40")
        self.accepted_work(simulator, "agreement-1")
        first = simulator.settle("agreement-1", REQUESTER, "operation-1")
        event_count = len(simulator.export_events())
        retry = simulator.settle("agreement-1", REQUESTER, "operation-1")
        self.assertEqual(retry, first)
        self.assertEqual(len(simulator.export_events()), event_count)

        self.accepted_work(simulator, "agreement-2")
        before_collision = deepcopy(simulator.snapshot())
        before_collision_events = deepcopy(simulator.export_events())
        with self.assertRaises(SimulationError):
            simulator.settle("agreement-2", REQUESTER, "operation-1")
        self.assertEqual(simulator.snapshot(), before_collision)
        self.assertEqual(simulator.export_events(), before_collision_events)

        # The identifier also cannot cross settlement and dispute-resolution actions.
        self.funded(simulator, "agreement-3")
        simulator.start("agreement-3", PROVIDER)
        simulator.submit("agreement-3", PROVIDER, "3", "meter:3", "result:3")
        simulator.dispute("agreement-3", REQUESTER, "contested")
        resolution_hash = simulator.propose_resolution("agreement-3", REQUESTER, "4", "compromise")
        simulator.assent_resolution("agreement-3", REQUESTER, resolution_hash)
        simulator.assent_resolution("agreement-3", PROVIDER, resolution_hash)
        with self.assertRaises(SimulationError):
            simulator.resolve("agreement-3", REQUESTER, "operation-1")

    def test_retry_still_checks_actor_and_returned_views_are_detached(self):
        simulator = EconomySimulator({REQUESTER: "20", PROVIDER: "5", "intruder": "1"})
        self.accepted_work(simulator)
        receipt = simulator.settle("agreement-1", REQUESTER, "settle-001")
        stable_snapshot = simulator.snapshot()
        stable_events = simulator.export_events()

        receipt["provider_amount"] = "tampered"
        snapshot_copy = simulator.snapshot()
        snapshot_copy["balances"][REQUESTER] = "tampered"
        events_copy = simulator.export_events()
        events_copy[0]["data"]["terms"]["unit"] = "tampered"

        with self.assertRaises(SimulationError):
            simulator.settle("agreement-1", "intruder", "settle-001")
        self.assertEqual(simulator.snapshot(), stable_snapshot)
        self.assertEqual(simulator.export_events(), stable_events)
        self.assertEqual(simulator.settle("agreement-1", PROVIDER, "settle-001")["provider_amount"], "6")

    def test_amending_a_resolution_discards_prior_assent(self):
        simulator = self.make_simulator()
        self.funded(simulator)
        simulator.start("agreement-1", PROVIDER)
        simulator.submit("agreement-1", PROVIDER, "3", "meter:1", "result:1")
        simulator.dispute("agreement-1", REQUESTER, "contested")
        first_hash = simulator.propose_resolution("agreement-1", REQUESTER, "4", "first offer")
        simulator.assent_resolution("agreement-1", REQUESTER, first_hash)
        second_hash = simulator.propose_resolution("agreement-1", PROVIDER, "5", "amended offer")

        resolution = simulator.snapshot()["agreements"]["agreement-1"]["resolution"]
        self.assertEqual(resolution["resolution_sha256"], second_hash)
        self.assertEqual(resolution["assents"], [])
        with self.assertRaises(SimulationError):
            simulator.assent_resolution("agreement-1", REQUESTER, first_hash)
        with self.assertRaises(SimulationError):
            simulator.resolve("agreement-1", PROVIDER, "resolve-001")

    def test_huge_amounts_are_bounded_and_failed_reservation_is_atomic(self):
        sixty_digits = "9" * 60
        with self.assertRaises(SimulationError):
            EconomySimulator({REQUESTER: "9" * 61})
        # A finite Decimal with a giant positive exponent must not leak a raw
        # decimal.Overflow or allocate an unbounded fixed-point string.
        with self.assertRaises(SimulationError):
            EconomySimulator({REQUESTER: "1e999999999"})

        simulator = EconomySimulator({REQUESTER: sixty_digits, PROVIDER: "0"})
        terms_hash = self.proposed(simulator, max_units="2", price=sixty_digits)
        simulator.assent("agreement-1", REQUESTER, terms_hash)
        simulator.assent("agreement-1", PROVIDER, terms_hash)
        before = deepcopy(simulator.snapshot())
        before_events = deepcopy(simulator.export_events())
        with self.assertRaises(SimulationError):
            simulator.fund("agreement-1", REQUESTER)
        self.assertEqual(simulator.snapshot(), before)
        self.assertEqual(simulator.export_events(), before_events)

    def test_failed_calls_are_atomic_for_snapshot_and_events(self):
        simulator = self.make_simulator()
        self.funded(simulator)
        before_snapshot = deepcopy(simulator.snapshot())
        before_events = deepcopy(simulator.export_events())

        with self.assertRaises(SimulationError):
            simulator.start("agreement-1", REQUESTER)
        self.assertEqual(simulator.snapshot(), before_snapshot)
        self.assertEqual(simulator.export_events(), before_events)

    def test_event_chain_is_deterministic_and_linked(self):
        left, right = self.make_simulator(), self.make_simulator()
        for simulator in (left, right):
            self.accepted_work(simulator)
            simulator.settle("agreement-1", REQUESTER, "settle-001")

        events = left.export_events()
        self.assertEqual(events, right.export_events())
        self.assertEqual([event["sequence"] for event in events], list(range(1, len(events) + 1)))
        for previous, current in zip(events, events[1:]):
            self.assertEqual(current["previous_hash"], previous["event_hash"])
        self.assertEqual(len(events[0]["previous_hash"]), 64)
        self.assertEqual(len(events[-1]["event_hash"]), 64)

    def test_decimal_conservation_across_settlement_and_cancellation(self):
        simulator = self.make_simulator(requester="30", provider="7")
        self.accepted_work(simulator, "agreement-1", units="1.5")
        simulator.settle("agreement-1", REQUESTER, "settle-001")
        self.funded(simulator, "agreement-2", max_units="2", price="3")
        simulator.cancel("agreement-2", REQUESTER)

        snapshot = simulator.snapshot()
        balances = sum(Decimal(value) for value in snapshot["balances"].values())
        self.assertEqual(balances + Decimal(snapshot["escrow_total"]), Decimal(snapshot["total_units"]))
        self.assertEqual(snapshot["total_units"], "37")

    def test_accounting_is_exact_under_a_hostile_low_precision_decimal_context(self):
        """The simulator's stated numeric policy must not inherit caller context."""
        with localcontext(Context(prec=3)):
            simulator = EconomySimulator({REQUESTER: "123456.789012", PROVIDER: "0"})
            self.funded(simulator, max_units="3.33333", price="0.1")
            funded = simulator.snapshot()
            self.assertEqual(funded["balances"][REQUESTER], "123456.455679")
            self.assertEqual(funded["escrow_total"], "0.333333")

            before_error = deepcopy(funded)
            before_events = deepcopy(simulator.export_events())
            simulator.start("agreement-1", PROVIDER)
            with self.assertRaises(SimulationError):
                simulator.submit("agreement-1", PROVIDER, "3.333331", "meter:bad", "result:bad")
            self.assertEqual(simulator.snapshot()["balances"], before_error["balances"])
            self.assertEqual(simulator.snapshot()["escrow_total"], before_error["escrow_total"])
            self.assertEqual(simulator.export_events()[:-1], before_events)

            simulator.submit("agreement-1", PROVIDER, "3.33333", "meter:ok", "result:ok")
            simulator.accept("agreement-1", REQUESTER)
            simulator.settle("agreement-1", PROVIDER, "precision-settle")

        snapshot = simulator.snapshot()
        self.assertEqual(snapshot["balances"], {REQUESTER: "123456.455679", PROVIDER: "0.333333"})
        self.assertEqual(snapshot["escrow_total"], "0")
        self.assertEqual(snapshot["total_units"], "123456.789012")


if __name__ == "__main__":
    unittest.main()
