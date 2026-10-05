#!/usr/bin/env python3
"""Validate the foundation's CHU/HSWM ecosystem design, sources and generated view.

Offline graph validation only. No runtime, payment, canonical state or KG writes.
"""
import argparse
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
EX = Namespace(base.BASE + "graph/ecosystem#")
EV = Namespace(base.BASE + "ecosystem-vocab#")
MHV = base.MHV
DATA = HERE / "ecosystem.jsonld"
QUERIES = HERE / "ecosystem-queries.json"
VIEW = REPO / "ECOSYSTEM.md"
require = base.require
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=base.unique_keys)


def safe_path(relative):
    path = Path(str(relative))
    require(not path.is_absolute() and ".." not in path.parts, "source path outside repository")
    result = (REPO / path).resolve()
    require(result.is_relative_to(REPO) and result.is_file(), "missing local source")
    return result


def check_documents(documents):
    philosophy.check_documents(documents)
    document = documents[-1]
    require(document["@context"]["ex"] == str(EX) and document["@context"]["ev"] == str(EV),
            "ecosystem namespaces changed")
    require(all(n["@id"].startswith("ex:") for n in document["@graph"]),
            "new graph must not redefine foreign owner IDs")


def load():
    documents = [read(HERE / name) for name in
                 ["spirit.jsonld", "economy.jsonld", "metahumocoin.jsonld", "philosophy.jsonld", "ecosystem.jsonld"]]
    check_documents(documents)
    vocab = Graph().parse(HERE / "vocab.ttl").parse(HERE / "ecosystem-vocab.ttl")
    graph = base.load_graph(documents) + vocab
    shapes = Graph().parse(HERE / "ecosystem.shapes.ttl")
    return documents, graph, shapes, vocab


