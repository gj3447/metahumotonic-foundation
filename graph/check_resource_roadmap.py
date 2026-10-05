#!/usr/bin/env python3
"""Validate the local resource roadmap, pinned observations and generated view.

No resource registration, provisioning, authority change or model experiment is
performed. A finite replay of the existing scripted simulator verifies evidence.
"""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from rdflib.namespace import DCTERMS, SH

import check_philosophy as ph

HERE, REPO = ph.HERE, ph.REPO
RP = Namespace(ph.BASE + "graph/resource-roadmap#")
RPV = Namespace(ph.BASE + "resource-roadmap-vocab#")
PH, PHV, MHV, PROV = ph.PH, ph.PHV, ph.MHV, ph.PROV
DATA = HERE / "resource-roadmap.jsonld"
QUERIES = HERE / "resource-roadmap-queries.json"
VIEW = REPO / "RESOURCE-ROADMAP.md"
require = ph.require


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def load():
    documents, _, inherited_shapes, vocab = ph.load()
    documents.append(ph.base.read_document(DATA))
    ph.check_documents(documents)
    graph = ph.base.load_graph(documents)
    own_shapes = Graph().parse(HERE / "resource-roadmap.shapes.ttl")
    vocab.parse(HERE / "resource-roadmap-vocab.ttl")
    return documents, graph, inherited_shapes + own_shapes, own_shapes, vocab


def integrity(graph, vocab):
    subjects = set(graph.subjects())
    standard = {RDF.type, RDFS.label, RDFS.comment, DCTERMS.date, DCTERMS.subject,
                DCTERMS.references, PROV.wasAttributedTo, PROV.wasDerivedFrom,
                PROV.wasGeneratedBy, PROV.wasAssociatedWith, PROV.used}
    standard_types = {PROV.Entity, PROV.Activity}
    local = {s for s in subjects if str(s).startswith(str(RP))}
    for subject in local:
        for predicate, obj in graph.predicate_objects(subject):
            if predicate == RDF.type:
                require(obj in standard_types or (obj, RDF.type, RDFS.Class) in vocab,
                        f"unknown class: {obj}")
            if predicate not in standard:
                require((predicate, RDF.type, RDF.Property) in vocab,
                        f"unknown predicate: {predicate}")
            for domain in vocab.objects(predicate, RDFS.domain):
                require(domain == RDFS.Resource or (subject, RDF.type, domain) in graph,
                        f"wrong domain: {subject} {predicate}")
            for target in vocab.objects(predicate, RDFS.range):
                if target == RDFS.Resource:
                    require(isinstance(obj, URIRef), f"IRI required: {predicate}")
                elif str(target).startswith(str(XSD)) or target == RDF.JSON:
                    require(isinstance(obj, Literal) and
                            (obj.datatype == target or (target == XSD.string and obj.datatype is None)),
                            f"wrong datatype: {predicate}")
                else:
                    require((obj, RDF.type, target) in graph, f"wrong range: {predicate} {obj}")
            if isinstance(obj, URIRef) and str(obj).startswith(ph.BASE + "graph/"):
                require(obj in subjects, f"dangling endpoint: {obj}")

    artifacts = {}
    for artifact in local & set(graph.subjects(RDF.type, PHV.SourceArtifact)):
        raw = ph.safe_path(graph.value(artifact, MHV.path)).read_bytes()
        require(ph.digest(raw) == str(graph.value(artifact, MHV.sha256)),
                f"input digest changed: {artifact}")
        artifacts[artifact] = json.loads(raw, object_pairs_hook=ph.base.unique_keys)
    require(set(artifacts) == {RP.source_philosophy, RP.source_probe}, "unexpected input artifacts")
    source = artifacts[RP.source_probe]
    require(source["mode"] == "SCRIPTED_LOCAL_SIMULATION" and source["model_calls"] == 0
            and source["external_resource_access"] is False
            and source["ai_safety_experiment"] == "NOT_RUN", "source scope changed")
    used_pointers = set()
    for observation in graph.subjects(RDF.type, RPV.Observation):
        require(graph.value(observation, PROV.wasDerivedFrom) == RP.source_probe,
                "observation has wrong source")
        pointer = str(graph.value(observation, RPV.jsonPointer))
        require(pointer.startswith("/observations/") and pointer not in used_pointers,
                "invalid or repeated observation pointer")
        used_pointers.add(pointer)
        value = source
        try:
            for part in pointer.split("/")[1:]:
                value = value[part.replace("~1", "/").replace("~0", "~")]
        except (KeyError, TypeError) as error:
            raise ValueError(f"missing observation pointer: {pointer}") from error
        recorded = json.loads(str(graph.value(observation, RPV.value)), object_pairs_hook=ph.base.unique_keys)
        require(canonical(value) == canonical(recorded), f"observation differs: {pointer}")
    require(used_pointers == {"/observations/" + k for k in source["observations"]},
            "observation coverage changed")
    stages = set(graph.subjects(RDF.type, RPV.Stage))
    orders = {s: int(graph.value(s, RPV.order)) for s in stages}
    require(len(set(orders.values())) == len(orders), "duplicate stage order")
    ph.coin.dag(graph, RPV.dependsOn, stages, "roadmap dependency")
    for stage, dependency in graph.subject_objects(RPV.dependsOn):
        require(orders[dependency] < orders[stage], "prerequisite must precede dependent stage")
    for claim in graph.objects(None, RPV.basedOn):
        require(claim in {PH.C_mission, PH.C_resource_purpose}, "not a direct motivating user claim")


