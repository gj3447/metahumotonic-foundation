#!/usr/bin/env python3
"""Validate executable local scenarios, provenance and their RDF projection."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, XSD
from rdflib.compare import isomorphic

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from economy.artifacts import bundle, to_jsonld, verify_bundle
from economy.scenarios import demo
import check as graph_check

MHV = graph_check.MHV
SH = graph_check.SH
ECO = graph_check.ECO


def rdf(document):
    return Graph().parse(data=json.dumps(document, ensure_ascii=False), format="json-ld")


def verify_projection(document, projected):
    verify_bundle(document)
    expected = rdf(to_jsonld(document))
    if not isomorphic(expected, rdf(projected)):
        raise ValueError("graph projection differs from the replay-verified bundle")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, help="optional saved simulation.json to replay")
    parser.add_argument("--graph", type=Path, help="optional saved simulation.jsonld to compare")
    args = parser.parse_args()
    if args.graph and not args.bundle:
        parser.error("--graph requires --bundle")
    if args.bundle:
        document = json.loads(args.bundle.read_text(encoding="utf-8"), object_pairs_hook=graph_check.unique_keys)
    else:
        simulator, initial, commands = demo()
        document = bundle(simulator, initial, commands)
    projected = graph_check.read_document(args.graph) if args.graph else to_jsonld(document)
    verify_projection(document, projected)
    data = graph_check.load_graph([graph_check.read_document(path) for path in graph_check.DATA_PATHS])
    data += rdf(projected)
    schema = graph_check.shapes()
    schema.parse(HERE / "economy-simulation.shapes.ttl")
    graph_check.check_integrity(data)
    ok, _, report = validate(data, shacl_graph=schema, meta_shacl=True)
    graph_check.require(ok, report)

    # Accept arbitrary saved runs, while the built-in demonstration has fixed CQs.
    questions = 0
    if not args.bundle:
        prefix = f"PREFIX mhv: <{MHV}> PREFIX prov: <{graph_check.PROV}> PREFIX eco: <{ECO}> "
        queries = [
            ("lifecycle outcomes", "SELECT ?id ?state WHERE { ?a a mhv:SimulationAgreement ; mhv:simAgreementId ?id ; mhv:simState ?state }",
             {("work-success", "SETTLED"), ("work-cancelled", "CANCELLED"), ("work-disputed", "RESOLVED")}),
            ("available balances", "SELECT ?id ?balance WHERE { ?a a mhv:SimulationAccount ; mhv:simAccountId ?id ; mhv:simAvailableBalance ?balance }",
             {("alice", "90"), ("bob", "10"), ("carol", "0")}),
            ("normal vs disputed settlement", "SELECT ?id ?kind ?amount ?refund WHERE { ?r a mhv:SimulationReceipt ; mhv:simOperationId ?id ; mhv:simReceiptKind ?kind ; mhv:simPaid ?amount ; mhv:simRefund ?refund }",
             {("settlement-success", "SETTLE", "6", "4"), ("resolution-disputed", "RESOLVE", "4", "8")}),
            ("preserved value", "SELECT ?total ?held WHERE { ?r a mhv:SimulationRun ; mhv:simTotal ?total ; mhv:simEscrow ?held }",
             {("100", "0")}),
            ("proposal provenance", "SELECT ?proposal ?claim WHERE { ?r a mhv:SimulationRun ; prov:used ?proposal . ?proposal mhv:basedOn ?claim . ?claim mhv:topic eco:metahumocoin }",
             {(str(ECO.D_simulation), str(ECO.C_coin))}),
        ]
        for name, query, expected in queries:
            actual = {tuple(str(item) for item in row) for row in data.query(prefix + query)}
            graph_check.require(actual == expected, f"simulation CQ {name}: {actual}")
        questions = len(queries)

    negatives = 0
    # Negative graph cases are tied to their intended SHACL focus/constraint.
    if not args.bundle:
        run = next(data.subjects(RDF.type, MHV.SimulationRun))
        account = next(s for s in data.subjects(RDF.type, MHV.SimulationAccount)
                       if str(data.value(s, MHV.simAccountId)) == "alice")
        event = next(s for s in data.subjects(RDF.type, MHV.SimulationEvent)
                     if data.value(s, MHV.eventSequence).toPython() == 2)
        receipt = next(s for s in data.subjects(RDF.type, MHV.SimulationReceipt)
                       if str(data.value(s, MHV.simReceiptKind)) == "SETTLE")
        cases = [
            ("false live status", run, MHV.simulationStatus,
             lambda g: g.set((run, MHV.simulationStatus, MHV.LIVE))),
            ("broken conservation", run, MHV.SimulationRunShape,
             lambda g: g.set((account, MHV.simAvailableBalance, Literal("91", datatype=XSD.decimal)))),
            ("missing acting party", event, MHV.simActor,
             lambda g: g.remove((event, MHV.simActor, None))),
            ("event self-cycle", event, MHV.SimulationEventShape,
             lambda g: g.set((event, MHV.previousSimEvent, event))),
            ("wrong receipt lifecycle", receipt, MHV.SimulationReceiptShape,
             lambda g: g.set((receipt, MHV.simReceiptKind, Literal("RESOLVE")))),
        ]
        for name, focus, path_or_shape, mutate in cases:
            bad = deepcopy(data)
            mutate(bad)
            ok, results, report = validate(bad, shacl_graph=schema)
            caught = any(results.value(result, SH.focusNode) == focus and
                         (results.value(result, SH.resultPath) == path_or_shape or
                          results.value(result, SH.sourceShape) == path_or_shape)
                         for result in results.subjects(RDF.type, SH.ValidationResult))
            graph_check.require(not ok and caught, f"negative simulation case: {name}\n{report}")
        negatives = len(cases)
        # Syntactically plausible projection edits must still match replay.
        bad_projection = deepcopy(projected)
        for node in bad_projection["@graph"]:
            if "amount" in node:
                node["amount"] = "0"
                break
        try:
            verify_projection(document, bad_projection)
        except ValueError:
            negatives += 1
        else:
            raise ValueError("modified projection was accepted")
    print(f"simulation: replay/source hashes/projection PASS; SHACL/meta-SHACL PASS; {questions} CQs; {negatives} negative cases ({len(document['events'])} events)")


if __name__ == "__main__":
    main()
