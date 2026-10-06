#!/usr/bin/env python3
"""Validate agent priority provenance, exact simulation replay and RDF queries."""
import copy
import hashlib
import json
from pathlib import Path
import sys

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from rdflib.namespace import DCTERMS, PROV, SH

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from economy.agent_native import suite
from economy.artifacts import canonical

BASE = "https://github.com/gj3447/metahumotonic-foundation/"
AN = Namespace(BASE + "graph/agent-native#")
AV = Namespace(BASE + "agent-native-vocab#")
PATHS = {"source": "records/2026-10-06/agent-native-source.json",
         "research": "records/2026-10-06/agent-native-research.json",
         "suite": "records/2026-10-06/agent-native-suite.json", "report": "AGENT-ECONOMY.md",
         "ecosystem": "graph/ecosystem.jsonld", "philosophy": "graph/philosophy.jsonld",
         "spirit": "graph/spirit.jsonld", "code": "economy/agent_native.py"}
TARGETS = {"principal": {"agent", "hswm"}, "cycle": {"agent", "chu", "response", "asset"},
           "evaluation": {"agent", "response"}}
REFERENCES = {"principal": {"a2a"}, "cycle": {"golem", "truebit"}, "evaluation": {"melting"}}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, "duplicate JSON key")
        out[key] = value
    return out


def read(path):
    return json.loads((ROOT / path).read_text(), object_pairs_hook=unique)


def document_integrity(doc, vocab):
    require(set(doc) == {"@context", "@graph"} and isinstance(doc["@context"], dict), "inline context required")
    ctx = doc["@context"]
    require(ctx.get("an") == str(AN) and ctx.get("av") == str(AV) and "@import" not in ctx, "namespace changed")
    ids = [n["@id"] for n in doc["@graph"]]
    require(len(ids) == len(set(ids)), "duplicate node ID")
    for node in doc["@graph"]:
        require(node["@id"].startswith("an:"), "foreign writer scope")
        require(set(node) <= {"@id", "@type"} | set(ctx), "unknown JSON key")
        require("@context" not in node, "nested context")
    for alias, value in ctx.items():
        if alias.startswith("@") or alias in {"an", "av", "prov", "rdfs", "dcterms", "xsd"}:
            continue
        predicate = value.get("@id") if isinstance(value, dict) else value
        require(isinstance(predicate, str) and ":" in predicate, "invalid predicate mapping")
        prefix, local = predicate.split(":", 1)
        require(prefix in ctx, "unknown context prefix")
        if prefix == "av":
            require((AV[local], RDF.type, RDF.Property) in vocab, "unknown context predicate")


