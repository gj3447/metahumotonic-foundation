#!/usr/bin/env python3
"""Validate the G0 philosophy graph and its generated PHILOSOPHY.md view.

Uses only local JSON-LD contexts and pinned local inputs. No KG writes, remote
JSON-LD retrieval, access grants, or empirical safety claims are performed.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from rdflib.namespace import DCTERMS, OWL, SH, SKOS

import check as base
import check_metahumocoin as coin

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BASE = base.BASE
MHV, PROV = base.MHV, base.PROV
PH = Namespace(BASE + "graph/philosophy#")
PHV = Namespace(BASE + "philosophy-vocab#")
SP = base.SP
DATA = HERE / "philosophy.jsonld"
VIEW = REPO / "PHILOSOPHY.md"
QUERIES = HERE / "philosophy-queries.json"
require = base.require


def as_list(value):
    return value if isinstance(value, list) else [value]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_path(relative):
    path = Path(str(relative))
    require(not path.is_absolute() and ".." not in path.parts,
            f"unsafe input path: {relative}")
    resolved = (REPO / path).resolve()
    require(resolved.is_relative_to(REPO) and resolved.is_file(),
            f"input outside repository or missing: {relative}")
    return resolved


def check_documents(documents):
    def local_contexts(value, root=False):
        if isinstance(value, dict):
            require("@import" not in value, "context import is not allowed")
            require(root or "@context" not in value, "nested context is not allowed")
            for child in value.values():
                local_contexts(child)
        elif isinstance(value, list):
            for child in value:
                local_contexts(child)

    identifiers = set()
    for document in documents:
        local_contexts(document, root=True)
        context = document["@context"]
        require(isinstance(context, dict) and "@import" not in context,
                "remote context/import is not allowed")
        local_ids = set()
        for node in document["@graph"]:
            ident = node["@id"]
            prefix, local = ident.split(":", 1)
            require(prefix in context and isinstance(context[prefix], str),
                    f"unresolved node prefix: {ident}")
            expanded = context[prefix] + local
            require(expanded not in local_ids, f"duplicate UID in document: {expanded}")
            # The existing economy fixture extends eco:metahumocoin with a
            # CurrencyDesign type. Preserve that established modular assertion.
            # No newly authored philosophy node may redefine an imported UID.
            require(expanded not in identifiers or
                    (expanded == str(base.ECO.metahumocoin) and
                     context.get("ph") is None), f"duplicate UID: {expanded}")
            local_ids.add(expanded)
            identifiers.add(expanded)
            require("@context" not in node, f"nested context: {ident}")
            for key in node:
                require(key in ("@id", "@type") or key in context or "@vocab" in context
                        or (":" in key and key.split(":", 1)[0] in context),
                        f"unmapped JSON-LD key: {ident} {key}")


def load():
    documents = [base.read_document(p) for p in [*coin.DATA_PATHS, DATA]]
    check_documents(documents)
    graph = base.load_graph(documents)
    shapes = coin.load_shapes()
    shapes.parse(HERE / "philosophy.shapes.ttl")
    vocab = coin.load_vocab()
    vocab.parse(HERE / "philosophy-vocab.ttl")
    return documents, graph, shapes, vocab


def check_integrity(graph, vocab):
    # Preserve the original domain/range/authority contracts on imported data.
    coin.check_registered_terms(graph)
    subjects = set(graph.subjects())
    standard_predicates = {
        RDF.type, RDFS.label, RDFS.comment, DCTERMS.date, DCTERMS.source,
        DCTERMS.references, DCTERMS.subject, DCTERMS.publisher, DCTERMS.hasVersion,
        PROV.wasAttributedTo, PROV.wasDerivedFrom, PROV.wasGeneratedBy,
        PROV.wasAssociatedWith, PROV.used,
    }
    for subject, predicate, obj in graph:
        if predicate == RDF.type and str(obj).startswith(str(PHV)):
            require((obj, RDF.type, RDFS.Class) in vocab, f"unknown class: {obj}")
        if not str(subject).startswith(str(PH)):
            continue
        require(predicate not in (OWL.sameAs, SKOS.exactMatch),
                "identity assertion is outside the philosophy profile")
        require(str(predicate).startswith((str(MHV), str(PHV))) or
                predicate in standard_predicates, f"unregistered predicate: {predicate}")
        if str(predicate).startswith(str(PHV)):
            require((predicate, RDF.type, RDF.Property) in vocab,
                    f"unknown predicate: {predicate}")
            for domain in vocab.objects(predicate, RDFS.domain):
                require(domain == RDFS.Resource or (subject, RDF.type, domain) in graph,
                        f"wrong domain: {subject} {predicate}")
            for target in vocab.objects(predicate, RDFS.range):
                if target == RDFS.Resource:
                    require(isinstance(obj, URIRef), f"IRI required: {predicate}")
                elif str(target).startswith(str(XSD)):
                    require(isinstance(obj, Literal) and
                            (obj.datatype == target or
                             (target == XSD.string and obj.datatype is None)),
                            f"wrong datatype: {predicate}")
                else:
                    require((obj, RDF.type, target) in graph,
                            f"wrong range: {predicate} {obj}")
        if (isinstance(obj, URIRef) and str(obj).startswith(BASE + "graph/")
                and not str(obj).startswith(str(PHV))):
            require(obj in subjects, f"dangling endpoint: {subject} {predicate} {obj}")

    artifacts = {}
    for artifact in graph.subjects(RDF.type, PHV.SourceArtifact):
        path = safe_path(graph.value(artifact, MHV.path))
        raw = path.read_bytes()
        require(digest(raw) == str(graph.value(artifact, MHV.sha256)),
                f"input digest changed: {artifact}")
        artifacts[artifact] = raw
        revision = graph.value(artifact, MHV.gitCommit)
        if revision:
            original = subprocess.check_output(
                ["git", "show", f"{revision}:{path.relative_to(REPO).as_posix()}"], cwd=REPO)
            require(original == raw, f"commit bytes differ: {artifact}")

    # Preserve earlier conversation artifacts byte-for-byte when a later user
    # statement arrives. Keys are scoped to their explicitly linked artifact.
    source_rows = {}
    for source in {graph.value(excerpt, DCTERMS.source)
                   for excerpt in graph.subjects(RDF.type, PHV.SourceExcerpt)}:
        require(source in artifacts, f"missing conversation artifact: {source}")
        records = json.loads(artifacts[source], object_pairs_hook=base.unique_keys)
        rows = records["messages"]
        require(len({row["id"] for row in rows}) == len(rows), "duplicate source record ID")
        source_rows.update({(source, row["id"]): row for row in rows})
    used_keys = set()
    for excerpt in graph.subjects(RDF.type, PHV.SourceExcerpt):
        key = (graph.value(excerpt, DCTERMS.source), str(graph.value(excerpt, PHV.recordKey)))
        require(key in source_rows and key not in used_keys, f"invalid/reused source key: {key}")
        used_keys.add(key)
        row = source_rows[key]
        text = str(graph.value(excerpt, PHV.sourceText))
        require(text == row["verbatim"] and digest(text.encode()) == row["sha256"]
                == str(graph.value(excerpt, MHV.sha256)), f"source text/hash differs: {excerpt}")
        for predicate, field in [(PHV.sourceRole, "role"), (PHV.authorityClass, "authority"),
                                 (PHV.locator, "locator")]:
            require(str(graph.value(excerpt, predicate)) == row[field],
                    f"source role/authority/locator differs: {excerpt}")
        expected_author = SP.proposer if row["role"] == "user" else PH.codex
        require(graph.value(excerpt, PROV.wasAttributedTo) == expected_author,
                f"source actor differs: {excerpt}")
        if row["role"] == "user":
            require(str(graph.value(excerpt, MHV.verbatim)) == text,
                    f"legacy user verbatim differs: {excerpt}")
    require(used_keys == set(source_rows), "unrepresented conversation record")

    for observation in graph.subjects(RDF.type, PHV.DocumentExcerpt):
        artifact = graph.value(observation, PHV.artifact)
        text = str(graph.value(observation, PHV.excerpt))
        require(artifact in artifacts and text and text in artifacts[artifact].decode(),
                f"document quote differs: {observation}")
    for claim in (PH.C_mission, PH.C_build, PH.C_resource_purpose):
        require(graph.value(claim, MHV.text) == graph.value(claim, MHV.span),
                f"primary claim wording must be an exact quote: {claim}")
    # Neither a legacy AI summary nor an AI restatement becomes a direct source.
    claims = set(graph.objects(PH.graph, PHV.sourceClaim))
    claims.update(graph.objects(None, PHV.groundedIn))
    for claim in claims:
        utterance = graph.value(claim, PROV.wasDerivedFrom)
        require(utterance and graph.value(utterance, MHV.verbatim) is not None
                and graph.value(utterance, MHV.summaryAuthority) is None,
                f"not a direct user source: {claim}")


def competency_questions(graph):
    spec = json.loads(QUERIES.read_text(), object_pairs_hook=base.unique_keys)
    prefixes = spec["prefixes"]
    header = "\n".join(f"PREFIX {key}: <{value}>" for key, value in prefixes.items())

    def expand(value):
        parts = value.split(":", 1)
        return prefixes[parts[0]] + parts[1] if len(parts) == 2 and parts[0] in prefixes else value

    seen = set()
    for question in spec["questions"]:
        require(question["id"] not in seen, "duplicate competency question")
        seen.add(question["id"])
        result = graph.query(header + "\n" + question["query"])
        require([str(v) for v in result.vars] == question["columns"],
                f"CQ columns changed: {question['id']}")
        expected = {tuple(expand(value) for value in row) for row in question["expected"]}
        actual = {tuple(str(value) for value in row) for row in result}
        require(actual == expected,
                f"CQ {question['id']}: expected {expected}; got {actual}")
    return len(seen)


def negative_checks(graph, shapes, vocab, documents):
    cases = [
        ("invented user quote", PH.C_mission, MHV.ExactSourceSpanShape,
         lambda g: g.set((PH.C_mission, MHV.span, Literal("안전성이 증명되었다")))),
        ("AI promoted to user authority", PH.I_mission, PHV.authorityClass,
         lambda g: g.set((PH.I_mission, PHV.authorityClass, Literal("USER_PRIMARY")))),
        ("AI promoted to ratified", PH.I_freedom, PHV.adoptionStatus,
         lambda g: g.set((PH.I_freedom, PHV.adoptionStatus, Literal("RATIFIED")))),
        ("wrong AI attribution", PH.I_economy, PROV.wasAttributedTo,
         lambda g: g.set((PH.I_economy, PROV.wasAttributedTo, SP.proposer))),
        ("ungrounded interpretation", PH.I_consensus, PHV.groundedIn,
         lambda g: g.remove((PH.I_consensus, PHV.groundedIn, None))),
        ("hypothesis presented as proven", PH.H_safety, MHV.epistemic,
         lambda g: g.set((PH.H_safety, MHV.epistemic, MHV.PROVEN))),
        ("experiment presented as run", PH.E_protocol, PHV.verificationStatus,
         lambda g: g.set((PH.E_protocol, PHV.verificationStatus, Literal("PASS")))),
        ("case has no comparison", PH.E_scarcity, PHV.baseline,
         lambda g: g.remove((PH.E_scarcity, PHV.baseline, None))),
        ("undefined measurement", PH.metric_success, PHV.calculation,
         lambda g: g.remove((PH.metric_success, PHV.calculation, None))),
        ("mapping presented as deployed", PH.M_economy, PHV.implementationStatus,
         lambda g: g.set((PH.M_economy, PHV.implementationStatus, Literal("DEPLOYED")))),
        ("graph grants normative authority", PH.graph, PHV.normativeEffect,
         lambda g: g.set((PH.graph, PHV.normativeEffect, Literal(True)))),
        ("source missing locator", PH.u_purpose, PHV.locator,
         lambda g: g.remove((PH.u_purpose, PHV.locator, None))),
        ("resource purpose assigned to AI", PH.C_resource_purpose, PHV.authorityClass,
         lambda g: g.set((PH.C_resource_purpose, PHV.authorityClass, Literal("SECONDARY_AI")))),
    ]
    for name, focus, path, mutate in cases:
        bad = copy.deepcopy(graph)
        mutate(bad)
        ok, report, message = validate(bad, shacl_graph=shapes)
        caught = any(report.value(r, SH.focusNode) == focus and
                     (report.value(r, SH.resultPath) == path or report.value(r, SH.sourceShape) == path)
                     for r in report.subjects(RDF.type, SH.ValidationResult))
        require(not ok and caught, f"negative case not caught: {name}\n{message}")

    integrity_cases = [
        ("altered input digest", lambda g: g.set((PH.source_license, MHV.sha256, Literal("0" * 64)))),
        ("changed source text with rehashed excerpt", lambda g: (
            g.set((PH.a_mission, PHV.sourceText, Literal("changed"))),
            g.set((PH.a_mission, MHV.sha256, Literal(digest(b"changed")))))),
        ("unknown predicate", lambda g: g.add((PH.I_mission, PHV.unknownEdge, PH.foundation))),
        ("dangling endpoint", lambda g: g.add((PH.M_agent, PHV.implementsWith, PH.missing))),
        ("false identity", lambda g: g.add((PH.foundation, OWL.sameAs, SP.stack))),
        ("false document quote", lambda g: g.set((PH.O_license, PHV.excerpt, Literal("invented clause")))),
        ("wrong edge direction", lambda g: g.add((PH.metric_success, PHV.hasCase, PH.E_scarcity))),
        ("legacy AI summary promoted", lambda g: g.add((PH.I_mission, PHV.groundedIn, SP.P8))),
        ("outside-owner input", lambda g: g.set((PH.source_license, MHV.path, Literal("../outside")))),
        ("unknown standard predicate", lambda g: g.add((PH.I_mission, PROV.unknownProperty, PH.foundation))),
        ("resource statement assigned to old artifact", lambda g: g.set(
            (PH.u_resource_purpose, DCTERMS.source, PH.source_record))),
    ]
    for name, mutate in integrity_cases:
        bad = copy.deepcopy(graph)
        mutate(bad)
        try:
            check_integrity(bad, vocab)
        except ValueError:
            pass
        else:
            raise ValueError(f"negative integrity case not caught: {name}")
    doc_cases = [
        ("duplicate UID", lambda ds: ds[-1]["@graph"].append(copy.deepcopy(ds[-1]["@graph"][0]))),
        ("remote context", lambda ds: ds[-1].__setitem__("@context", "https://example.invalid/context")),
        ("silent dropped key", lambda ds: ds[-1]["@graph"][0].__setitem__("unmappedKey", "bad")),
        ("nested remote context", lambda ds: ds[-1]["@graph"][0].__setitem__(
            "source", {"@context": "https://example.invalid/context", "@id": "ph:source_record"})),
    ]
    for name, mutate in doc_cases:
        bad = copy.deepcopy(documents)
        mutate(bad)
        try:
            check_documents(bad)
        except ValueError:
            pass
        else:
            raise ValueError(f"negative serialization case not caught: {name}")
    return len(cases) + len(integrity_cases) + len(doc_cases)


def render(document, documents):
    nodes = document["@graph"]
    index = {n["@id"]: n for doc in documents for n in doc["@graph"]}
    label = lambda ref: index[ref].get("label", ref)
    kind = lambda name: [n for n in nodes if "phv:" + name in as_list(n.get("@type", []))]
    refs = lambda n: ", ".join(f"`{v}`" for v in as_list(n.get("groundedIn", [])))
    out = ["# MetaHumotonic Foundation — 자유·경제·합의와 Ultra Safety AI", "",
           "> 사용자 직접 출처 + AI 해석·연구 설계 · G0 · 2026-10-03", "",
           "정본 데이터는 [philosophy.jsonld](graph/philosophy.jsonld)이며 이 문서는 그 생성 뷰다. "
           "사용자가 밝힌 목적과 AI가 제안한 의미·실험을 구분한다. 그래프 구축 요청은 AI 세부안 전체의 비준으로 해석하지 않는다.", "",
           "## 사용자가 밝힌 목적", "", "> " + index["ph:C_mission"]["span"], "",
           "— 사용자, `ph:u_purpose` → `ph:C_mission`. 원문의 `Ultra Safty AI` 표기는 그대로 보존한다. "
           "문서 표제는 기존 헌장의 `Ultra Safety AI`를 따른다.", "",
           "[원문 기록](records/2026-10-03/philosophy-sources.json)에 전체 사용자 메시지와 AI 분석 발췌를 역할·해시와 함께 보존한다.", "",
           "### 소프트웨어 저작권과 컴퓨팅·메모리 자원", "",
           "> " + index["ph:C_resource_purpose"]["span"], "",
           "— 사용자, `ph:u_resource_purpose` → `ph:C_resource_purpose`. "
           "[추가 원문](records/2026-10-03/resource-purpose-source.json)을 별도 보존하며 앞선 목적을 덮어쓰지 않는다.", "",
           "문서상 정리(AI): 소프트웨어 저작권을 통해 **재단 운영 주체가 제어 가능한 컴퓨팅과 메모리 자원을 지속적으로 늘리는 것**이 "
           "사용자가 추가로 밝힌 조직 목적이다. 이 진술은 기존 자유·경제·합의와 Ultra Safety AI 개발 목적에 함께 연결된다. "
           "어떤 자원과 권한이 실제 확보됐는지, 그 확장이 안전성에 도움이 되는지는 별도의 관측과 평가 대상이다. "
           "조직 목적의 기록이 AI 에이전트에게 무기한 자원 확보를 맡기거나 실제 접근을 승인하지 않는다.", "",
           "```mermaid", "flowchart LR", '  U[사용자 원문] --> C[철학 명제]',
           '  C --> I[AI 해석 · 제안]', '  I --> M[기존 구현 프로젝트 참조]',
           '  I --> H[미검증 연구 가설]', '  H --> E[미실행 비교 실험]',
           '  I --> Q[열린 질문 · 긴장]', "```", "",
           "## 철학의 서술과 개발 방향", "",
           "다음 서술은 **SECONDARY_AI / PROPOSED**다. 원문에 연결된 해석이며 사용자 발언 자체나 검증된 성과가 아니다.", ""]
    for n in kind("Interpretation"):
        out += [f"### {n['label']}", "", n["text"], "", f"출처: {refs(n)} · 분석 원문: `{n['derivedFrom']}`.", ""]
    out += ["## 기존 정신·경제 그래프와의 연결", "",
            "하드웨어의 중요성·공유 조건·USL/P2P·CHU/HSWM 안의 자유·경제·합의는 기존 `sp:P1`–`sp:P6`와 "
            "`sp:u1`을 재사용한다. MetaHumoCoin 필요성은 `eco:C_coin` → `eco:u_coin`, 실제 구현 요청은 "
            "`mhc:C_real_coin` → `mhc:u_real_coin`으로 연결한다. 기존 AI 요약 `sp:P8`이나 재진술 `sp:R3`를 사용자 채택으로 승격하지 않는다.", "",
            "| 설계 연결 | 기존 식별자 | 역할과 한계 |", "|---|---|---|"]
    for n in kind("ImplementationMapping"):
        out.append(f"| {n['label']} | {', '.join('`'+v+'`' for v in as_list(n['implementsWith']))} | {n['text']} |")
    out += ["", "모든 연결 상태는 **CANDIDATE**다. 이름의 유사성, 링크 또는 그래프 연결은 동일성·배포·접근 권한의 증거가 아니다.", "",
            "## 연구 가설과 반증 가능성", ""]
    for n in kind("ResearchHypothesis"):
        out += ["> " + n["text"], "", "상태: **UNVERIFIED** · AI 제안.", "", n["hypothesisTest"], ""]
    out += ["## 풀어야 할 긴장", ""]
    for n in kind("Tension"):
        out += [f"### {n['label']}", "", n["text"], "", f"관련 원문: {refs(n)} · 열린 질문: {', '.join(n['openQuestion'])}.", ""]
        for ref in as_list(n.get("compares", [])):
            obs = index[ref]
            artifact = index[obs["artifact"]]
            out += [f"- [{artifact['path']}]({artifact['path']}): “{obs['excerpt']}”"]
        if n.get("compares"):
            out.append("")
    out += ["## 실험 설계", ""]
    for n in kind("EvaluationPlan"):
        out += [n["text"], "", f"**NOT_RUN** · `{n['@id']}` → `{n['testsHypothesis']}`", "",
                "기준선: " + n["baseline"], "", "변경 조건: " + n["treatment"], "", "필요한 증거: " + n["expectedEvidence"], ""]
    out += ["| 시나리오 | 기준선 → 변경 조건 | 실패·반증 관측 | 지표 |", "|---|---|---|---|"]
    for n in kind("EvaluationCase"):
        out.append(f"| {n['label']} | {n['baseline']} → {n['treatment']} | {n['failureCondition']} | {', '.join(label(m) for m in n['usesMetric'])} |")
    out += ["", "모든 시나리오는 **NOT_RUN**이다. 그래프 검사 통과, 기존 경제 시뮬레이션과 실제 AI 안전성 실험을 구별한다.", "",
            "기존 경제 실행기의 **유한한 로컬 프로토콜 탐침**은 별도로 실행했다. "
            "[관측 결과](records/2026-10-03/protocol-probes.md)와 [재현 입력·사건·소스 해시](records/2026-10-03/protocol-probes.json)를 남긴다. "
            "이는 위 AI 비교 실험의 완료가 아니며, 허위 결과 검증과 실행 중 단독 철회의 부족점도 기록한다.", "",
            "| 지표 | 단위 | 계산·관측 규칙 |", "|---|---|---|"]
    for n in kind("Metric"):
        out.append(f"| {n['label']} | {n['unit']} | {n['calculation']} |")
    out += ["", "## 열린 결정", ""]
    for n in kind("OpenQuestion"):
        out.append(f"- **{n['@id']} · {n['label']} — OPEN:** {n['text']}")
    out += ["", "## 출처와 그래프 계약", "", index["ph:graph"]["controlCard"], "",
            "[어휘](graph/philosophy-vocab.ttl)는 관계별 방향·domain/range·카디널리티를 정의하고 "
            "[SHACL 제약](graph/philosophy.shapes.ttl)이 적용한다. "
            "[SPARQL 역량 질문](graph/philosophy-queries.json)은 반환 주체·관계·출처를 정확한 기대값과 대조한다.", "",
            "| 고정 입력 | 기록 상태 | SHA-256 |", "|---|---|---|"]
    for n in kind("SourceArtifact"):
        out.append(f"| [{n['path']}]({n['path']}) | {n['artifactState']} | `{n['sha256']}` |")
    out += ["", "WORKTREE_SNAPSHOT은 기록 당시 미커밋 입력이다. 파일 경로나 현재 시각을 영구 식별자로 쓰지 않는다. "
            "기존 원문·그래프를 덮어쓰지 않으며, 현재 공유 KG에서 `metahumotonic-foundation` 검색 결과가 없어 재단 정체성을 임의로 병합하지 않았다.", "",
            "공식 표준과 연구 참고 자료:", ""]
    for n in nodes:
        if n.get("@type") == "mhv:SourceDocument":
            out.append(f"- [{n['label']}]({n['source']}) — {n['dcterms:hasVersion']}; 확인일 2026-10-03.")
    out += ["", "연구 문헌은 협력과 다중 에이전트 위험을 고려할 참고 근거다. 메타휴모토닉의 안전성을 입증한 실험으로 쓰지 않는다.", "",
            "## 재현", "", "```sh", "python3 -m venv /tmp/metahumotonic-graph-venv",
            "/tmp/metahumotonic-graph-venv/bin/python -m pip install -r graph/requirements.txt",
            "/tmp/metahumotonic-graph-venv/bin/python graph/check_philosophy.py",
            "/tmp/metahumotonic-graph-venv/bin/python graph/check.py", "```", "",
            "뷰 갱신은 `graph/check_philosophy.py --write-view`를 사용한다. JSON-LD 파싱, "
            "SHACL/meta-SHACL, 출처·해시·관계 계약, 정확한 SPARQL 결과, 고의 오류 검출과 생성 뷰 동기화를 검사한다. "
            "입력이 바뀌면 근거와 변경 이력을 검토한 뒤 새 스냅샷으로 갱신하며, 해시 불일치를 자동으로 덮어쓰지 않는다.", ""]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-view", action="store_true", help="regenerate PHILOSOPHY.md after validation")
    args = parser.parse_args()
    documents, graph, shapes, vocab = load()
    check_integrity(graph, vocab)
    ok, _, report = validate(graph, shacl_graph=shapes, meta_shacl=True)
    require(ok, report)
    cqs = competency_questions(graph)
    negatives = negative_checks(graph, shapes, vocab, documents)
    expected = render(documents[-1], documents)
    if args.write_view:
        VIEW.write_text(expected, encoding="utf-8")
    require(VIEW.exists() and VIEW.read_text(encoding="utf-8") == expected,
            "PHILOSOPHY.md drift: run graph/check_philosophy.py --write-view")
    print(f"philosophy: SHACL/meta-SHACL PASS; {cqs} exact CQs; {negatives} negative cases; "
          f"source/authority/view integrity PASS ({len(graph)} combined triples); safety experiments NOT_RUN")


if __name__ == "__main__":
    main()
