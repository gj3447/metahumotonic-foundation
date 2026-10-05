#!/usr/bin/env python3
"""Offline source, ontology and question checks; not an economic proof."""
import copy
import hashlib
import json
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from rdflib.namespace import DCTERMS, OWL, PROV, SH, SKOS

import check as base
import check_philosophy as philosophy

HERE = Path(__file__).resolve().parent
CC = Namespace(base.BASE + "graph/compute-coin#")
CV = Namespace(base.BASE + "compute-coin-vocab#")
require = base.require


def read(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=base.unique_keys)


def check_documents(documents):
    philosophy.check_documents(documents)
    doc = documents[-1]
    require(doc["@context"]["cc"] == str(CC) and doc["@context"]["cv"] == str(CV), "namespace changed")
    require(all(n["@id"].startswith("cc:") for n in doc["@graph"]), "foreign owner ID redefined")


def load():
    docs = [read(HERE / name) for name in ["spirit.jsonld", "economy.jsonld", "metahumocoin.jsonld",
            "philosophy.jsonld", "ecosystem.jsonld", "compute-coin.jsonld"]]
    check_documents(docs)
    vocab = Graph().parse(HERE / "vocab.ttl").parse(HERE / "compute-coin-vocab.ttl")
    return docs, base.load_graph(docs) + vocab, Graph().parse(HERE / "compute-coin.shapes.ttl"), vocab