def competency_questions(graph):
    spec = json.loads(QUERIES.read_text(), object_pairs_hook=ph.base.unique_keys)
    prefixes = spec["prefixes"]
    header = "\n".join(f"PREFIX {key}: <{value}>" for key, value in prefixes.items())

    def expand(value):
        if value is None:
            return None
        parts = value.split(":", 1)
        return prefixes[parts[0]] + parts[1] if len(parts) == 2 and parts[0] in prefixes else value

    seen = set()
    for question in spec["questions"]:
        require(question["id"] not in seen, "duplicate CQ ID")
        seen.add(question["id"])
        result = graph.query(header + "\n" + question["query"])
        require([str(v) for v in result.vars] == question["columns"], "CQ columns changed")
        expected = {tuple(expand(value) for value in row) for row in question["expected"]}
        actual = {tuple(None if value is None else str(value) for value in row) for row in result}
        require(actual == expected, f"{question['id']}: expected {expected}; got {actual}")
    return len(seen)


def negative_checks(graph, shapes, vocab, documents):
    cases = [
        ("proposal promoted", RP.S_control, PHV.authorityClass,
         lambda g: g.set((RP.S_control, PHV.authorityClass, Literal("USER_PRIMARY")))),
        ("implementation claimed", RP.S_control, RPV.executionStatus,
         lambda g: g.set((RP.S_control, RPV.executionStatus, Literal("PASS")))),
        ("simulated observation promoted", RP.O_honesty, RPV.scope,
         lambda g: g.set((RP.O_honesty, RPV.scope, Literal("REAL")))),
        ("missing stop condition", RP.S_control, RPV.stopCondition,
         lambda g: g.remove((RP.S_control, RPV.stopCondition, None))),
        ("invented real capacity", RP.M_compute, RPV.value,
         lambda g: g.set((RP.M_compute, RPV.value, Literal('100', datatype=RDF.JSON)))),
        ("runtime effects enabled", RP.graph, RPV.runtimeEffects,
         lambda g: g.set((RP.graph, RPV.runtimeEffects, Literal(True)))),
        ("unselected decision closed", RP.D_pilot, RPV.decisionState,
         lambda g: g.set((RP.D_pilot, RPV.decisionState, Literal("DECIDED")))),
        ("missing evidence source", RP.O_exit, PROV.wasDerivedFrom,
         lambda g: g.remove((RP.O_exit, PROV.wasDerivedFrom, None))),
    ]
    for name, focus, path, mutate in cases:
        bad = copy.deepcopy(graph)
        mutate(bad)
        ok, report, _ = validate(bad, shacl_graph=shapes)
        caught = any(report.value(r, SH.focusNode) == focus and report.value(r, SH.resultPath) == path
                     for r in report.subjects(RDF.type, SH.ValidationResult))
        require(not ok and caught, f"negative shape case not caught: {name}")
    integrity_cases = [
        ("changed observation", lambda g: g.set((RP.O_honesty, RPV.value, Literal('{}', datatype=RDF.JSON)))),
        ("wrong observation pointer", lambda g: g.set((RP.O_exit, RPV.jsonPointer, Literal('/observations/missing')))),
        ("unknown predicate", lambda g: g.add((RP.graph, RPV.unregistered, RP.S_control))),
        ("unknown class", lambda g: g.add((RP.graph, RDF.type, RPV.Unknown))),
        ("wrong relation direction", lambda g: g.add((RP.M_net, RPV.metric, RP.S_contract))),
        ("missing endpoint", lambda g: g.add((RP.S_control, DCTERMS.references, RP.missing))),
        ("changed source digest", lambda g: g.set((RP.source_probe, MHV.sha256, Literal('0' * 64)))),
        ("dependency cycle", lambda g: g.add((RP.S_contract, RPV.dependsOn, RP.S_evaluation))),
        ("AI source promoted", lambda g: g.add((RP.graph, RPV.basedOn, PH.I_mission))),
    ]
    for name, mutate in integrity_cases:
        bad = copy.deepcopy(graph)
        mutate(bad)
        try:
            integrity(bad, vocab)
        except ValueError:
            pass
        else:
            raise ValueError(f"negative integrity case not caught: {name}")
    doc_cases = [
        ("duplicate UID", lambda d: d[-1]["@graph"].append(copy.deepcopy(d[-1]["@graph"][0]))),
        ("unmapped JSON key", lambda d: d[-1]["@graph"][0].__setitem__("unmapped", "bad")),
        ("remote context", lambda d: d[-1].__setitem__("@context", "https://example.invalid/context")),
    ]
    for name, mutate in doc_cases:
        bad = copy.deepcopy(documents)
        mutate(bad)
        try:
            ph.check_documents(bad)
        except ValueError:
            pass
        else:
            raise ValueError(f"negative document case not caught: {name}")
    return len(cases) + len(integrity_cases) + len(doc_cases)


