#!/usr/bin/env python3
"""Offline daily record validation. Use --write-view to regenerate README.md."""
import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from rdflib.namespace import DCTERMS, OWL, PROV, SH

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = "https://github.com/gj3447/metahumotonic-foundation/"
REC = Namespace(BASE + "records/2026-10-05#")
SV = Namespace(BASE + "records/2026-10-05/vocab#")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def integrity(graph, vocab):
    subjects = set(graph.subjects())
    external = {RDF.type, RDFS.label, PROV.wasAttributedTo, PROV.hadMember, DCTERMS.references}
    for subject, predicate, obj in graph:
        require(str(subject).startswith(str(REC)), "foreign subject redefined")
        require(predicate in external or (predicate, RDF.type, RDF.Property) in vocab, "unregistered predicate")
        if predicate == RDF.type:
            require(obj in {PROV.Agent, PROV.Person, PROV.SoftwareAgent, PROV.Bundle} or
                    (obj, RDF.type, RDFS.Class) in vocab, "unregistered class")
        for domain in vocab.objects(predicate, RDFS.domain):
            require(domain == RDFS.Resource or (subject, RDF.type, domain) in graph, "wrong domain")
        for target in vocab.objects(predicate, RDFS.range):
            if str(target).startswith(str(XSD)):
                require(isinstance(obj, Literal) and (obj.datatype == target or
                        (target == XSD.string and obj.datatype is None)), "wrong literal datatype")
            else:
                require((obj, RDF.type, target) in graph, "wrong range")
        if isinstance(obj, URIRef) and str(obj).startswith(str(REC)):
            require(obj in subjects, "dangling endpoint")
    require(set(graph.objects(REC.record, PROV.hadMember)) == subjects - {REC.record}, "incomplete record membership")

    blobs = {}
    for node in graph.subjects(RDF.type, SV.Artifact):
        if str(graph.value(node, SV.kind)) == "PRIVATE_REFERENCE":
            require(graph.value(node, SV.path) is None and not list(graph.objects(node, DCTERMS.references)),
                    "private location exported")
            continue
        relative = str(graph.value(node, SV.path))
        path = (ROOT / relative).resolve()
        require(not Path(relative).is_absolute() and path.is_relative_to(ROOT), "path escapes repository")
        revision = graph.value(node, SV.revision)
        blob = subprocess.check_output(["git", "show", f"{revision}:{relative}"], cwd=ROOT) if revision else path.read_bytes()
        require(digest(blob) == str(graph.value(node, SV.sha256)), f"artifact digest mismatch: {relative}")
        blobs[node] = blob
        for ref in graph.objects(node, DCTERMS.references):
            artifact = json.loads(blob, object_pairs_hook=unique)
            indexed = Graph().parse(data=json.dumps(artifact), format="json-ld")
            require(ref in set(indexed.subjects()), "reference not present in pinned graph")

    sources = json.loads(blobs[REC.artifact_sources], object_pairs_hook=unique)
    messages = {row["id"]: row for row in sources["messages"]}
    require(len(messages) == len(sources["messages"]), "duplicate source ID")
    require(set(graph.subjects(RDF.type, SV.UserSource)) == {REC["u_" + k] for k in messages}, "source coverage")
    for key, source in messages.items():
        node = REC["u_" + key]
        require(source["role"] == "user" and source["authority"] == "USER_PRIMARY" and source["event_time"] is None,
                "source authority or unknown event time changed")
        require(str(graph.value(node, SV.text)) == source["verbatim"], "user text changed")
        require(str(graph.value(node, SV.sourceKey)) == key, "source key changed")
        require(set(graph.objects(node, SV.sourceArtifact)) == {REC.artifact_sources}, "wrong source artifact")
        require(digest(source["verbatim"].encode()) == source["sha256"] == str(graph.value(node, SV.sha256)), "utterance hash mismatch")

    visiting, visited = set(), set()
    def visit(node):
        require(node not in visiting, "cyclic dependency")
        if node in visited:
            return
        visiting.add(node)
        for dep in graph.objects(node, SV.dependsOn):
            visit(dep)
        visiting.remove(node)
        visited.add(node)
    for node in graph.subjects(RDF.type, SV.WorkItem):
        visit(node)


