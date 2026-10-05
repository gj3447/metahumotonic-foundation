import copy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from .contracts import MarketError, digest, invoice, normalize_hswm, quote_hswm_observation, read_json
from .core import Market
from .runner import hswm_fixture, live_hswm_status, run


RATES = {"input_tokens": [0, 1], "output_tokens": [0, 1], "cpu_ms": [1, 1], "memory_mib_ms": [0, 1]}
TASK = {"kind": "sum", "n": 50000, "delay_ms": 0}
LIMITS = {"input_tokens": 0, "output_tokens": 0, "cpu_ms": 1000, "memory_mib_ms": 128000}


class MarketTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "market.sqlite3"
        self.market = Market(self.path)
        self.market.bootstrap({"buyer": 10000, "provider": 0, "outsider": 0})
        self.market.register_resource("provider", "cpu", slots=1, memory_mib=256, usl_resource_id="usl:test:cpu")
        self.market.grant("provider", "grant", "cpu", provider="provider", expires_at_ms=self.market.clock() + 60000)
        self.market.publish("provider", "offer", "grant", rates=copy.deepcopy(RATES))

    def tearDown(self):
        self.directory.cleanup()

    def reserve(self, order="work", task=None, wall_ms=1000):
        limits = {**LIMITS, "memory_mib_ms": 128 * wall_ms}
        quote = self.market.quote("buyer", "offer", task=task or TASK, limits=limits, wall_ms=wall_ms)
        self.market.reserve("buyer", order, quote, max_budget=1000)
        return quote

    def test_real_work_and_persistent_atomic_settlement(self):
        self.reserve()
        receipt = run(self.market, "provider", "work")
        self.assertEqual(receipt["state"], "SETTLED")
        self.assertGreater(receipt["usage"]["cpu_ms"], 0)
        self.assertEqual(receipt["paid_atoms"], invoice(RATES, receipt["usage"])["atoms"])
        self.assertEqual(receipt["paid_atoms"] + receipt["refund_atoms"], 1000)
        reopened = Market(self.path)
        self.assertEqual(reopened.snapshot()["receipts"]["work"], receipt)
        before = reopened.snapshot()
        duplicate = reopened.finish("work", before["orders"]["work"]["lease"], output=None,
                                    usage=None, evidence=None, process_stopped=True)
        self.assertEqual(duplicate, receipt)
        self.assertEqual(reopened.snapshot()["balances"], before["balances"])
        self.assertEqual(reopened.snapshot()["events"], before["events"])

    def test_cancel_before_start_refunds_and_releases(self):
        self.reserve()
        self.market.cancel("buyer", "work")
        self.assertEqual(self.market.snapshot()["balances"]["buyer"], 10000)
        self.assertEqual(self.market.available()["cpu"]["free_slots"], 1)
        with self.assertRaises(MarketError): run(self.market, "provider", "work")

    def test_revoke_running_worker_stops_then_refunds(self):
        self.reserve(task={**TASK, "delay_ms": 2000}, wall_ms=4000)
        result, errors = [], []
        def execute():
            try: result.append(run(Market(self.path), "provider", "work"))
            except BaseException as e: errors.append(e)
        thread = threading.Thread(target=execute)
        thread.start()
        deadline = time.monotonic() + 2
        while self.market.snapshot()["orders"]["work"]["state"] != "RUNNING" and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(self.market.snapshot()["orders"]["work"]["state"], "RUNNING")
        time.sleep(0.05)
        self.market.revoke("provider", "grant")
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(result[0]["state"], "CANCELLED")
        self.assertEqual(self.market.snapshot()["balances"]["buyer"], 10000)
        self.assertEqual(self.market.available()["cpu"]["free_slots"], 0)

    def test_runtime_deadline_refunds(self):
        self.reserve(task={**TASK, "delay_ms": 1000}, wall_ms=100)
        receipt = run(self.market, "provider", "work")
        self.assertEqual(receipt["state"], "EXPIRED")
        self.assertEqual(receipt["paid_atoms"], 0)

    def test_cpu_timer_stops_compute_and_refunds(self):
        q = self.market.quote("buyer", "offer", task={**TASK, "n": 2_000_000},
                              limits={**LIMITS, "cpu_ms": 1})
        self.market.reserve("buyer", "cpu-limit", q, max_budget=1)
        receipt = run(self.market, "provider", "cpu-limit")
        self.assertEqual(receipt["state"], "REFUNDED")
        self.assertEqual(receipt["paid_atoms"], 0)
        self.assertEqual(self.market.snapshot()["balances"]["buyer"], 10000)
        self.assertEqual(self.market.available()["cpu"]["free_slots"], 1)

    def test_concurrent_capacity_reservation_has_one_winner(self):
        q = self.market.quote("buyer", "offer", task=TASK, limits=LIMITS)
        barrier = threading.Barrier(2)
        outcomes = []
        def reserve(i):
            m = Market(self.path)
            barrier.wait()
            try:
                m.reserve("buyer", "order" + str(i), q, max_budget=1000)
                outcomes.append("OK")
            except MarketError:
                outcomes.append("REJECTED")
        threads = [threading.Thread(target=reserve, args=(i,)) for i in range(2)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=3)
        self.assertEqual(sorted(outcomes), ["OK", "REJECTED"])
        self.assertEqual(self.market.snapshot()["balances"]["buyer"], 9000)

    def test_failed_budget_reservation_does_not_mutate(self):
        q = self.market.quote("buyer", "offer", task=TASK, limits=LIMITS)
        before = self.market.snapshot()
        with self.assertRaises(MarketError): self.market.reserve("buyer", "bad", q, max_budget=999)
        self.assertEqual(self.market.snapshot(), before)

    def test_concurrent_spend_on_distinct_resources_cannot_exceed_balance(self):
        rates = {**RATES, "cpu_ms": [9, 1]}
        self.market.publish("provider", "costly1", "grant", rates=rates)
        self.market.register_resource("provider", "cpu2", slots=1, memory_mib=256, usl_resource_id="usl:test:cpu2")
        self.market.grant("provider", "grant2", "cpu2", provider="provider", expires_at_ms=self.market.clock()+60000)
        self.market.publish("provider", "costly2", "grant2", rates=rates)
        quotes = [self.market.quote("buyer", offer, task=TASK, limits=LIMITS) for offer in ("costly1", "costly2")]
        barrier = threading.Barrier(2)
        outcomes = []
        def reserve(index):
            market = Market(self.path)
            barrier.wait()
            try:
                market.reserve("buyer", "spend"+str(index), quotes[index], max_budget=9000)
                outcomes.append("OK")
            except MarketError:
                outcomes.append("REJECTED")
        threads = [threading.Thread(target=reserve, args=(i,)) for i in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=3)
        self.assertEqual(sorted(outcomes), ["OK", "REJECTED"])
        self.assertEqual(self.market.snapshot()["balances"]["buyer"], 1000)
        self.assertEqual(sum(o["escrow"] for o in self.market.snapshot()["orders"].values()), 9000)

    def test_altered_quote_is_rejected(self):
        q = self.market.quote("buyer", "offer", task=TASK, limits=LIMITS)
        q["maximum_charge"]["atoms"] = 1
        with self.assertRaises(MarketError): self.market.reserve("buyer", "bad", q, max_budget=1000)

    def test_same_order_cannot_be_started_twice(self):
        self.reserve()
        self.market.claim("provider", "work")
        with self.assertRaises(MarketError): self.market.claim("provider", "work")

    def test_wrong_execution_lease_does_not_release_funds_or_capacity(self):
        self.reserve()
        self.market.claim("provider", "work")
        before = self.market.snapshot()
        with self.assertRaises(MarketError):
            self.market.finish("work", "wrong-lease", output=None, usage=None, evidence=None, process_stopped=True)
        self.assertEqual(self.market.snapshot(), before)

    def test_false_result_never_pays(self):
        self.reserve()
        order = self.market.claim("provider", "work")
        receipt = self.market.finish("work", order["lease"], output={"sum": -1},
            usage={**LIMITS, "cpu_ms": 1, "memory_mib_ms": 100}, evidence={"mode": "TEST"}, process_stopped=True)
        self.assertEqual(receipt["state"], "REJECTED")
        self.assertEqual(receipt["paid_atoms"], 0)

    def test_excess_usage_never_pays(self):
        self.reserve()
        order = self.market.claim("provider", "work")
        receipt = self.market.finish("work", order["lease"], output={"sum": 1},
            usage={**LIMITS, "cpu_ms": 1001}, evidence={}, process_stopped=True)
        self.assertEqual(receipt["state"], "REJECTED")

    def test_stop_ack_required_before_release(self):
        self.reserve()
        order = self.market.claim("provider", "work")
        self.market.cancel("buyer", "work")
        with self.assertRaises(MarketError):
            self.market.finish("work", order["lease"], output=None, usage=None, evidence=None, process_stopped=False)
        self.assertEqual(self.market.available()["cpu"]["free_slots"], 0)

    def test_expired_unstarted_order_refunds(self):
        self.reserve()
        self.market.clock = lambda: self.market.snapshot()["orders"]["work"]["terms"]["expires_at_ms"] + 1
        self.market.sweep()
        self.assertEqual(self.market.snapshot()["orders"]["work"]["state"], "EXPIRED")
        self.assertEqual(self.market.snapshot()["balances"]["buyer"], 10000)

    def test_lost_supervisor_refunds_but_quarantines_capacity(self):
        self.reserve()
        order = self.market.claim("provider", "work")
        self.market.clock = lambda: order["deadline_ms"] + 2000
        self.market.sweep()
        self.assertEqual(self.market.snapshot()["balances"]["buyer"], 10000)
        self.assertTrue(self.market.available()["cpu"]["quarantined"])
        with self.assertRaises(MarketError): self.market.quote("buyer", "offer", task=TASK, limits=LIMITS)
        self.market.reconcile_stopped_resource("provider", "cpu", evidence_reference="test:manual-stop-check")
        self.assertEqual(self.market.available()["cpu"]["free_slots"], 1)

    def test_offer_withdrawal_keeps_already_accepted_terms(self):
        self.reserve()
        self.market.withdraw("provider", "offer")
        with self.assertRaises(MarketError): self.market.quote("buyer", "offer", task=TASK, limits=LIMITS)
        receipt = run(self.market, "provider", "work")
        self.assertEqual(receipt["state"], "SETTLED")

    def test_multiple_grants_do_not_multiply_capacity(self):
        self.market.grant("provider", "grant2", "cpu", provider="provider", expires_at_ms=self.market.clock()+60000)
        self.assertEqual(self.market.available()["cpu"]["free_slots"], 1)
        self.reserve()
        self.assertEqual(self.market.available()["cpu"]["free_slots"], 0)

    def test_permissions_and_live_hswm_gate(self):
        with self.assertRaises(MarketError): self.market.revoke("outsider", "grant")
        self.reserve()
        with self.assertRaises(MarketError): self.market.cancel("outsider", "work")
        with self.assertRaises(MarketError): self.market.claim("outsider", "work")
        with self.assertRaises(MarketError): self.market.publish("provider", "live", "grant", rates=RATES, backend="hswm")
        self.assertEqual(live_hswm_status()["status"], "NOT_READY")

    def test_unknown_workloads_and_numeric_ambiguity_rejected(self):
        for task in [{**TASK, "kind": "shell"}, {**TASK, "n": True}, {**TASK, "n": -1}]:
            with self.assertRaises(MarketError): self.market.quote("buyer", "offer", task=task, limits=LIMITS)
        for value in [True, -1, 1.5, float("inf")]:
            with self.assertRaises(MarketError): invoice(RATES, {**LIMITS, "cpu_ms": value})

    def test_fractional_prices_round_once(self):
        rates = {u: [1, 3] for u in LIMITS}
        self.assertEqual(invoice(rates, {u: 1 for u in LIMITS})["atoms"], 2)
        with self.assertRaises(MarketError): invoice({**rates, "cpu_ms": [1, 0]}, LIMITS)

    def test_hswm_native_usage_adapter(self):
        offer = {"cell_id": "cell", "model": "model", "configuration_sha256": "a"*64}
        native = hswm_fixture(offer, {"sum": 10})
        row = normalize_hswm(native, **offer)
        self.assertEqual((row["input_tokens"], row["output_tokens"]), (100, 20))
        self.assertEqual(row["meter_status"], "PROVIDER_REPORTED")
        mutations = [
            lambda x: x["metadata"]["execution_observation_v1"]["provider_usage"].update(status="UNAVAILABLE"),
            lambda x: x["metadata"]["execution_observation_v1"]["provider_usage"].update(total_tokens=121),
            lambda x: x["metadata"]["execution_observation_v1"]["provider_usage"].update(prompt_tokens=True),
            lambda x: x["metadata"]["execution_observation_v1"].update(configured_model="another"),
            lambda x: x.update(output="forged"),
        ]
        for mutate in mutations:
            bad = copy.deepcopy(native); mutate(bad)
            with self.assertRaises(MarketError): normalize_hswm(bad, **offer)

    def test_hswm_quote_preserves_unknown_hardware_usage(self):
        offer = {"cell_id": "cell", "model": "model", "configuration_sha256": "a"*64,
                 "asset": "sandbox:SIM-MHC", "rates": {**RATES, "input_tokens": [2, 1],
                 "output_tokens": [4, 1], "cpu_ms": [0, 1]}}
        native = hswm_fixture(offer, {"sum": 10})
        q = quote_hswm_observation(native, offer)
        self.assertEqual(q["invoice"]["atoms"], 280)
        self.assertIsNone(q["metered_usage"]["cpu_ms"])
        self.assertFalse(q["funds_moved"])
        offer["rates"]["cpu_ms"] = [1, 1]
        with self.assertRaises(MarketError): quote_hswm_observation(native, offer)

    def test_ambiguous_json_and_missing_hswm_identity_are_rejected(self):
        for document in ['{"asset":"first","asset":"second"}', '{"value":NaN}', '{"value":Infinity}']:
            with self.assertRaises(MarketError): read_json(document)
        with self.assertRaises(MarketError): quote_hswm_observation({}, [])
        native = hswm_fixture({"model": None, "cell_id": None, "configuration_sha256": None}, {"sum": 10})
        with self.assertRaises(MarketError):
            normalize_hswm(native, model=None, cell_id=None, configuration_sha256=None)

    def test_demo_competition_and_portable_snapshot(self):
        from .demo import build_demo
        from .projection import project, verify_snapshot
        market, report = build_demo(Path(self.directory.name) / "demo.sqlite3")
        self.assertEqual(report["chosen_offer"], "provider-b:offer")
        self.assertEqual([q["maximum_charge"]["atoms"] for q in report["quotes"]], [508, 648])
        self.assertEqual(report["receipt"]["state"], "SETTLED")
        self.assertEqual(report["model_calls"], 0)
        snapshot = market.snapshot()
        verify_snapshot(snapshot)
        self.assertEqual(project(snapshot), project(copy.deepcopy(snapshot)))
        for change in [lambda s: s["balances"].update(buyer=0),
                       lambda s: s["receipts"]["demo-completed"].update(paid_atoms=0),
                       lambda s: s["events"][0].update(action="forged")]:
            altered = copy.deepcopy(snapshot); change(altered)
            with self.assertRaises(MarketError): verify_snapshot(altered)


if __name__ == "__main__":
    unittest.main()