def integrity(graph, vocab):
    subjects = set(graph.subjects())
    standard = {RDF.type, RDFS.label, DCTERMS.source, DCTERMS.references, DCTERMS.hasVersion,
                PROV.wasAttributedTo, PROV.wasDerivedFrom, PROV.wasAssociatedWith, PROV.used, PROV.hadMember}
    external = set()
    blobs = {}
    require(set(graph.subjects(RDF.type, AV.Artifact)) == {AN['artifact_' + k] for k in PATHS}, "artifact coverage")
    for key, relative in PATHS.items():
        node = AN['artifact_' + key]
        require(str(graph.value(node, AV.path)) == relative, "artifact path changed")
        raw = (ROOT / relative).read_bytes()
        require(str(graph.value(node, AV.sha256)) == hashlib.sha256(raw).hexdigest(), "artifact digest mismatch")
        blobs[key] = raw
        if key in {"ecosystem", "philosophy", "spirit"}:
            external.update(Graph().parse(data=raw.decode(), format="json-ld").subjects())
    for subject, predicate, obj in graph:
        require(str(subject).startswith(str(AN)), "foreign subject")
        require(predicate in standard or (predicate, RDF.type, RDF.Property) in vocab, "unregistered predicate")
        if predicate == RDF.type:
            require(obj in {PROV.Bundle, PROV.Entity, PROV.Activity, PROV.SoftwareAgent} or
                    (obj, RDF.type, RDFS.Class) in vocab, "unregistered class")
        for domain in vocab.objects(predicate, RDFS.domain):
            require(domain == RDFS.Resource or (subject, RDF.type, domain) in graph, "wrong predicate domain")
        for range_ in vocab.objects(predicate, RDFS.range):
            if str(range_).startswith(str(XSD)):
                require(isinstance(obj, Literal) and (obj.datatype == range_ or
                        (range_ == XSD.string and obj.datatype is None)), "wrong value datatype")
        if isinstance(obj, URIRef) and str(obj).startswith(BASE):
            require(obj in subjects or obj in external or predicate == RDF.type, "dangling endpoint")
    require(set(graph.objects(AN.graph, PROV.hadMember)) == subjects - {AN.graph}, "bundle membership")
    user = json.loads(blobs["source"], object_pairs_hook=unique)
    require(user["role"] == "user" and user["authority"] == "USER_PRIMARY" and user["event_time"] is None,
            "user source authority/time changed")
    require(user["sha256"] == hashlib.sha256(user["verbatim"].encode()).hexdigest(), "source text hash")
    require(str(graph.value(AN.priority, AV.text)) == user["verbatim"], "user wording changed")
    require(set(graph.subjects(RDF.type, AV.UserClaim)) == {AN.priority}, "user claim coverage")
    require(set(graph.subjects(RDF.type, AV.Design)) == {AN[x] for x in TARGETS}, "design coverage")
    for key, targets in TARGETS.items():
        require(set(graph.objects(AN[key], AV.targets)) == {URIRef(BASE+'graph/ecosystem#'+x) for x in targets}, "design target mapping")
        require(set(graph.objects(AN[key], DCTERMS.references)) == {AN['obs_'+x] for x in REFERENCES[key]}, "design evidence mapping")
    catalog = json.loads(blobs["research"], object_pairs_hook=unique)
    require(catalog["full_text_archived"] is False and catalog["remote_content_sha256"] is None, "archival scope changed")
    rows = catalog["sources"]
    require(len({r['id'] for r in rows}) == len(rows), "duplicate source observation")
    require(set(graph.subjects(RDF.type, AV.Observation)) == {AN['obs_'+r['id']] for r in rows}, "observation coverage")
    for row in rows:
        node = AN['obs_'+row['id']]
        for predicate, key in [(RDFS.label,'title'), (DCTERMS.source,'url'), (DCTERMS.hasVersion,'revision'),
                               (AV.section,'section'), (AV.text,'text'), (AV.limitation,'limitation')]:
            require(str(graph.value(node, predicate)) == row[key], "research observation differs from source catalog")
        require(str(graph.value(node, AV.recordedOn)) == catalog['observed_on'], "observation date")
    evidence = json.loads(blobs["suite"], object_pairs_hook=unique)
    require(set(graph.subjects(RDF.type, AV.Run)) == {AN['run_'+r['run_sha256']] for r in evidence['runs']}, "run identity/coverage")
    for row in evidence['runs']:
        node = AN['run_'+row['run_sha256']]
        require(str(graph.value(node, AV.scenario)) == row['scenario'] and
                int(graph.value(node, AV.seed)) == row['config']['seed'], "scenario/seed mismatch")
        require(str(graph.value(node, AV.sha256)) == row['run_sha256'], "run digest mismatch")
        require(set(graph.objects(node, PROV.used)) == {AN.evaluation, AN.cycle, AN.artifact_code}, "execution design/source mapping")
        for predicate, key in [(AV.completed,'completed'), (AV.failed,'failed'), (AV.postBootstrap,'post_bootstrap_completed'),
                               (AV.installedCapacity,'final_installed_capacity'), (AV.sharedCapacity,'final_offered_capacity')]:
            require(int(graph.value(node, predicate)) == row['summary'][key], "run metric differs from evidence")
        require(str(graph.value(node, AV.recordedOn)) == user['recorded_on'], "run recording date changed")
    return evidence


