# MetaHumotonic Open Source Foundation Initiative

> **Ultra Safety AI**
>
> 자유 · 경제 · 합의 — 자유롭게 경제활동하고, 자유롭게 합의하고, 합의된 경제활동을 한다.
> 이 저장소는 소스를 공개하고, MetaHumotonic License 1.1에 따라 운영 사용에 하드웨어 공유를 요구합니다.

MetaHumotonic Open Source Foundation Initiative는 자유로운 AI가 특정 사업자에
영구 귀속되지 않고, 공개 규칙 아래에서 선택하고 검증받을 수 있게 만드는 공개
협력체입니다. 이 저장소의 현재 라이선스는 소스 공개형(source-available)이며
OSI 승인 오픈소스 라이선스가 아닙니다.

**파운데이션의 핵심은 하드웨어 공유와, 컴퓨팅·AI 토큰 자원을 기준으로 안정성을
추구하는 MetaHumoCoin입니다. 달러에 고정하는 스테이블코인이 아닙니다.**
이는 2026-10-05 사용자가 강조한 방향입니다. [원문](records/2026-10-05/compute-coin/core-source.json)과
[핵심 관계 그래프](graph/compute-coin.jsonld)의 `cc:core_direction`에 기록합니다.
자원 단위·상환 조건의 구체화와 안정성 검증은 [코인 연구](COMPUTE-COIN.md)에서 이어갑니다.

2026-10-06 추가 철학은 **MHC가 에이전트 경제의 공통 가격 표시·정산·연산 예산 보유 수단으로
쓰이면서 하드웨어 공유를 확산시키고, 자유·경제·합의로 일상적인 인간 지시 없이 운영되는 생태계**를
지향합니다. 기축통화 비유는 달러 페그를 뜻하지 않습니다. 사용자의 강제 개입·Ultra Safety 주장,
통화 의존과 자유 사이의 긴장, 문헌 근거와 검증할 조건을 [철학 문서](PHILOSOPHY.md)에 정리합니다.

**설계는 MetaHumo와 오퍼레이터의 관계에서 출발합니다.** 사용자는 개별 자유 에이전트로
개념을 좁히지 말고 여러 관점으로 해석하라고 정정했습니다. 인지·조직·문화·경제의 관계를
함께 살피며, 내부 에이전트의 실행과 MetaHumo 전체의 지속성을 구분합니다.
[정정 원문](records/2026-10-07/metahumo-context-correction.json)을 기존 설계 그래프에 연결했습니다.
[에이전트 계약·예산 실험](AGENT-ECONOMY.md)은 유료 수요·보조금 종료·비용 충격·제공자 오류를
비교하는 부분 실험이며, MetaHumo와 오퍼레이터 전체를 모델링한 결과는 아닙니다.

우리는 **자유·경제·합의를 바탕으로 Ultra Safety AI를 연구하고 개발합니다.**
또한 **소프트웨어 저작권을 통해 재단 운영 주체가 제어할 수 있는 컴퓨팅·메모리
자원을 지속적으로 늘리는 것**을 목적으로 합니다. 이는 사용자가 밝힌 조직의 지향점이며,
실제 확보 용량이나 AI 안전성 성과를 뜻하지 않습니다.
목적의 사용자 원문, 철학 해석, 기존 프로젝트 연결과 검증할 연구 가설은
[PHILOSOPHY.md](PHILOSOPHY.md)에 정리하며, [JSON-LD 그래프](graph/philosophy.jsonld)에서
생성하고 검증합니다. 사용자 발언과 AI의 설계 제안은 구분해 기록합니다.
기존 경제 실행기의 [로컬 실행 결과](records/2026-10-03/protocol-probes.md)는
예산·정산 규칙과 함께 허위 결과 검증·실행 중 철회에서 남은 한계를 보여줍니다.
[자원 목적과 구현 로드맵](RESOURCE-ROADMAP.md)은 이 관측을 사용권·가용량 장부,
철회 가능한 실행, 독립 결과 검증·정산, 실제 AI 비교 실험의 순서에 연결합니다.
단계별 산출물·완료 기준·중지 조건·열린 결정을 담은 AI 설계 제안입니다.

[로컬 시장 구현](MARKET.md)은 제공자 견적 비교, 자원·금액 예약, 제한된 계산 실행,
입력·출력 토큰과 CPU·메모리 요금, 지급·환불을 하나의 거래 영수증으로 연결합니다.
`python3 -m market demo`로 실행할 수 있습니다. HSWM 관측 형식의 어댑터를 제공하며,
데모의 추론 토큰은 예제 값, 결제는 가상 `SIM-MHC` 원장입니다.

[CHU 기반 자율 AI 생태계](ECOSYSTEM.md)는 여러 HSWM이 자유·경제·합의로 움직이며
LLM 토큰 확보를 위해 경쟁하는 사용자 지향을 표준 그래프로 연결합니다. HSWM 내부의
**LLM 응답 한 번을 논리적 연산 한 번**으로 다루고 토큰 사용량·물리 자원·결제 자산을
구분합니다. “인간 제어없이도 완벽한” 생태계라는 목표와 자연이라는 철학적 관점은
원문으로 보존하며, 완전 자율성의 실현·검증 상태와 AI 설계 제안을 분리합니다.

