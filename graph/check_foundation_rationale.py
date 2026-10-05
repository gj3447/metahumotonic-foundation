#!/usr/bin/env python3
"""Offline checks for the research report and its attributed argument index.

These checks establish source/structure consistency, not truth of the rationale,
policy adoption, successful institutional experiments or permission to execute.
"""
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
REPO = HERE.parent
FR = Namespace(base.BASE + "graph/foundation-rationale#")
RV = Namespace(base.BASE + "rationale-vocab#")
EX = Namespace(base.BASE + "graph/ecosystem#")
EV = Namespace(base.BASE + "ecosystem-vocab#")
PH = Namespace(base.BASE + "graph/philosophy#")
require = base.require
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=base.unique_keys)


def check_documents(documents):
    philosophy.check_documents(documents)
    doc = documents[-1]
    require(doc["@context"]["fr"] == str(FR) and doc["@context"]["rv"] == str(RV),
            "research namespace changed")
    require(all(n["@id"].startswith("fr:") for n in doc["@graph"]),
            "research must not redefine imported owner IDs")


def load():
    documents = [read(HERE / name) for name in [
        "spirit.jsonld", "economy.jsonld", "metahumocoin.jsonld",
        "philosophy.jsonld", "ecosystem.jsonld", "foundation-rationale.jsonld"]]
    check_documents(documents)
    vocab = Graph().parse(HERE / "vocab.ttl").parse(HERE / "foundation-rationale-vocab.ttl")
    graph = base.load_graph(documents) + vocab
    shapes = Graph().parse(HERE / "foundation-rationale.shapes.ttl")
    return documents, graph, shapes, vocab


