"""Portable source snapshot and JSON-LD view; neither is a chain receipt."""
import copy
from urllib.parse import quote

from .contracts import ASSET, digest, integer, invoice, quantities, require
from .core import Market, TERMINAL


BASE = "https://github.com/gj3447/metahumotonic-foundation/"
VOCAB = BASE + "market-vocab#"


def verify_snapshot(s):
    require(s["schema"] == "metahumotonic-market/v1" and s["mode"] == "LOCAL_SANDBOX" and s["asset"] == ASSET, "invalid snapshot profile")
    Market.invariants(s)
    for value in s["initial_balances"].values(): integer(value, "initial balance")
    require(s["supply"] == sum(s["initial_balances"].values()), "initial supply changed")
    previous = "0" * 64
    for i, event in enumerate(s["events"], 1):
        payload = {k: v for k, v in event.items() if k != "sha256"}
        require(event["sequence"] == i and event["previous_sha256"] == previous and digest(payload) == event["sha256"], "event chain changed")
        previous = event["sha256"]
    for offer in s["offers"].values():
        require(digest(offer["terms"]) == offer["terms_sha256"], "offer terms changed")
    balances = copy.deepcopy(s["initial_balances"])
    require(set(s["receipts"]) == {oid for oid, o in s["orders"].items() if o["state"] in TERMINAL}, "receipt/order coverage differs")
    for oid, order in s["orders"].items():
        terms = order["terms"]
        require(order["state"] in TERMINAL | {"RESERVED", "RUNNING", "STOP_REQUESTED"}, "unknown order state")
        require(order["requester"] == terms["requester"]
                and all(order[k] == order["offer_terms"][k] for k in ("provider", "resource_id", "grant_id")),
                "order parties/resource changed")
        require(terms["sha256"] == digest({k: v for k, v in terms.items() if k != "sha256"}), "quote changed")
        require(terms["offer_sha256"] == digest(order["offer_terms"]), "offer binding changed")
        require(order["offer_terms"] == s["offers"][terms["offer_id"]]["terms"], "order no longer matches offer")
        maximum = invoice(order["offer_terms"]["rates"], terms["limits"])
        require(maximum == terms["maximum_charge"], "reserved invoice changed")
        balances[order["requester"]] -= maximum["atoms"]
        if order["state"] not in TERMINAL:
            require(order["escrow"] == maximum["atoms"], "open escrow changed")
            continue
        r = s["receipts"][oid]
        for key in ("paid_atoms", "refund_atoms", "reserved_atoms"): integer(r[key], key)
        require(r["sha256"] == digest({k: v for k, v in r.items() if k != "sha256"}), "receipt digest changed")
        require(r["order_id"] == oid and r["state"] == order["state"] and r["asset"] == ASSET
                and r["quote_sha256"] == terms["sha256"] and r["offer_sha256"] == terms["offer_sha256"], "receipt binding changed")
        require(r["usage"] == order["usage"] and r["evidence"] == order["evidence"], "evidence binding changed")
        require(r["paid_atoms"] + r["refund_atoms"] == r["reserved_atoms"] == maximum["atoms"], "receipt conservation failed")
        if order["state"] == "SETTLED":
            quantities(r["usage"])
            require(all(r["usage"][u] <= terms["limits"][u] for u in r["usage"]), "settled usage exceeds limits")
            bill = invoice(order["offer_terms"]["rates"], r["usage"])
            require(r["invoice"] == bill and r["paid_atoms"] == bill["atoms"], "settled invoice differs")
        else:
            require(r["paid_atoms"] == 0, "non-success payment forbidden in this profile")
        balances[order["requester"]] += r["refund_atoms"]
        balances[order["provider"]] += r["paid_atoms"]
    require(balances == s["balances"], "balances do not match orders/receipts")


