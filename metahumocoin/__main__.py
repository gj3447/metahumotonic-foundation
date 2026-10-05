"""Run a finite local demonstration with no external IO or purchased compute."""
import json
from .ledger import Ledger, Rejected, run_reference


def demo():
    ledger = Ledger()
    try:
        sid = ledger.apply("create", "create", 0, start=0, end=100)
        ledger.apply("capacity", "capacity", 0, sid=sid, lot="lot-a", slot="fixture-device-a", quantity=100, fresh_until=100)
        ledger.apply("issue", "mint", 0, sid=sid, account="customer", quantity=80)
        initial = ledger.report(sid, 0)
        try:
            ledger.apply("overissue", "mint", 0, sid=sid, account="customer", quantity=1)
        except Rejected as error:
            overissue = str(error)
        ledger.apply("fee", "transfer", 1, sid=sid, sender="customer", recipient="foundation", quantity=2)
        ledger.apply("reserve", "lock", 1, sid=sid, account="customer", claim="job-1", quantity=10)
        result = run_reference(10)
        receipt = ledger.apply("deliver", "finish", 2, claim="job-1", result=result)
        delivered = ledger.report(sid, 2)
        ledger.apply("loss", "revoke", 3, lot="lot-a")
        return {"scope": "LOCAL_PROTOTYPE", "capacity_evidence": "TRUSTED_FIXTURE",
                "series": sid, "initial": initial, "overissue": overissue,
                "reference_result": result, "receipt": receipt, "after_delivery": delivered,
                "after_revocation": ledger.report(sid, 3), "after_expiry": ledger.report(sid, 100),
                "foundation_fee_balance": ledger.snapshot()["series"][sid]["balances"]["foundation"],
                "blockchain": "NOT_IMPLEMENTED", "physical_capacity_verified": False}
    finally:
        ledger.close()


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
