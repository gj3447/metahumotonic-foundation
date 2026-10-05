"""Deterministic replay bundle and RDF projection of a local simulation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

from .scenarios import replay_commands
from .simulator import SimulationError


BASE = "https://github.com/gj3447/metahumotonic-foundation/"
ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATHS = ["economy/simulator.py", "economy/scenarios.py", "economy/artifacts.py"]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def source_digests():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_PATHS}


def bundle(simulator, initial_balances, commands):
    result = {
        "format": "metahumotonic-simulation/v1",
        "mode": "SIMULATED",
        "initial_balances": deepcopy(initial_balances),
        "commands": deepcopy(commands),
        "snapshot": simulator.snapshot(),
        "events": simulator.export_events(),
        "source_sha256": source_digests(),
    }
    result["bundle_sha256"] = digest(result)
    return result


def verify_bundle(document):
    """Replay supplied inputs. Hashes are integrity checks, not actor signatures."""
    expected_keys = {"format", "mode", "initial_balances", "commands", "snapshot",
                     "events", "source_sha256", "bundle_sha256"}
    if not isinstance(document, dict) or set(document) != expected_keys:
        raise SimulationError("invalid simulation bundle fields")
    if document["format"] != "metahumotonic-simulation/v1" or document["mode"] != "SIMULATED":
        raise SimulationError("unsupported simulation bundle format or mode")
    payload = {key: value for key, value in document.items() if key != "bundle_sha256"}
    if document["bundle_sha256"] != digest(payload):
        raise SimulationError("bundle digest mismatch")
    if document["source_sha256"] != source_digests():
        raise SimulationError("simulator source revision differs from the bundle")
    if not isinstance(document["commands"], list) or not isinstance(document["events"], list):
        raise SimulationError("commands and events must be lists")
    simulator = replay_commands(document["initial_balances"], document["commands"])
    if simulator.snapshot() != document["snapshot"]:
        raise SimulationError("snapshot differs from replay")
    if simulator.export_events() != document["events"]:
        raise SimulationError("event journal differs from replay")
    previous_hash = "0" * 64
    for sequence, event in enumerate(document["events"], start=1):
        if event["sequence"] != sequence or event["previous_hash"] != previous_hash:
            raise SimulationError("event sequence/hash chain mismatch")
        payload = {key: value for key, value in event.items() if key != "event_hash"}
        if digest(payload) != event["event_hash"]:
            raise SimulationError("event digest mismatch")
        previous_hash = event["event_hash"]
    return simulator


def to_jsonld(document):
    """Project a verified bundle with local stable IDs and explicit simulation status."""
    verify_bundle(document)
    document = deepcopy(document)
    # Bind run identity to inputs AND source bytes. Different inputs/revisions do
    # not accidentally identify the same run when graphs are merged.
    namespace = BASE + "graph/economy-simulation/" + document["bundle_sha256"] + "#"
    def iri(kind, name):
        return namespace + kind + "/" + quote(str(name), safe="")
    context = {
        "@version": 1.1, "mhv": BASE + "vocab#", "eco": BASE + "graph/economy#",
        "prov": "http://www.w3.org/ns/prov#", "dcterms": "http://purl.org/dc/terms/",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#", "xsd": "http://www.w3.org/2001/XMLSchema#",
        "@vocab": BASE + "vocab#", "label": "rdfs:label", "comment": "rdfs:comment",
        "simulationStatus": {"@type": "@id"}, "summaryAuthority": {"@type": "@id"},
        "proposalStatus": {"@type": "@id"}, "sourcePath": "mhv:sourcePath",
        "sha256": "mhv:sha256", "state": "mhv:simState",
        "sequence": {"@id": "mhv:eventSequence", "@type": "xsd:integer"},
        "operation": "mhv:eventOperation", "previousHash": "mhv:previousEventHash",
        "eventHash": "mhv:eventHash", "termsHash": "mhv:termsHash",
        "agreementId": "mhv:simAgreementId", "accountId": "mhv:simAccountId",
        "operationId": "mhv:simOperationId", "receiptKind": "mhv:simReceiptKind",
    }
    for alias, predicate in {"snapshot": "simSnapshot", "eventPayload": "simEventPayload",
                              "agreementPayload": "simAgreementPayload", "receiptPayload": "simReceiptPayload"}.items():
        context[alias] = {"@id": "mhv:" + predicate, "@type": "@json"}
    for alias, predicate in {"hasAccount": "hasSimAccount", "hasAgreement": "hasSimAgreement",
                              "hasReceipt": "hasSimReceipt", "hasEvent": "hasSimEvent",
                              "actor": "simActor", "agreement": "simAgreement", "requester": "simRequester",
                              "provider": "simProvider", "previousEvent": "previousSimEvent",
                              "sourceArtifact": "simSourceArtifact"}.items():
        context[alias] = {"@id": "mhv:" + predicate, "@type": "@id"}
    for alias, predicate in {"initialBalance": "simInitialBalance", "availableBalance": "simAvailableBalance",
                              "escrow": "simEscrow", "total": "simTotal", "amount": "simPaid",
                              "refund": "simRefund"}.items():
        context[alias] = {"@id": "mhv:" + predicate, "@type": "xsd:decimal"}
    context["attributedTo"] = {"@id": "prov:wasAttributedTo", "@type": "@id"}
    context["used"] = {"@id": "prov:used", "@type": "@id"}
    context["associatedWith"] = {"@id": "prov:wasAssociatedWith", "@type": "@id"}
    nodes = []
    def add(node_id, types, **values):
        nodes.append({"@id": node_id, "@type": types, "simulationStatus": "mhv:SIMULATED", **values})
    snapshot = document["snapshot"]
    add(namespace + "run", ["prov:Activity", "mhv:SimulationRun"],
        label="MetaHumoCoin local economy simulation", summaryAuthority="mhv:SECONDARY_AI",
        proposalStatus="mhv:PROPOSED", associatedWith=namespace + "software",
        used=["eco:D_simulation"], snapshot=snapshot, sha256=document["bundle_sha256"],
        total=snapshot["total_units"], escrow=snapshot["escrow_total"],
        hasAccount=[iri("account", actor) for actor in sorted(snapshot["balances"])],
        hasAgreement=[iri("agreement", key) for key in sorted(snapshot["agreements"])],
        hasReceipt=[iri("receipt", key) for key in sorted(snapshot["receipts"])],
        hasEvent=[iri("event", event["sequence"]) for event in document["events"]],
        sourceArtifact=[iri("source", path) for path in sorted(document["source_sha256"])],
        comment="Deterministic local simulation. Initial balances/rates are illustrative inputs; no real issuance, signatures, execution or chain payment.")
    add(namespace + "software", ["prov:Agent", "prov:SoftwareAgent"], label="MetaHumoCoin local simulator")
    for path, sha in sorted(document["source_sha256"].items()):
        add(iri("source", path), ["prov:Entity", "mhv:SimulationSource"], sourcePath=path, sha256=sha)
    for actor, balance in sorted(snapshot["balances"].items()):
        add(iri("account", actor), ["prov:Agent", "mhv:SimulationAccount"], accountId=actor,
            initialBalance=snapshot["initial_balances"][actor], availableBalance=balance)
    for agreement_id, agreement in sorted(snapshot["agreements"].items()):
        terms = agreement["terms"]
        add(iri("agreement", agreement_id), ["prov:Entity", "mhv:SimulationAgreement"],
            agreementId=agreement_id, state=agreement["status"], termsHash=agreement["terms_sha256"],
            requester=iri("account", terms["requester"]), provider=iri("account", terms["provider"]),
            escrow=agreement["escrow"], agreementPayload=agreement)
    for operation_id, receipt in sorted(snapshot["receipts"].items()):
        add(iri("receipt", operation_id), ["prov:Entity", "mhv:SimulationReceipt"],
            operationId=operation_id, receiptKind=receipt["action"],
            agreement=iri("agreement", receipt["agreement_id"]), amount=receipt["provider_amount"],
            refund=receipt["requester_refund"], receiptPayload=receipt)
    for event in document["events"]:
        fields = {"sequence": event["sequence"], "operation": event["operation"],
                  "actor": iri("account", event["actor"]), "agreement": iri("agreement", event["agreement_id"]),
                  "previousHash": event["previous_hash"], "eventHash": event["event_hash"], "eventPayload": event}
        if event["sequence"] > 1:
            fields["previousEvent"] = iri("event", event["sequence"] - 1)
        add(iri("event", event["sequence"]), ["prov:Entity", "mhv:SimulationEvent"], **fields)
    return {"@context": context, "@graph": nodes}
