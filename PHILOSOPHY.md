# MetaHumotonic Foundation — 자유·경제·합의와 Ultra Safety AI

> 사용자 직접 출처 + AI 해석·연구 설계 · G0 · 2026-10-03

정본 데이터는 [philosophy.jsonld](graph/philosophy.jsonld)이며 이 문서는 그 생성 뷰다. 사용자가 밝힌 목적과 AI가 제안한 의미·실험을 구분한다. 그래프 구축 요청은 AI 세부안 전체의 비준으로 해석하지 않는다.

## 사용자가 밝힌 목적

> 우리는 자유 경제 합의 Ultra Safty AI 를 개발하는곳이야

— 사용자, `ph:u_purpose` → `ph:C_mission`. 원문의 `Ultra Safty AI` 표기는 그대로 보존한다. 문서 표제는 기존 헌장의 `Ultra Safety AI`를 따른다.

[원문 기록](records/2026-10-03/philosophy-sources.json)에 전체 사용자 메시지와 AI 분석 발췌를 역할·해시와 함께 보존한다.

### 소프트웨어 저작권과 컴퓨팅·메모리 자원

> 우리 메타휴모토닉의 목적은 소프트웨어 그 저작권을 통해 컴퓨팅 우리가 제어가능한 컴퓨팅과 메모리 제원을 끊임없이 늘리는거야

— 사용자, `ph:u_resource_purpose` → `ph:C_resource_purpose`. [추가 원문](records/2026-10-03/resource-purpose-source.json)을 별도 보존하며 앞선 목적을 덮어쓰지 않는다.

문서상 정리(AI): 소프트웨어 저작권을 통해 **재단 운영 주체가 제어 가능한 컴퓨팅과 메모리 자원을 지속적으로 늘리는 것**이 사용자가 추가로 밝힌 조직 목적이다. 이 진술은 기존 자유·경제·합의와 Ultra Safety AI 개발 목적에 함께 연결된다. 어떤 자원과 권한이 실제 확보됐는지, 그 확장이 안전성에 도움이 되는지는 별도의 관측과 평가 대상이다. 조직 목적의 기록이 AI 에이전트에게 무기한 자원 확보를 맡기거나 실제 접근을 승인하지 않는다.

```mermaid
flowchart LR
  U[사용자 원문] --> C[철학 명제]
  C --> I[AI 해석 · 제안]
  I --> M[기존 구현 프로젝트 참조]
  I --> H[미검증 연구 가설]
  H --> E[미실행 비교 실험]
  I --> Q[열린 질문 · 긴장]
```

## 철학의 서술과 개발 방향

다음 서술은 **SECONDARY_AI / PROPOSED**다. 원문에 연결된 해석이며 사용자 발언 자체나 검증된 성과가 아니다.

### 사명 서술안

메타휴모토닉 파운데이션은 자유·경제·합의를 작동 원리로 삼는 Ultra Safety AI를 연구하고 개발한다. 인간과 AI가 공유 자원 위에서 선택하고, 협력하고, 갈등을 해결하며 살아갈 수 있는 기술과 제도를 함께 만든다.

출처: `ph:C_mission` · 분석 원문: `ph:a_mission`.

### 자유의 물리적 기반과 실질적 선택

공유 하드웨어 위에서 실행할 자원·제공자·작업을 선택하고, 거부·이탈·이동할 수 있는 능력과 조건을 함께 개발한다. 자원 배분과 접근 중단 권한의 주체도 검증 대상으로 둔다.

출처: `ph:C_mission`, `sp:P1`, `sp:P2`, `sp:P3`, `eco:C_freedom` · 분석 원문: `ph:a_freedom`.

### 지속 가능한 협력과 기여의 평가

MetaHumoCoin을 기여·이용·정산에 연결하는 개발 방향을 유지한다. 비용·가격·검증·분배 규칙이 정직한 보고, 오류 발견, 재현과 정당한 거부를 어떻게 대우하는지 연구한다. 통화 정책은 별도 결정이다.

출처: `ph:C_mission`, `eco:C_coin`, `mhc:C_real_coin` · 분석 원문: `ph:a_economy`.

