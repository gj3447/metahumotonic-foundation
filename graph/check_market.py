#!/usr/bin/env python3
"""Check a local market snapshot, exact RDF projection and token/money boundaries."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from rdflib.namespace import DCTERMS, PROV, SH

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))
from market.contracts import MarketError, read_json, require
from market.demo import build_demo
from market.projection import BASE, VOCAB, project, verify_snapshot

MK = Namespace(VOCAB)


def source_integrity():
    manifest = read_json((REPO / "market/interop.json").read_text(encoding="utf-8"))
    path = (REPO / manifest["user_source"]).resolve()
    require(path.is_relative_to(REPO), "source path outside repository")
    require(hashlib.sha256(path.read_bytes()).hexdigest() == manifest["user_source_sha256"], "source file changed")
    for message in read_json(path.read_text(encoding="utf-8"))["messages"]:
        require(message["role"] == "user" and message["authority"] == "USER_PRIMARY", "source attribution changed")
        require(hashlib.sha256(message["verbatim"].encode()).hexdigest() == message["sha256"], "user words changed")
    require(manifest["native_schema"] == "hswm-adaptive-execution-observation/v1"
            and manifest["status"] == "LOCAL_ADAPTER_IMPLEMENTED_LIVE_NOT_READY", "interop scope changed")
    # Resolve existing owner graph IDs; a reference never promotes stage status.
    for name, prefix, keys in [("resource-roadmap", "rp", ["S_contract", "S_control", "S_evidence"]),
                               ("philosophy", "ph", ["C_resource_purpose"])]:
        document = read_json((HERE / (name + ".jsonld")).read_text(encoding="utf-8"))
        require(document["@context"][prefix] == BASE + "graph/" + name + "#", "reference namespace changed")
        ids = {node["@id"] for node in document["@graph"]}
        require(all(prefix + ":" + key in ids for key in keys), "missing roadmap/philosophy reference")


def registered(graph, vocab):
    subjects = set(graph.subjects())
    standard = {RDF.type, RDFS.label, DCTERMS.references, PROV.wasGeneratedBy, PROV.wasAssociatedWith}
    standard_types = {PROV.Entity, PROV.Activity, PROV.SoftwareAgent}
    for subject, predicate, obj in graph:
        if predicate == RDF.type:
            require(obj in standard_types or (obj, RDF.type, RDFS.Class) in vocab, f"unknown class: {obj}")
        elif predicate not in standard:
            require((predicate, RDF.type, RDF.Property) in vocab, f"unknown predicate: {predicate}")
        for domain in vocab.objects(predicate, RDFS.domain):
            require(domain == RDFS.Resource or (subject, RDF.type, domain) in graph, f"wrong domain: {predicate}")
        for target in vocab.objects(predicate, RDFS.range):
            if str(target).startswith(str(XSD)):
                require(isinstance(obj, Literal) and (obj.datatype == target or (target == XSD.string and obj.datatype is None)), "wrong literal datatype")
            else:
                require((obj, RDF.type, target) in graph, f"wrong range: {predicate}")
        if isinstance(obj, URIRef) and str(obj).startswith("urn:metahumotonic:market:"):
            require(obj in subjects, "dangling market reference")


def exact_queries(graph, snapshot):
    head = f"PREFIX mk: <{MK}>\n"
    checks = [
        ("order parties and states", "SELECT ?id ?state ?buyer ?provider WHERE { ?o a mk:Order ; mk:sourceID ?id ; mk:state ?state ; mk:requester/mk:sourceID ?buyer ; mk:provider/mk:sourceID ?provider . }",
         {(oid, o["state"], o["requester"], o["provider"]) for oid, o in snapshot["orders"].items()}),
        ("usage remains dimensioned", "SELECT ?id ?in ?out ?cpu ?memory WHERE { ?o a mk:Order ; mk:sourceID ?id ; mk:usage ?u . ?u mk:inputTokens ?in ; mk:outputTokens ?out ; mk:cpuMs ?cpu ; mk:memoryMiBMs ?memory . }",
         {(oid, *(str(o["usage"][u]) for u in ("input_tokens", "output_tokens", "cpu_ms", "memory_mib_ms"))) for oid, o in snapshot["orders"].items() if o["usage"] is not None}),
        ("receipt financial binding", "SELECT ?id ?asset ?paid ?refund ?reserved WHERE { ?r a mk:Receipt ; mk:order/mk:sourceID ?id ; mk:asset/mk:sourceID ?asset ; mk:paidAtoms ?paid ; mk:refundAtoms ?refund ; mk:reservedAtoms ?reserved . }",
         {(oid, r["asset"], str(r["paid_atoms"]), str(r["refund_atoms"]), str(r["reserved_atoms"])) for oid, r in snapshot["receipts"].items()}),
        ("HSWM usage provenance", "SELECT ?id ?model ?tokenizer ?status ?mode WHERE { ?o a mk:Order ; mk:sourceID ?id ; mk:usage ?u . ?u mk:model ?model ; mk:tokenizer ?tokenizer ; mk:meterStatus ?status ; mk:evidenceMode ?mode . }",
         {(oid, o["offer_terms"]["model"], o["offer_terms"]["tokenizer"], o["evidence"]["hswm"]["meter_status"], o["evidence"]["mode"]) for oid, o in snapshot["orders"].items() if o["evidence"] and o["evidence"].get("hswm")}),
        ("grant has owner and resource", "SELECT ?id ?owner ?resource ?state WHERE { ?g a mk:Grant ; mk:sourceID ?id ; mk:owner/mk:sourceID ?owner ; mk:resource/mk:sourceID ?resource ; mk:state ?state . }",
         {(gid, g["owner"], g["resource_id"], g["state"]) for gid, g in snapshot["grants"].items()}),
        ("sandbox identity", "SELECT ?mode ?asset WHERE { ?s a mk:MarketSnapshot ; mk:mode ?mode ; mk:asset/mk:sourceID ?asset . }",
         {("LOCAL_SANDBOX", "sandbox:SIM-MHC")}),
        ("exact prices connect usage units to settlement asset", "SELECT ?offer ?unit ?numerator ?denominator ?asset WHERE { ?o a mk:Offer ; mk:sourceID ?offer ; mk:hasPrice ?p . ?p mk:offer ?o ; mk:unit ?unit ; mk:priceNumerator ?numerator ; mk:priceDenominator ?denominator ; mk:asset/mk:sourceID ?asset . }",
         {(oid, unit, str(rate[0]), str(rate[1]), o["terms"]["asset"]) for oid, o in snapshot["offers"].items()
          for unit, rate in o["terms"]["rates"].items()}),
        ("owner references and user source", "SELECT ?source WHERE { ?s a mk:MarketSnapshot ; <http://purl.org/dc/terms/references> ?source . }",
         {(BASE + suffix,) for suffix in ["graph/resource-roadmap#S_contract", "graph/resource-roadmap#S_control",
          "graph/resource-roadmap#S_evidence", "graph/philosophy#C_resource_purpose", "market/interop.json",
          "records/2026-10-04/market-source.json"]}),
    ]
    for name, query, expected in checks:
        actual = {tuple(str(x) for x in row) for row in graph.query(head + query)}
        require(actual == expected, f"CQ mismatch: {name}")
    return len(checks)


def check(snapshot, document):
    source_integrity()
    verify_snapshot(snapshot)
    require(document == project(snapshot), "JSON-LD is not the exact local projection")
    # Equality above enforces a locally authored context before the RDF parser.
    graph = Graph().parse(data=json.dumps(document), format="json-ld")
    vocab = Graph().parse(HERE / "market-vocab.ttl")
    shapes = Graph().parse(HERE / "market.shapes.ttl")
    registered(graph, vocab)
    ok, _, report = validate(graph, shacl_graph=shapes, meta_shacl=True)
    require(ok, report)
    cqs = exact_queries(graph, snapshot)
    root = next(graph.subjects(RDF.type, MK.MarketSnapshot))
    asset = next(graph.subjects(RDF.type, MK.Asset))
    # Fixed negative boundaries apply even when a user exports an empty market.
    cases = [(root, MK.mode, Literal("MAINNET")), (asset, MK.sourceID, Literal("real:MHC")),
             (root, MK.supplyAtoms, Literal(-1)), (asset, MK.mode, Literal("LIVE_HSWM"))]
    price = next(graph.subjects(RDF.type, MK.UnitPrice), None)
    if price is not None: cases.append((price, MK.priceDenominator, Literal(0)))
    for focus, prop, value in cases:
        bad = copy.deepcopy(graph); bad.set((focus, prop, value))
        conforms, report, _ = validate(bad, shacl_graph=shapes)
        caught = any(report.value(r, SH.focusNode) == focus and report.value(r, SH.resultPath) == prop
                     for r in report.subjects(RDF.type, SH.ValidationResult))
        require(not conforms and caught, "negative boundary not detected")
    for mutation in [lambda g: g.add((root, MK.unknown, asset)),
                     lambda g: g.set((root, MK.asset, URIRef("urn:metahumotonic:market:missing"))),
                     lambda g: g.add((asset, MK.paidAtoms, Literal(1)))]:
        bad = copy.deepcopy(graph); mutation(bad)
        try: registered(bad, vocab)
        except MarketError: pass
        else: raise MarketError("negative term contract not detected")
    print(f"market: snapshot/ledger/exact projection PASS; SHACL/meta-SHACL PASS; {cqs} exact CQs; {len(cases)+3} negative cases; LOCAL_SANDBOX")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--graph", type=Path)
    args = parser.parse_args()
    require(bool(args.snapshot) == bool(args.graph), "provide both --snapshot and --graph")
    if args.snapshot:
        check(read_json(args.snapshot.read_text(encoding="utf-8")), read_json(args.graph.read_text(encoding="utf-8")))
    else:
        with tempfile.TemporaryDirectory(prefix="market-graph-") as directory:
            market, report = build_demo(Path(directory) / "market.sqlite3")
            require(report["chosen_offer"] == "provider-b:offer" and report["receipt"]["state"] == "SETTLED", "demo trade failed")
            snapshot = market.snapshot()
            check(snapshot, project(snapshot))


if __name__ == "__main__":
    main()