def check_integrity(graph, vocab):
    subjects = set(graph.subjects())
    standard = {RDF.type, RDFS.label, DCTERMS.source, DCTERMS.subject, PROV.wasAttributedTo}
    for subject, predicate, obj in graph:
        if not str(subject).startswith(str(CC)):
            continue
        require(predicate not in {OWL.sameAs, SKOS.exactMatch}, "research cannot assert identity")
        require(predicate in standard or (predicate, RDF.type, RDF.Property) in vocab, "unregistered predicate")
        if predicate == RDF.type:
            require(obj == PROV.SoftwareAgent or (obj, RDF.type, RDFS.Class) in vocab, "unregistered class")
        for domain in vocab.objects(predicate, RDFS.domain):
            require(domain == RDFS.Resource or (subject, RDF.type, domain) in graph, "wrong domain")
        for target in vocab.objects(predicate, RDFS.range):
            if target == RDFS.Resource:
                require(isinstance(obj, URIRef), "IRI required")
            elif str(target).startswith(str(XSD)):
                require(isinstance(obj, Literal) and (obj.datatype == target or
                        (target == XSD.string and obj.datatype is None)), "wrong datatype")
            else:
                require((obj, RDF.type, target) in graph, "wrong range")
        if isinstance(obj, URIRef) and str(obj).startswith(base.BASE + "graph/"):
            require(obj in subjects, "dangling endpoint")

    paths = {"user": "records/2026-10-05/compute-coin/user-source.json",
             "sources": "records/2026-10-05/compute-coin/sources.json",
             "report": "COMPUTE-COIN.md", "prototype": "metahumocoin/ledger.py"}
    raw = {}
    require(set(graph.subjects(RDF.type, CV.Artifact)) == {CC["artifact_" + k] for k in paths}, "artifact coverage")
    require(set(graph.objects(CC.graph, CV.inputArtifact)) == {CC["artifact_" + k] for k in paths}, "root artifacts")
    for key, expected in paths.items():
        node = CC["artifact_" + key]
        relative = str(graph.value(node, base.MHV.path))
        require(relative == expected, "artifact path mismatch")
        raw[key] = philosophy.safe_path(relative).read_bytes()
        require(hashlib.sha256(raw[key]).hexdigest() == str(graph.value(node, base.MHV.sha256)), "artifact hash mismatch")
    user = json.loads(raw["user"], object_pairs_hook=base.unique_keys)
    require(user["role"] == "user" and user["authority"] == "USER_PRIMARY", "user authority")
    require(str(graph.value(CC.U_request, CV.text)) == user["verbatim"] and
            graph.value(CC.U_request, DCTERMS.source) == CC.artifact_user, "user source changed")
    require(set(graph.subjects(RDF.type, CV.UserClaim)) == {CC.U_request}, "extra user claim")
    expected_claims = {CC.U_request, URIRef(base.BASE + "graph/philosophy#C_resource_purpose"),
                       URIRef(base.BASE + "graph/ecosystem#C_operation"), URIRef(base.BASE + "graph/ecosystem#C_population")}
    require(set(graph.objects(CC.graph, CV.sourceClaim)) == expected_claims, "source claim scope")

    catalog = json.loads(raw["sources"], object_pairs_hook=base.unique_keys)
    rows = {row["id"]: row for row in catalog["sources"]}
    require(len(rows) == len(catalog["sources"]), "duplicate source ID")
    require(set(graph.subjects(RDF.type, CV.Observation)) == {CC["S_" + k] for k in rows}, "source coverage")
    for key, row in rows.items():
        node = CC["S_" + key]
        fields = {CV.key: "id", CV.text: "text", CV.limitation: "limitation", CV.locator: "locator",
                  CV.mode: "mode", CV.sourceStatus: "status", CV.observedOn: "observed_on",
                  CV.authority: "authority", DCTERMS.source: "url", RDFS.label: "title"}
        for predicate, field in fields.items():
            require(str(graph.value(node, predicate)) == row[field], "observation differs from catalog")
        revision = graph.value(node, CV.revision)
        require((revision is None and row["revision"] is None) or
                (revision is not None and str(revision) == row["revision"]), "source revision invented or lost")
        require(row["mode"] == "PARAPHRASE" and row["url"].startswith("https://") and
                row["full_text_archived"] is False and row["remote_content_sha256"] is None, "source scope promoted")

    proposals = set(graph.subjects(RDF.type, CV.Proposal))
    observations = set(graph.subjects(RDF.type, CV.Observation))
    allowed_basis = proposals | observations | {CC.U_request}
    for proposal in proposals:
        require(set(graph.objects(proposal, CV.basis)) <= allowed_basis, "invalid inference basis")
    for kind in [CV.Proposal, CV.Risk, CV.Question]:
        for node in graph.subjects(RDF.type, kind):
            require(graph.value(node, DCTERMS.source) == CC.artifact_report, "missing authored report provenance")
    for node, target in graph.subject_objects(CV.targets):
        require(not str(target).startswith(str(CC)) and target in subjects, "target must reuse existing owner entity")
    visiting, visited = set(), set()
    def visit(node):
        require(node not in visiting, "circular inference")
        if node in visited:
            return
        visiting.add(node)
        for premise in graph.objects(node, CV.basis):
            if premise in proposals:
                visit(premise)
        visiting.remove(node)
        visited.add(node)
    for node in proposals:
        visit(node)

    components = {CC[x]: x.upper() for x in ["unit", "capacity", "mint", "liability", "redemption", "receipt"]}
    require(set(graph.subjects(RDF.type, CV.Component)) == set(components), "component identity changed")
    for node, kind in components.items():
        require(str(graph.value(node, CV.kind)) == kind, "component role mismatch")
    relationships = {CV.forUnit: {(CC.capacity, CC.unit)}, CV.boundsMint: {(CC.capacity, CC.mint)},
                     CV.createsLiability: {(CC.mint, CC.liability)}, CV.settles: {(CC.redemption, CC.liability)},
                     CV.requiresReceipt: {(CC.redemption, CC.receipt)}}
    for predicate, expected in relationships.items():
        require(set(graph.subject_objects(predicate)) == expected, "protocol edge missing or reversed")


def competency_questions(graph):
    spec = read(HERE / "compute-coin-queries.json")
    prefix = "\n".join(f"PREFIX {k}: <{v}>" for k, v in spec["prefixes"].items())
    def expand(value):
        head, sep, rest = value.partition(":")
        return spec["prefixes"][head] + rest if sep and head in spec["prefixes"] else value
    seen = set()
    for question in spec["questions"]:
        require(question["id"] not in seen, "duplicate question")
        seen.add(question["id"])
        result = graph.query(prefix + "\n" + question["query"])
        require([str(v) for v in result.vars] == question["columns"], "query columns")
        actual = {tuple(str(x) for x in row) for row in result}
        expected = {tuple(expand(x) for x in row) for row in question["expected"]}
        require(actual == expected, f"CQ {question['id']} mismatch: {actual}")
    return len(seen)