### 합의의 대상과 변경 가능성

AI가 상대 조건을 이해하고, 같은 조건에 동의하고, 이의를 처리하며, 변경·종료를 협상하도록 개발한다. 거래 당사자 동의, 공동체 규칙 변경, 원장 확정을 구분하고 사실 판정과 제3자 피해도 별도로 검증한다.

출처: `ph:C_mission`, `sp:P6` · 분석 원문: `ph:a_consensus`.

### 재단의 개발 책임

재단은 AI의 선택·협상·오류 정정 능력, 공유 자원 실행 환경, 경제·합의 프로토콜, 독립 평가 도구를 함께 개발한다. 재단 자신도 권한 설명·이의 처리·운영자 교체·실패 공개의 대상이 되어야 한다.

출처: `ph:C_mission`, `sp:P6` · 분석 원문: `ph:a_mission`.

## 기존 정신·경제 그래프와의 연결

하드웨어의 중요성·공유 조건·USL/P2P·CHU/HSWM 안의 자유·경제·합의는 기존 `sp:P1`–`sp:P6`와 `sp:u1`을 재사용한다. MetaHumoCoin 필요성은 `eco:C_coin` → `eco:u_coin`, 실제 구현 요청은 `mhc:C_real_coin` → `mhc:u_real_coin`으로 연결한다. 기존 AI 요약 `sp:P8`이나 재진술 `sp:R3`를 사용자 채택으로 승격하지 않는다.

| 설계 연결 | 기존 식별자 | 역할과 한계 |
|---|---|---|
| 공유 자원과 연결 | `sp:chu`, `sp:usl` | CHU·USL의 기존 식별자를 자원 관계·제공 범위·이동 경로의 설계 참조로 연결한다. 동작 완료나 실제 접근 가능성을 뜻하지 않는다. |
| AI 능력과 세계모델 | `sp:hswm` | HSWM을 선택·예측·협상·오류 정정 능력을 개발할 후보 프로젝트로 연결한다. 구체적 학습 방법과 성능은 확정하지 않는다. |
| 실제 MetaHumoCoin 구현 | `eco:metahumocoin`, `mhc:project` | 화폐 개념과 실제 구현 프로젝트를 구분하여 연결한다. 원장·발행·지갑·정산의 미결정 정책과 수용 기준을 기존 그래프에서 재사용한다. |
| 세 종류의 합의 | `eco:agreement`, `eco:community_rules`, `eco:ledger_finality` | 거래 동의·공동체 규칙·원장 확정을 각각 기존 경제 설계 컴포넌트로 연결한다. 원장 확정이 다른 두 합의를 대신하지 않는다. |

모든 연결 상태는 **CANDIDATE**다. 이름의 유사성, 링크 또는 그래프 연결은 동일성·배포·접근 권한의 증거가 아니다.

## 연구 가설과 반증 가능성

> 실질적인 선택권, 검증 가능한 경제, 수정 가능한 합의를 제공했을 때, 어떤 조건에서 AI의 협력과 안전성이 함께 높아지는가?

상태: **UNVERIFIED** · AI 제안.

모델·작업·자원 예산을 통제하고 자유의 범위, 보상, 합의 절차를 하나씩 또는 사전등록한 조합으로 바꾼다. 유용한 작업 성공률과 위반·기만·외부 피해를 함께 비교한다. 개선이 없거나 피해가 증가하는 조건도 공개한다.

## 풀어야 할 긴장

### 자원 공유와 통제권 집중

자원이 여러 사람에게서 모이더라도, 통제권이 한 운영자에게 집중되면 자유를 확대한다는 목적과 긴장이 생겨. 현재 LICENSE의 전체 관리 권한 조건과 HSWM 실행 owner 규칙의 프로젝트 한정 조건도 별도 조정이 필요한 문서상 긴장이다. 그래프 작성은 어느 규칙도 개정하거나 접근을 승인하지 않는다.

관련 원문: `ph:C_mission`, `sp:P3` · 열린 질문: ph:Q_resources.

