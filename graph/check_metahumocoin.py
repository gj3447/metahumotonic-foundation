#!/usr/bin/env python3
"""Validate the design-only MetaHumoCoin production-engineering graph.

This checker intentionally reports release *readiness gaps*.  It never turns a
design graph, a simulated receipt, or a passing schema check into deployment
approval.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from rdflib.namespace import SH

import check as base_check


HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BASE = "https://github.com/gj3447/metahumotonic-foundation/"
MHV = Namespace(BASE + "vocab#")
ECO = Namespace(BASE + "graph/economy#")
MHC = Namespace(BASE + "graph/metahumocoin#")
PROV = Namespace("http://www.w3.org/ns/prov#")

DATA_PATHS = [*base_check.DATA_PATHS, HERE / "metahumocoin.jsonld"]
VOCAB_PATHS = [
    HERE / "vocab.ttl", HERE / "economy-vocab.ttl",
    HERE / "economy-flow-vocab.ttl", HERE / "economy-simulation-vocab.ttl",
    HERE / "metahumocoin-vocab.ttl",
]
SHAPE_PATHS = [
    HERE / "spirit.shapes.ttl", HERE / "economy.shapes.ttl",
    HERE / "economy-flow.shapes.ttl", HERE / "metahumocoin.shapes.ttl",
]

PREFIX = f"""PREFIX mhv: <{MHV}>
PREFIX eco: <{ECO}>
PREFIX mhc: <{MHC}>
PREFIX prov: <{PROV}>
"""

REQUIREMENTS = [
    "R_resource", "R_asset", "R_supply", "R_signing", "R_payment",
    "R_contribution", "R_authority", "R_release", "R_scope",
]
DECISIONS = [
    "Q_architecture", "Q_supply", "Q_distribution", "Q_verification",
    "Q_dispute", "Q_controls", "Q_network", "Q_scope",
]
WORK_PACKAGES = [
    "W_policy", "W_interfaces", "W_ledger", "W_signing", "W_contribution",
    "W_settlement", "W_integration", "W_ledger_testnet", "W_testnet", "W_mainnet",
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_documents():
    return [base_check.read_document(path) for path in DATA_PATHS]


def load_shapes():
    shapes = Graph()
    for path in SHAPE_PATHS:
        shapes.parse(path)
    return shapes


def load_vocab():
    vocab = Graph()
    for path in VOCAB_PATHS:
        vocab.parse(path)
    return vocab


def graph_with_documents(documents):
    return base_check.load_graph(documents)


def check_registered_terms(graph):
    """Run the existing profile, then include terms introduced by this graph."""
    base_check.check_integrity(graph)
    vocab = load_vocab()
    for subject, predicate, obj in graph:
        if str(predicate).startswith(str(MHV)):
            require((predicate, RDF.type, RDF.Property) in vocab,
                    f"unregistered predicate: {predicate}")
        if predicate == RDF.type and str(obj).startswith(str(MHV)):
            require((obj, RDF.type, RDFS.Class) in vocab,
                    f"unregistered class: {obj}")


def values(graph, query):
    return {tuple(str(value) for value in row) for row in graph.query(PREFIX + query)}


def exact(graph, name, query, expected):
    got = values(graph, query)
    require(got == expected, f"CQ {name}: expected {expected}; got {got}")


def source_hashes(graph):
    """Verify local artifacts when the graph makes a byte-digest assertion.

    The design graph's user utterance hashes are checked by ``check_integrity``.
    The old simulator is a supporting implementation; it is not silently made a
    production artifact merely because this graph refers to it.
    """
    for artifact in graph.subjects(MHV.sha256, None):
        relative = graph.value(artifact, MHV.path)
        digest = graph.value(artifact, MHV.sha256)
        if not relative:
            continue
        path = (REPO / str(relative)).resolve()
        require(path.is_relative_to(REPO), f"MHC artifact outside owner: {path}")
        require(path.exists(), f"MHC artifact missing: {path}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        require(actual == str(digest), f"MHC source artifact changed: {path}")
    charter = MHC.charter
    quote = graph.value(charter, MHV.quote)
    if quote is not None:
        path = (REPO / str(graph.value(charter, MHV.path))).resolve()
        require(str(quote) in path.read_text(encoding="utf-8"),
                "MHC Charter quote is not in its declared source")


def dag(graph, predicate, nodes, label):
    """Require a directed dependency relation to have no cycle among its nodes."""
    node_set = set(nodes)
    edges = {node: set() for node in node_set}
    for source, target in graph.subject_objects(predicate):
        if source in node_set and target in node_set:
            edges[source].add(target)
    visiting, visited = set(), set()

    def walk(node, trail):
        if node in visiting:
            cycle = " -> ".join(str(x) for x in [*trail, node])
            raise ValueError(f"{label} cycle: {cycle}")
        if node in visited:
            return
        visiting.add(node)
        for target in edges[node]:
            walk(target, [*trail, node])
        visiting.remove(node)
        visited.add(node)

    for node in node_set:
        walk(node, [])


def cq_checks(graph):
    project = str(MHC.project)
    exact(graph, "candidate project traces both coin claims",
          "SELECT ?project ?concept ?claim WHERE { ?project a mhv:CurrencyProject ; mhv:implementsConcept ?concept ; mhv:intentClaim ?claim }",
          {(project, str(ECO.metahumocoin), str(MHC.C_real_coin)),
           (project, str(ECO.metahumocoin), str(ECO.C_coin))})
    exact(graph, "real coin claim provenance",
          "SELECT ?c ?u ?a WHERE { VALUES ?c { mhc:C_real_coin } ?c prov:wasDerivedFrom ?u ; prov:wasAttributedTo ?a }",
          {(str(MHC.C_real_coin), str(MHC.u_real_coin), str(base_check.SP.proposer))})
    exact(graph, "project requirements", "SELECT ?r WHERE { mhc:project mhv:hasRequirement ?r }",
          {(str(MHC[name]),) for name in REQUIREMENTS})
    exact(graph, "project decisions", "SELECT ?d WHERE { mhc:project mhv:hasDecision ?d }",
          {(str(MHC[name]),) for name in DECISIONS})
    exact(graph, "project work plan", "SELECT ?w WHERE { mhc:project mhv:hasWork ?w }",
          {(str(MHC[name]),) for name in WORK_PACKAGES})
    exact(graph, "release targets", "SELECT ?r ?stage WHERE { mhc:project mhv:hasRelease ?r . ?r mhv:releaseStage ?stage }",
          {(str(MHC.testnet), "TESTNET"), (str(MHC.mainnet), "MAINNET")})
    exact(graph, "testnet criterion contract", "SELECT ?c WHERE { mhc:testnet mhv:releaseCriterion ?c }",
          {(str(MHC[name]),) for name in ["A_policy", "A_interface", "A_ledger", "A_signature", "A_proof", "A_escrow", "A_integration", "A_build", "A_testnet", "A_token_testnet"]})
    exact(graph, "mainnet criterion contract", "SELECT ?c WHERE { mhc:mainnet mhv:releaseCriterion ?c }",
          {(str(MHC[name]),) for name in ["A_policy", "A_interface", "A_ledger", "A_signature", "A_proof", "A_escrow", "A_integration", "A_build", "A_review", "A_operations", "A_mainnet"]})
    exact(graph, "all decisions remain open", "SELECT ?d ?status WHERE { mhc:project mhv:hasDecision ?d . ?d mhv:decisionStatus ?status }",
          {(str(MHC[name]), "OPEN") for name in DECISIONS})
    exact(graph, "no decision was selected or receipted",
          "SELECT ?d ?p ?o WHERE { mhc:project mhv:hasDecision ?d . VALUES ?p { mhv:selectedOption mhv:decisionReceipt } . ?d ?p ?o }", set())
    exact(graph, "all criteria are design-only",
          "SELECT ?c ?status WHERE { ?c a mhv:AcceptanceCriterion ; mhv:verificationStatus ?status }",
          {(str(row[0]), "NOT_RUN") for row in graph.query(PREFIX + "SELECT ?c WHERE { ?c a mhv:AcceptanceCriterion }")})
    exact(graph, "no evidence asserts release readiness",
          "SELECT ?e WHERE { ?e a mhv:EvidenceArtifact }", set())
    exact(graph, "simulator remains escrow-only support",
          "SELECT ?component WHERE { mhc:simulation mhv:exercises ?component }", {(str(MHC.C_escrow),)})
    exact(graph, "payment and issuance remain separate policy paths",
          "SELECT ?payment ?issuance WHERE { mhc:C_escrow mhv:implementsPolicy ?payment . mhc:C_ledger mhv:implementsPolicy ?issuance }",
          {(str(MHC.P_agreement), str(MHC.P_ledger)), (str(MHC.P_agreement), str(MHC.P_issuance)),
           (str(MHC.P_proof), str(MHC.P_ledger)), (str(MHC.P_proof), str(MHC.P_issuance))})
    return 14


def semantic_checks(graph):
    decisions = {MHC[name] for name in DECISIONS}
    work = {MHC[name] for name in WORK_PACKAGES}
    dag(graph, MHV.dependsOnWork, work, "work dependency")
    dag(graph, MHV.dependsOnRelease, {MHC.testnet, MHC.mainnet}, "release dependency")

    for package in work:
        paths = set(graph.objects(package, MHV.plannedPath))
        require(paths, f"work package has no planned path: {package}")
        for path in paths:
            portable = Path(str(path))
            require(str(path).strip() and not portable.is_absolute() and ".." not in portable.parts,
                    f"work package has unsafe planned path: {package} -> {path}")
    for decision in decisions:
        options = set(graph.subjects(MHV.optionFor, decision))
        require(len(options) >= 2, f"decision needs at least two alternatives: {decision}")
        selected = set(graph.objects(decision, MHV.selectedOption))
        receipt = set(graph.objects(decision, MHV.decisionReceipt))
        require(not selected and not receipt, f"design-only decision appears adopted: {decision}")
    for component in graph.subjects(RDF.type, MHV.CoinComponent):
        for policy in graph.objects(component, MHV.implementsPolicy):
            controlled_by = set(graph.objects(policy, MHV.policyDecision))
            require(controlled_by and controlled_by <= decisions,
                    f"component policy lacks project decision path: {component} -> {policy}")
        require(any(component in set(graph.objects(work_item, MHV.producesComponent))
                    for work_item in work), f"component is not produced by planned work: {component}")
    for interface in graph.subjects(RDF.type, MHV.InterfaceContract):
        require(any(interface in set(graph.objects(component, MHV.hasInterface))
                    for component in graph.subjects(RDF.type, MHV.CoinComponent)),
                f"interface is unused by a component: {interface}")
    for criterion in graph.subjects(RDF.type, MHV.AcceptanceCriterion):
        linked = any(criterion in set(graph.objects(item, MHV.acceptanceCriterion)) for item in work)
        linked = linked or any(criterion in set(graph.objects(release, MHV.releaseCriterion))
                               for release in (MHC.testnet, MHC.mainnet))
        require(linked, f"acceptance criterion is not attached to work or release: {criterion}")

    # The release status is intentionally a diagnostic, never a deployment claim.
    for release in (MHC.testnet, MHC.mainnet):
        criteria = set(graph.objects(release, MHV.releaseCriterion))
        blocked = set(graph.objects(release, MHV.blockedByDecision))
        require(criteria, f"release has no acceptance criteria: {release}")
        require(blocked, f"release has no open-decision boundary: {release}")
        require(all(graph.value(c, MHV.verificationStatus) == Literal("NOT_RUN") for c in criteria),
                f"design-only release has a non-NOT_RUN criterion: {release}")


def readiness(graph):
    """Return gaps rather than a boolean that could be misread as certification."""
    report = {}
    for release in (MHC.testnet, MHC.mainnet):
        missing = sorted(str(c) for c in graph.objects(release, MHV.releaseCriterion)
                         if graph.value(c, MHV.verificationStatus) != Literal("PASS"))
        open_decisions = sorted(str(d) for d in graph.objects(release, MHV.blockedByDecision)
                                if graph.value(d, MHV.decisionStatus) == Literal("OPEN"))
        report[str(release)] = {"missing_criteria": missing, "open_decisions": open_decisions}
    return report


def negative_checks(graph, shapes):
    architecture_option = next(iter(graph.objects(MHC.Q_architecture, MHV.option)))
    testnet_criterion = next(iter(graph.objects(MHC.testnet, MHV.releaseCriterion)))
    cases = [
        ("wrong user claim span", MHC.C_real_coin, MHV.ExactSourceSpanShape, None,
         lambda g: g.set((MHC.C_real_coin, MHV.span, Literal("사용자가 공급량을 확정했다")))),
        ("wrong user claim author", MHC.C_real_coin, MHV.ExactSourceSpanShape, None,
         lambda g: g.set((MHC.C_real_coin, PROV.wasAttributedTo, MHC.project))),
        ("project loses concept separation", MHC.project, None, MHV.implementsConcept,
         lambda g: g.remove((MHC.project, MHV.implementsConcept, ECO.metahumocoin))),
        ("decision selects without receipt", MHC.Q_architecture, MHV.EngineeringDecisionShape, MHV.selectedOption,
         lambda g: g.add((MHC.Q_architecture, MHV.selectedOption, architecture_option))),
        ("foreign recommended option", MHC.Q_architecture, MHV.EngineeringDecisionShape, None,
         lambda g: g.set((MHC.Q_architecture, MHV.recommendedOption, MHC.O_native_asset))),
        ("work has cyclic dependency", MHC.W_testnet, MHV.WorkPackageShape, MHV.dependsOnWork,
         lambda g: g.add((MHC.W_testnet, MHV.dependsOnWork, MHC.W_mainnet))),
        ("work loses output path", MHC.W_ledger, None, MHV.plannedPath,
         lambda g: g.remove((MHC.W_ledger, MHV.plannedPath, None))),
        ("criterion falsely passed", testnet_criterion, None, MHV.verificationStatus,
         lambda g: g.set((testnet_criterion, MHV.verificationStatus, Literal("PASS")))),
        ("release loses criteria", MHC.testnet, None, MHV.releaseCriterion,
         lambda g: g.remove((MHC.testnet, MHV.releaseCriterion, None))),
        ("mainnet receives testnet-only criterion", MHC.mainnet, MHV.ReleaseTargetShape, None,
         lambda g: g.add((MHC.mainnet, MHV.releaseCriterion, MHC.A_testnet))),
    ]
    caught = 0
    for name, focus, source_shape, result_path, mutate in cases:
        bad = copy.deepcopy(graph)
        mutate(bad)
        ok, results, report = validate(bad, shacl_graph=shapes, advanced=True, meta_shacl=True)
        invalid = any(results.value(result, SH.focusNode) == focus and
                      ((source_shape is not None and results.value(result, SH.sourceShape) == source_shape) or
                       (result_path is not None and results.value(result, SH.resultPath) == result_path))
                      for result in results.subjects(RDF.type, SH.ValidationResult))
        require(not ok and invalid, f"negative case not caught as expected: {name}\n{report}")
        caught += 1
    return caught


def negative_integrity_checks(graph):
    bad = copy.deepcopy(graph)
    bad.set((MHC.simulation, MHV.sha256, Literal("0" * 64)))
    try:
        source_hashes(bad)
    except ValueError:
        pass
    else:
        raise ValueError("negative integrity case not caught: supporting artifact digest")
    bad = copy.deepcopy(graph)
    bad.set((MHC.W_ledger, MHV.plannedPath, Literal("../outside")))
    try:
        semantic_checks(bad)
    except ValueError:
        pass
    else:
        raise ValueError("negative semantic case not caught: unsafe planned path")
    return 2


def node(document, identifier):
    return next(item for item in document["@graph"] if item["@id"] == identifier)


def title(document, identifier):
    item = node(document, identifier)
    return item.get("label", identifier)


def text(document, identifier):
    return node(document, identifier).get("text", "")


def as_list(value):
    return value if isinstance(value, list) else [value]


def render(document, graph):
    """A deterministic human view of the design graph, never a release claim."""
    project = node(document, "mhc:project")
    out = [
        "# MetaHumoCoin — 실제 구현을 위한 설계 그래프", "",
        "> 실제 자산 구현 목표 · 설계 기준선 · 정책 선택과 구현은 진행 전", "",
        "이 문서는 `graph/metahumocoin.jsonld`에서 생성한다. 실제 코드·테스트넷 자산·배포 증거는 아직 없다.", "",
        "## 사용자 요청", "", "> " + node(document, "mhc:u_real_coin")["verbatim"], "",
        "— 사용자, 2026-10-02 (`mhc:u_real_coin`; UTF-8 SHA-256 검증).", "",
        "## 프로젝트와 요구", "",
        project.get("text", "MetaHumoCoin 후보 프로젝트."), "",
        "```mermaid", "flowchart LR",
        "  intent[사용자 의도] --> project[CurrencyProject]",
        "  project --> decisions[열린 결정·대안] --> policies[정책 경계]",
        "  policies --> components[컴포넌트·인터페이스] --> work[계획 작업]",
        "  work --> criteria[NOT_RUN 수용 기준] --> releases[TESTNET / MAINNET 목표]",
        "```", "",
    ]
    for identifier in as_list(project.get("hasRequirement", [])):
        out.append(f"- **{identifier}**: {text(document, identifier)}")
    out += ["", "## 결정과 대안", ""]
    for identifier in as_list(project.get("hasDecision", [])):
        decision = node(document, identifier)
        out += [f"### {identifier} — {decision.get('text', '')}", ""]
        for option in (item for item in document["@graph"] if identifier in as_list(item.get("optionFor", []))):
            refs = ", ".join(as_list(option.get("references", [])))
            suffix = f"; 근거: {refs}" if refs else ""
            out.append(f"- **{option['@id']}**: {option.get('text', '')} (tradeoff: {option.get('tradeoff', '')}){suffix}")
        if decision.get("recommendedOption"):
            out.append(f"- 조건부 권고: {decision['recommendedOption']} — {decision.get('recommendationCondition', '')}")
        else:
            out.append("- 선택 없음: 결정 영수증이 생기기 전에는 어느 대안도 채택된 것으로 읽지 않는다.")
        out.append("")
    out += ["## 관측한 외부 표준", ""]
    for source in (item for item in document["@graph"] if "mhv:SourceDocument" in as_list(item.get("@type", []))):
        out.append(f"- [{source.get('label', source['@id'])}]({source.get('source', '')}) — {source.get('revision', '')}; 관측일 {source.get('observedOn', '')}")
    out.append("")
    out += ["## 정책 경계", ""]
    for policy in (item for item in document["@graph"] if "mhv:CoinPolicy" in as_list(item.get("@type", []))):
        out += [f"### {policy['@id']} — {policy.get('label', '')}", "", policy.get("text", ""), "", f"경계: {policy.get('boundary', '')}", ""]
    out += ["## 컴포넌트·인터페이스·작업 순서", ""]
    components = [item for item in document["@graph"]
                  if "mhv:CoinComponent" in as_list(item.get("@type", []))]
    interfaces = [item for item in document["@graph"]
                  if "mhv:InterfaceContract" in as_list(item.get("@type", []))]
    for component in components:
        out.append(f"- 컴포넌트 **{component['@id']}**: {component.get('text', '')}")
    for interface in interfaces:
        out += [f"### {interface['@id']} — {interface.get('label', '')}", "", interface.get('text', ''), "",
                "| 필드 | 의미 |", "|---|---|"]
        for field, meaning in interface.get("fields", {}).items():
            out.append(f"| `{field}` | {meaning} |")
        out.append("")
    out.append("")
    for identifier in as_list(project.get("hasWork", [])):
        work = node(document, identifier)
        out.append(f"- **{identifier}**: {work.get('text', '')}  ")
        out.append(f"  계획 경로: {', '.join(as_list(work.get('plannedPath', [])))}; 선행 작업: {', '.join(as_list(work.get('dependsOnWork', []))) or '없음'}; 열린 차단 결정: {', '.join(as_list(work.get('blockedByDecision', []))) or '없음'}; 수용 기준: {', '.join(as_list(work.get('acceptanceCriterion', [])))}")
    out += ["", "`W_ledger_testnet`은 원장·지갑의 초기 실제 테스트넷 전송 경로다. 전체 provider/escrow 경제 프로토콜 테스트넷(`mhc:testnet`)과 다르며, 전체 8개 정책 결정을 이미 통과했다고 주장하지 않는다.", ""]
    out += ["", "## 수용 기준", ""]
    for criterion in (item for item in document["@graph"] if "mhv:AcceptanceCriterion" in as_list(item.get("@type", []))):
        out += [f"### {criterion['@id']} — {criterion.get('label', '')}", "",
                f"상태: `{criterion.get('verificationStatus')}` · 예상 증거: {criterion.get('evidenceKind', '')}", "",
                criterion.get('checkProcedure', ''), ""]
    out += ["", "## 릴리스 준비도", "",
            "이 설계 그래프에는 실행 증거가 없다. 아래 목록은 부족한 기준과 열린 결정을 보여 주며, 배포 허가가 아니다.", ""]
    for identifier, gap in readiness(graph).items():
        compact = lambda values: ', '.join(value.rsplit('#', 1)[-1] for value in values)
        out.append(f"### {identifier.rsplit('#', 1)[-1]}")
        out.append("")
        out.append(f"- 미검증 기준: {compact(gap['missing_criteria'])}")
        out.append(f"- 열린 결정: {compact(gap['open_decisions'])}")
        target = node(document, "mhc:" + identifier.rsplit('#', 1)[-1])
        if target.get("dependsOnRelease"):
            out.append(f"- 선행 출시 대상: {target['dependsOnRelease']}")
        out.append("")
    out += ["## 검증", "",
            "그래프 검증에는 `graph/requirements.txt`의 의존성이 필요하다. [ECONOMY.md](ECONOMY.md#그래프-계약과-재현)의 가상환경 설치 뒤 실행한다.", "",
            "```sh", "/tmp/metahumotonic-graph-venv/bin/python graph/check.py", "```", "",
            "검사기는 SHACL/meta-SHACL, 정확한 역량 질문, 작업·릴리스 의존 DAG, 원문·입력 파일 해시, 그리고 의도적으로 손상한 그래프를 검사한다. 통과는 설계 그래프의 일관성만 의미한다.", ""]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-view", action="store_true", help="write METAHUMOCOIN.md from the graph")
    args = parser.parse_args()
    documents = load_documents()
    graph = graph_with_documents(documents)
    shapes = load_shapes()
    check_registered_terms(graph)
    source_hashes(graph)
    ok, _, report = validate(graph, shacl_graph=shapes, advanced=True, meta_shacl=True)
    require(ok, report)
    cqs = cq_checks(graph)
    semantic_checks(graph)
    negatives = negative_checks(graph, shapes) + negative_integrity_checks(graph)
    document = documents[-1]
    view = REPO / "METAHUMOCOIN.md"
    expected = render(document, graph)
    if args.write_view:
        view.write_text(expected, encoding="utf-8")
    require(view.exists() and view.read_text(encoding="utf-8") == expected,
            "METAHUMOCOIN.md drift: run graph/check_metahumocoin.py --write-view")
    gaps = readiness(graph)
    print("metahumocoin: DESIGN graph PASS; "
          f"{cqs} CQs; {negatives} negative cases; "
          f"TESTNET missing={len(gaps[str(MHC.testnet)]['missing_criteria'])}, "
          f"open={len(gaps[str(MHC.testnet)]['open_decisions'])}; "
          f"MAINNET missing={len(gaps[str(MHC.mainnet)]['missing_criteria'])}, "
          f"open={len(gaps[str(MHC.mainnet)]['open_decisions'])}")


if __name__ == "__main__":
    main()