def check_integrity(graph, vocab):
    require((EX.graph, RDF.type, EV.EcosystemGraph) in graph, "missing design root")
    subjects = set(graph.subjects())
    standard = {RDF.type, RDFS.label, DCTERMS.source, DCTERMS.references,
                PROV.wasDerivedFrom, PROV.wasAttributedTo, PROV.wasGeneratedBy, PROV.wasAssociatedWith}
    for subject, predicate, obj in graph:
        if not str(subject).startswith(str(EX)):
            continue
        require(predicate not in {OWL.sameAs, SKOS.exactMatch}, "identity is not established by design mapping")
        require(predicate in standard or (predicate, RDF.type, RDF.Property) in vocab,
                f"unknown predicate: {predicate}")
        if predicate == RDF.type:
            require(obj in {PROV.SoftwareAgent, PROV.Activity} or (obj, RDF.type, RDFS.Class) in vocab,
                    f"unregistered node type: {obj}")
        for domain in vocab.objects(predicate, RDFS.domain):
            require(domain == RDFS.Resource or (subject, RDF.type, domain) in graph,
                    f"wrong domain: {subject} {predicate}")
        for target in vocab.objects(predicate, RDFS.range):
            if target == RDFS.Resource:
                require(isinstance(obj, URIRef), "IRI required")
            elif str(target).startswith(str(XSD)):
                require(isinstance(obj, Literal) and
                        (obj.datatype == target or (target == XSD.string and obj.datatype is None)),
                        f"wrong datatype: {predicate}")
            else:
                require((obj, RDF.type, target) in graph, f"wrong range: {predicate}")
        if isinstance(obj, URIRef) and str(obj).startswith(base.BASE + "graph/"):
            require(obj in subjects, f"dangling owner reference: {obj}")

    artifacts = {}
    for artifact in graph.subjects(RDF.type, EV.SourceArtifact):
        raw = safe_path(graph.value(artifact, MHV.path)).read_bytes()
        require(sha(raw) == str(graph.value(artifact, MHV.sha256)), "source bytes changed")
        artifacts[artifact] = raw
    require(set(graph.objects(EX.graph, EV.inputArtifact)) == set(artifacts), "source coverage differs")
    manifest = json.loads(artifacts[EX.source_manifest], object_pairs_hook=base.unique_keys)
    require(manifest["authority"] == "DOCUMENT_OBSERVATION", "manifest attribution changed")
    for row in manifest["sources"]:
        artifact = EX["source_" + row["id"]]
        require(artifact in artifacts and sha(artifacts[artifact]) == row["sha256"], "owner source mismatch")
        require(str(graph.value(artifact, MHV.path)) == row["copy_path"]
                and str(graph.value(artifact, EV.revision)) == row["revision"]
                and str(graph.value(artifact, DCTERMS.source)) == row["source_uri"], "owner provenance changed")
        require(row["state"] == "COMMITTED_BYTES" and len(row["revision"]) == 40
                and all(c in "0123456789abcdef" for c in row["revision"]), "invalid pinned revision")

    for source in graph.subjects(RDF.type, EV.SourceExcerpt):
        artifact = graph.value(source, DCTERMS.source)
        data = json.loads(artifacts[artifact], object_pairs_hook=base.unique_keys)
        rows = data["messages"]
        require(len({r["id"] for r in rows}) == len(rows), "duplicate source record key")
        row = next((r for r in rows if r["id"] == str(graph.value(source, EV.recordKey))), None)
        require(row is not None and row["role"] == "user" and row["authority"] == "USER_PRIMARY", "source role mismatch")
        text = str(graph.value(source, EV.sourceText))
        require(text == row["verbatim"] == str(graph.value(source, MHV.verbatim)), "source text changed")
        require(sha(text.encode()) == row["sha256"] == str(graph.value(source, MHV.sha256)), "source digest changed")
        require(row["locator"] == str(graph.value(source, EV.locator)), "source locator changed")
    for claim in graph.subjects(RDF.type, EV.UserClaim):
        source = graph.value(claim, PROV.wasDerivedFrom)
        span = str(graph.value(claim, MHV.span))
        require(bool(span) and span in str(graph.value(source, MHV.verbatim))
                and str(graph.value(claim, MHV.text)) == span, "claim is not an exact source span")
    for observation in graph.subjects(RDF.type, EV.DocumentObservation):
        source = graph.value(observation, DCTERMS.source)
        text = str(graph.value(observation, EV.sourceText))
        require(bool(text) and text in artifacts[source].decode(), "document excerpt is not in pinned source")

    for relation in graph.subjects(RDF.type, EV.RelationSpec):
        subject = graph.value(relation, EV.subject)
        predicate = graph.value(relation, EV.relationKind)
        obj = graph.value(relation, EV.object)
        require((predicate, RDF.type, RDF.Property) in vocab
                and (predicate, RDFS.domain, EV.ComponentSpec) in vocab
                and (predicate, RDFS.range, EV.ComponentSpec) in vocab, "unregistered logical relation")
        require((subject, RDF.type, EV.ComponentSpec) in graph and (obj, RDF.type, EV.ComponentSpec) in graph,
                "logical endpoints have wrong type")
    for edge in graph.subjects(RDF.type, EV.HyperedgeSpec):
        parts = list(graph.objects(edge, EV.participant))
        positions = [int(graph.value(p, EV.position)) for p in parts]
        roles = [str(graph.value(p, EV.role)) for p in parts]
        require(sorted(positions) == list(range(len(parts))), "incidence positions missing or duplicated")
        require(len(roles) == len(set(roles)), "incidence roles duplicated")
    for part in graph.subjects(RDF.type, EV.ParticipationSpec):
        require(len(set(graph.subjects(EV.participant, part))) == 1, "incidence must belong to exactly one edge")


def competency_questions(graph):
    spec = read(QUERIES)
    header = "\n".join(f"PREFIX {k}: <{v}>" for k, v in spec["prefixes"].items())
    def expand(text):
        prefix, sep, local = text.partition(":")
        return spec["prefixes"][prefix] + local if sep and prefix in spec["prefixes"] else text
    seen = set()
    for question in spec["questions"]:
        require(question["id"] not in seen, "duplicate CQ ID")
        seen.add(question["id"])
        result = graph.query(header + "\n" + question["query"])
        require([str(v) for v in result.vars] == question["columns"], "CQ columns changed")
        actual = {tuple(str(x) for x in row) for row in result}
        expected = {tuple(expand(x) for x in row) for row in question["expected"]}
        require(actual == expected, f"CQ {question['id']}: expected {expected}; got {actual}")
    return len(seen)