def project(s):
    verify_snapshot(s)
    ns = "urn:metahumotonic:market:" + digest(s) + ":"
    context = {"@version": 1.1, "mk": VOCAB, "run": ns,
               "prov": "http://www.w3.org/ns/prov#", "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
               "xsd": "http://www.w3.org/2001/XMLSchema#", "label": "rdfs:label"}
    links = {"hasOrder": "MarketSnapshot", "hasOffer": "MarketSnapshot", "hasGrant": "MarketSnapshot",
             "hasResource": "MarketSnapshot", "hasAccount": "MarketSnapshot", "asset": None, "owner": None,
             "provider": None, "requester": None, "resource": None, "grant": None, "offer": None,
             "usage": None, "receipt": None, "order": None, "hasPrice": None}
    for prop in links: context[prop] = {"@id": "mk:" + prop, "@type": "@id"}
    for prop in ["mode", "state", "sha256", "sourceID", "backend", "model", "tokenizer", "meterStatus", "evidenceMode", "uslID", "unit"]:
        context[prop] = "mk:" + prop
    for prop in ["balanceAtoms", "supplyAtoms", "reservedAtoms", "paidAtoms", "refundAtoms", "escrowAtoms",
                 "inputTokens", "outputTokens", "cpuMs", "memoryMiBMs", "slots", "memoryMiB", "expiresAtMs",
                 "priceNumerator", "priceDenominator"]:
        context[prop] = {"@id": "mk:" + prop, "@type": "xsd:integer"}
    context["references"] = {"@id": "http://purl.org/dc/terms/references", "@type": "@id"}
    context["generatedBy"] = {"@id": "prov:wasGeneratedBy", "@type": "@id"}
    context["associatedWith"] = {"@id": "prov:wasAssociatedWith", "@type": "@id"}
    nodes = []
    def ref(kind, key): return "run:" + kind + ":" + quote(key, safe="")
    def add(kind, key, **fields):
        node = {"@id": ref(kind, key), "@type": ["mk:" + kind, "prov:Entity"], **fields}
        nodes.append(node)
        return node["@id"]
    asset = add("Asset", "sandbox", label="SIM-MHC sandbox atoms", sourceID=ASSET, mode="LOCAL_SANDBOX")
    nodes.extend([{"@id": "run:projection", "@type": "prov:Activity", "associatedWith": "run:operator",
                   "label": "Local market snapshot projection; no HSWM admission or chain settlement"},
                  {"@id": "run:operator", "@type": "prov:SoftwareAgent", "label": "metahumotonic-market/v1"}])
    add("MarketSnapshot", "root", mode=s["mode"], sha256=digest(s), asset=asset, supplyAtoms=s["supply"],
               generatedBy="run:projection",
               references=[BASE + "graph/resource-roadmap#S_contract", BASE + "graph/resource-roadmap#S_control",
                           BASE + "graph/resource-roadmap#S_evidence", BASE + "graph/philosophy#C_resource_purpose",
                           BASE + "market/interop.json", BASE + "records/2026-10-04/market-source.json"],
               hasOrder=[ref("Order", k) for k in sorted(s["orders"])],
               hasOffer=[ref("Offer", k) for k in sorted(s["offers"])],
               hasGrant=[ref("Grant", k) for k in sorted(s["grants"])],
               hasResource=[ref("Resource", k) for k in sorted(s["resources"])],
               hasAccount=[ref("Account", k) for k in sorted(s["balances"])])
    for actor, balance in sorted(s["balances"].items()):
        add("Account", actor, sourceID=actor, balanceAtoms=balance, asset=asset)
    for key, r in sorted(s["resources"].items()):
        add("Resource", key, sourceID=key, owner=ref("Account", r["owner"]), slots=r["slots"], memoryMiB=r["memory_mib"],
            uslID=r["usl_resource_id"], state="QUARANTINED" if r["quarantined"] else r["observation_status"])
    for key, g in sorted(s["grants"].items()):
        add("Grant", key, sourceID=key, owner=ref("Account", g["owner"]), provider=ref("Account", g["provider"]),
            resource=ref("Resource", g["resource_id"]), state=g["state"], expiresAtMs=g["expires_at_ms"])
    for key, o in sorted(s["offers"].items()):
        t = o["terms"]
        fields = {"model": t["model"], "tokenizer": t["tokenizer"]} if t["model"] else {}
        price_ids = [add("UnitPrice", key + ":" + unit, offer=ref("Offer", key), asset=asset,
                         unit=unit, priceNumerator=rate[0], priceDenominator=rate[1])
                     for unit, rate in sorted(t["rates"].items())]
        add("Offer", key, sourceID=key, provider=ref("Account", t["provider"]), grant=ref("Grant", t["grant_id"]),
            asset=asset, backend=t["backend"], state=o["state"], sha256=o["terms_sha256"], hasPrice=price_ids, **fields)
    for key, o in sorted(s["orders"].items()):
        fields = {}
        if o["usage"] is not None:
            e = o["evidence"]; u = o["usage"]
            native = e.get("hswm")
            extra = {"model": native["model"], "tokenizer": o["offer_terms"]["tokenizer"],
                     "meterStatus": native["meter_status"]} if native else {"meterStatus": "LOCAL_PROCESS_MEASURED"}
            fields["usage"] = add("Usage", key, order=ref("Order", key), inputTokens=u["input_tokens"],
                outputTokens=u["output_tokens"], cpuMs=u["cpu_ms"], memoryMiBMs=u["memory_mib_ms"],
                evidenceMode=e["mode"], sha256=digest(e), **extra)
        if key in s["receipts"]:
            r = s["receipts"][key]
            fields["receipt"] = add("Receipt", key, order=ref("Order", key), asset=asset, state=r["state"],
                reservedAtoms=r["reserved_atoms"], paidAtoms=r["paid_atoms"], refundAtoms=r["refund_atoms"], sha256=r["sha256"])
        add("Order", key, sourceID=key, offer=ref("Offer", o["terms"]["offer_id"]), grant=ref("Grant", o["grant_id"]),
            requester=ref("Account", o["requester"]), provider=ref("Account", o["provider"]), resource=ref("Resource", o["resource_id"]),
            asset=asset, state=o["state"], escrowAtoms=o["escrow"], sha256=o["terms"]["sha256"], **fields)
    return {"@context": context, "@graph": nodes}
