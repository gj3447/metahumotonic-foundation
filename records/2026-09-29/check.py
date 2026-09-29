#!/usr/bin/env python3
"""2026-09-29 세션 기록 검증기.

1. SHACL 1.0: session.jsonld 가 session.shapes.ttl 을 만족해야 한다 (positive).
2. SHACL 1.0: 일부러 망가뜨린 사본은 실패해야 한다 (negative).
3. SPARQL 1.1 역량 질문(CQ): 개수가 아니라 기대한 subject 를 돌려줘야 한다.
4. 파일 해시: 기록된 sha256 이 커밋 9c40207 의 파일 바이트와 같아야 한다.

  python records/2026-09-29/check.py      # pyshacl, rdflib 필요
"""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import Graph

HERE = Path(__file__).parent
REPO = HERE.parents[1]
DATA = json.loads((HERE / "session.jsonld").read_text())
SHAPES = Graph().parse(HERE / "session.shapes.ttl")
REC = "https://github.com/gj3447/metahumotonic-foundation/records/2026-09-29#"
PFX = """PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX mhv: <https://github.com/gj3447/metahumotonic-foundation/vocab#>
"""
failures = []


def load(doc):
    return Graph().parse(data=json.dumps(doc), format="json-ld")


def shacl(g):
    ok, _, text = validate(g, shacl_graph=SHAPES)
    return ok, text


g = load(DATA)
ok, text = shacl(g)
print(f"[1] SHACL positive: {'PASS' if ok else 'FAIL'}  triples={len(g)}")
if not ok:
    failures.append("positive SHACL")
    print(text)

bad = copy.deepcopy(DATA)
for node in bad["@graph"]:
    if node["@id"] == "rec:s03":
        node.pop("associatedWith")
        node.pop("comment")
        node.pop("summaryAuthority")
    if node["@id"] == "rec:std_rdf12":
        node["adoption"] = "ADOPTED"
    if node["@id"] == "rec:d1":
        node["status"] = "RESOLVED"
    if node["@id"] == "rec:commit_dfd0a59":
        node.pop("parentCommit")
    if node["@id"] == "rec:charter":
        node.pop("sha256")
bad["@graph"] = [n for n in bad["@graph"] if n["@id"] != "rec:c1"]
ok_bad, text_bad = shacl(load(bad))
expected = ["wasAssociatedWith", "summaryAuthority", "NonDoneExplainedShape", "NoDraftAdoptionShape",
            "ResolvedDecisionShape", "GitCommitShape", "CommittedFileShape", "SupersededHasCorrectionShape"]
missing = [m for m in expected if m not in text_bad]
print(f"[2] SHACL negative: {'PASS' if not ok_bad and not missing else 'FAIL'}  "
      f"({len(expected)} injected violations, caught={len(expected) - len(missing)})")
if ok_bad or missing:
    failures.append(f"negative SHACL missing {missing}")

CQS = {
    "CQ1 거절·중단된 단계는?": (
        "SELECT ?s WHERE { ?s a mhv:Step ; mhv:outcome ?o FILTER(?o IN (mhv:DECLINED, mhv:STOPPED)) }",
        {"s03", "s04", "s05", "s08"}),
    "CQ2 커밋 9c40207 을 만든 단계는?": (
        "SELECT ?s WHERE { ?s prov:generated ?c . ?c a mhv:GitCommit ; mhv:gitCommit ?h FILTER(STRSTARTS(?h, '9c40207')) }",
        {"s09"}),
    "CQ3 초안이라 채택하지 않고 추적만 하는 표준은?": (
        "SELECT ?s WHERE { ?s a mhv:Standard ; mhv:adoption mhv:TRACKED }",
        {"std_rdf12", "std_sparql12", "std_shacl12"}),
    "CQ4 커밋 체인 (bb34100 에서 부모를 따라)": (
        "SELECT ?s WHERE { ?h a mhv:GitCommit ; mhv:gitCommit ?x FILTER(STRSTARTS(?x, 'bb34100')) . ?h mhv:parentCommit* ?s }",
        {"commit_bb34100", "commit_dfd0a59", "commit_230eecb", "commit_9c40207", "commit_738dd7a"}),
    "CQ5 제거된(무효화된) 파일은?": (
        "SELECT ?s WHERE { ?a prov:invalidated ?s }",
        {"partial_license_1", "partial_license_2", "partial_license_3"}),
    "CQ6 정정된 주장과 그 정정은?": (
        "SELECT ?s WHERE { ?c a mhv:Correction ; mhv:supersedes ?a . ?a mhv:status mhv:SUPERSEDED . BIND(?c AS ?s) }",
        {"c1"}),
    "CQ7 이 세션이 만들지 않은 커밋은?": (
        "SELECT ?s WHERE { ?s a mhv:GitCommit ; prov:wasAttributedTo ?p . ?p a prov:Person . "
        "FILTER NOT EXISTS { ?x prov:generated ?s } }",
        {"commit_230eecb"}),
    "CQ8 해결된 결정과 해결한 단계는?": (
        "SELECT ?s WHERE { ?d mhv:status mhv:RESOLVED ; mhv:resolvedBy ?st . "
        "BIND(CONCAT(STRAFTER(STR(?d), '#'), '->', STRAFTER(STR(?st), '#')) AS ?s) }",
        {"d3->s12", "d4->s13"}),
    "CQ9 사람 결정을 기다리는 항목은?": (
        "SELECT ?s WHERE { ?s a mhv:OpenDecision ; mhv:status mhv:PENDING_HUMAN }",
        {"d1", "d2", "d5"}),
}
for name, (q, want) in CQS.items():
    got = {str(r.s).removeprefix(REC) for r in g.query(PFX + q)}
    status = "PASS" if got == want else "FAIL"
    print(f"[3] {name}: {status}  {sorted(got)}")
    if got != want:
        failures.append(f"{name}: want {sorted(want)} got {sorted(got)}")

for node in DATA["@graph"]:
    if "sha256" in node and "gitCommit" in node:
        blob = subprocess.run(["git", "-C", str(REPO), "show", f"{node['gitCommit']}:{node['path']}"],
                              capture_output=True, check=True).stdout
        actual = hashlib.sha256(blob).hexdigest()
        status = "PASS" if actual == node["sha256"] else "FAIL"
        print(f"[4] sha256 {node['path']}@{node['gitCommit'][:7]}: {status}")
        if status == "FAIL":
            failures.append(f"hash {node['path']}")

# 커밋 체인이 실제 git 이력과 같은지
chain = {n["@id"]: n for n in DATA["@graph"] if "mhv:GitCommit" in n.get("@type", [])}
for cid, n in chain.items():
    if n.get("parentCommit") and n["status"] == "PUSHED":
        want = chain[n["parentCommit"]]["gitCommit"]
        got = subprocess.run(["git", "-C", str(REPO), "rev-parse", f"{n['gitCommit']}^"],
                             capture_output=True, text=True, check=True).stdout.strip()
        status = "PASS" if got.startswith(want) else "FAIL"
        print(f"[5] parent {n['gitCommit'][:7]} -> {want[:7]}: {status}")
        if status == "FAIL":
            failures.append(f"parent of {n['gitCommit'][:7]}")

print("\nOK" if not failures else "\nFAIL\n  " + "\n  ".join(failures))
sys.exit(1 if failures else 0)