def negative_checks(documents, graph, shapes, vocab):
    cases = [
        (EX.D_autonomy, EV.authorityClass, Literal("USER_PRIMARY")),
        (EX.D_economy, EV.designStatus, Literal("RATIFIED")),
        (EX.C_autonomy, EV.verificationStatus, Literal("PROVEN")),
        (EX.E_ecology, EV.verificationStatus, Literal("PASS")),
        (EX.graph, EV.executionEffect, Literal(True)),
        (EX.D_step, PROV.wasAttributedTo, base.SP.proposer),
        (EX.unit_response, EV.responsesPerUnit, Literal(2)),
    ]
    for focus, path, value in cases:
        bad = copy.deepcopy(graph); bad.set((focus, path, value))
        ok, report, message = validate(bad, shacl_graph=shapes)
        caught = any(report.value(r, SH.focusNode) == focus and report.value(r, SH.resultPath) == path
                     for r in report.subjects(RDF.type, SH.ValidationResult))
        require(not ok and caught, f"missed negative constraint: {path}\n{message}")
    mutations = [
        lambda g: g.set((EX.source_chu_scope, MHV.sha256, Literal("0"*64))),
        lambda g: g.set((EX.C_operation, MHV.span, Literal("1 response equals 1 FLOP"))),
        lambda g: g.set((EX.O_chu_scope, EV.sourceText, Literal("CHU is only HSWM"))),
        lambda g: g.add((EX.chu, OWL.sameAs, base.SP.chu)),
        lambda g: g.add((EX.chu, EV.unregistered, EX.hswm)),
        lambda g: g.set((EX.R_host, EV.object, EX.missing)),
        lambda g: g.set((EX.R_host, EV.subject, EX.unit_response)),
        lambda g: g.set((EX.R_host, EV.relationKind, EV.groundedIn)),
        lambda g: g.set((EX.part_executor, EV.position, Literal(0))),
        lambda g: g.set((EX.part_executor, EV.role, Literal("system"))),
        lambda g: g.set((EX.source_chu_scope, MHV.path, Literal("../outside"))),
    ]
    for mutate in mutations:
        bad = copy.deepcopy(graph); mutate(bad)
        try: check_integrity(bad, vocab)
        except (ValueError, KeyError): pass
        else: raise ValueError("negative integrity mutation accepted")
    serializations = [
        lambda d: d[-1]["@graph"].append(copy.deepcopy(d[-1]["@graph"][0])),
        lambda d: d[-1].__setitem__("@context", "https://example.invalid/context"),
        lambda d: d[-1]["@graph"][0].__setitem__("unknownKey", "silently dropped"),
        lambda d: d[-1]["@graph"][0].__setitem__("@id", "sp:unowned-new-id"),
    ]
    for mutate in serializations:
        bad = copy.deepcopy(documents); mutate(bad)
        try: check_documents(bad)
        except ValueError: pass
        else: raise ValueError("negative document mutation accepted")
    wrong_unit = copy.deepcopy(graph)
    wrong_unit.set((EX.unit_response, EV.unit, Literal("FLOP")))
    try: competency_questions(wrong_unit)
    except ValueError: pass
    else: raise ValueError("response/FLOP confusion was not detected")
    return len(cases) + len(mutations) + len(serializations) + 1


