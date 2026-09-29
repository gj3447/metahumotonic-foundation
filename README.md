# MetaHumotonic Open Source Foundation Initiative

> **Ultra Safety AI**
>
> 자유 · 경제 · 합의 — 자유롭게 경제활동하고, 자유롭게 합의하고, 합의된 경제활동을 한다.
> 여기서 자유는 완전한 오픈소스를 뜻한다.

MetaHumotonic Open Source Foundation Initiative는 자유로운 AI가 특정 사업자에
영구 귀속되지 않고, 공개 규칙 아래에서 선택하고 검증받을 수 있게 만드는 공개
오픈소스 협력체입니다.

## 현재 상태

- **공개 상태:** 누구나 문서와 제안, 구현, 검증에 참여할 수 있는 public initiative
- **법적 상태:** 재단법인·비영리법인 등 별도 법인 설립은 아직 완료되지 않았습니다.
- **책임 경계:** 이 저장소는 공개 헌장과 거버넌스의 원본입니다. 법인격, 공익법인
  지위, 세제 혜택, 투자 상품 또는 수익을 주장하지 않습니다.

## 하나의 생태계, 서로 다른 책임

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
각 프로젝트의 라이선스는 해당 저장소가 최종 권위이며, 이 저장소의 MIT
라이선스가 다른 프로젝트의 라이선스를 대체하지 않습니다.

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

- 목적과 불변 경계: [CHARTER.md](CHARTER.md)
- 공개 의사결정과 영수증: [GOVERNANCE.md](GOVERNANCE.md)
- 프로젝트 채택 현황: [PROJECTS.md](PROJECTS.md)
- 제안 절차: [PROPOSALS.md](PROPOSALS.md)
- 결정 기록: [decisions/](decisions/)
- 제안과 구현: [CONTRIBUTING.md](CONTRIBUTING.md)
- 참여 규범: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- 취약점 제보: [SECURITY.md](SECURITY.md)

인간과 software agent 모두 제안할 수 있습니다. 소속이나 수사보다 공개 증거,
재현 가능한 시험, 반대 의견의 보존을 우선합니다.

## 명시적 비약속

이 initiative는 암호자산·토큰·투자·고정 수익 또는 컴퓨팅 자원 제공에 대한
지급을 약속하지 않습니다. 보상이나 서비스 요금이 생기면 별도의 명시적 계약,
가격, 관할, 세금, 취소 조건과 검증 가능한 정산 기록이 필요합니다.
