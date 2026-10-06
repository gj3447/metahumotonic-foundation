"""Economic counterexamples and agent/escrow boundaries, not growth forecasts."""
from copy import deepcopy
from dataclasses import replace
import unittest

from .agent_native import Config, run, verify
from .artifacts import digest
from .simulator import SimulationError


class AgentNativeTests(unittest.TestCase):
    def test_paid_work_continues_after_bootstrap_with_conserved_money(self):
        result = run()
        self.assertGreater(result["summary"]["post_bootstrap_completed"], 0)
        self.assertGreater(result["summary"]["final_installed_capacity"], 4)
        self.assertEqual(result["summary"]["repeat_solvers"], 3)
        self.assertTrue(result["summary"]["money_conserved"])
        self.assertEqual(result["summary"]["escrow"], "0")
        self.assertEqual(result["summary"]["investment_paid"],
                         (result["summary"]["final_installed_capacity"] - 4) * Config().investment_cost)
        self.assertFalse(result["summary"]["safety_evaluated"])

    def test_subsidies_do_not_create_permanent_demand(self):
        result = run(replace(Config(), external_jobs=0))
        self.assertGreater(result["summary"]["subsidy_paid"], 0)
        self.assertEqual(result["summary"]["external_paid"], 0)
        self.assertEqual(result["summary"]["post_bootstrap_completed"], 0)
        self.assertEqual(result["summary"]["final_offered_capacity"], 0)

    def test_energy_shock_allows_providers_to_withdraw(self):
        result = run(replace(Config(), cost_shock_round=4))
        self.assertEqual(result["summary"]["post_bootstrap_completed"], 0)
        self.assertTrue(any(d["reason"] == "OUTSIDE_OPTION" for d in result["decisions"]))

    def test_agent_can_refuse_unprofitable_or_overbudget_work(self):
        for change in ({"reward": 3}, {"worker_max_spend": 2}, {"worker_budget": 3}):
            with self.subTest(change=change):
                result = run(replace(Config(), rounds=2, **change))
                self.assertEqual(result["summary"]["completed"], 0)
                self.assertEqual(result["summary"]["external_paid"], 0)

    def test_finite_customer_budget_is_never_replenished(self):
        result = run(replace(Config(), customer_budget=6, sponsor_budget=0, rounds=4))
        self.assertEqual(result["summary"]["completed"], 1)
        self.assertEqual(result["summary"]["external_paid"], 6)
        self.assertEqual(result["ledger"]["snapshot"]["balances"]["agent:customer"], "0")

    def test_invalid_results_refund_both_contracts_and_change_provider(self):
        result = run(replace(Config(), faulty_provider=True, rounds=4))
        failed = [j for j in result["jobs"] if not j["verified"]]
        self.assertTrue(failed)
        for job in failed:
            for field in ("compute_agreement", "output_agreement"):
                receipt = result["ledger"]["snapshot"]["receipts"]["refund:" + job[field]]
                self.assertEqual(receipt["provider_amount"], "0")
            subsequent = [j for j in result["jobs"] if j["round"] > job["round"] and j["solver"] == job["solver"]]
            self.assertTrue(all(j["provider"] != job["provider"] for j in subsequent))
        self.assertGreater(result["summary"]["energy_paid"], 0)
        self.assertTrue(result["summary"]["money_conserved"])

    def test_reinvestment_requires_earned_surplus(self):
        result = run(replace(Config(), rounds=4, upkeep_per_slot=3))
        self.assertEqual(result["summary"]["investment_paid"], 0)

    def test_physical_capacity_does_not_mean_shared_capacity(self):
        result = run(replace(Config(), external_jobs=0, subsidy_jobs=0, rounds=2))
        self.assertEqual(result["summary"]["final_installed_capacity"], 4)
        self.assertEqual(result["summary"]["final_offered_capacity"], 0)
        self.assertIsNone(result["summary"]["provider_hhi"])

    def test_replay_detects_tampered_policy_trace_even_with_new_digest(self):
        result = run(replace(Config(), rounds=2))
        self.assertEqual(verify(result), result["summary"])
        bad = deepcopy(result)
        bad["decisions"][0]["reason"] = "human override"
        bad["sha256"] = digest({k: v for k, v in bad.items() if k != "sha256"})
        with self.assertRaises(SimulationError):
            verify(bad)

    def test_input_bounds(self):
        for change in ({"seed": True}, {"reward": 0}, {"rounds": 31}, {"energy_cost": -1},
                       {"external_jobs": 30}, {"faulty_provider": 1}, {"compute_price": 3.0}):
            with self.subTest(change=change), self.assertRaises(SimulationError):
                run(replace(Config(), **change))


if __name__ == "__main__":
    unittest.main()