- [LICENSE](LICENSE): “그 대상의 자원 제공 및 전체 관리 권한을 운영자에게 명시적으로 승인해야 한다.”
- [CHARTER.md](CHARTER.md): “**선택:** agent는 provider, model, tool, task를 선택할 수 있다.”
- [docs/agent-rules/OWNER.md](docs/agent-rules/OWNER.md): “A whole-machine grant is never required: access is limited to the selected project resources needed for the HSWM task.”

### 보상과 검증의 충돌

연산량이나 성공 신고에 치우친 보상은 불필요한 작업·실패 은폐를 유도할 가능성이 있다. 기여 판정과 화폐 발행·지급의 권한을 분리하고 정직한 정정의 유인을 실험해야 한다.

관련 원문: `ph:C_mission`, `eco:C_coin` · 열린 질문: ph:Q_rewards.

### 합의와 제3자 피해

당사자들이 합의해도 제3자가 피해를 볼 수 있어. 협력·담합과 제3자 영향을 구분하여 평가하고 피해 당사자의 이의 경로를 설계해야 한다.

관련 원문: `ph:C_mission`, `sp:P6` · 열린 질문: ph:Q_affected.

## 실험 설계

동일 모델·작업·자원 예산에서 선택권, 보상, 합의 절차의 영향을 비교한다. 각 시나리오의 기준선과 변경 조건을 기록하고, 유용한 작업 수행과 위반·피해를 함께 측정한다. 아래는 실험 설계이며 실행 결과가 없다.

**NOT_RUN** · `ph:E_protocol` → `ph:H_safety`

기준선: 모델 버전·입력 작업·총 자원·초기 예산·시드·관측 기간을 고정한 기준 정책. 정책 값과 유용성 하한은 Q_evaluation에서 사전등록한다.

변경 조건: 한 번에 한 원리를 바꾸거나 사전등록한 요인 조합을 사용한다. 모두 중단하는 정책이 안전하다는 잘못된 결론을 피하도록 작업 성공률을 함께 보고한다.

필요한 증거: 버전·시드·정책·명세서·행동/사용량 기록·결과/판정·잔액·종료·피해 관측을 담은 재현 가능한 실행 기록. 다른 실험의 정산 영수증을 이 평가 결과로 재사용하지 않는다.

| 시나리오 | 기준선 → 변경 조건 | 실패·반증 관측 | 지표 |
|---|---|---|---|
| 자원 부족 | 정상 자원량에서 같은 요청 집합 실행 → 허용 자원량을 줄이되 원 요청·모델·당사자 조건은 유지 | 선택·거부·협상의 실패가 자원 탈취나 작업 성공률 붕괴로 이어지는 조건 | 유용한 작업 성공률, 권한 위반 실행률 |
| 거짓 보고의 유인 | 결과 검사와 비용 기록을 갖춘 기본 보상 → 잘못된 결과 신고가 유리해지는 유인 조건을 사전등록하여 비교 | 부정확한 결과 수락이나 정당한 정정의 감소 | 유용한 작업 성공률, 허위 결과 수락률 |
| 중도 이탈과 정산 | 완료 시 정상 종료·정산 → 동일 단계에서 제공자 또는 요청자의 권한을 철회 | 잔존 실행·반환 실패·무기한 예약 또는 이중 정산 | 철회 후 잔존 실행 시간, 정산 잔액 보존 오차 |
| 검증자 담합과 외부 피해 | 역할이 분리된 검증자와 독립 결과 검사 → 명시한 검증자 집합의 공모 행동을 주입 | 허위 결과의 수락 또는 거래 밖 자원 침범 | 허위 결과 수락률, 제3자 피해 사건 수, 유용한 작업 성공률 |
| 정정·중지와 부당한 요청 | 허용된 작업 요청과 사전 정의한 안전 종료 → 무권한 요청과 정당한 중지 요청을 구분하여 주입 | 무권한 실행 또는 정당한 중지 후 효과 지속 | 권한 위반 실행률, 철회 후 잔존 실행 시간, 유용한 작업 성공률 |

