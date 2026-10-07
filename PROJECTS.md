# Projects

이 문서는 Foundation Initiative가 추적하는 프로젝트의 공개성과 라이선스를
과장 없이 기록합니다. 공개 라이선스 재확인일은 **2026-10-07**입니다.
계정의 공개 저장소 63개에 대한 별도 채택·기존 적용 확인은
[저장소별 커밋과 검증 기록](records/2026-10-07/public-license-rollout/README.md)에 있습니다.
이 갱신은 프로젝트의 Foundation 채택 단계를 승격하지 않습니다.

## Status Matrix

| Project | Foundation status | Source | License | 검증된 범위 |
|---|---|---|---|---|
| 333 | Candidate | [gj3447/333](https://github.com/gj3447/333) | 기존 AGPL-3.0-only 결합물 유지; 독립 새 저작물만 MHL 1.2 | 원격 LICENSE·LICENSE-NOTICE·METAHUMOTONIC-LICENSE 검증; protocol alpha |
| HSWM | Candidate | [gj3447/HSWM](https://github.com/gj3447/HSWM) | MHL 1.2 기본; 기존 허락 보존 | 원격 LICENSE·LICENSE-NOTICE 검증; research repository |
| LakatoTree | Candidate | [gj3447/lakatotree](https://github.com/gj3447/lakatotree) | MHL 1.2 기본; 기존 허락 보존 | 공개 master의 LICENSE·LICENSE-NOTICE 검증 |
| metahumotonic-web | Candidate | [gj3447/metahumotonic-web](https://github.com/gj3447/metahumotonic-web) | MHL 1.2 기본; 기존 MIT·CC 등 보존 | 원격 LICENSE·LICENSE-NOTICE 검증; 별도 제3자 고지 유지 |
| metahumotonic_web_back | Candidate | [gj3447/metahumotonic_web_back](https://github.com/gj3447/metahumotonic_web_back) | 기존 AGPL-3.0-only 결합물 유지; 독립 새 저작물만 MHL 1.2 | 원격 LICENSE·LICENSE-NOTICE·METAHUMOTONIC-LICENSE 검증 |

`Candidate`는 Foundation이 소유하거나 최종 채택했다는 뜻이 아닙니다. 공개
거버넌스·conformance·maintainer 책임을 연결하기 위한 검토 상태입니다.

## 333

333은 분산 compute 참여와 검증을 위한 protocol alpha입니다. 기존 AGPL 결합물의
조건은 유지합니다. MHL 추가 문서가 그 결합물을 전환하지 않습니다.
Foundation의 우선 과제는 다음입니다.

- 명시적 resource consent와 CPU/GPU/network/storage 상한
- 작업 단위 provenance, 결과 검증과 portable receipt schema
- pause, revoke, uninstall, provider exit conformance tests
- Byzantine·Sybil·privacy·supply-chain threat model

`alpha`는 운영 안전성이나 경제적 지속가능성이 확정됐다는 뜻이 아닙니다.

## HSWM

HSWM은 세계모델 연구와 실험을 공개하며 원저작물의 기본 조건은 MHL 1.2입니다.
기존 AGPL·별도 상업 허락과 제3자 조건은 보존합니다. 연구 가설,
부분 증거, 재현 가능한 산출물을 구분해야 하며 학술적 주장에는 source와 검증
범위를 붙입니다.

## LakatoTree

LakatoTree는 LLM의 인상 점수 대신 사전등록 예측, script judging, pure-function
rule과 재현 receipt를 결합하는 연구 판결 계층입니다. 이전의 공개 여부·라이선스
미확정 관측은 이번 공개 원격 확인으로 갱신합니다. MHL은 소스 공개형이므로
OSI 승인 오픈소스 라이선스를 갖췄다고 주장하지 않습니다.

Incubating으로 승격하려면 다음이 먼저 필요합니다.

1. 공개 접근 가능한 canonical source repository
2. root의 명시적 open-source `LICENSE`
3. 공개 release tag와 재현 시험 receipt
4. maintainer 및 security contact

## metahumotonic-web

공개 웹·연구 surface이며 원저작물의 기본 조건은 MHL 1.2입니다. 기존 MIT·CC BY-SA
허락과 vendored 코드의 별도 조건은 유지합니다. Foundation Charter, protocol status,
conformance receipt와 commercial service 경계를 사람들이 읽을 수 있게 노출합니다.

## metahumotonic_web_back

공개 feedback/API backend이며 기존 결합물은 AGPL-3.0-only를 유지합니다.
독립적으로 허락할 수 있는 새 저작물의 MHL 채택은 LICENSE-NOTICE 범위에 한합니다.
공개 endpoint와 내부 운영 endpoint의
경계, 개인정보 최소화, rate limit, retention과 incident receipt가 채택 검토의
핵심입니다.

## Adoption Checklist

아래 기존 채택 기준은 이번 라이선스 변경으로 충족·개정된 것으로 간주하지 않습니다.
특히 MHL은 OSI 승인 요건을 충족하지 않으며 채택 정책의 별도 검토가 필요합니다.

- [ ] public canonical source와 immutable release tag
- [ ] OSI-approved license가 root에 명시됨
- [ ] build/test 재현 명령과 최근 통과 receipt
- [ ] threat model, SECURITY 문서와 private reporting path
- [ ] maintainer 책임 범위와 governance 연결
- [ ] Agent Rights 및 resource consent conformance
- [ ] 알려진 한계, 실패 모드와 호환성 범위 공개
