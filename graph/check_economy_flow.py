#!/usr/bin/env python3
"""Validate the proposed, entirely simulated economy-flow fixture."""
from decimal import Decimal
from pathlib import Path
from rdflib import Graph, Literal, Namespace, RDF, XSD
from pyshacl import validate

ROOT = Path(__file__).resolve().parent
MHV = Namespace("https://github.com/gj3447/metahumotonic-foundation/vocab#")
EX = Namespace("https://github.com/gj3447/metahumotonic-foundation/graph/economy-example#")
ECO = Namespace("https://github.com/gj3447/metahumotonic-foundation/graph/economy#")


def load_graph():
    graph = Graph()
    graph.parse(ROOT / "fixtures/economy-flow.jsonld", format="json-ld")
    return graph

def shacl_ok(graph):
    shapes = Graph().parse(ROOT / "economy-flow.shapes.ttl", format="turtle")
    return validate(graph, shacl_graph=shapes, inference="rdfs", advanced=True, meta_shacl=True)[0]


def shacl_report(graph):
    shapes = Graph().parse(ROOT / "economy-flow.shapes.ttl", format="turtle")
    return validate(graph, shacl_graph=shapes, inference="rdfs", advanced=True, meta_shacl=True)[2]

def semantic_ok(graph):
    # Every fixture-local runtime/concept example is explicitly a simulation.
    if any(graph.value(subject, MHV.simulationStatus) != MHV.SIMULATED
           for subject in graph.subjects() if str(subject).startswith(str(EX))):
        return False
    for receipt in graph.subjects(RDF.type, MHV.SettlementReceipt):
        usage = graph.value(receipt, MHV.basedOnUsage)
        agreement = graph.value(receipt, MHV.settlesAgreement)
        amount = graph.value(receipt, MHV.settlementAmount)
        units = graph.value(usage, MHV.meteredUnits)
        price = graph.value(agreement, MHV.agreedUnitPrice)
        values = (amount, units, price)
        try:
            decimals = tuple(Decimal(str(value)) for value in values)
        except Exception:
            return False
        if (None in (usage, agreement, *values) or any(not value.is_finite() or value < 0 for value in decimals)
                or decimals[0] != decimals[1] * decimals[2]):
            return False
    return True

def check(graph):
    return shacl_ok(graph) and semantic_ok(graph)

def expect_invalid(name, mutate, message=None):
    graph = load_graph()
    mutate(graph)
    assert not check(graph), name
    if message:
        assert message in shacl_report(graph), name

def main():
    assert check(load_graph()), "positive synthetic flow"
    expect_invalid("missing provider assent", lambda g: g.remove((EX.agreement, MHV.hasAssent, EX.provider_assent)))
    expect_invalid("mismatched agreement version", lambda g: g.set((EX.provider_assent, MHV.acceptedVersion, Literal("v2", datatype=XSD.string))))
    expect_invalid("unaccepted usage", lambda g: g.set((EX.usage, MHV.usageStatus, MHV.SIMULATED)))
    expect_invalid("unaccepted result", lambda g: g.set((EX.result, MHV.resultStatus, MHV.SIMULATED)))
    expect_invalid("agreement missing execution", lambda g: g.remove((EX.agreement, MHV.hasExecution, EX.execution)))
    expect_invalid("execution missing result evidence", lambda g: g.remove((EX.execution, MHV.hasResultEvidence, EX.result)))
    expect_invalid("provider differs from offer", lambda g: g.set((EX.offer, MHV.offeredBy, EX.requester)))

    def wrong_agreement_usage(g):
        g.add((EX.other_usage, RDF.type, MHV.UsageObservation))
        for predicate, obj in ((MHV.meteredUnits, Literal("3", datatype=XSD.decimal)), (MHV.observedUnit, EX.compute_unit),
                               (MHV.usageStatus, MHV.ACCEPTED), (MHV.acceptedBy, EX.requester),
                               (MHV.simulationStatus, MHV.SIMULATED),
                               (Namespace("http://www.w3.org/ns/prov#").wasAttributedTo, EX.provider),
                               (Namespace("http://purl.org/dc/terms/").source, EX.usage_meter_report)):
            g.add((EX.other_usage, predicate, obj))
        g.set((EX.receipt, MHV.basedOnUsage, EX.other_usage))

    expect_invalid("usage is not under agreement execution", wrong_agreement_usage)
    expect_invalid("wrong usage unit", lambda g: g.set((EX.usage, MHV.observedUnit, EX.demo_currency)))
    expect_invalid("wrong settlement currency", lambda g: g.set((EX.receipt, MHV.denominatedIn, ECO.metahumocoin)))
    expect_invalid("wrong settlement amount", lambda g: g.set((EX.receipt, MHV.settlementAmount, Literal("5", datatype=XSD.decimal))))
    expect_invalid("negative units", lambda g: g.set((EX.usage, MHV.meteredUnits, Literal("-3", datatype=XSD.decimal))))
    expect_invalid("negative agreed price", lambda g: g.set((EX.agreement, MHV.agreedUnitPrice, Literal("-2", datatype=XSD.decimal))))
    expect_invalid("negative settlement amount", lambda g: g.set((EX.receipt, MHV.settlementAmount, Literal("-6", datatype=XSD.decimal))))

    def duplicate(g, settlement_id, payment_reference):
        g.add((EX.receipt_two, RDF.type, MHV.SettlementReceipt))
        for predicate, obj in ((MHV.settlesAgreement, EX.agreement), (MHV.basedOnUsage, EX.usage), (MHV.denominatedIn, EX.demo_currency),
                               (MHV.settlementAmount, Literal("6", datatype=XSD.decimal)),
                               (MHV.settlementId, Literal(settlement_id, datatype=XSD.string)),
                               (MHV.paymentReference, Literal(payment_reference, datatype=XSD.string)),
                               (MHV.simulationStatus, MHV.SIMULATED)):
            g.add((EX.receipt_two, predicate, obj))

    expect_invalid("duplicate settlement ID", lambda g: duplicate(g, "sim-settlement-001", "sim-payment-002"),
                   "settlementId must be unique among receipts.")
    expect_invalid("duplicate payment reference", lambda g: duplicate(g, "sim-settlement-002", "sim-payment-001"),
                   "paymentReference must be unique among receipts.")
    expect_invalid("same usage paid twice", lambda g: duplicate(g, "sim-settlement-002", "sim-payment-002"))
    expect_invalid("minted supply claim", lambda g: g.add((ECO.metahumocoin, MHV.mintedSupply, Literal("1", datatype=XSD.decimal))))
    print("economy-flow: positive fixture and 18 negative checks passed")

if __name__ == "__main__":
    main()