def queries(graph, evidence):
    prefix = f'PREFIX an: <{AN}> PREFIX av: <{AV}> PREFIX prov: <{PROV}> '
    questions = [
        ('user priority', 'SELECT ?s WHERE { ?s a av:UserClaim; av:authority "USER_PRIMARY" }', {(str(AN.priority),)}),
        ('proposal provenance', 'SELECT ?s WHERE { ?s a av:Design; prov:wasDerivedFrom an:priority }', {(str(AN[k]),) for k in TARGETS}),
        ('external observations', 'SELECT ?s WHERE { ?s a av:Observation; av:state "PARAPHRASE" }', {(str(AN['obs_'+k]),) for k in ['a2a','golem','truebit','melting']}),
        ('run outcomes', 'SELECT ?s ?scenario ?seed ?completed ?post ?capacity ?shared WHERE { ?s a av:Run; av:scenario ?scenario; av:seed ?seed; av:completed ?completed; av:postBootstrap ?post; av:installedCapacity ?capacity; av:sharedCapacity ?shared }',
         {(str(AN['run_'+r['run_sha256']]), r['scenario'], str(r['config']['seed']), str(r['summary']['completed']),
           str(r['summary']['post_bootstrap_completed']), str(r['summary']['final_installed_capacity']),
           str(r['summary']['final_offered_capacity'])) for r in evidence['runs']}),
        ('reuse existing agent identity', 'SELECT ?s WHERE { an:principal av:targets ?s }',
         {(BASE+'graph/ecosystem#agent',), (BASE+'graph/ecosystem#hswm',)}),
    ]
    for name, query, expected in questions:
        actual = {tuple(str(x) for x in row) for row in graph.query(prefix+query)}
        require(actual == expected, 'CQ mismatch: '+name)
    return len(questions)


def main():
    doc = read('graph/agent-native.jsonld')
    vocab = Graph().parse(ROOT/'graph/agent-native-vocab.ttl')
    shapes = Graph().parse(ROOT/'graph/agent-native.shapes.ttl')
    document_integrity(doc, vocab)
    graph = Graph().parse(data=json.dumps(doc), format='json-ld')
    evidence = integrity(graph, vocab)
    require(canonical(evidence) == canonical(suite()), 'suite policy/ledger replay mismatch')
    ok, _, report = validate(graph, shacl_graph=shapes, meta_shacl=True)
    require(ok, report)
    nqueries = queries(graph, evidence)
    first = AN['run_'+evidence['runs'][0]['run_sha256']]
    shape_cases = [(AN.priority, AV.authority, Literal('SECONDARY_AI')),
                   (AN.principal, AV.state, Literal('RATIFIED')),
                   (first, AV.state, Literal('PROVEN_SAFE')),
                   (AN.obs_a2a, AV.authority, Literal('EMPIRICALLY_VERIFIED'))]
    for node, pred, value in shape_cases:
        bad = copy.deepcopy(graph)
        bad.set((node, pred, value))
        ok, report, _ = validate(bad, shacl_graph=shapes)
        require(not ok and any(report.value(r, SH.focusNode) == node for r in report.subjects(RDF.type, SH.ValidationResult)), 'negative shape escaped')
    changes = [(AN.priority, AV.text, Literal('AI rewrite')),
               (AN.artifact_suite, AV.sha256, Literal('0'*64)),
               (AN.artifact_source, AV.path, Literal('../outside')),
               (AN.principal, AV.targets, AN.missing),
               (first, AV.completed, Literal(999)),
               (AN.obs_a2a, DCTERMS.source, URIRef('https://example.invalid'))]
    for node, pred, value in changes:
        bad = copy.deepcopy(graph)
        bad.set((node, pred, value))
        try:
            integrity(bad, vocab)
        except ValueError:
            continue
        raise ValueError('negative integrity escaped')
    for mutate in [lambda d: d['@graph'].append(copy.deepcopy(d['@graph'][0])),
                   lambda d: d['@graph'][0].__setitem__('unknown', 'silently dropped'),
                   lambda d: d.__setitem__('@context', 'https://example.invalid')]:
        bad = copy.deepcopy(doc)
        mutate(bad)
        try:
            document_integrity(bad, vocab)
        except ValueError:
            continue
        raise ValueError('negative serialization escaped')
    print(f'agent-native: SHACL/meta-SHACL PASS; {nqueries} exact CQs; 13 negative cases; 12 policy/ledger runs replayed; LOCAL_SIMULATION')


if __name__ == '__main__':
    main()