def negative_checks(docs, graph, shapes, vocab):
    shape_cases = [(CC.D_anchor, CV.authority, Literal("USER_PRIMARY")),
                   (CC.D_capacity, CV.status, Literal("RATIFIED")),
                   (CC.Q_rollover, CV.status, Literal("DECIDED")),
                   (CC.graph, CV.executionEffect, Literal(True)),
                   (CC.graph, CV.normativeEffect, Literal(True)),
                   (CC.S_clawcoin, CV.authority, Literal("EMPIRICALLY_VERIFIED")),
                   (CC.unit, CV.status, Literal("DEPLOYED"))]
    for subject, predicate, obj in shape_cases:
        bad = copy.deepcopy(graph)
        bad.set((subject, predicate, obj))
        ok, report, _ = validate(bad, shacl_graph=shapes)
        caught = any(report.value(r, SH.focusNode) == subject and report.value(r, SH.resultPath) == predicate
                     for r in report.subjects(RDF.type, SH.ValidationResult))
        require(not ok and caught, "negative shape case escaped")
    mutations = [
        lambda g: g.set((CC.artifact_report, base.MHV.sha256, Literal("0" * 64))),
        lambda g: g.set((CC.artifact_user, base.MHV.path, Literal("../outside"))),
        lambda g: g.set((CC.U_request, CV.text, Literal("AI rewrite"))),
        lambda g: g.set((CC.S_clawcoin, DCTERMS.source, URIRef("https://example.invalid"))),
        lambda g: g.set((CC.S_icp, CV.revision, Literal("invented revision"))),
        lambda g: g.set((CC.S_truebit, CV.sourceStatus, Literal("DEPLOYED"))),
        lambda g: g.add((CC.D_capacity, CV.basis, CC.artifact_user)),
        lambda g: g.add((CC.D_capacity, CV.basis, CC.D_settlement)),
        lambda g: g.add((CC.D_anchor, CV.unknown, CC.unit)),
        lambda g: g.add((CC.D_anchor, OWL.sameAs, CC.unit)),
        lambda g: g.set((CC.capacity, CV.forUnit, CC.missing)),
        lambda g: g.set((CC.capacity, CV.boundsMint, CC.liability)),
        lambda g: g.remove((CC.redemption, CV.requiresReceipt, None)),
        lambda g: g.set((CC.D_agents, CV.targets, CC.unit)),
    ]
    for mutate in mutations:
        bad = copy.deepcopy(graph)
        mutate(bad)
        try:
            check_integrity(bad, vocab)
        except (ValueError, KeyError):
            pass
        else:
            raise ValueError("negative integrity case escaped")
    serializations = [
        lambda d: d[-1]["@graph"].append(copy.deepcopy(d[-1]["@graph"][0])),
        lambda d: d[-1].__setitem__("@context", "https://example.invalid/context"),
        lambda d: d[-1]["@graph"][0].__setitem__("unknownKey", "dropped silently"),
        lambda d: d[-1]["@graph"][0].__setitem__("@id", "ph:foreign-writer"),
    ]
    for mutate in serializations:
        bad = copy.deepcopy(docs)
        mutate(bad)
        try:
            check_documents(bad)
        except ValueError:
            pass
        else:
            raise ValueError("negative document case escaped")
    return len(shape_cases) + len(mutations) + len(serializations)


def main():
    docs, graph, shapes, vocab = load()
    check_integrity(graph, vocab)
    ok, _, report = validate(graph, shacl_graph=shapes, meta_shacl=True)
    require(ok, report)
    questions = competency_questions(graph)
    negatives = negative_checks(docs, graph, shapes, vocab)
    print(f"compute-coin: SHACL/meta-SHACL PASS; {questions} CQs; {negatives} negative cases; source integrity PASS; local research only")


if __name__ == "__main__":
    main()