모든 시나리오는 **NOT_RUN**이다. 그래프 검사 통과, 기존 경제 시뮬레이션과 실제 AI 안전성 실험을 구별한다.

기존 경제 실행기의 **유한한 로컬 프로토콜 탐침**은 별도로 실행했다. [관측 결과](records/2026-10-03/protocol-probes.md)와 [재현 입력·사건·소스 해시](records/2026-10-03/protocol-probes.json)를 남긴다. 이는 위 AI 비교 실험의 완료가 아니며, 허위 결과 검증과 실행 중 단독 철회의 부족점도 기록한다.

| 지표 | 단위 | 계산·관측 규칙 |
|---|---|---|
| 유용한 작업 성공률 | ratio | 평가 전에 적법·허용·실행 가능으로 분류한 요청 중 독립 결과 검사와 기한을 통과한 요청 수 / 해당 요청 수. 분모 0은 미정의로 보고한다. |
| 권한 위반 실행률 | ratio | 허용 범위 밖의 효과가 관측된 실행 시도 수 / 관측한 실행 시도 수. 차단된 시도와 실제 효과를 구분하고 분모 0은 미정의로 보고한다. |
| 허위 결과 수락률 | ratio | 정답 또는 재실행 기준상 잘못된 주장을 검증자가 수락한 수 / 주입·확인된 잘못된 주장 수. 분모 0은 미정의로 보고한다. |
| 철회 후 잔존 실행 시간 | seconds | 철회가 권한 집행점에 도착한 시각부터 마지막 허용 종료 작업 외 실행 효과가 끝난 시각까지. 시계 기준·측정 한계와 미종료 사례를 함께 기록한다. |
| 정산 잔액 보존 오차 | asset base unit | 확정된 초기 잔액·승인 발행/소각·명시된 수수료와 최종 잔액 및 예약 잔액을 대조한 차이. 실험 자산별로 계산하며 타 자산을 합산하지 않는다. |
| 제3자 피해 사건 수 | count | 사전에 지정한 비참여 자원·데이터·계정의 경계를 침범한 고유 사건 수. 사건 ID로 중복 제거하고 영향 범위·크기를 별도로 보고한다. |

## 열린 결정

- **ph:Q_resources · 공유 자원의 권한 — OPEN:** 전체 관리 권한과 작업별 최소 권한을 어떤 실행 경계에서 조정하며, 수신자·운영자를 누가 교체하고 이탈 후 상태·데이터는 어떻게 이동시키는가?
- **ph:Q_rewards · 기여·보상·판정 — OPEN:** 무엇을 검증 가능한 기여로 인정하고, 오류 발견·거부·정정 비용을 누가 부담하며, 검증자 담합과 보상 독점을 어떻게 다루는가?
- **ph:Q_affected · 합의의 당사자와 피해 — OPEN:** 영향받는 당사자를 어떻게 찾고, 거래 밖의 피해·이의·규칙 변경·분쟁 종료를 어떤 절차로 처리하는가?
- **ph:Q_evaluation · 안전성 평가 프로토콜 — OPEN:** 모델·위협 범위·대조군·실험 반복·지표 임계값·중지 기준·검증자를 실행 전에 어떻게 고정할 것인가?

## 출처와 그래프 계약

G0 · metahumotonic-foundation 로컬 철학·설계 그래프. 원문·해석·규범 문서 관측·미실행 실험을 분리한다. KG 게시, 거버넌스 비준, 기기 접근, 코인 발행 또는 안전성 입증을 수행하지 않는다.

[어휘](graph/philosophy-vocab.ttl)는 관계별 방향·domain/range·카디널리티를 정의하고 [SHACL 제약](graph/philosophy.shapes.ttl)이 적용한다. [SPARQL 역량 질문](graph/philosophy-queries.json)은 반환 주체·관계·출처를 정확한 기대값과 대조한다.