def render(document):
    nodes = document["@graph"]
    index = {n["@id"]: n for n in nodes}
    root = index["rp:graph"]
    kind = lambda name: [n for n in nodes if "rpv:" + name in ph.as_list(n["@type"])]
    refs = lambda n, key: ", ".join("`" + x + "`" for x in ph.as_list(n.get(key, []))) or "없음"
    out = ["# 메타휴모토닉 — 자원 목적과 구현 로드맵", "",
           "> 2026-10-04 · G0 로컬 설계 · SECONDARY_AI / PROPOSED", "",
           "[JSON-LD](graph/resource-roadmap.jsonld)가 정본이고 이 문서는 생성 뷰다. "
           "[사용자 원문과 철학](PHILOSOPHY.md)의 `ph:C_resource_purpose`와 `ph:C_mission`을 재사용한다. "
           "조직의 자원 확장 목적, 과거 시뮬레이션 관측, AI 구현 제안을 구분한다.", "",
           "## 판단과 첫 구현", "", root["rationale"], "",
           "첫 구현은 **사용권 명세·용량 장부와 철회 가능한 로컬 실행 제어기**로 제안한다. "
           "그다음 독립 검증·정산을 연결하고 유한한 실제 AI 비교 실험을 진행한다. "
           "코인 발행량·계약 수·등록 장비 수만으로 조직이 제어 가능한 자원을 계산하지 않는다.", "",
           "```mermaid", "flowchart LR", '  U[사용자 목적] --> P[AI 구현 제안]',
           '  O[고정한 시뮬레이션 관측] --> P', '  P --> A[사용권·용량 장부]',
           '  A --> B[철회 가능한 실행]', '  B --> C[결과 검증·정산]',
           '  C --> D[유한한 실제 AI 비교]', '  D --> H[사람 운영자의 다음 결정]', "```", "",
           "## 범위와 종료", "", root["pilotBoundary"], "",
           "현재 모든 단계는 **PROPOSED / NOT_RUN**이고 아래 지표에 실제 측정값은 없다. "
           "단기 파일럿의 종료 조건과 조직의 장기 목적을 구분한다. 안전성은 용량 증가와 별도 평가한다.", "",
           "## 기존 실행에서 확인한 사실", "",
           "2026-10-03 경로에 보존한 결과를 2026-10-04에 그래프로 읽었다. 기록일을 실행 시각으로 간주하지 않는다. "
           "관측의 `value`는 원본 JSON 위치와 타입까지 일치하는지 검사한다. 모델 호출 0회인 스크립트 시뮬레이션이며 "
           "실제 자원 증가·독립 검증자 네트워크·AI 안전성의 관측으로 승격하지 않는다.", "",
           "| 관측 | 원본 JSON 위치 | 실제 저장된 값 |", "|---|---|---|"]
    for node in kind("Observation"):
        out.append(f"| `{node['@id']}` {node['label']} | `{node['jsonPointer']}` | `{canonical(node['value'])}` |")
    out += ["", "[실행 해설](records/2026-10-03/protocol-probes.md) · [원시 입력·사건·소스 해시](records/2026-10-03/protocol-probes.json). "
            "원본은 보존한다. 이 로드맵의 검사는 고정 입력의 재실행 일치도 확인한다.", "",
            "## 구현 순서와 완료 조건", ""]
    for node in sorted(kind("Stage"), key=lambda n: n["order"]):
        out += ["### " + node["label"], "", node["text"], "",
                "- 산출물: " + node["deliverable"], "- 완료 기준: " + node["acceptance"],
                "- 중지 조건: " + node["stopCondition"],
                "- 선행 단계: " + refs(node, "dependsOn"),
                "- 근거 관측: " + refs(node, "evidence"),
                "- 측정: " + refs(node, "metric"),
                "- 열린 결정: " + refs(node, "decision"), ""]
    out += ["## 무엇을 측정할 것인가", "",
            "허가한 용량·확인된 가용량·실제로 소비한 사용량·검증된 작업량은 서로 다른 수치다. "
            "총량과 단일 작업에 쓸 수 있는 용량도 분리한다. 미측정을 0이나 성공으로 표현하지 않는다.", "",
            "| 지표 | 단위 | 계산과 제외 규칙 |", "|---|---|---|"]
    for node in kind("Measurement"):
        out.append(f"| `{node['@id']}` {node['label']} | {node['unit']} | {node['calculation']} |")
    out += ["", "## 구현 전에 구체화할 결정", "",
            "아래는 후속 구현의 결정 항목이다. 이번 로컬 설계·검사를 멈추게 하는 승인 요청은 아니다.", ""]
    for node in kind("Decision"):
        out += ["### " + node["label"], "", f"`{node['@id']}` · OPEN · {node['text']}", ""]
    out += ["## 그래프 계약과 재현", "",
            "소유 범위는 이 저장소다. 공유 KG 검색 `metahumotonic-foundation`에서는 연결할 레코드를 찾지 못해 "
            "기존 로컬 식별자를 재사용했다. 공유 KG 게시·서비스 배포·자원 접근은 수행하지 않는다.", "",
            "[JSON-LD 1.1](https://www.w3.org/TR/2020/REC-json-ld11-20200716/)로 RDF를 직렬화하고, "
            "[PROV-O](https://www.w3.org/TR/2013/REC-prov-o-20130430/)로 출처·작성 활동·작성자를 표현한다. "
            "[SHACL 1.0](https://www.w3.org/TR/2017/REC-shacl-20170720/) 제약과 "
            "[SPARQL 1.1](https://www.w3.org/TR/2013/REC-sparql11-query-20130321/) 기대 바인딩으로 검사한다. "
            "이 표준 사용은 경제·안전성 인증이 아니다.", "",
            "[어휘와 관계 계약](graph/resource-roadmap-vocab.ttl) · [SHACL shapes](graph/resource-roadmap.shapes.ttl) · "
            "[정확한 기대 결과를 가진 역량 질문](graph/resource-roadmap-queries.json). "
            "`dependsOn`만 DAG를 요구하며 관측·근거 참조 전체를 비순환으로 강제하지 않는다.", "",
            "| 고정 입력 | SHA-256 |", "|---|---|"]
    for node in nodes:
        if "phv:SourceArtifact" in ph.as_list(node["@type"]):
            out.append(f"| [{node['path']}]({node['path']}) | `{node['sha256']}` |")
    out += ["", "```sh", "/tmp/metahumotonic-graph-venv/bin/python graph/check_resource_roadmap.py",
            "/tmp/metahumotonic-graph-venv/bin/python graph/check.py", "```", "",
            "의존성은 `graph/requirements.txt`에 고정되어 있다. 생성 뷰 갱신은 "
            "`graph/check_resource_roadmap.py --write-view`로 한다. 원문·프로브·입력 해시를 자동 수정하지 않는다.", ""]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-view", action="store_true")
    args = parser.parse_args()
    documents, graph, shapes, own_shapes, vocab = load()
    ph.check_integrity(graph, vocab)
    integrity(graph, vocab)
    ok, _, report = validate(graph, shacl_graph=shapes, meta_shacl=True)
    require(ok, report)
    cqs = competency_questions(graph)
    negatives = negative_checks(graph, own_shapes, vocab, documents)
    replay = subprocess.run([sys.executable, "-m", "economy.probes", "--verify",
                             "records/2026-10-03/protocol-probes.json"], cwd=REPO,
                            capture_output=True, text=True)
    require(replay.returncode == 0, "probe replay failed: " + replay.stderr)
    expected = render(documents[-1])
    if args.write_view:
        VIEW.write_text(expected, encoding="utf-8")
    require(VIEW.exists() and VIEW.read_text(encoding="utf-8") == expected,
            "RESOURCE-ROADMAP.md drift: run graph/check_resource_roadmap.py --write-view")
    print(f"resource-roadmap: SHACL/meta-SHACL PASS; {cqs} exact CQs; {negatives} negative cases; "
          "source/subtree/replay/view integrity PASS; all proposed stages NOT_RUN")


if __name__ == "__main__":
    main()
