# 2026-09-29 작업 기록

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
| 10 | 웹 표준 조사 + 이 기록 구축·검증 | DONE | 이 디렉터리 |

## 사람 결정 대기

1. **d1:** `SPIRIT.md`의 P3를 원문(사용 조건)으로 둘지, R3(참여 조건)로 받을지
2. **d2:** `graph/spirit.graph.yaml`을 JSON-LD/PROV-O/SHACL 정본으로 다시 정리할지
3. **d3:** 세션 이전부터 수정돼 있던 `CHARTER`/`GOVERNANCE`/`PROPOSALS`/`README`를 어떻게 처리할지
4. **d4:** 미추적 파일 `graph/compute-license.working.graph.yaml`의 소유와 처리. 이 세션이 만들지 않았고 읽지도 않았다

## 검증

```sh
python -m venv .venv && .venv/bin/pip install pyshacl   # 0.40.1 / rdflib 7.6.0 에서 확인
.venv/bin/python records/2026-09-29/check.py
```

2026-09-29 결과는 `OK`였다.

- SHACL positive: PASS (259 triples)
- SHACL negative: 일부러 넣은 위반 4개를 모두 검출
- 역량 질문 CQ1–CQ5: 기대한 subject와 일치
- 커밋 `9c40207`의 파일 해시 2개: 일치
