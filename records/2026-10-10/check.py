#!/usr/bin/env python3
"""Validate the daily closeout using the existing session vocabulary and harness."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import PROV, RDF, SH

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / "2026-10-05"
spec = importlib.util.spec_from_file_location("prior_session_check", PREVIOUS / "check.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
REC = Namespace(base.BASE + "records/2026-10-10#")
SV = base.SV
base.REC = REC
PENDING = {"w_performance", "w_license_review", "w_nonprofit", "w_ai_ops", "w_live_system"}
PREFIX = f"PREFIX sv: <{SV}> PREFIX rec: <{REC}> "
QUESTIONS = [
    ("remaining", 'SELECT ?s WHERE { ?s a sv:WorkItem ; sv:state "PENDING" }', PENDING),
    ("private", 'SELECT ?s WHERE { ?s a sv:Artifact ; sv:visibility "PRIVATE" }', {"artifact_omc", "artifact_hub"}),
    ("hypothesis", 'SELECT ?s WHERE { ?s a sv:SummaryClaim ; sv:kind "UNTESTED_HYPOTHESIS" }', {"c_premise"}),
    ("deferral_source", 'SELECT ?s WHERE { rec:c_defer sv:evidence ?s }', {"u_closeout", "u_ai_operations"}),
    ("license_baseline", 'SELECT ?s WHERE { rec:w_license_baseline sv:artifact ?s }', {"artifact_license", "artifact_license_followup", "artifact_draft"}),
    ("performance_prerequisite", 'SELECT ?s WHERE { rec:w_performance sv:dependsOn ?s }', {"w_flywheel"}),
    ("live_prerequisites", 'SELECT ?s WHERE { rec:w_live_system sv:dependsOn ?s }', {"w_performance", "w_license_review", "w_ai_ops"}),
]


def integrity(graph, vocab):
    base.integrity(graph, vocab)
    for name in PENDING:
        base.require(str(graph.value(REC[name], SV.state)) == "PENDING", "deferred work promoted without evidence")
    base.require(str(graph.value(REC.c_premise, SV.kind)) == "UNTESTED_HYPOTHESIS", "efficacy not observed")


def render(doc):
    nodes = doc["@graph"]
    lines = ["# 2026-10-10 작업 정리와 후속 검토", "",
             "오늘 이 대화에서 진행한 입체운행구름 작업공간, 자원 기여 목적, 토큰당 지능 전제, 플라이휠과 연구 연결을 정리했다.",
             "기술 연구는 입체운행구름에서 이어가고, 이 재단 저장소에서는 라이선스·실제 운영·미국 비영리 법인 검토를 후속 과제로 관리한다.", "",
             "**동일 기본 LLM·동일 총토큰에서 HSWM·CHU가 더 유용한 답변을 만든다**는 것이 플라이휠의 첫 가설이다.",
             "유용성 → 이용 수요 → 기여 → 공동 연산·기억 → 조직 개선 → 유용성의 순환을 설계했으며 실제 성능 우위는 미검증이다.", "",
             "## 오늘 기록한 상태", "", "| 작업 | 상태 | 완료 범위 또는 남은 일 |", "|---|---|---|"]
    for n in nodes:
        if n["@type"] == "sv:WorkItem":
            lines.append(f'| {n["label"]} | {n["state"]} | {n["text"]} |')
    lines += ["", "## 재단에서 나중에 검토할 질문", "",
              "- 라이선스와 실제 기여·접근·서비스 계약을 어떻게 연결할 것인가?",
              "- 미국 비영리 법인의 목적·조직 형태·관할·설립 절차와 지속 운영 의무는 무엇인가?",
              "- AI 중심 운영에서 법적 책임 주체와 기술적 의사결정·실행 권한은 어떻게 배분할 것인가?",
              "- 계약·회계·지출·기록 보존·오류 정정·복구를 어떤 운영 절차로 묶을 것인가?", "",
              "이 질문들은 후속 조사 목록이다. 법률·세무 검토 결과나 설립 관할 추천, 실제 법인 설립·운영 개시를 기록한 것이 아니다.",
              "개인 재무 구상과 전체 최신 발화는 비공개 기록에 유지한다. 공개 기록의 발췌는 원문 전체와 구별한다.", "",
              "## 출처와 검증", "",
              "정본은 [session.jsonld](session.jsonld), 공개 가능한 사용자 발화와 발췌는 [user-sources.json](user-sources.json)이다.",
              "요약은 SECONDARY_AI이며 원문과 분리한다. 비공개 산출물은 관측 커밋만 참조하고 내부 위치·본문을 복제하지 않는다.",
              "JSON-LD와 PROV-O로 출처를 연결하며, 기존 [일일 기록 어휘](../2026-10-05/session-vocab.ttl)와",
              "[SHACL 계약](../2026-10-05/session.shapes.ttl)을 재사용한다. SHACL의 기록 namespace만 오늘의 namespace로 대입한다.", "",
              "```mermaid", "flowchart LR", '  U["원문과 공개 발췌"] --> C["목적과 품질 가설"]',
              '  C --> W["오늘 완료한 기록과 그래프"]', '  W --> E["커밋과 출처 근거"]',
              '  C --> N["나중에 검토할 라이선스와 운영"]', '  N --> L["미국 비영리 법인과 AI 운영"]', "```", "",
              "```sh", ".venv/bin/python records/2026-10-10/check.py", "```", "",
              "검사는 원문·고정 커밋 해시, 관계 끝점·타입·기수, 의존 순환, SHACL·meta-SHACL, SPARQL 질문 7개와 고의 위반 10개를 다룬다.",
              "그래프 무결성 검사는 법적 유효성·AI 성능·안전성의 검증과 구분한다. 현행 라이선스 1.2와 미채택 1.3 초안은 그대로 유지한다.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-view", action="store_true")
    args = parser.parse_args()
    doc = base.read(HERE / "session.jsonld")
    ids = [n["@id"] for n in doc["@graph"]]
    base.require(len(ids) == len(set(ids)), "duplicate UID")
    base.require(doc["@context"]["rec"] == str(REC), "record namespace changed")
    graph = Graph().parse(data=json.dumps(doc), format="json-ld")
    vocab = Graph().parse(PREVIOUS / "session-vocab.ttl")
    shape_text = (PREVIOUS / "session.shapes.ttl").read_text().replace(base.BASE + "records/2026-10-05#", str(REC))
    shapes = Graph().parse(data=shape_text, format="turtle")
    integrity(graph, vocab)
    ok, _, report = validate(graph, shacl_graph=shapes, meta_shacl=True)
    base.require(ok, report)
    for label, query, expected in QUESTIONS:
        got = {str(r[0]) for r in graph.query(PREFIX + query)}
        base.require(got == {str(REC[x]) for x in expected}, "CQ mismatch: " + label)
    shape_cases = [(REC.c_premise, SV.authority, Literal("USER_PRIMARY")),
                   (REC.c_premise, SV.kind, Literal("PROVEN_OPTIMAL")),
                   (REC.record, SV.normativeEffect, Literal(True)),
                   (REC.artifact_omc, SV.visibility, Literal("PUBLIC")),
                   (REC.c_scope, PROV.wasAttributedTo, REC.user)]
    for s, p, o in shape_cases:
        bad = copy.deepcopy(graph)
        bad.set((s, p, o))
        conforms, results, _ = validate(bad, shacl_graph=shapes)
        base.require(not conforms and any(results.value(n, SH.focusNode) == s for n in results.subjects(RDF.type, SH.ValidationResult)), "shape counterexample escaped")
    mutations = [lambda g: g.set((REC.u_closeout, SV.text, Literal("rewritten"))),
                 lambda g: g.set((REC.artifact_sources, SV.sha256, Literal("0" * 64))),
                 lambda g: g.set((REC.w_nonprofit, SV.state, Literal("VERIFIED"))),
                 lambda g: g.add((REC.w_workspace, SV.dependsOn, REC.w_hub)),
                 lambda g: g.add((REC.artifact_omc, base.DCTERMS.references, URIRef("https://private.invalid/")))]
    for mutate in mutations:
        bad = copy.deepcopy(graph)
        mutate(bad)
        try:
            integrity(bad, vocab)
        except ValueError:
            continue
        raise ValueError("integrity counterexample escaped")
    view = render(doc)
    if args.write_view:
        (HERE / "README.md").write_text(view)
    base.require((HERE / "README.md").read_text() == view, "stale daily view")
    print(json.dumps({"ok": True, "nodes": len(ids), "triples": len(graph), "sparql_questions": len(QUESTIONS),
                      "negative_checks": len(shape_cases) + len(mutations), "shacl": "PASS", "meta_shacl": "PASS",
                      "scope": "RECORD_INTEGRITY_NOT_LEGAL_OR_PERFORMANCE_VALIDATION"}))


if __name__ == "__main__":
    main()
