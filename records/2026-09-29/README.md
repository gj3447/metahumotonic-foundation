# 2026-09-29 작업 기록 (2차 개정)

> `SECONDARY_AI` 기록. **정본은 [session.jsonld](session.jsonld)**이고, 이 문서는 사람이 읽는 뷰다.
> 요청 요약은 AI가 쓴 요약이며 사용자 발화 인용이 아니다(원문 인용은 [SPIRIT.md](../../SPIRIT.md) §0에만 있다).

## 표준 스택

2026-09-29에 웹에서 표준 상태를 확인했다. 완성된 표준만 채택하고, 초안은 추적만 한다.

| 표준 | 상태 | 여기서 |
|---|---|---|
| [JSON-LD 1.1](https://www.w3.org/TR/json-ld11/) | W3C REC | 채택: 기록 형식 |
| [PROV-O](https://www.w3.org/TR/prov-o/) | W3C REC | 채택: 행위자·단계·산출물 계보 |
| [SHACL 1.0](https://www.w3.org/TR/shacl/) | W3C REC | 채택: [session.shapes.ttl](session.shapes.ttl) |
| [SPARQL 1.1](https://www.w3.org/TR/sparql11-query/) | W3C REC | 채택: 역량 질문 |
| [RDF 1.2](https://www.w3.org/news/2026/w3c-invites-implementations-of-rdf-1-2-concepts-and-abstract-data-model-and-rdf-1-2-semantics/) | W3C CR (2026-04) | 추적. 명제는 명시적 노드로 두고 REC 이후 reifier로 옮긴다 |
| [SPARQL 1.2](https://www.w3.org/TR/2026/WD-sparql12-query-20260910/) · [SHACL 1.2](https://www.w3.org/TR/shacl12-core/) | W3C WD | 추적 |
| [ISO/IEC 39075 GQL](https://www.iso.org/standard/76120.html) | ISO 2024 | 해당 없음 (property-graph DB용) |
| SYMPOSIUM Graph Engineering · HSWM 규칙 · CHU plan 규칙 | 로컬 | 채택: 그래프 종류 분리, 이 레포는 G0 |

## 단계 (PROV-O `prov:Activity`, `prov:wasInformedBy`로 연결)

| # | 단계 | 결과 | 산출/영향 |
|---|---|---|---|
| 1 | 레포 구조·기존 규범 파악 | DONE | |
| 2 | 정신 명제 P1–P6 기록, 충돌 검토, 재진술 R3·R5·H1 | DONE | `SPIRIT.md`, `graph/spirit.graph.yaml` |
| 3 | 사용 조건 라이선스 초안 요청 | DECLINED | 중단된 부분 파일 제거 |
| 4 | 라이선스 설계 그래프 요청 | DECLINED | 중단된 부분 파일 제거 |
| 5 | 하드웨어 전체 공유를 필수로 한 재작성 요청 | DECLINED | 대안만 제시, 파일 없음 |
| 6 | 표준 그래프 엔지니어링 확인·조사 | DONE | 앞선 YAML 그래프는 표준 부적합으로 판정 |
| 7 | kg-ontology로 SYMPOSIUM·공유 KG 확인 | DONE | `sym:DefinedTerm:메타휴모토닉` 참조 |
| 8 | SPIRIT 정리 계획 그래프 작성 시도 | STOPPED | 파일 생성 안 됨 |
| 9 | 고려사항으로 커밋·푸시 | DONE | `9c40207` @ `mhp-0002-spirit-consideration` |
| 10 | 웹 표준 조사 + 1차 기록 구축·검증 | DONE | 1차본 (CQ2 쿼리 한 번 수정) |
| 11 | 1차 기록 커밋·푸시 | DONE | `dfd0a59`. 이 세션이 만들지 않은 `230eecb`가 함께 올라감 → 보고 |
| 12 | 남은 변경 전부 커밋·푸시 | DONE | `bb34100` (세션 전 수정 문서 4개). 미추적 조각 파일은 열어 보고 제외 |
| 13 | 조각 파일 삭제 | DONE | `graph/compute-license.working.graph.yaml` 삭제 |
| 14 | 기록 2차 개정 | DONE | 이 디렉터리 |

## 커밋 체인 (`mhv:parentCommit`, 실제 git 부모와 대조)

```
738dd7a (세션 시작 HEAD, mhp-0001-covenant)
  └ 9c40207  SPIRIT.md · spirit.graph.yaml       [이 세션]
     └ 230eecb  agent rules 라우팅                 [제안자 측, 의도한 커밋]
        └ dfd0a59  1차 기록                        [이 세션]
           └ bb34100  CHARTER·GOVERNANCE·PROPOSALS·README  [내용: 제안자 측 / 커밋: 이 세션]
```

커밋된 파일 10개는 모두 해당 커밋의 바이트로 sha256을 대조한다.

## 정정 (`mhv:Assertion` → `mhv:Correction`)

- **a1 (SUPERSEDED):** "`graph/compute-license.working.graph.yaml`은 이 세션이 만들지 않은 파일이다."
  - 9·10단계와 1차 README에서 파일을 열어 보지 않고 추정한 것이다.
- **c1:** 그 파일은 이 세션의 중단된 응답이 남긴 조각이었다. 작성자 표기로 확인했다.
  - 공개하지 않고 삭제했다.
  - 틀린 주장은 지우지 않고 정정과 함께 남긴다.

## 결정

| ID | 내용 | 상태 |
|---|---|---|
| d1 | `SPIRIT.md`의 P3를 원문(사용 조건)으로 둘지, R3(참여 조건)로 받을지 | 대기 |
| d2 | `graph/spirit.graph.yaml`을 JSON-LD/PROV-O/SHACL 정본으로 다시 정리할지 | 대기 |
| d3 | 세션 전부터 수정돼 있던 문서 4개 처리 | 해결: 12단계, `bb34100` |
| d4 | 조각 파일 처리 | 해결: 13단계, 삭제 |
| d5 | `mhp-0002-spirit-consideration` 브랜치를 PR로 열지, main에 어떻게 합칠지 | 대기 |

## 검증

```sh
python -m venv .venv && .venv/bin/pip install pyshacl   # 0.40.1 / rdflib 7.6.0 에서 확인
.venv/bin/python records/2026-09-29/check.py
```

2026-09-29 2차 개정 결과는 `OK`였다.

1. SHACL positive: PASS (460 triples)
2. SHACL negative: 일부러 넣은 위반 8개를 모두 검출
   - 행위자 누락, AI 요약 권한 표시 누락, 거절 단계 설명 누락, 초안 표준 채택
   - 해결자 없는 해결, 부모 없는 커밋, 해시 없는 커밋 파일, 정정 없는 SUPERSEDED 주장
3. 역량 질문 CQ1–CQ9: 기대한 subject와 일치
   - 거절·중단 단계, 커밋 생성 단계, 추적 표준, 커밋 체인, 제거 파일
   - 정정, 세션 외 커밋, 해결된 결정, 대기 결정
4. 파일 해시: 3개 커밋의 파일 10개가 기록과 일치
5. 커밋 부모: 4개가 `git rev-parse <commit>^`와 일치

2차 개정 중 CQ4(커밋 체인이 커밋된 파일까지 잡음)와 CQ8(유효하지 않은 IRI 생성) 쿼리 버그를 고쳤다.
1차본은 git `dfd0a59`에 그대로 남아 있다 (`prov:wasRevisionOf`).
