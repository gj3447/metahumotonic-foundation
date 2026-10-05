#!/usr/bin/env python3
"""Offline graph checks and deterministic ECONOMY.md view generation.

Install graph/requirements.txt in a virtual environment. Run from any directory:
  python graph/check.py                 # verify data, views and negative cases
  python graph/check.py --write-view    # refresh ECONOMY.md, then verify
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from rdflib.namespace import OWL, SKOS

import check_economy_flow

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BASE = "https://github.com/gj3447/metahumotonic-foundation/"
MHV = Namespace(BASE + "vocab#")
ECO = Namespace(BASE + "graph/economy#")
SP = Namespace(BASE + "graph/spirit#")
EX = Namespace(BASE + "graph/economy-example#")
PROV = Namespace("http://www.w3.org/ns/prov#")
SH = Namespace("http://www.w3.org/ns/shacl#")
DATA_PATHS = [HERE / "spirit.jsonld", HERE / "economy.jsonld", HERE / "fixtures/economy-flow.jsonld"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_document(path):
    document = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_keys)
    require(isinstance(document["@context"], dict), f"remote/list context: {path}")
    require("@import" not in document["@context"], f"remote context import: {path}")
    ids = [node["@id"] for node in document["@graph"]]
    require(len(ids) == len(set(ids)), f"duplicate node IDs in {path}")
    return document


def load_graph(documents):
    graph = Graph()
    for doc in documents:
        graph.parse(data=json.dumps(doc, ensure_ascii=False), format="json-ld")
    return graph


def shapes():
    result = Graph()
    for name in ["spirit.shapes.ttl", "economy.shapes.ttl", "economy-flow.shapes.ttl"]:
        result.parse(HERE / name)
    return result


def check_integrity(graph):
    vocab = Graph()
    for name in ["vocab.ttl", "economy-vocab.ttl", "economy-flow-vocab.ttl", "economy-simulation-vocab.ttl", "metahumocoin-vocab.ttl"]:
        vocab.parse(HERE / name)
    subjects = set(graph.subjects())
    for subject, predicate, obj in graph:
        if str(predicate).startswith(str(MHV)):
            require((predicate, RDF.type, RDF.Property) in vocab,
                    f"unregistered predicate: {predicate}")
        if predicate == RDF.type and str(obj).startswith(str(MHV)):
            require((obj, RDF.type, RDFS.Class) in vocab, f"unregistered class: {obj}")
        if isinstance(obj, URIRef) and str(obj).startswith(BASE + "graph/"):
            require(obj in subjects, f"dangling endpoint: {subject} {predicate} {obj}")
        require(predicate not in (OWL.sameAs, SKOS.exactMatch),
                f"identity/equivalence outside this design profile: {subject}")
    for utterance in graph.subjects(MHV.verbatim, None):
        raw = str(graph.value(utterance, MHV.verbatim))
        require(hashlib.sha256(raw.encode("utf-8")).hexdigest()
                == str(graph.value(utterance, MHV.sha256)), f"source hash: {utterance}")
    for artifact in graph.objects(ECO.graph, MHV.usesArtifact):
        path = (REPO / str(graph.value(artifact, MHV.path))).resolve()
        require(path.is_relative_to(REPO), f"source artifact outside owner: {path}")
        require(hashlib.sha256(path.read_bytes()).hexdigest()
                == str(graph.value(artifact, MHV.sha256)), f"source artifact changed: {path}")
    # Validate declared domains/ranges without using inference to repair bad data.
    for predicate in set(graph.predicates()):
        for subject, obj in graph.subject_objects(predicate):
            for domain in vocab.objects(predicate, RDFS.domain):
                if domain != RDFS.Resource:
                    require((subject, RDF.type, domain) in graph,
                            f"predicate domain: {predicate} on {subject}")
            for range_ in vocab.objects(predicate, RDFS.range):
                if range_ == RDFS.Resource:
                    continue
                if str(range_).startswith(str(XSD)) or range_ == RDF.JSON:
                    require(isinstance(obj, Literal) and
                            (obj.datatype == range_ or (range_ == XSD.string and obj.datatype is None)),
                            f"predicate datatype: {predicate} -> {obj}")
                else:
                    require((obj, RDF.type, range_) in graph,
                            f"predicate range: {predicate} -> {obj}")


PREFIX = f"""PREFIX mhv: <{MHV}>
PREFIX eco: <{ECO}>
PREFIX sp: <{SP}>
PREFIX ex: <{EX}>
PREFIX prov: <{PROV}>
PREFIX dcterms: <http://purl.org/dc/terms/>
"""


def cq_checks(graph):
    # Compare subjects AND provenance paths, not just counts.
    queries = [
        ("coin source", "SELECT ?c ?u ?a WHERE { ?c a mhv:Claim ; mhv:topic eco:metahumocoin ; prov:wasDerivedFrom ?u ; prov:wasAttributedTo ?a }",
         {(str(ECO.C_coin), str(ECO.u_coin), str(SP.proposer))}),
        ("freedom source", "SELECT ?c ?u WHERE { ?c a mhv:Claim ; mhv:topic eco:freedom ; prov:wasDerivedFrom ?u }",
         {(str(ECO.C_freedom), str(ECO.u_coin))}),
        ("x402 mapping to source", "SELECT ?p ?m ?s WHERE { ?p mhv:targets eco:settlement ; mhv:borrowsFrom ?m . ?m mhv:implementation eco:x402 ; mhv:sourceDocument ?s }",
         {(str(ECO.D_api), str(ECO.M_x402), str(ECO.src_x402_v2))}),
        ("unresolved money policy", "SELECT ?q WHERE { ?q a mhv:OpenDecision ; mhv:openOn eco:C_coin ; mhv:proposalStatus mhv:OPEN }",
         {(str(ECO[q]),) for q in ["Q_currency", "Q_issuance", "Q_pricing", "Q_charter"]}),
        ("AI proposals", "SELECT ?p ?a WHERE { ?p a mhv:DesignProposal ; mhv:summaryAuthority mhv:SECONDARY_AI ; mhv:proposalStatus mhv:PROPOSED ; prov:wasAttributedTo ?a }",
         {(str(ECO[p]), str(ECO.codex)) for p in ["D_resource", "D_accounting", "D_api", "D_consensus", "D_simulation"]}),
        ("distinct consensus targets", "SELECT ?t WHERE { eco:D_consensus mhv:targets ?t }",
         {(str(ECO[t]),) for t in ["agreement", "community_rules", "ledger_finality"]}),
        ("draft effect", "SELECT ?a ?b WHERE { eco:graph mhv:inEffect ?a ; mhv:governanceEffect ?b }",
         {("false", "false")}),
        ("settlement evidence trace", "SELECT ?r ?a ?u ?e ?amount WHERE { ?r a mhv:SettlementReceipt ; mhv:settlesAgreement ?a ; mhv:basedOnUsage ?u ; mhv:settlementAmount ?amount . ?a mhv:hasExecution ?w . ?w mhv:hasUsage ?u ; mhv:hasResultEvidence ?e }",
         {(str(EX.receipt), str(EX.agreement), str(EX.usage), str(EX.result), "6")}),
        ("simulation currency points to concept", "SELECT ?c ?concept WHERE { ex:receipt mhv:denominatedIn ?c . ?c dcterms:references ?concept ; mhv:simulationStatus mhv:SIMULATED }",
         {(str(EX.demo_currency), str(ECO.metahumocoin))}),
    ]
    for name, query, expected in queries:
        got = {tuple(str(value) for value in row) for row in graph.query(PREFIX + query)}
        require(got == expected, f"CQ {name}: expected {expected}; got {got}")
    return len(queries)


def negative_checks(graph, schema):
    cases = [
        ("false user quote", ECO.C_coin, MHV.ExactSourceSpanShape,
         lambda g: g.set((ECO.C_coin, MHV.span, Literal("사용자는 공급량을 확정했다")))),
        ("missing user span", ECO.C_coin, MHV.ClaimProvenanceShape,
         lambda g: g.remove((ECO.C_coin, MHV.span, None))),
        ("AI proposal relabelled user-authored", ECO.D_api, PROV.wasAttributedTo,
         lambda g: g.set((ECO.D_api, PROV.wasAttributedTo, SP.proposer))),
        ("AI proposal declared ratified", ECO.D_api, MHV.proposalStatus,
         lambda g: g.set((ECO.D_api, MHV.proposalStatus, MHV.RATIFIED))),
        ("missing external source", ECO.M_golem, MHV.sourceDocument,
         lambda g: g.remove((ECO.M_golem, MHV.sourceDocument, None))),
        ("concept declared implementation", ECO.metahumocoin, MHV.CoinConceptShape,
         lambda g: g.add((ECO.metahumocoin, RDF.type, MHV.Project))),
        ("unknown target", ECO.D_api, MHV.targets,
         lambda g: g.set((ECO.D_api, MHV.targets, ECO.missing_target))),
        ("governance promotion", ECO.graph, MHV.governanceEffect,
         lambda g: g.set((ECO.graph, MHV.governanceEffect, Literal(True)))),
    ]
    for name, focus, path_or_shape, mutate in cases:
        bad = copy.deepcopy(graph)
        mutate(bad)
        ok, results, report = validate(bad, shacl_graph=schema)
        caught = any(results.value(result, SH.focusNode) == focus and
                     (results.value(result, SH.resultPath) == path_or_shape or
                      results.value(result, SH.sourceShape) == path_or_shape)
                     for result in results.subjects(RDF.type, SH.ValidationResult))
        require(not ok and caught, f"negative case not caught as expected: {name}\n{report}")
    for name, mutate in [
        ("changed original hash", lambda g: g.set((ECO.u_coin, MHV.sha256, Literal("0" * 64)))),
        ("unknown predicate", lambda g: g.add((ECO.C_coin, MHV.misspelledTopic, ECO.metahumocoin))),
        ("false identity", lambda g: g.add((ECO.metahumocoin, OWL.sameAs, ECO.golem))),
    ]:
        bad = copy.deepcopy(graph)
        mutate(bad)
        try:
            check_integrity(bad)
        except ValueError:
            pass
        else:
            raise ValueError(f"negative integrity case not caught: {name}")
    return len(cases) + 3


def render(document):
    nodes = {node["@id"]: node for node in document["@graph"]}
    def typed(kind):
        return [node for node in nodes.values() if kind in
                (node["@type"] if isinstance(node["@type"], list) else [node["@type"]])]
    def cell(text):
        return text.replace("|", "\\|").replace("\n", " ")
    out = [
        "# MetaHumoCoin — 자유의 기반에서 경제의 설계로", "",
        "> CONSIDERATION · G0 설계/근거 그래프 · 규범 효력 없음 · 2026-10-02", "",
        "이 문서는 [economy.jsonld](graph/economy.jsonld)에서 생성한다. 사용자 원문, 외부 공식 문서에 대한 관측, AI의 적용 제안을 각각 구분한다. `python graph/check.py --write-view`로 갱신한다.", "",
        "## 철학과 직접 출처", "",
        "하드웨어와 접근 권한의 공유, USL/P2P 연결, CHU·HSWM 안의 자유·경제·합의가 기존 정신의 맥락이다. 이번 사용자는 그 기반으로 자유가 충족되며 경제에는 MetaHumoCoin이 필요하다고 덧붙였다. 기존 P3의 전체 권한 공유 주장은 그대로 참조하며, 과거 AI 검토안 R3를 사용자에게 채택된 뜻으로 바꾸지 않는다.", "",
        "> " + nodes["eco:u_coin"]["verbatim"], "",
        "— 사용자, 2026-10-01 (`eco:u_coin`; 원문 UTF-8 SHA-256을 검사한다).", "",
    ]
    for node in typed("mhv:Claim"):
        out += [f"- **{node['@id']}**: {node['text']} 원문 구간: “{node['span']}”."]
    out += ["", "화폐 개념 `eco:metahumocoin`과 이를 실현할 실제 구현 프로젝트 `mhc:project`를 구별한다. 사용자가 명확히 한 실제 코인 구현 목표, 원장·발행·지갑·정산 설계와 테스트넷/메인넷 작업은 [METAHUMOCOIN.md](METAHUMOCOIN.md)에 연결했다. 아래 경제 비교와 시뮬레이터는 그 구현의 보조 자료다. 특정 체인·공급량·분배 규칙은 아직 결정하지 않았다.", "",
            "## 외부 구현체에서 참고한 구조", "",
            "2026-10-02 공식 문서와 구현 저장소를 확인했다. `DOCUMENTED`는 문서를 읽었다는 상태이고, 로컬 연동이나 성능 검증 상태가 아니다. 아래 적용은 모두 AI 설계 후보다.", "",
            "| 구현·메커니즘 | 확인한 내용 | 적용 범위의 한계 | 근거 |", "|---|---|---|---|"]
    for node in typed("mhv:DocumentedMechanism"):
        impl = nodes[node["implementation"]]
        sources = " · ".join(f"[{nodes[s]['label']}]({nodes[s]['source']})" for s in node["sourceDocument"])
        out += [f"| [{cell(node['label'])}]({impl['source']}) | {cell(node['text'])} | {cell(node['limitation'])} | {sources} |"]
    out += ["", "구현 저장소의 관측 커밋: " + " · ".join(
        f"[{node['label']} `{node['revision'][:8]}`]({node['references']})" for node in typed("mhv:ExternalImplementation")) + ".", "",
            "x402 규격은 커밋을 고정했다. Golem·Akash 문서는 버전 없는 웹 문서여서 관측일을 기록하며, 이후 변경 가능성이 있다. 구현 커밋은 소스 위치를 식별한 것이며, 기능 설명은 공식 문서에 근거한다. 이 비교는 코드 라이선스 검토나 통합 시험을 대신하지 않는다.", "",
            "## 메타휴모토닉에 적용한 설계 후보", ""]
    for node in typed("mhv:DesignProposal"):
        out += [f"### {node['@id']} — {node['label']}", "", node["text"], "", node["limitation"], "",
                "근거 명제: " + ", ".join(f"`{x}`" for x in node["basedOn"]) + ". 참고 메커니즘: " + ", ".join(f"`{x}`" for x in node["borrowsFrom"]) + ".", ""]
    out += ["## 검증 가능한 가상 거래 예제", "",
            "[거래 예제](graph/fixtures/economy-flow.jsonld)는 아래 관계를 가진다. 예제의 모든 실행·거래 노드는 `SIMULATED`다. 예제 통화는 MetaHumoCoin 구상을 참조하는 가상 표시 단위이고, 실제 코인을 발행하거나 전송하지 않는다.", "",
            "```mermaid", "flowchart LR", '  offer["자원 제공 조건"] --> agreement["동일 버전에 양측 동의"]',
            '  agreement --> work["작업"]', '  work --> usage["사용량 관측"]', '  work --> result["결과 판정·근거"]',
            '  usage --> receipt["정산 영수증"]', '  result --> receipt', '  agreement --> receipt', "```", "",
            "가상 사용량 3 × 합의한 가상 단가 2 = 정산 6을 `Decimal`로 검사한다. 당사자 동의, 결과 수락, 정산 연결과 중복 청구도 확인한다. 이 정적 예제는 한 작업을 한 번 전액 정산한 형태다. 실행 가능한 상태 전이와 취소·분쟁 정산은 아래 로컬 시뮬레이터에서 확장한다. SHACL 통과는 그래프 일관성만 뜻하며 실제 작업의 정확성이나 경제 성립을 증명하지 않는다.", "",
            "## 실행 가능한 로컬 경제 시뮬레이터", "",
            "[실행 방법과 실험 정책](economy/README.md) · [시뮬레이터](economy/simulator.py) · [상태 전이 그래프 제약](graph/economy-simulation.shapes.ttl). `eco:D_simulation`의 SECONDARY_AI/PROPOSED 구현이다.", "",
            "`python3 -m economy demo --output-dir /tmp/metahumotonic-economy-demo`로 정상 정산·실행 전 취소·양측 합의에 의한 분쟁 정산을 재현한다. 데모의 총 가상 잔액 100은 최종 90·10·0으로 보존되고 예약 잔액은 0이다. 정산 재요청은 중복 지급 없이 같은 영수증을 반환한다.", "",
            "실행 결과에는 초기 입력, 명령 목록, 최종 상태, 해시 체인 이벤트와 소스 파일 해시가 들어간다. `python3 -m economy verify /tmp/metahumotonic-economy-demo/simulation.json`은 같은 명령을 다시 실행해 상태와 이벤트의 일치를 확인한다. JSON-LD 실행 기록은 사용자 원문까지 이어지는 설계 제안 참조를 가진다. 이 기록은 실험용 거래이고 실제 서명·원장 결제·작업 수행을 증명하지 않는다.", "",
            "## 아직 결정하지 않은 정책", ""]
    for node in typed("mhv:OpenDecision"):
        out += [f"- **{node['@id']}**: {node['text']}"]
    out += ["", "헌장·참여 약정은 이 작업으로 개정하지 않는다. `Q_charter`는 실제 도입 범위와 현재 규범의 정합성을 판단할 연결점이다. 현재 비약속은 연구·구현 자체의 금지로 확대하지 않는다. 구체적인 구현 결정은 [실제 코인 엔지니어링 그래프](METAHUMOCOIN.md)에서 추적한다. 기존 AI의 암호화폐 요약 P8이나 검토 판정 X11을 새 사용자 발언의 뜻으로 상속하지 않는다.", "",
            "## 그래프 계약과 재현", "",
            "- **형식:** [JSON-LD 1.1](https://www.w3.org/TR/json-ld11/)의 RDF 직렬화, [PROV-O](https://www.w3.org/TR/prov-o/)의 출처·작성자·작성 활동, [SHACL](https://www.w3.org/TR/shacl/) 제약, [SPARQL 1.1](https://www.w3.org/TR/sparql11-query/) 역량 질문.",
            "- **소유·범위:** 이 저장소의 로컬 G0 설계. 공유 KG 게시·실행 그래프·서비스 배포를 의미하지 않는다. 새 IRI는 이 저장소의 `graph/economy#` 범위를 쓰고 기존 `sp:` IRI는 재사용한다.",
            "- **계약:** [설계 어휘](graph/economy-vocab.ttl)·[설계 shapes](graph/economy.shapes.ttl), [거래 어휘](graph/economy-flow-vocab.ttl)·[거래 shapes](graph/economy-flow.shapes.ttl). 방향·domain/range·카디널리티를 명시한다.",
            "- **출처 분리:** `Claim → Utterance`, `DesignProposal → basedOn Claim / borrowsFrom DocumentedMechanism → SourceDocument`. 사용자 원문으로 돌아갈 수 있고 AI 제안의 귀속을 자동으로 승격하지 않는다.",
            "- **기존 자료:** `spirit.jsonld`의 기존 바이트·UID·원문은 보존한다. 기존 SPIRIT/YAML과 JSON-LD 간 전체 동기화는 이번 확장의 범위 밖이며, 이 문서는 경제 확장만의 생성 뷰다.", "",
            "```sh", "python3 -m venv /tmp/metahumotonic-graph-venv", "/tmp/metahumotonic-graph-venv/bin/pip install -r graph/requirements.txt", "python3 -m unittest discover -s economy -t .", "/tmp/metahumotonic-graph-venv/bin/python graph/check.py", "/tmp/metahumotonic-graph-venv/bin/python records/2026-09-29/check.py", "```", "",
            "검사기는 UID/JSON 키 중복, 등록된 술어·타입, 단절된 참조, domain/range, 원문·입력 파일 해시, SHACL 양성·음성 사례, 역량 질문과 이 문서의 생성 결과 일치를 확인한다. 네트워크에 접속하지 않는다. 외부 문서가 여전히 같은 내용인지, 실제 자원 권한·경제 동작이 유효한지는 별도 검증이다.", "",
            "역량 질문은 코인과 자유의 직접 출처, 외부 구현→설계 연결, 미결정 통화 정책, AI 제안의 작성자, 세 합의의 구분, 규범 효력 여부, 정산의 계약·사용량·결과 근거, 예제 통화의 참조를 정확한 주체·출처 조합으로 검사한다.", ""]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-view", action="store_true")
    args = parser.parse_args()
    documents = [read_document(path) for path in DATA_PATHS]
    graph = load_graph(documents)
    schema = shapes()
    check_integrity(graph)
    ok, _, report = validate(graph, shacl_graph=schema, meta_shacl=True)
    require(ok, report)
    count = cq_checks(graph)
    negatives = negative_checks(graph, schema)
    expected = render(documents[1])
    view = REPO / "ECONOMY.md"
    if args.write_view:
        view.write_text(expected, encoding="utf-8")
    require(view.exists() and view.read_text(encoding="utf-8") == expected,
            "ECONOMY.md drift: run graph/check.py --write-view")
    check_economy_flow.main()
    print(f"economy: SHACL/meta-SHACL PASS; {count} CQs; {negatives} isolated negative cases; source integrity and generated view PASS ({len(graph)} triples)")
    subprocess.run([sys.executable, str(HERE / "check_economy_simulation.py")], check=True)
    subprocess.run([sys.executable, str(HERE / "check_metahumocoin.py")]
                   + (["--write-view"] if args.write_view else []), check=True)
    subprocess.run([sys.executable, str(HERE / "check_philosophy.py")]
                   + (["--write-view"] if args.write_view else []), check=True)
    subprocess.run([sys.executable, str(HERE / "check_resource_roadmap.py")]
                   + (["--write-view"] if args.write_view else []), check=True)
    subprocess.run([sys.executable, str(HERE / "check_market.py")], check=True)
    subprocess.run([sys.executable, str(HERE / "check_ecosystem.py")]
                   + (["--write-view"] if args.write_view else []), check=True)
    subprocess.run([sys.executable, str(HERE / "check_foundation_rationale.py")], check=True)
    subprocess.run([sys.executable, str(HERE / "check_compute_coin.py")], check=True)


if __name__ == "__main__":
    main()