def render(document):
    nodes = document["@graph"]
    index = {n["@id"]: n for n in nodes}
    def typed(kind):
        return [n for n in nodes if "ev:" + kind in philosophy.as_list(n.get("@type", []))]
    def cell(text): return str(text).replace("|", "\\|").replace("\n", " ")
    out = ["# MetaHumotonic — CHU 기반 자율 AI 생태계", "",
           "> 사용자 방향 + 출처에 결속된 AI 설계 · G0 · 2026-10-04", "",
           "정본 데이터는 [ecosystem.jsonld](graph/ecosystem.jsonld)다. 이 문서는 그래프의 생성 뷰이며, "
           "새 사용자 발언을 보존하고 기존 CHU·HSWM 정의에 연결한다. 설계·출처 검사는 수행하지만 "
           "생태계 런타임이나 완전 자율성의 실현을 선언하는 문서는 아니다.", "",
           "## 사용자 방향", "", "> " + index["ex:utterance"]["verbatim"], "",
           "— [전체 원문](records/2026-10-04/ecosystem/user-source.json). 기록일과 발화 시각을 구별하며 발화 시각은 미상이다.", "",
           "| 직접 출처 항목 | 원문 구간 |", "|---|---|"]
    for n in typed("UserClaim"):
        out.append(f"| `{n['@id']}` · {cell(n['label'])} | {cell(n['span'])} |")
    out += ["", "위 인용은 USER_PRIMARY다. 표제·분류명과 아래 관계·계약·평가 방법은 "
            "**SECONDARY_AI / PROPOSED**로 구분한다. ‘완벽’은 목표이고 ‘자연’은 사용자의 철학적 서술이다. "
            "현재 완전성·안전성·경제적 안정성이 증명된 상태로 승격하지 않는다.", "",
            "## 구조", "", "```mermaid", "flowchart TD",
            '  CHU["CHU: 계산가능 하이퍼우주"] --> OS["CHU OS: 하이퍼그래프 작업환경"]',
            '  OS --> P["여러 HSWM이 참여하는 생태계"]',
            '  P --> H["HSWM: 하나의 거대한 AI"]',
            '  H --> A["내부 에이전트·국소 LLM 연산자"]',
            '  A --> R["LLM 응답 1회 = 논리 연산 1회"]',
            '  G["Semantic Weight 하이퍼그래프 상태"] --> A',
            '  R --> O["응답·사용량·독립 결과 관측"]',
            '  O --> V["검증된 상태 revision 후보"]',
            '  V --> G',
            '  R --> C["물리 컴퓨팅·메모리 사용"]',
            '  H --> E["선택·경쟁·협력·합의"]',
            '  E --> B["계약·정산·다음 추론 예산"]',
            '  B --> R',
            '  H -. "합성·분리와 계보 보존" .-> BIG["더 큰 HSWM"]',
            "```", "",
            "이 그림의 화살표는 설명용 뷰다. 정본은 아래의 방향·의미가 명시된 관계와 역할 있는 n항 연결이다. "
            "CHU를 폴더 트리로 정의하거나 그림의 층을 고정 실행 계층으로 강제하지 않는다.", "",
            "| 구성 개념 | 정의·구현 방향 |", "|---|---|"]
    for n in typed("ComponentSpec"):
        out.append(f"| **{cell(n['label'])}** | {cell(n['text'])} |")
    out += ["", "## 연산·토큰·자원·화폐의 단위", "",
            "응답 한 번은 논리적 연산 단위다. 한 번의 응답에 쓰이는 토큰 수와 물리 비용은 가변적이므로 "
            "응답 횟수만으로 계산능력이나 가격을 비교하지 않는다.", "",
            "| 단위 | 계측·계약 규칙 |", "|---|---|"]
    for n in typed("UnitSpec"):
        out.append(f"| {cell(n['label'])} · `{n['unit']}` | {cell(n['countingRule'])} |")
    out += ["", "## 자유·경제·합의의 작동 제안", ""]
    for n in typed("ContractSpec"):
        out += [f"### {n['label']}", "", n["contract"], ""]
    out += ["## 명시적 관계와 하이퍼엣지", "",
            "관계 자체를 `RelationSpec`으로 두어 주체·술어·대상·출처·제안 상태를 보존한다. "
            "관계 이름을 기록했다는 사실은 실행·허가·배포를 뜻하지 않는다.", "",
            "| 주체 → 관계 → 대상 | 의미 |", "|---|---|"]
    for n in typed("RelationSpec"):
        out.append(f"| `{n['subject']}` → `{n['relationKind']}` → `{n['object']}` | {cell(n['text'])} |")
    out += ["", index["ex:execution_binding"]["text"], "",
            "| 위치 | 역할 | 대상 |", "|---:|---|---|"]
    for n in sorted(typed("ParticipationSpec"), key=lambda x: x["position"]):
        out.append(f"| {n['position']} | `{n['role']}` | `{n['endpoint']}` |")
    out += ["", "RDF의 관계 노드와 incidence로 n항 의미를 명시했다. CHU native CID·rewrite·multiway history의 "
            "저장/실행을 이 그래프가 대신하지 않는다. CHU native 변환기는 별도 구현·왕복 검증 대상이다.", "",
            "## 완전 자율성의 열린 결정", ""]
    for n in typed("OpenQuestion"):
        out += [f"- **{n['label']} — OPEN:** {n['text']}"]
    out += ["", "새 발언은 기존 [제어 가능한 자원 확대 목적](PHILOSOPHY.md)과 함께 보존한다. "
            "일상적인 에이전트 자율성, 자원 소유·제공 권한, 기존 이탈·철회 조건을 별도 축으로 검토하는 것이 "
            "현재 AI 설계 제안이다. 이 문서로 사용자의 ‘인간 제어 없이’라는 원문을 재작성하거나 "
            "기존 라이선스·헌장의 효력을 변경하지 않는다.", "",
            "## 검증할 생태계", ""]
    plan = index["ex:E_ecology"]
    out += ["**NOT_RUN** — " + plan["text"], "", "기준선: " + plan["baseline"], "",
            "변경 조건: " + plan["treatment"], "", "실패 판정: " + plan["failureCondition"], "",
            "| 지표 | 단위 | 계산 |", "|---|---|---|"]
    for n in typed("MetricSpec"):
        out.append(f"| {cell(n['label'])} | `{n['unit']}` | {cell(n['calculation'])} |")
    out += ["", "HSWM의 인지 효능·독창성 비교로 확장할 때는 해당 저장소의 핵심 비교 대상인 "
            "OpenCog Hyperon의 component·commit·configuration·성숙도를 명시해야 한다. "
            "이 생태계 그래프는 그 비교를 새로 실행했거나 우위를 입증한 자료가 아니다.", "",
            "## 현재 구현과의 연결", "", index["ex:M_existing"]["text"], "",
            "[기존 로컬 시장](MARKET.md)의 영수증·단가·예약·환불 구조는 이 모델의 부품으로 참조한다. "
            "기존 로컬 시장의 실행 기록과 이번 **DESIGN_ONLY** 그래프를 분리했다. "
            "다음 산출물은 CHU/HSWM native mapping, 응답·사용량 영수증 계약, 유한한 복수 HSWM 비교 실험이다. "
            "토큰 경쟁의 무기한 실행기를 이번 그래프 구축으로 시작하지 않는다.", "",
            "## 소스와 표준 그래프 계약", "", index["ex:graph"]["scope"], "",
            "CHU·HSWM의 기존 프로젝트 UID인 `sp:chu`·`sp:hswm`을 재사용한다. CHU 개념 전체, "
            "OS 구현, HSWM 개체와 프로세스를 새 동일성 관계로 합치지 않는다. KG의 CHU 검색 결과는 "
            "정의가 없는 directory 기록이어서 소유 저장소 원문을 사용했다. HSWM KG에 남은 과거 "
            "고정 H/W/A/F 문구는 현재 소유자 헌법의 폐기 기록으로 대조했다.", "",
            "[소스 manifest](records/2026-10-04/ecosystem/source-manifest.json)에 원본 저장소·commit·경로·"
            "SHA-256·복사 경로를 결속했다. 원본과 commit의 바이트 일치를 확인한 후 로컬 사본을 보존했다. "
            "원문 안의 AI 주석이나 과거 검증 서술은 이번 실행의 새 증거로 재사용하지 않는다.", "",
            "| 보존 입력 | 상태 | SHA-256 |", "|---|---|---|"]
    for n in typed("SourceArtifact"):
        out.append(f"| [{cell(n['label'])}]({n['path']}) | {n['artifactState']} | `{n['sha256']}` |")
    out += ["", "직렬화는 [JSON-LD 1.1](https://www.w3.org/TR/json-ld11/), 출처·작성자는 "
            "[PROV-O](https://www.w3.org/TR/prov-o/), 제약 검사는 [SHACL](https://www.w3.org/TR/shacl/)을 사용한다. "
            "생태계의 도메인 어휘는 이 저장소 소유의 제안이며 W3C가 표준화한 AI 경제 모델이라고 주장하지 않는다.", "",
            "[어휘와 관계 계약](graph/ecosystem-vocab.ttl) · [SHACL](graph/ecosystem.shapes.ttl) · "
            "[SPARQL 역량 질문](graph/ecosystem-queries.json) · [검사기](graph/check_ecosystem.py).", "",
            "검사기는 원문·파일 해시, 역할·상태 분리, UID·참조·domain/range, n항 역할·순서의 보존, "
            "정확한 SPARQL 기대 결과와 생성 뷰를 검사한다. ‘완벽’을 PROVEN으로 바꾸거나 AI 제안을 "
            "사용자 권위로 올리는 고의 오류도 거절한다. 그래프 검사는 인지능력·경제·안전성의 실험이 아니다.", "",
            "```sh", "python3 -m venv /tmp/metahumotonic-graph-venv",
            "/tmp/metahumotonic-graph-venv/bin/python -m pip install -r graph/requirements.txt",
            "/tmp/metahumotonic-graph-venv/bin/python graph/check_ecosystem.py",
            "/tmp/metahumotonic-graph-venv/bin/python graph/check.py", "```", "",
            "그래프를 변경한 뒤 뷰 갱신은 `graph/check_ecosystem.py --write-view`로 수행한다. "
            "기존 source hash 불일치는 자동으로 덮어쓰지 않는다.", ""]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-view", action="store_true")
    args = parser.parse_args()
    documents, graph, shapes, vocab = load()
    check_integrity(graph, vocab)
    ok, _, report = validate(graph, shacl_graph=shapes, meta_shacl=True)
    require(ok, report)
    cqs = competency_questions(graph)
    negatives = negative_checks(documents, graph, shapes, vocab)
    expected = render(documents[-1])
    if args.write_view: VIEW.write_text(expected, encoding="utf-8")
    require(VIEW.exists() and VIEW.read_text(encoding="utf-8") == expected, "ECOSYSTEM.md drift; run --write-view")
    print(f"ecosystem: SHACL/meta-SHACL PASS; {cqs} exact CQs; {negatives} negative cases; "
          "source/identity/units/n-ary roles/view PASS; DESIGN_ONLY; ecology experiment NOT_RUN")


if __name__ == "__main__":
    main()