def check_integrity(graph, vocab):
    require((FR.graph, RDF.type, RV.ResearchGraph) in graph, "missing research root")
    subjects = set(graph.subjects())
    standard = {RDF.type, RDFS.label, DCTERMS.source, DCTERMS.subject,
                DCTERMS.references, PROV.wasAttributedTo, PROV.wasDerivedFrom}
    for subject, predicate, obj in graph:
        if not str(subject).startswith(str(FR)):
            continue
        require(predicate not in {OWL.sameAs, SKOS.exactMatch}, "research cannot assert identity")
        require(predicate in standard or (predicate, RDF.type, RDF.Property) in vocab,
                f"unregistered predicate: {predicate}")
        if predicate == RDF.type:
            require(obj == PROV.SoftwareAgent or (obj, RDF.type, RDFS.Class) in vocab,
                    "unregistered node class")
        for domain in vocab.objects(predicate, RDFS.domain):
            require(domain == RDFS.Resource or (subject, RDF.type, domain) in graph,
                    f"wrong domain: {predicate}")
        for target in vocab.objects(predicate, RDFS.range):
            if target == RDFS.Resource:
                require(isinstance(obj, URIRef), "IRI endpoint required")
            elif str(target).startswith(str(XSD)):
                require(isinstance(obj, Literal) and
                        (obj.datatype == target or (target == XSD.string and obj.datatype is None)),
                        "wrong literal datatype")
            else:
                require((obj, RDF.type, target) in graph, f"wrong range: {predicate}")
        if isinstance(obj, URIRef) and str(obj).startswith(base.BASE + "graph/"):
            require(obj in subjects, f"dangling owner endpoint: {obj}")

    artifacts = {}
    for artifact in graph.subjects(RDF.type, RV.Artifact):
        raw = philosophy.safe_path(graph.value(artifact, base.MHV.path)).read_bytes()
        require(sha(raw) == str(graph.value(artifact, base.MHV.sha256)), "artifact digest mismatch")
        artifacts[artifact] = raw
    require(set(graph.objects(FR.graph, RV.inputArtifact)) == set(artifacts), "input coverage differs")
    require(graph.value(FR.graph, RV.evidenceArtifact) == FR.artifact_evidence
            and graph.value(FR.graph, RV.reportArtifact) == FR.artifact_report,
            "wrong report or evidence artifact")
    require(str(graph.value(FR.artifact_report, base.MHV.path)) == "FOUNDATION-RATIONALE.md",
            "report path changed")
    evidence = json.loads(artifacts[FR.artifact_evidence], object_pairs_hook=base.unique_keys)
    require(evidence["authority"] == "DOCUMENT_OBSERVATION", "evidence authority changed")
    rows = {row["id"]: row for row in evidence["sources"]}
    require(len(rows) == len(evidence["sources"]), "duplicate evidence key")
    observations = set(graph.subjects(RDF.type, RV.Observation))
    require(observations == {FR["S_" + key] for key in rows}, "observation coverage differs")
    for observation in observations:
        key = str(graph.value(observation, RV.recordKey))
        require(observation == FR["S_" + key], "observation key mismatch")
        row = rows[key]
        require(str(graph.value(observation, RV.text)) == row["text"]
                and str(graph.value(observation, RV.mode)) == row["mode"]
                and str(graph.value(observation, RV.locator)) == row["locator"]
                and str(graph.value(observation, RV.sourceStatus)) == row["source_status"]
                and str(graph.value(observation, RV.limitation)) == row["limitation"]
                and str(graph.value(observation, RV.recordedOn)) == row["observed_on"],
                "observation no longer matches evidence")
        revision = graph.value(observation, RV.revision)
        require((revision is None and row["revision"] is None)
                or (revision is not None and str(revision) == row["revision"]),
                "source revision absent or invented")
        source = graph.value(observation, DCTERMS.source)
        if row["mode"] == "EXACT_EXCERPT":
            require(source == FR["artifact_" + key] and source in artifacts, "wrong snapshot artifact")
            require(str(graph.value(source, base.MHV.path)) == row["copy_path"]
                    and sha(artifacts[source]) == row["sha256"], "snapshot provenance mismatch")
            require(row["text"] in artifacts[source].decode("utf-8"), "excerpt not found in snapshot")
            require(row["revision"] is None and row["revision_state"] == "WORKTREE_BYTES_NOT_CLAIMED_AS_COMMITTED",
                    "worktree snapshot promoted to committed revision")
        else:
            require(row["mode"] == "PARAPHRASE" and str(source) == row["source_uri"]
                    and str(source).startswith("https://"), "external source mismatch")
            require(row["full_text_archived"] is False and row["remote_content_sha256"] is None,
                    "unobserved remote full-text integrity claim")

    user_sources = {FR.U_request: FR.artifact_user, FR.U_extend: FR.artifact_extension_user,
                    FR.U_structure: FR.artifact_structure_user}
    for claim, artifact in user_sources.items():
        source = json.loads(artifacts[artifact], object_pairs_hook=base.unique_keys)
        require(len(source["messages"]) == 1, "user source coverage differs")
        row = source["messages"][0]
        require(row["role"] == "user" and row["authority"] == "USER_PRIMARY", "user attribution mismatch")
        require(graph.value(claim, DCTERMS.source) == artifact
                and str(graph.value(claim, RV.recordKey)) == row["id"]
                and str(graph.value(claim, RV.text)) == row["verbatim"]
                and sha(row["verbatim"].encode()) == row["sha256"], "user text provenance changed")
    require(set(graph.subjects(RDF.type, RV.UserClaim)) == set(user_sources), "unexpected new user claim")
    require(set(graph.objects(FR.graph, RV.sourceClaim)) == {
        FR.U_request, FR.U_extend, FR.U_structure, PH.C_mission, PH.C_resource_purpose, EX.C_autonomy,
        EX.C_population, EX.C_operation, EX.C_competition}, "user source scope changed")

    statements = set(graph.subjects(RDF.type, RV.Statement))
    report = artifacts[FR.artifact_report].decode("utf-8")
    markers = []
    for node in statements | set(graph.subjects(RDF.type, RV.Experiment)):
        marker = str(graph.value(node, RV.marker))
        require(marker == "[" + str(node).removeprefix(str(FR)) + "]"
                and report.count(marker) == 1, "report marker missing, mismatched or duplicated")
        markers.append(marker)
    require(len(markers) == len(set(markers)), "duplicate report marker")
    allowed_premises = statements | observations | set(graph.objects(FR.graph, RV.sourceClaim))
    for claim in statements:
        require(set(graph.objects(claim, RV.premise)) <= allowed_premises, "invalid premise kind")
        if str(graph.value(claim, RV.kind)) in {"OBJECTION", "ALTERNATIVE"}:
            require(any(graph.objects(claim, RV.challenges)), "missing challenged claim")
    for experiment in graph.subjects(RDF.type, RV.Experiment):
        require(any(graph.subjects(RV.testedBy, experiment)), "experiment detached from argument")
    # Only inference-premise dependencies are a DAG. Objections may point back.
    visiting, visited = set(), set()
    def visit(node):
        require(node not in visiting, "circular inference presented as evidence")
        if node in visited:
            return
        visiting.add(node)
        for premise in graph.objects(node, RV.premise):
            if premise in statements:
                visit(premise)
        visiting.remove(node)
        visited.add(node)
    for claim in statements:
        visit(claim)

    allowed_targets = {PH.foundation} | set(graph.subjects(RDF.type, EV.ComponentSpec))
    mapping_keys = set()
    for mapping in graph.subjects(RDF.type, RV.MappingProposal):
        targets = set(graph.objects(mapping, RV.targets))
        require(bool(targets) and targets <= allowed_targets, "mapping target is not an owner entity")
        source = graph.value(mapping, DCTERMS.source)
        key = (source, graph.value(mapping, RV.role))
        require(key not in mapping_keys, "duplicate source-role mapping")
        mapping_keys.add(key)
        tests = set()
        for argument in graph.objects(mapping, RV.justifiedBy):
            require(str(graph.value(argument, RV.kind)) == "ARGUMENT"
                    and (argument, RV.premise, source) in graph, "mapping rationale has no source premise")
            tests.update(graph.objects(argument, RV.testedBy))
        require(bool(tests) and tests == set(graph.objects(mapping, RV.evaluatedBy)),
                "mapping tests detached from rationale")
    require(render_mappings(graph) in report, "mapping report differs from graph")


