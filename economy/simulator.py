"""A deterministic, local-only escrow simulator for proposed SIM-MHC policy.

This module models a proposed experimental policy.  It does not mint, transfer,
or connect to any real MetaHumoCoin network.
"""

from __future__ import annotations

import copy
import hashlib
import json
from decimal import Context, Decimal, InvalidOperation, Overflow, ROUND_HALF_EVEN, localcontext
from typing import Any, Mapping


class SimulationError(ValueError):
    """Raised when a proposed simulation transition is invalid."""


# Local simulator policy, deliberately not a claim about eventual coin decimals.
_MONEY_CONTEXT = Context(prec=140, rounding=ROUND_HALF_EVEN)
_MAX_DECIMAL_PLACES = 6
_MAX_SIGNIFICANT_DIGITS = 60
_ZERO = Decimal("0")
_GENESIS_HASH = "0" * 64


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _amount(value: Any, field: str, *, allow_zero: bool = True) -> Decimal:
    """Parse a non-negative exact local-policy amount without ambient context."""
    if isinstance(value, bool) or isinstance(value, float):
        raise SimulationError(f"{field} must be a decimal string or Decimal, never float/bool")
    if not isinstance(value, (str, Decimal, int)):
        raise SimulationError(f"{field} must be a decimal string, Decimal, or integer")
    if isinstance(value, str) and len(value) > 256:
        raise SimulationError(f"{field} is too large")
    try:
        with localcontext(_MONEY_CONTEXT):
            number = Decimal(value)
    except (InvalidOperation, Overflow, ValueError) as error:
        raise SimulationError(f"{field} is not a decimal") from error
    if not number.is_finite():
        raise SimulationError(f"{field} must be finite")
    if number < _ZERO or (not allow_zero and number == _ZERO):
        qualifier = "positive" if not allow_zero else "non-negative"
        raise SimulationError(f"{field} must be {qualifier}")
    exponent = number.as_tuple().exponent
    places = max(0, -exponent) if isinstance(exponent, int) else _MAX_DECIMAL_PLACES + 1
    if places > _MAX_DECIMAL_PLACES:
        raise SimulationError(f"{field} exceeds {_MAX_DECIMAL_PLACES} decimal places")
    # Check adjusted exponent before normalize: `1e999999999` must be an input
    # error, never an implementation-dependent Decimal overflow.
    if number != _ZERO and number.adjusted() >= _MAX_SIGNIFICANT_DIGITS:
        raise SimulationError(f"{field} exceeds {_MAX_SIGNIFICANT_DIGITS} significant digits")
    if len(number.as_tuple().digits) > _MAX_SIGNIFICANT_DIGITS:
        raise SimulationError(f"{field} exceeds {_MAX_SIGNIFICANT_DIGITS} significant digits")
    try:
        with localcontext(_MONEY_CONTEXT):
            return number.normalize() if number != _ZERO else _ZERO
    except (InvalidOperation, Overflow, ValueError) as error:
        raise SimulationError(f"{field} is outside local numeric bounds") from error


def _amount_text(value: Decimal) -> str:
    if value == _ZERO:
        return "0"
    with localcontext(_MONEY_CONTEXT):
        return format(value.normalize(), "f")


def _product(left: Decimal, right: Decimal, field: str) -> Decimal:
    with localcontext(_MONEY_CONTEXT):
        result = left * right
    # Do not round an economic value just to fit the local policy.
    return _amount(result, field)


def _nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SimulationError(f"{field} must be a non-empty string")
    return value


