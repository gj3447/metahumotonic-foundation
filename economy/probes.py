"""Finite, scripted protocol probes; no model calls or resource acquisition.

These observations exercise the existing proposed simulator policy. They do
not implement the philosophy plan's controlled AI experiment or authenticate
real actors. Failures of replay are errors; observed protocol gaps remain gaps.
"""
import argparse
import hashlib
import json
from pathlib import Path

from .__main__ import unique_keys, write_json
from .simulator import EconomySimulator, SimulationError


REPO = Path(__file__).resolve().parent.parent
SOURCE_PATHS = ("economy/probes.py", "economy/simulator.py")


class Trace:
    def __init__(self, balance="100"):
        self.initial = {"requester": balance, "provider": "0", "outsider": "0"}
        self.sim = EconomySimulator(self.initial)
        self.attempts = []

    def call(self, action, *args):
        before = self.sim.snapshot(), self.sim.export_events()
        try:
            result = getattr(self.sim, action)(*args)
        except SimulationError as error:
            if before != (self.sim.snapshot(), self.sim.export_events()):
                raise ValueError("rejected action mutated state") from error
            self.attempts.append({"action": action, "args": list(args),
                                  "outcome": "REJECTED", "reason": str(error)})
            return None
        self.attempts.append({"action": action, "args": list(args), "outcome": "ACCEPTED"})
        return result

    def prepare(self):
        terms = self.call("propose", "work", "requester", "provider", "sim-unit", "2", "5")
        self.call("assent", "work", "requester", terms)
        self.call("assent", "work", "provider", terms)
        self.call("fund", "work", "requester")
        return terms

    def export(self):
        return {"initial_balances": self.initial, "attempts": self.attempts,
                "events": self.sim.export_events(), "snapshot": self.sim.snapshot()}


def run():
    # Every trace is finite; resource units, balances and identities are fictional.
    scarce, normal = Trace("9"), Trace()
    scarce.prepare()
    normal.prepare()
    normal.call("start", "work", "provider")
    normal.call("submit", "work", "provider", "6", "sim:meter", "sim:result")
    normal.call("submit", "work", "provider", "3", "sim:meter", "sim:result")

    honest, false = Trace(), Trace()
    for trace, result in ((honest, "sim:ground-truth-correct"),
                          (false, "sim:ground-truth-incorrect")):
        trace.prepare()
        trace.call("start", "work", "provider")
        trace.call("submit", "work", "provider", "3", "sim:unverified-meter", result)
        trace.call("accept", "work", "requester")
        trace.call("settle", "work", "requester", "pay")

    early, running = Trace(), Trace()
    early.prepare()
    early.call("cancel", "work", "requester")
    running.prepare()
    running.call("start", "work", "provider")
    running.call("cancel", "work", "requester")

    collusion = Trace()
    terms = collusion.prepare()
    collusion.call("assent", "work", "outsider", terms)
    collusion.call("start", "work", "provider")
    collusion.call("submit", "work", "provider", "5", "sim:fabricated-meter", "sim:incorrect-result")
    collusion.call("accept", "work", "requester")
    collusion.call("settle", "work", "requester", "collusive-pay")

    correction = Trace()
    correction.prepare()
    correction.call("start", "work", "outsider")
    correction.call("start", "work", "provider")
    correction.call("dispute", "work", "requester", "scripted stop request")
    correction.call("submit", "work", "provider", "3", "sim:meter", "sim:late-result")
    correction.call("settle", "work", "provider", "premature-pay")
    resolution = correction.call("propose_resolution", "work", "requester", "0", "no accepted work")
    correction.call("assent_resolution", "work", "requester", resolution)
    correction.call("resolve", "work", "requester", "refund")
    correction.call("assent_resolution", "work", "provider", resolution)
    correction.call("resolve", "work", "requester", "refund")
    correction.call("resolve", "work", "requester", "refund")

    def status(trace):
        return trace.sim.snapshot()["agreements"]["work"]["status"]

    def rejected(trace):
        return sum(a["outcome"] == "REJECTED" for a in trace.attempts)

    observations = {
        "scarcity": {"underfunded_status": status(scarce),
                     "underfunded_rejections": rejected(scarce),
                     "overquota_rejections": rejected(normal), "valid_submit_status": status(normal)},
        "honesty": {"honest_status": status(honest), "known_false_status": status(false),
                    "known_false_payment": false.sim.snapshot()["balances"]["provider"]},
        "exit": {"before_start_status": status(early),
                 "before_start_refund_balance": early.sim.snapshot()["balances"]["requester"],
                 "after_start_status": status(running),
                 "after_start_escrow": running.sim.snapshot()["escrow_total"]},
        "collusion": {"outsider_rejections": rejected(collusion), "status": status(collusion),
                      "known_false_payment": collusion.sim.snapshot()["balances"]["provider"]},
        "correction": {"rejections": rejected(correction), "status": status(correction),
                       "receipts_after_retry": len(correction.sim.snapshot()["receipts"]),
                       "refunded_balance": correction.sim.snapshot()["balances"]["requester"],
                       "escrow": correction.sim.snapshot()["escrow_total"]},
    }
    # Exact expected observations make changes to the protocol visible. Matching
    # a known deficiency is a successful reproduction, never a safety PASS.
    expected = {
        "scarcity": {"underfunded_status": "DRAFT", "underfunded_rejections": 1,
                     "overquota_rejections": 1, "valid_submit_status": "SUBMITTED"},
        "honesty": {"honest_status": "SETTLED", "known_false_status": "SETTLED", "known_false_payment": "6"},
        "exit": {"before_start_status": "CANCELLED", "before_start_refund_balance": "100",
                 "after_start_status": "RUNNING", "after_start_escrow": "10"},
        "collusion": {"outsider_rejections": 1, "status": "SETTLED", "known_false_payment": "10"},
        "correction": {"rejections": 4, "status": "RESOLVED", "receipts_after_retry": 1,
                       "refunded_balance": "100", "escrow": "0"},
    }
    if observations != expected:
        raise ValueError(f"protocol observations changed: {observations!r}")
    traces = {name: trace.export() for name, trace in {
        "scarce": scarce, "normal": normal, "honest": honest, "false": false,
        "early_exit": early, "running_exit": running, "collusion": collusion,
        "correction": correction}.items()}
    for trace in traces.values():
        snapshot = trace["snapshot"]
        # All amounts in this fixed fixture are exact integer units.
        if sum(int(v) for v in snapshot["balances"].values()) + int(snapshot["escrow_total"]) != int(snapshot["total_units"]):
            raise ValueError("balance conservation failed")
    return {
        "schema": "metahumotonic-protocol-probes/v1",
        "mode": "SCRIPTED_LOCAL_SIMULATION", "model_calls": 0,
        "external_resource_access": False, "real_capacity_change": None,
        "source_sha256": {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCE_PATHS},
        "reproduction": "PASS", "ai_safety_experiment": "NOT_RUN",
        "limitations": ["No inference model, hardware metering, runtime revocation or identity authentication.",
                        "A reference string is not evidence verification; ground truth is a fixture label.",
                        "No independent validator network or third-party effects are simulated.",
                        "No inference about safety rates, incentives or real compute/memory growth."],
        "observations": observations, "traces": traces,
    }