def render_mappings(graph):
    """Deterministic report fragment, using existing entity IDs and observed URLs."""
    def compact(term):
        for prefix, namespace in [("fr", FR), ("ex", EX), ("ph", PH)]:
            if str(term).startswith(str(namespace)):
                return prefix + ":" + str(term)[len(str(namespace)):]
        raise ValueError(f"unrecognized mapping view endpoint: {term}")
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    def refs(subject, predicate):
        return ", ".join("`" + compact(term) + "`" for term in sorted(graph.objects(subject, predicate), key=str))
    lines = ["<!-- rationale-mappings:begin -->", "",
             "| 적용 연결 | 출처 관측 | 기존 대상 ID | 논증 → 검증 계획 | 적용 한계 |",
             "|---|---|---|---|---|"]
    for mapping in sorted(graph.subjects(RDF.type, RV.MappingProposal), key=str):
        source = graph.value(mapping, DCTERMS.source)
        url = graph.value(source, DCTERMS.source)
        lines.append("| " + " | ".join([
            f"`{compact(mapping)}` · {cell(graph.value(mapping, RV.text))}",
            f"[{compact(source)}]({url})",
            refs(mapping, RV.targets),
            refs(mapping, RV.justifiedBy) + " → " + refs(mapping, RV.evaluatedBy),
            cell(graph.value(mapping, RV.boundary)),
        ]) + " |")
    lines.extend(["", "<!-- rationale-mappings:end -->"])
    return "\n".join(lines)


def competency_questions(graph):
    spec = read(HERE / "foundation-rationale-queries.json")
    header = "\n".join(f"PREFIX {k}: <{v}>" for k, v in spec["prefixes"].items())
    def expand(value):
        prefix, sep, tail = value.partition(":")
        return spec["prefixes"][prefix] + tail if sep and prefix in spec["prefixes"] else value
    seen = set()
    for q in spec["questions"]:
        require(q["id"] not in seen, "duplicate competency question")
        seen.add(q["id"])
        result = graph.query(header + "\n" + q["query"])
        require([str(v) for v in result.vars] == q["columns"], "query columns changed")
        actual = {tuple(str(x) for x in row) for row in result}
        expected = {tuple(expand(x) for x in row) for row in q["expected"]}
        require(actual == expected, f"CQ {q['id']}: expected {expected}; got {actual}")
    return len(seen)