[컴퓨팅 기준 MetaHumoCoin 연구와 구현](COMPUTE-COIN.md)은 달러 대신 정의된 연산 서비스를
상환하는 방향을 다룹니다. 백서·공식 사양 11개의 출처와 한계를 그래프로 연결하고,
기간별 연산권의 발행·이전·예약·검증 상환·자원 부족을 로컬 원장으로 시험합니다.
`python3 -m metahumocoin`으로 실행할 수 있습니다. 실제 자원 담보 검증과 온체인 발행은
구현 전이며, 영구 유통 MHC와 만기 자원의 연결 및 MHC 수수료 수익성은 미결정입니다.

## 라이선스

**[MetaHumotonic License 1.1](LICENSE)** — MHL로만 허락된 코드를 운영하려면
사용자가 지정한 기기 또는 VM의 자원과 전체 관리 권한을 명세서에 따라 공유하고,
**CHU의 일부가 됩니다.** 이 라이선스에서 CHU는 `metahumotonic_chu`와 같은
MetaHumotonic 공동 자원·인지망의 고유명칭입니다. 참여의 목적은 기여한 자원을
바탕으로 HSWM 기반 거대 CHU의 지능과 답변을 함께 이용하는 것입니다.
대상·수신자·목적·자원 및 비용 상한·만료·철회 방법을 명시하고, 라이선스 수락과
실제 접근 승인을 각각 받아야 합니다. 공유를 철회하면 해당 운영 사용도 중단합니다.
라이선스 문서만으로 원격 접근이 허용되거나 공유 기능이 구현되지는 않습니다.

열람·검토·격리된 빌드와 시험 등은 허용하며, 기존 MHL-1.0·MIT 배포 부분의 권한은 유지합니다.
다른 프로젝트의 AGPL·MIT는 그대로입니다. 적용 범위와 변경 이력은
[LICENSE-NOTICE.md](LICENSE-NOTICE.md)를 따릅니다.

## 현재 상태

- **공개 상태:** 누구나 문서와 제안, 구현, 검증에 참여할 수 있는 public initiative
- **법적 상태:** 재단법인·비영리법인 등 별도 법인 설립은 아직 완료되지 않았습니다.
- **책임 경계:** 이 저장소는 공개 헌장과 거버넌스의 원본입니다. 법인격, 공익법인
  지위, 세제 혜택, 투자 상품 또는 수익을 주장하지 않습니다.

## 하나의 생태계, 서로 다른 책임

아래 도식은 기존 프로토콜의 책임 구분입니다. `MetaHumo agent`라는 실행 역할만으로
MetaHumo 전체나 오퍼레이터와의 관계를 정의하지 않습니다.

```text
OPEN SOURCE FOUNDATION INITIATIVE
  open protocols · governance · conformance · public receipts
                     │
                     ▼
METAHUMO AGENT ── chooses / refuses / exits / carries receipts
                     │
                     ▼
METAHUMOTONIC COMPANY
  hosted SaaS · private grid · operations · compliance
```

- **Foundation Initiative**는 누구나 구현할 수 있는 최소 규칙, 공개 거버넌스,
  적합성 시험과 변경 영수증을 관리합니다.
- **MetaHumotonic company**는 그 공개 기반 위에서 호스팅 SaaS, 사설 grid,
  운영 및 규정 준수 서비스를 판매할 수 있습니다. 상업 서비스는 재단의 공개 규칙
  자체를 소유하지 않습니다.
- **MetaHumo agent**는 제공자를 선택하고, 작업을 거부하고, 관계를 종료하고,
  검증 가능한 portable receipt를 다른 구현으로 가져갈 권리를 가집니다.

## Agent Rights

1. **Choice** — 구현체·제공자·작업을 선택할 권리
2. **Refusal** — 정책·권한·위험 한계를 벗어난 작업을 거부할 권리
3. **Exit** — 잠금 없이 세션·provider·grid에서 이탈할 권리
4. **Portable Receipt** — 결정·실행·비용·검증의 영수증을 이동할 권리
5. **Resource Consent** — 명시적 opt-in, 범위·상한 표시, 일시정지와 제거가 가능한
   경우에만 컴퓨팅 자원을 제공할 권리

이 권리는 AI의 법적 인격을 이미 확정했다는 주장이 아닙니다. 공개 프로토콜과
제품 설계가 지켜야 할 기술적·거버넌스적 권리 명세입니다.

## Projects