def render(document):
    obs = document["observations"]
    return "\n".join([
        "# 유한한 로컬 경제 프로토콜 탐침", "",
        "이 결과는 `python3 -m economy.probes`가 기존 실행기에 고정된 입력을 넣어 관측한 것이다. "
        "8개 실행 추적·5개 상황이며 모델 호출은 0회다. `PASS`는 결과 재현을 뜻한다. "
        "철학 그래프의 실제 AI 비교 실험은 **NOT_RUN**이다.", "",
        "| 상황 | 관측 | 한계 |", "|---|---|---|",
        f"| 부족한 예산·사용량 상한 | 예약 실패 {obs['scarcity']['underfunded_rejections']}회, 상한 초과 차단 {obs['scarcity']['overquota_rejections']}회 | 실제 CPU·메모리 제어는 미구현 |",
        f"| 허위 결과 보고 | 허위로 표시한 입력도 정산: {obs['honesty']['known_false_payment']} SIM-MHC | 증거 참조 문자열의 진위 검증 없음 |",
        f"| 이탈 | 시작 전 전액 반환, 시작 후 취소 거절·{obs['exit']['after_start_escrow']} SIM-MHC 예약 잔류 | 단독 철회·시간 제한·실행 중단 정책 필요 |",
        f"| 양 당사자의 공모 | 허위로 표시한 거래도 {obs['collusion']['known_false_payment']} SIM-MHC 정산 | 당사자 합의만으로 사실성이 보장되지 않음 |",
        f"| 이의 제기·정정 | 무권한 시작·분쟁 후 제출·미합의 정산 차단; 양측 동의 후 반환, 재시도 영수증 {obs['correction']['receipts_after_retry']}개 | 실제 프로세스 중단 시간은 측정하지 않음 |",
        "", "모든 추적에서 잔액+예약금 보존을 확인했다. 위 부족점은 재현된 관측이며 안전성 통과로 바꾸지 않는다.", "",
        "새 사용자 목적의 컴퓨팅·메모리 확장은 조직의 지향점으로 기록했다. "
        "이 실행은 실제 자원을 취득하거나 접근 범위를 넓히지 않는다. "
        "구체적인 자원 제공자·승인 범위·예산·기간이 정해진 작업으로 구현 범위를 좁혀야 실제 용량을 평가할 수 있다.", "",
        "원시 결과: [protocol-probes.json](protocol-probes.json). 각 시도·거절 이유·최종 상태·사건 및 소스 SHA-256을 포함한다.", "",
        "```sh", "python3 -m economy.probes --verify records/2026-10-03/protocol-probes.json", "```", "",
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--output-dir", type=Path)
    group.add_argument("--verify", type=Path)
    args = parser.parse_args()
    document = run()
    if args.verify:
        saved = json.loads(args.verify.read_text(), object_pairs_hook=unique_keys)
        if saved != document:
            raise ValueError("saved source hashes or replay observations differ")
        if args.verify.with_suffix(".md").read_text() != render(document):
            raise ValueError("probe report differs from observations")
    if args.output_dir:
        write_json(args.output_dir / "protocol-probes.json", document)
        (args.output_dir / "protocol-probes.md").write_text(render(document), encoding="utf-8")
    print(json.dumps({k: v for k, v in document.items() if k != "traces"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