PREFIX = f"PREFIX sv: <{SV}> PREFIX rec: <{REC}> PREFIX prov: <{PROV}> PREFIX dcterms: <{DCTERMS}> "
QUESTIONS = [
    ("remaining work", 'SELECT ?s WHERE { ?s a sv:WorkItem ; sv:state "PENDING" }',
     {"w_public_repo", "w_shared_kg", "w_live_coin", "w_operator_eval"}),
    ("local implementation", 'SELECT ?s WHERE { ?s a sv:WorkItem ; sv:state "LOCAL_PROTOTYPE" }', {"w_compute"}),
    ("publication correction source", 'SELECT ?s WHERE { rec:c_publication sv:evidence ?s }', {"u_public_request", "u_public_correction"}),
    ("operator source", 'SELECT ?s WHERE { rec:c_operator sv:evidence ?s }', {"u_operator"}),
    ("normative position", 'SELECT ?s WHERE { ?s a sv:SummaryClaim ; sv:kind "NORMATIVE_POSITION" }', {"c_ideal"}),
    ("unverified efficiency", 'SELECT ?s WHERE { ?s a sv:SummaryClaim ; sv:kind "UNTESTED_HYPOTHESIS" }', {"c_efficiency"}),
    ("private record remains private", 'SELECT ?s WHERE { ?s a sv:Artifact ; sv:visibility "PRIVATE" }', {"artifact_operator"}),
    ("live coin prerequisite", 'SELECT ?s WHERE { rec:w_live_coin sv:dependsOn ?s }', {"w_compute"}),
]


def queries(graph):
    for label, query, expected in QUESTIONS:
        got = {str(row[0]) for row in graph.query(PREFIX + query)}
        require(got == {str(REC[x]) for x in expected}, f"CQ {label}: {got}")


def negative_checks(graph, vocab, shapes):
    cases = [
        (REC.c_operator, SV.authority, Literal("USER_PRIMARY")),
        (REC.c_efficiency, SV.kind, Literal("PROVEN_OPTIMAL")),
        (REC.record, SV.normativeEffect, Literal(True)),
        (REC.artifact_operator, SV.visibility, Literal("PUBLIC")),
        (REC.w_public_repo, SV.state, Literal("DEPLOYED")),
        (REC.c_operator, PROV.wasAttributedTo, REC.user),
    ]
    for node, predicate, value in cases:
        bad = copy.deepcopy(graph)
        bad.set((node, predicate, value))
        ok, result, _ = validate(bad, shacl_graph=shapes)
        require(not ok and any(result.value(r, SH.focusNode) == node
                for r in result.subjects(RDF.type, SH.ValidationResult)), "negative shape escaped")
    mutations = [
        lambda g: g.set((REC.u_operator, SV.text, Literal("AI rewrite"))),
        lambda g: g.set((REC.artifact_sources, SV.sha256, Literal("0" * 64))),
        lambda g: g.add((REC.c_operator, OWL.sameAs, REC.c_mission)),
        lambda g: g.set((REC.c_operator, SV.evidence, REC.missing)),
        lambda g: g.set((REC.c_operator, SV.evidence, REC.w_operator)),
        lambda g: g.add((REC.w_operator, SV.dependsOn, REC.w_shared_kg)),
    ]
    for change in mutations:
        bad = copy.deepcopy(graph)
        change(bad)
        try:
            integrity(bad, vocab)
        except ValueError:
            continue
        raise ValueError("negative integrity case escaped")
    return len(cases) + len(mutations)