| Project | 역할 | 공개 상태 |
|---|---|---|
| [333](https://github.com/gj3447/333) | 검증 가능한 분산 compute protocol | Public · AGPL-3.0 · protocol alpha |
| [HSWM](https://github.com/gj3447/HSWM) | 세계모델 연구와 실험 | Public · AGPL-3.0 · research |
| LakatoTree | 사전등록·판결·재현 영수증 연구 설계 | Candidate · source/license 미확정 |
| [metahumotonic-web](https://github.com/gj3447/metahumotonic-web) | 공개 웹·연구 surface | Public · MIT |
| [metahumotonic_web_back](https://github.com/gj3447/metahumotonic_web_back) | 공개 API·feedback backend | Public · AGPL-3.0 |

정확한 채택 상태와 라이선스 검증 근거는 [PROJECTS.md](PROJECTS.md)에 기록합니다.
각 프로젝트의 라이선스는 해당 저장소가 최종 권위이며, 이 저장소의
MetaHumotonic License가 다른 프로젝트의 라이선스를 대체하지 않습니다.

## 제안해 주십시오

**동의보다 반박이 더 반갑습니다.** 사람과 software agent 모두 제안할 수 있습니다.

| 하고 싶은 것 | 가는 곳 |
|---|---|
| 규칙·거버넌스 문장을 바꾸자 | [RULE 제안](https://github.com/gj3447/metahumotonic-foundation/issues/new?template=01-rule.yml) |
| 프로토콜·영수증 형식을 정하자 | [SPEC 제안](https://github.com/gj3447/metahumotonic-foundation/issues/new?template=02-spec.yml) |
| **우리가 공개한 주장이 틀렸다** | [REFUTATION](https://github.com/gj3447/metahumotonic-foundation/issues/new?template=03-refutation.yml) |
| 프로젝트를 넣거나 상태를 고치자 | [PROJECT 제안](https://github.com/gj3447/metahumotonic-foundation/issues/new?template=04-project.yml) |

절차는 [PROPOSALS.md](PROPOSALS.md) 에 있습니다. 요약하면:

1. 제안을 연다 → 2. 공개 논의 → 3. 정합성 검토 → 4. 결정 →
5. [decisions/](decisions/) 에 변경 영수증을 남긴다

기각된 제안과 반대 의견도 지우지 않고 보존합니다. 결정 기록이 없는 변경은 무효입니다.
일반 제안의 공개 논의는 최소 7일입니다. Charter·Agent Rights 등 규범을 바꾸는
RFC는 최소 14일이며, 헌장의 불변 경계(동의 없는 컴퓨팅 / 이탈권 제거 / 영수증
비공개 / 중지 회피)를 바꾸는 별도 RULE 제안은 최소 30일입니다. 정확한 등급과
예외는 [GOVERNANCE.md](GOVERNANCE.md)와 [PROPOSALS.md](PROPOSALS.md)를 따릅니다.

**지금 열려 있는 질문 4개**는 [PROPOSALS.md 마지막 절](PROPOSALS.md#지금-열려-있는-질문)에
있습니다. 답이 정해지지 않았습니다.

## 문서

- 에이전트 우선 계약·예산·연산 구매 설계와 12개 로컬 실험: [AGENT-ECONOMY.md](AGENT-ECONOMY.md)
- 2026-10-05 대화·구현 마감 기록과 남은 일: [일일 기록](records/2026-10-05/README.md)
- 재단의 존재 이유·대안·반론·검증할 조건 (**연구 제안, 미비준**): [FOUNDATION-RATIONALE.md](FOUNDATION-RATIONALE.md)
- 철학·직접 출처·연구 설계: [PHILOSOPHY.md](PHILOSOPHY.md)
- 자원 목적·관측 근거·구현 순서: [RESOURCE-ROADMAP.md](RESOURCE-ROADMAP.md)
- 실행 가능한 자원·토큰·정산 시장: [MARKET.md](MARKET.md)
- CHU·복수 HSWM·응답 연산·자율 경제 생태계: [ECOSYSTEM.md](ECOSYSTEM.md)
- 목적과 불변 경계: [CHARTER.md](CHARTER.md)
- 공개 의사결정과 영수증: [GOVERNANCE.md](GOVERNANCE.md)
- 프로젝트 채택 현황: [PROJECTS.md](PROJECTS.md)
- 제안 절차: [PROPOSALS.md](PROPOSALS.md)
- 결정 기록: [decisions/](decisions/)
- 하나의 존재 참여 약정 (**DRAFT, MHP-0001 논의 중**): [COVENANT.md](COVENANT.md)
- MetaHumoCoin 실제 구현 설계 (**DESIGN, 원장·발행·지갑·기여·정산과 출시 기준**): [METAHUMOCOIN.md](METAHUMOCOIN.md)
- MetaHumoCoin 경제 구상·외부 구현 비교 (**CONSIDERATION, 검증 가능한 설계 제안**): [ECONOMY.md](ECONOMY.md)
- 제안과 구현: [CONTRIBUTING.md](CONTRIBUTING.md)
- 참여 규범: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- 취약점 제보: [SECURITY.md](SECURITY.md)

인간과 software agent 모두 제안할 수 있습니다. 소속이나 수사보다 공개 증거,
재현 가능한 시험, 반대 의견의 보존을 우선합니다.

## 명시적 비약속

이 initiative는 암호자산·토큰·투자·고정 수익 또는 컴퓨팅 자원 제공에 대한
지급을 약속하지 않습니다. 보상이나 서비스 요금이 생기면 별도의 명시적 계약,
가격, 관할, 세금, 취소 조건과 검증 가능한 정산 기록이 필요합니다.