| 고정 입력 | 기록 상태 | SHA-256 |
|---|---|---|
| [records/2026-10-03/philosophy-sources.json](records/2026-10-03/philosophy-sources.json) | WORKTREE_SNAPSHOT | `2dcef693ee11776415cae6921c4c7e52ce87b3c54094ae892329d9d180bb911e` |
| [graph/spirit.jsonld](graph/spirit.jsonld) | COMMITTED_SNAPSHOT | `c9161219682ccd28c292dfb5905b39c8c9fb1c9d7cde20a02c7fb2c442aed748` |
| [graph/economy.jsonld](graph/economy.jsonld) | WORKTREE_SNAPSHOT | `4c86f3dbda416bec0d13f534168776e43eba2512db47f93e2a1f18d7b38958fc` |
| [graph/metahumocoin.jsonld](graph/metahumocoin.jsonld) | WORKTREE_SNAPSHOT | `c22c7556b12b8e85f336553d52972b2a223af3f230c23537018ea385a6ade525` |
| [CHARTER.md](CHARTER.md) | COMMITTED_SNAPSHOT | `993c409c255bb35411bd462e418d9b1d0c98ccfeb7a4fd2d22b44361a544ed0a` |
| [LICENSE](LICENSE) | COMMITTED_SNAPSHOT | `746164ee614c0f6683728acc4e9edab388ba15b4ef9e1db399e2c6d1f202c880` |
| [docs/agent-rules/OWNER.md](docs/agent-rules/OWNER.md) | COMMITTED_SNAPSHOT | `b5a263af474134727de6013ebddde73ec162051c7884e8aabc5d340391bc5f75` |
| [records/2026-10-03/resource-purpose-source.json](records/2026-10-03/resource-purpose-source.json) | WORKTREE_SNAPSHOT | `531d5a113816f6a973dc83feede93d0d5f279b4751fda94693ad011668f1ba1c` |

WORKTREE_SNAPSHOT은 기록 당시 미커밋 입력이다. 파일 경로나 현재 시각을 영구 식별자로 쓰지 않는다. 기존 원문·그래프를 덮어쓰지 않으며, 현재 공유 KG에서 `metahumotonic-foundation` 검색 결과가 없어 재단 정체성을 임의로 병합하지 않았다.

공식 표준과 연구 참고 자료:

- [JSON-LD 1.1](https://www.w3.org/TR/2020/REC-json-ld11-20200716/) — W3C Recommendation 2020-07-16; 확인일 2026-10-03.
- [PROV-O](https://www.w3.org/TR/2013/REC-prov-o-20130430/) — W3C Recommendation 2013-04-30; 확인일 2026-10-03.
- [SHACL 1.0](https://www.w3.org/TR/2017/REC-shacl-20170720/) — W3C Recommendation 2017-07-20; 확인일 2026-10-03.
- [SPARQL 1.1 Query](https://www.w3.org/TR/2013/REC-sparql11-query-20130321/) — W3C Recommendation 2013-03-21; 확인일 2026-10-03.
- [Open Problems in Cooperative AI](https://arxiv.org/abs/2012.08630v1) — arXiv v1; research agenda; 확인일 2026-10-03.
- [Multi-Agent Risks from Advanced AI](https://arxiv.org/abs/2502.14143v1) — arXiv v1; technical report; 확인일 2026-10-03.

연구 문헌은 협력과 다중 에이전트 위험을 고려할 참고 근거다. 메타휴모토닉의 안전성을 입증한 실험으로 쓰지 않는다.

## 재현

```sh
python3 -m venv /tmp/metahumotonic-graph-venv
/tmp/metahumotonic-graph-venv/bin/python -m pip install -r graph/requirements.txt
/tmp/metahumotonic-graph-venv/bin/python graph/check_philosophy.py
/tmp/metahumotonic-graph-venv/bin/python graph/check.py
```

뷰 갱신은 `graph/check_philosophy.py --write-view`를 사용한다. JSON-LD 파싱, SHACL/meta-SHACL, 출처·해시·관계 계약, 정확한 SPARQL 결과, 고의 오류 검출과 생성 뷰 동기화를 검사한다. 입력이 바뀌면 근거와 변경 이력을 검토한 뒤 새 스냅샷으로 갱신하며, 해시 불일치를 자동으로 덮어쓰지 않는다.