def render(doc):
    nodes = {n["@id"]: n for n in doc["@graph"]}
    cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
    lines = ["# 2026-10-05 대화와 구현 마감 기록", "",
             "> SECONDARY_AI 정리. 정본은 [session.jsonld](session.jsonld), 사용자 원문은 [user-sources.json](user-sources.json).", "",
             "오늘 확인한 대화 맥락과 작업 상태를 기록한다. 앞선 대화도 출처로 포함하며, 발화의 발생 날짜·시각을 오늘로 추정하지 않는다. 사용자 철학, AI 해석, 로컬 구현, 실제 배포는 구분한다.", "",
             "## 연결한 내용", "", "| 내용 | 기록한 뜻 | 직접 출처 |", "|---|---|---|"]
    for node in nodes.values():
        if node["@type"] == "sv:SummaryClaim":
            lines.append(f"| {cell(node['label'])} | {cell(node['text'])} | {', '.join(node['evidence'])} |")
    lines += ["", "## 완료 범위와 이어 할 일", "", "| 작업 | 현재 상태 | 확인한 범위 | 다음 행동 |", "|---|---|---|---|"]
    for node in nodes.values():
        if node["@type"] == "sv:WorkItem":
            lines.append(f"| {cell(node['label'])} | `{node['state']}` | {cell(node['text'])} | {cell(node['nextAction'])} |")
    lines += ["", "## 산출물과 근거", ""]
    for node in nodes.values():
        if node["@type"] != "sv:Artifact":
            continue
        if node["kind"] == "PRIVATE_REFERENCE":
            lines.append(f"- {node['label']}: 관측 커밋 `{node['revision'][:7]}`. 내부 위치·내용은 원래 비공개 저장소에 유지한다.")
        else:
            link = "../../" + node["path"]
            lines.append(f"- [{node['label']}]({link})" + (f" — 바이트 고정 커밋 `{node['revision'][:7]}`." if node.get("revision") else " — 이 기록의 입력 스냅샷."))
    lines += ["", "공개 범위는 별도 소개 저장소에 대한 사용자 요청을 따르며 dashboard를 공개로 전환하지 않는다. 국부론의 분업을 AI 지시 복종의 최적성을 실증한 결과로 취급하지 않는다.", "",
              "## 그래프 계약과 검증", "",
              "JSON-LD 1.1 직렬화와 PROV-O 출처 연결을 사용한다. [어휘](session-vocab.ttl)에 관계 방향·domain/range를, [SHACL](session.shapes.ttl)에 타입·필수 속성·카디널리티를 둔다. 기존 재단 그래프의 IRI를 참조하며 조직의 법적 동일성이나 공유 KG의 수학적 Operator 개념과 같다고 선언하지 않는다.", "",
              "```mermaid", "flowchart LR", '  U["사용자 원문"] --> C["AI 요약·해석"]', '  C --> W["작업 상태·남은 일"]', '  W --> A["커밋·출처 파일"]', '  W --> N["후속 작업"]', "```", "",
              "```sh", "python3 -m venv .venv", ".venv/bin/pip install -r graph/requirements.txt", ".venv/bin/python records/2026-10-05/check.py", "```", "",
              "검사기는 JSON 키·UID 중복, 참조 대상, 원문/파일/커밋 해시, 관계 타입, 작업 의존성, SHACL·meta-SHACL, 기대 주체가 명시된 SPARQL 질문 8개와 고의 위반 12개를 검사한다. `--write-view`로 이 뷰를 재생성한다. 실행 시 네트워크나 공유 KG에 쓰지 않는다.", "",
              "전체 구현 검증 명령은 `python graph/check.py`, `python -m unittest discover -s economy -t .`, `python -m unittest discover -s market -t .`, `python -m unittest discover -s metahumocoin -t .`다. 그래프 검사 통과는 실제 AI 안전성·경제 성립·완전 자율성의 검증을 뜻하지 않는다.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-view", action="store_true")
    args = parser.parse_args()
    doc = read(HERE / "session.jsonld")
    ids = [n["@id"] for n in doc["@graph"]]
    require(len(ids) == len(set(ids)), "duplicate node ID")
    require(doc["@context"]["rec"] == str(REC), "namespace changed")
    graph = Graph().parse(data=json.dumps(doc), format="json-ld")
    vocab = Graph().parse(HERE / "session-vocab.ttl")
    shapes = Graph().parse(HERE / "session.shapes.ttl")
    integrity(graph, vocab)
    ok, _, report = validate(graph, shacl_graph=shapes, meta_shacl=True)
    require(ok, report)
    queries(graph)
    count = negative_checks(graph, vocab, shapes)
    view = render(doc)
    if args.write_view:
        (HERE / "README.md").write_text(view, encoding="utf-8")
    require((HERE / "README.md").read_text(encoding="utf-8") == view, "README drift; use --write-view")
    print(f"daily record: SHACL/meta-SHACL PASS; {len(QUESTIONS)} exact CQs; {count} negative cases; source/commit hashes and generated view PASS ({len(graph)} triples)")


if __name__ == "__main__":
    main()