def negative_checks(documents, graph, shapes, vocab):
    cases = [
        (FR.A1, RV.authorityClass, Literal("USER_PRIMARY")),
        (FR.A5, RV.status, Literal("RATIFIED")),
        (FR.T1, RV.status, Literal("PASS")),
        (FR.graph, RV.normativeEffect, Literal(True)),
        (FR.graph, RV.executionEffect, Literal(True)),
        (FR.A6, PROV.wasAttributedTo, base.SP.proposer),
        (FR.S_ethereum, RV.mode, Literal("VERIFIED_OUTCOME")),
        (FR.S_erc8004, RV.sourceStatus, Literal("FINAL")),
        (FR.M_a2a, RV.status, Literal("DEPLOYED")),
        (FR.M_ap2, RV.authorityClass, Literal("USER_PRIMARY")),
        (FR.M_ostrom, RV.role, Literal("UNRESTRICTED_CONTROL")),
    ]
    for subject, predicate, obj in cases:
        bad = copy.deepcopy(graph)
        bad.set((subject, predicate, obj))
        ok, report, message = validate(bad, shacl_graph=shapes)
        caught = any(report.value(r, SH.focusNode) == subject and report.value(r, SH.resultPath) == predicate
                     for r in report.subjects(RDF.type, SH.ValidationResult))
        require(not ok and caught, f"missed negative constraint: {predicate}\n{message}")
    mutations = [
        lambda g: g.set((FR.artifact_report, base.MHV.sha256, Literal("0" * 64))),
        lambda g: g.set((FR.U_request, RV.text, Literal("AI paraphrase of user"))),
        lambda g: g.set((FR.U_extend, DCTERMS.source, FR.artifact_user)),
        lambda g: g.set((FR.S_license, RV.text, Literal("voluntary donation only"))),
        lambda g: g.set((FR.S_ethereum, DCTERMS.source, URIRef("https://example.invalid"))),
        lambda g: g.set((FR.S_a2a, RV.revision, Literal("latest"))),
        lambda g: g.set((FR.S_ap2, RV.revision, Literal("invented-fixed-version"))),
        lambda g: g.remove((FR.S_ostrom, RV.limitation, None)),
        lambda g: g.set((FR.artifact_charter, base.MHV.path, Literal("../outside"))),
        lambda g: g.add((FR.A1, OWL.sameAs, PH.foundation)),
        lambda g: g.add((FR.A2, RV.premise, FR.A1)),
        lambda g: g.add((FR.A1, RV.premise, FR.missing)),
        lambda g: g.add((FR.A1, RV.premise, FR.artifact_user)),
        lambda g: g.add((FR.A1, RV.unregistered, FR.A2)),
        lambda g: g.set((FR.A5, RV.marker, Literal("[A1]"))),
        lambda g: g.remove((FR.O1, RV.challenges, None)),
        lambda g: g.set((FR.M_ap2, RV.targets, FR.S_ap2)),
        lambda g: g.set((FR.M_a2a, RV.justifiedBy, FR.A12)),
        lambda g: g.set((FR.M_a2a, RV.evaluatedBy, FR.T5)),
        lambda g: g.set((FR.M_ap2, RV.boundary, Literal("payment grants compute root access"))),
    ]
    for mutate in mutations:
        bad = copy.deepcopy(graph)
        mutate(bad)
        try:
            check_integrity(bad, vocab)
        except (ValueError, KeyError):
            pass
        else:
            raise ValueError("negative integrity mutation accepted")
    serializations = [
        lambda d: d[-1]["@graph"].append(copy.deepcopy(d[-1]["@graph"][0])),
        lambda d: d[-1].__setitem__("@context", "https://example.invalid/context"),
        lambda d: d[-1]["@graph"][0].__setitem__("unknownKey", "silently ignored"),
        lambda d: d[-1]["@graph"][0].__setitem__("@id", "ph:unowned-new-id"),
    ]
    for mutate in serializations:
        bad = copy.deepcopy(documents)
        mutate(bad)
        try:
            check_documents(bad)
        except ValueError:
            pass
        else:
            raise ValueError("negative document mutation accepted")
    bad = copy.deepcopy(graph)
    bad.remove((FR.O1, RV.challenges, FR.A3))
    try:
        competency_questions(bad)
    except ValueError:
        pass
    else:
        raise ValueError("CQ missed lost counterargument")
    return len(cases) + len(mutations) + len(serializations) + 1


def main():
    documents, graph, shapes, vocab = load()
    check_integrity(graph, vocab)
    ok, _, report = validate(graph, shacl_graph=shapes, meta_shacl=True)
    require(ok, report)
    questions = competency_questions(graph)
    negatives = negative_checks(documents, graph, shapes, vocab)
    print(f"foundation rationale: SHACL/meta-SHACL PASS; {questions} CQs; {negatives} negative cases; "
          "source/report integrity PASS; institutional experiments NOT_RUN; no ratification")


if __name__ == "__main__":
    main()