class EconomySimulator:
    """In-memory deterministic lifecycle for a bilateral local economy agreement."""

    def __init__(self, initial_balances: Mapping[str, str | Decimal]) -> None:
        if not isinstance(initial_balances, Mapping) or not initial_balances:
            raise SimulationError("initial_balances must be a non-empty actor-to-balance mapping")
        balances: dict[str, Decimal] = {}
        for actor, balance in initial_balances.items():
            name = _nonempty_text(actor, "actor")
            if name in balances:
                raise SimulationError(f"duplicate actor: {name}")
            balances[name] = _amount(balance, f"initial balance for {name}")
        self._balances = balances
        self._initial_balances = copy.deepcopy(balances)
        self._escrow = _ZERO
        self._initial_total = _amount(self._sum(balances.values()), "initial total")
        self._agreements: dict[str, dict[str, Any]] = {}
        self._receipts: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-safe deep copy; no wall clock or ambient state is used."""
        agreements = {agreement_id: self._agreement_view(agreement)
                      for agreement_id, agreement in sorted(self._agreements.items())}
        return copy.deepcopy({
            "mode": "SIMULATED",
            "policy": {"authority": "SECONDARY_AI", "status": "PROPOSED"},
            "currency": "SIM-MHC",
            "numeric_policy": {"max_decimal_places": _MAX_DECIMAL_PLACES, "rounding": "REJECT"},
            "initial_balances": {actor: _amount_text(balance) for actor, balance in sorted(self._initial_balances.items())},
            "balances": {actor: _amount_text(balance) for actor, balance in sorted(self._balances.items())},
            "escrow": {agreement_id: _amount_text(agreement["escrow"])
                       for agreement_id, agreement in sorted(self._agreements.items()) if agreement["escrow"] != _ZERO},
            "escrow_total": _amount_text(self._escrow),
            "agreements": agreements,
            "receipts": copy.deepcopy({key: self._receipt_view(value) for key, value in sorted(self._receipts.items())}),
            "total_units": _amount_text(self._initial_total),
        })

    def export_events(self) -> list[dict[str, Any]]:
        """Return a detached JSON-safe event log with its deterministic hash chain."""
        return copy.deepcopy(self._events)

    def propose(self, agreement_id: str, requester: str, provider: str, unit: str,
                unit_price: str | Decimal, max_units: str | Decimal) -> str:
        agreement_id = _nonempty_text(agreement_id, "agreement_id")
        requester = self._actor(requester)
        provider = self._actor(provider)
        if requester == provider:
            raise SimulationError("requester and provider must be distinct")
        if agreement_id in self._agreements:
            raise SimulationError(f"agreement already exists: {agreement_id}")
        unit = _nonempty_text(unit, "unit")
        price = _amount(unit_price, "unit_price")
        maximum = _amount(max_units, "max_units")
        terms = {
            "agreement_id": agreement_id, "requester": requester, "provider": provider,
            "unit": unit, "unit_price": _amount_text(price), "max_units": _amount_text(maximum),
        }
        terms_sha256 = _digest(terms)
        agreement = {
            "terms": terms, "terms_sha256": terms_sha256, "status": "DRAFT",
            "assents": [], "escrow": _ZERO, "submitted_units": None,
            "usage_evidence": None, "result_evidence": None, "resolution": None,
        }
        self._agreements[agreement_id] = agreement
        self._event(requester, "PROPOSE", agreement_id, {"terms_sha256": terms_sha256, "terms": terms})
        return terms_sha256

    def assent(self, agreement_id: str, actor: str, terms_sha256: str) -> None:
        agreement = self._agreement(agreement_id)
        actor = self._party(agreement, actor)
        if agreement["status"] != "DRAFT":
            raise SimulationError("terms can only be assented while DRAFT")
        if not isinstance(terms_sha256, str) or terms_sha256 != agreement["terms_sha256"]:
            raise SimulationError("terms_sha256 does not match immutable terms")
        if actor in agreement["assents"]:
            return
        agreement["assents"].append(actor)
        agreement["assents"].sort()
        self._event(actor, "ASSENT", agreement_id, {"terms_sha256": terms_sha256})

    def fund(self, agreement_id: str, actor: str) -> None:
        agreement = self._agreement(agreement_id)
        actor = self._party(agreement, actor)
        terms = agreement["terms"]
        if actor != terms["requester"]:
            raise SimulationError("only the requester may fund")
        if agreement["status"] != "DRAFT" or len(agreement["assents"]) != 2:
            raise SimulationError("both parties must assent before funding")
        reserve = _product(_amount(terms["unit_price"], "unit_price"), _amount(terms["max_units"], "max_units"), "reservation")
        if self._balances[actor] < reserve:
            raise SimulationError("insufficient requester balance")
        new_balance = self._subtract(self._balances[actor], reserve, "requester balance")
        new_escrow = self._add(self._escrow, reserve, "escrow")
        self._balances[actor] = new_balance
        self._escrow = new_escrow
        agreement["escrow"] = reserve
        agreement["status"] = "FUNDED"
        self._event(actor, "FUND", agreement_id, {"reserved": _amount_text(reserve)})
        self._assert_conserved()

    def start(self, agreement_id: str, actor: str) -> None:
        agreement = self._agreement(agreement_id)
        actor = self._party(agreement, actor)
        if actor != agreement["terms"]["provider"]:
            raise SimulationError("only the provider may start")
        if agreement["status"] != "FUNDED":
            raise SimulationError("only a FUNDED agreement may start")
        agreement["status"] = "RUNNING"
        self._event(actor, "START", agreement_id, {})

    def submit(self, agreement_id: str, actor: str, units: str | Decimal,
               usage_evidence: str, result_evidence: str) -> None:
        agreement = self._agreement(agreement_id)
        actor = self._party(agreement, actor)
        if actor != agreement["terms"]["provider"]:
            raise SimulationError("only the provider may submit")
        if agreement["status"] != "RUNNING":
            raise SimulationError("only a RUNNING agreement may be submitted")
        submitted = _amount(units, "units")
        maximum = _amount(agreement["terms"]["max_units"], "max_units")
        if submitted > maximum:
            raise SimulationError("submitted units exceed max_units")
        cost = _product(submitted, _amount(agreement["terms"]["unit_price"], "unit_price"), "submitted cost")
        usage_evidence = _nonempty_text(usage_evidence, "usage_evidence")
        result_evidence = _nonempty_text(result_evidence, "result_evidence")
        agreement["submitted_units"] = submitted
        agreement["usage_evidence"] = usage_evidence
        agreement["result_evidence"] = result_evidence
        agreement["status"] = "SUBMITTED"
        self._event(actor, "SUBMIT", agreement_id, {
            "units": _amount_text(submitted), "cost": _amount_text(cost),
            "usage_evidence": usage_evidence, "result_evidence": result_evidence,
        })

    def accept(self, agreement_id: str, actor: str) -> None:
        agreement = self._agreement(agreement_id)
        actor = self._party(agreement, actor)
        if actor != agreement["terms"]["requester"]:
            raise SimulationError("only the requester may accept")
        if agreement["status"] != "SUBMITTED":
            raise SimulationError("only a SUBMITTED agreement may be accepted")
        agreement["status"] = "ACCEPTED"
        self._event(actor, "ACCEPT", agreement_id, {"submitted_units": _amount_text(agreement["submitted_units"])})

    def settle(self, agreement_id: str, actor: str, operation_id: str) -> dict[str, Any]:
        agreement = self._agreement(agreement_id)
        actor = self._party(agreement, actor)
        existing = self._existing_receipt(operation_id, "SETTLE", agreement_id)
        if existing is not None:
            return existing
        if agreement["status"] != "ACCEPTED":
            raise SimulationError("only an ACCEPTED agreement may settle")
        payment = _product(agreement["submitted_units"], _amount(agreement["terms"]["unit_price"], "unit_price"), "settlement")
        return self._close(agreement_id, agreement, actor, operation_id, "SETTLE", payment, None)

    def cancel(self, agreement_id: str, actor: str) -> None:
        agreement = self._agreement(agreement_id)
        actor = self._party(agreement, actor)
        if agreement["status"] not in {"DRAFT", "FUNDED"}:
            raise SimulationError("only DRAFT or FUNDED agreements may be cancelled")
        refund = agreement["escrow"]
        if refund:
            requester = agreement["terms"]["requester"]
            new_balance = self._add(self._balances[requester], refund, "requester balance")
            new_escrow = self._subtract(self._escrow, refund, "escrow")
            self._balances[requester] = new_balance
            self._escrow = new_escrow
            agreement["escrow"] = _ZERO
        agreement["status"] = "CANCELLED"
        self._event(actor, "CANCEL", agreement_id, {"refund": _amount_text(refund)})
        self._assert_conserved()

    def dispute(self, agreement_id: str, actor: str, reason: str) -> None:
        agreement = self._agreement(agreement_id)
        actor = self._party(agreement, actor)
        if agreement["status"] not in {"RUNNING", "SUBMITTED", "ACCEPTED"}:
            raise SimulationError("only RUNNING, SUBMITTED, or ACCEPTED agreements may be disputed")
        reason = _nonempty_text(reason, "reason")
        agreement["status"] = "DISPUTED"
        self._event(actor, "DISPUTE", agreement_id, {"reason": reason})

    def propose_resolution(self, agreement_id: str, actor: str, amount: str | Decimal, reason: str) -> str:
        agreement = self._agreement(agreement_id)
        actor = self._party(agreement, actor)
        if agreement["status"] != "DISPUTED":
            raise SimulationError("a resolution may only be proposed while DISPUTED")
        amount = _amount(amount, "resolution amount")
        maximum = self._submitted_cost(agreement)
        if amount > maximum:
            raise SimulationError("resolution amount exceeds submitted cost")
        reason = _nonempty_text(reason, "reason")
        payload = {"agreement_id": agreement_id, "amount": _amount_text(amount), "reason": reason}
        resolution_sha256 = _digest(payload)
        agreement["resolution"] = {"amount": amount, "reason": reason, "resolution_sha256": resolution_sha256, "assents": []}
        self._event(actor, "PROPOSE_RESOLUTION", agreement_id, {**payload, "resolution_sha256": resolution_sha256})
        return resolution_sha256

    def assent_resolution(self, agreement_id: str, actor: str, resolution_sha256: str) -> None:
        agreement = self._agreement(agreement_id)
        actor = self._party(agreement, actor)
        resolution = agreement["resolution"]
        if agreement["status"] != "DISPUTED" or resolution is None:
            raise SimulationError("there is no disputed resolution to assent")
        if not isinstance(resolution_sha256, str) or resolution_sha256 != resolution["resolution_sha256"]:
            raise SimulationError("resolution_sha256 does not match proposed resolution")
        if actor in resolution["assents"]:
            return
        resolution["assents"].append(actor)
        resolution["assents"].sort()
        self._event(actor, "ASSENT_RESOLUTION", agreement_id, {"resolution_sha256": resolution_sha256})

    def resolve(self, agreement_id: str, actor: str, operation_id: str) -> dict[str, Any]:
        agreement = self._agreement(agreement_id)
        actor = self._party(agreement, actor)
        existing = self._existing_receipt(operation_id, "RESOLVE", agreement_id)
        if existing is not None:
            return existing
        resolution = agreement["resolution"]
        if agreement["status"] != "DISPUTED" or resolution is None or len(resolution["assents"]) != 2:
            raise SimulationError("both parties must assent to a disputed resolution")
        return self._close(agreement_id, agreement, actor, operation_id, "RESOLVE", resolution["amount"], resolution["resolution_sha256"])

    def _close(self, agreement_id: str, agreement: dict[str, Any], actor: str, operation_id: str,
               action: str, payment: Decimal, resolution_sha256: str | None) -> dict[str, Any]:
        operation_id = _nonempty_text(operation_id, "operation_id")
        held = agreement["escrow"]
        if payment > held:
            raise SimulationError("payment exceeds escrow")
        refund = self._subtract(held, payment, "refund")
        terms = agreement["terms"]
        receipt: dict[str, Any] = {
            "operation_id": operation_id, "action": action, "agreement_id": agreement_id,
            "provider_amount": _amount_text(payment), "requester_refund": _amount_text(refund),
            "escrow_before": _amount_text(held), "escrow_after": "0",
            "status": "SETTLED" if action == "SETTLE" else "RESOLVED",
            "terms_sha256": agreement["terms_sha256"],
        }
        if resolution_sha256 is not None:
            receipt["resolution_sha256"] = resolution_sha256
        # Every possible failure above occurs before balances, agreement, receipt, or event mutate.
        provider_balance = self._add(self._balances[terms["provider"]], payment, "provider balance")
        requester_balance = self._add(self._balances[terms["requester"]], refund, "requester balance")
        new_escrow = self._subtract(self._escrow, held, "escrow")
        self._balances[terms["provider"]] = provider_balance
        self._balances[terms["requester"]] = requester_balance
        self._escrow = new_escrow
        agreement["escrow"] = _ZERO
        agreement["status"] = receipt["status"]
        self._receipts[operation_id] = receipt
        self._event(actor, action, agreement_id, copy.deepcopy(receipt))
        self._assert_conserved()
        return copy.deepcopy(receipt)

    def _existing_receipt(self, operation_id: str, action: str, agreement_id: str) -> dict[str, Any] | None:
        operation_id = _nonempty_text(operation_id, "operation_id")
        receipt = self._receipts.get(operation_id)
        if receipt is None:
            return None
        if receipt["action"] != action or receipt["agreement_id"] != agreement_id:
            raise SimulationError("operation_id is already bound to another action or agreement")
        return copy.deepcopy(receipt)

    def _agreement(self, agreement_id: str) -> dict[str, Any]:
        agreement_id = _nonempty_text(agreement_id, "agreement_id")
        try:
            return self._agreements[agreement_id]
        except KeyError as error:
            raise SimulationError(f"unknown agreement: {agreement_id}") from error

    def _actor(self, actor: Any) -> str:
        actor = _nonempty_text(actor, "actor")
        if actor not in self._balances:
            raise SimulationError(f"unknown actor: {actor}")
        return actor

    def _party(self, agreement: dict[str, Any], actor: Any) -> str:
        actor = self._actor(actor)
        if actor not in (agreement["terms"]["requester"], agreement["terms"]["provider"]):
            raise SimulationError("actor is not a party to this agreement")
        return actor

    def _submitted_cost(self, agreement: dict[str, Any]) -> Decimal:
        if agreement["submitted_units"] is None:
            return _ZERO
        return _product(agreement["submitted_units"], _amount(agreement["terms"]["unit_price"], "unit_price"), "submitted cost")

    @staticmethod
    def _sum(values: Any) -> Decimal:
        with localcontext(_MONEY_CONTEXT):
            return sum(values, _ZERO)

    @staticmethod
    def _add(left: Decimal, right: Decimal, field: str) -> Decimal:
        with localcontext(_MONEY_CONTEXT):
            return _amount(left + right, field)

    @staticmethod
    def _subtract(left: Decimal, right: Decimal, field: str) -> Decimal:
        with localcontext(_MONEY_CONTEXT):
            return _amount(left - right, field)

    def _assert_conserved(self) -> None:
        if self._escrow < _ZERO or any(balance < _ZERO for balance in self._balances.values()):
            raise AssertionError("economy invariant: negative balance or escrow")
        with localcontext(_MONEY_CONTEXT):
            current_total = self._sum(self._balances.values()) + self._escrow
        if current_total != self._initial_total:
            raise AssertionError("economy invariant: total units changed")

    def _event(self, actor: str, operation: str, agreement_id: str, data: dict[str, Any]) -> None:
        previous_hash = self._events[-1]["event_hash"] if self._events else _GENESIS_HASH
        event = {
            "sequence": len(self._events) + 1, "actor": actor, "operation": operation,
            "agreement_id": agreement_id, "data": copy.deepcopy(data), "previous_hash": previous_hash,
        }
        event["event_hash"] = _digest(event)
        self._events.append(event)

    @staticmethod
    def _receipt_view(receipt: dict[str, Any]) -> dict[str, Any]:
        return copy.deepcopy(receipt)

    @staticmethod
    def _agreement_view(agreement: dict[str, Any]) -> dict[str, Any]:
        result = {
            "terms": copy.deepcopy(agreement["terms"]), "terms_sha256": agreement["terms_sha256"],
            "status": agreement["status"], "assents": list(agreement["assents"]),
            "escrow": _amount_text(agreement["escrow"]),
            "submitted_units": None if agreement["submitted_units"] is None else _amount_text(agreement["submitted_units"]),
            "usage_evidence": agreement["usage_evidence"], "result_evidence": agreement["result_evidence"],
            "resolution": None,
        }
        if agreement["resolution"] is not None:
            resolution = agreement["resolution"]
            result["resolution"] = {
                "amount": _amount_text(resolution["amount"]), "reason": resolution["reason"],
                "resolution_sha256": resolution["resolution_sha256"], "assents": list(resolution["assents"]),
            }
        return result
