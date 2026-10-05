"""Behavioral checks for deterministic export and replay of the economy demo."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from .artifacts import bundle, digest, to_jsonld, verify_bundle
from .scenarios import demo
from .simulator import SimulationError


class ArtifactsTest(unittest.TestCase):
    def make(self):
        simulator, initial, commands = demo()
        return bundle(simulator, initial, commands)

    def test_demo_final_balances_and_states(self):
        document = self.make()
        snapshot = verify_bundle(document).snapshot()
        self.assertEqual(snapshot["balances"], {"alice": "90", "bob": "10", "carol": "0"})
        self.assertEqual(snapshot["escrow_total"], "0")
        self.assertEqual(snapshot["total_units"], "100")
        self.assertEqual({key: value["status"] for key, value in snapshot["agreements"].items()},
                         {"work-success": "SETTLED", "work-cancelled": "CANCELLED", "work-disputed": "RESOLVED"})
        self.assertEqual(len(snapshot["receipts"]), 2)

    def test_replay_and_graph_are_deterministic(self):
        first, second = self.make(), self.make()
        self.assertEqual(first, second)
        self.assertEqual(to_jsonld(first), to_jsonld(second))

    def test_modified_bundle_is_rejected(self):
        document = self.make()
        document["snapshot"]["balances"]["alice"] = "999"
        with self.assertRaisesRegex(SimulationError, "digest"):
            verify_bundle(document)

    def test_recomputed_outer_digest_cannot_hide_edited_state(self):
        document = self.make()
        document["snapshot"]["balances"]["alice"] = "999"
        document["bundle_sha256"] = digest({k: v for k, v in document.items() if k != "bundle_sha256"})
        with self.assertRaisesRegex(SimulationError, "snapshot differs"):
            verify_bundle(document)

    def test_event_tampering_is_rejected_even_with_new_bundle_digest(self):
        document = self.make()
        document["events"][0]["actor"] = "carol"
        document["bundle_sha256"] = digest({k: v for k, v in document.items() if k != "bundle_sha256"})
        with self.assertRaisesRegex(SimulationError, "event journal"):
            verify_bundle(document)

    def test_source_mismatch_is_visible(self):
        document = self.make()
        document["source_sha256"]["economy/simulator.py"] = "0" * 64
        document["bundle_sha256"] = digest({k: v for k, v in document.items() if k != "bundle_sha256"})
        with self.assertRaisesRegex(SimulationError, "source revision"):
            verify_bundle(document)

    def test_cli_round_trip(self):
        cwd = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as directory:
            run = subprocess.run([sys.executable, "-m", "economy", "demo", "--output-dir", directory],
                                 cwd=cwd, check=True, capture_output=True, text=True)
            replay = subprocess.run([sys.executable, "-m", "economy", "verify", str(Path(directory) / "simulation.json")],
                                    cwd=cwd, check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(run.stdout), json.loads(replay.stdout))
            graph = json.loads((Path(directory) / "simulation.jsonld").read_text())
            self.assertTrue(graph["@graph"])

    def test_payloads_do_not_alias_bundle(self):
        document = self.make()
        untouched = deepcopy(document)
        graph = to_jsonld(document)
        graph["@graph"][0]["snapshot"]["balances"]["alice"] = "999"
        self.assertEqual(document, untouched)


if __name__ == "__main__":
    unittest.main()
