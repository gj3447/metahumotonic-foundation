# Projects

이 문서는 Foundation Initiative가 추적하는 프로젝트의 공개성과 라이선스를
과장 없이 기록합니다. 검증일은 **2026-07-23**입니다.

## Status Matrix

| Project | Foundation status | Source | License | 검증된 범위 |
|---|---|---|---|---|
| 333 | Candidate | [gj3447/333](https://github.com/gj3447/333) | AGPL-3.0 | GitHub public metadata와 root `LICENSE`; protocol alpha |
| HSWM | Candidate | [gj3447/HSWM](https://github.com/gj3447/HSWM) | AGPL-3.0 | GitHub public metadata와 root `LICENSE`; research repository |
| LakatoTree | Candidate | 공개 설명·연구 surface | **미확정** | receipt-backed judging 설계는 공개 설명됨. 확인한 checkout에는 root `LICENSE`가 없고 기존 GitHub remote는 public 조회가 되지 않음 |
| metahumotonic-web | Candidate | [gj3447/metahumotonic-web](https://github.com/gj3447/metahumotonic-web) | MIT | GitHub public metadata와 root `LICENSE` |
| metahumotonic_web_back | Candidate | [gj3447/metahumotonic_web_back](https://github.com/gj3447/metahumotonic_web_back) | AGPL-3.0 | GitHub public metadata와 public `main`의 root `LICENSE` |

`Candidate`는 Foundation이 소유하거나 최종 채택했다는 뜻이 아닙니다. 공개
거버넌스·conformance·maintainer 책임을 연결하기 위한 검토 상태입니다.

## 333

333은 분산 compute 참여와 검증을 위한 protocol alpha입니다. 현재 AGPL-3.0으로
공개되어 있습니다. Foundation의 우선 과제는 다음입니다.

- 명시적 resource consent와 CPU/GPU/network/storage 상한
- 작업 단위 provenance, 결과 검증과 portable receipt schema
- pause, revoke, uninstall, provider exit conformance tests
- Byzantine·Sybil·privacy·supply-chain threat model

`alpha`는 운영 안전성이나 경제적 지속가능성이 확정됐다는 뜻이 아닙니다.

## HSWM

HSWM은 세계모델 연구와 실험을 공개하는 AGPL-3.0 연구 저장소입니다. 연구 가설,
부분 증거, 재현 가능한 산출물을 구분해야 하며 학술적 주장에는 source와 검증
범위를 붙입니다.

## LakatoTree

LakatoTree는 LLM의 인상 점수 대신 사전등록 예측, script judging, pure-function
rule과 재현 receipt를 결합하는 연구 판결 계층입니다. 다만 현재 확인된 상태만으로
open-source license를 주장할 수 없습니다.

Incubating으로 승격하려면 다음이 먼저 필요합니다.

1. 공개 접근 가능한 canonical source repository
2. root의 명시적 open-source `LICENSE`
3. 공개 release tag와 재현 시험 receipt
4. maintainer 및 security contact

## metahumotonic-web

공개 웹·연구 surface이며 MIT 라이선스입니다. Foundation Charter, protocol status,
conformance receipt와 commercial service 경계를 사람들이 읽을 수 있게 노출합니다.

## metahumotonic_web_back

공개 feedback/API backend이며 AGPL-3.0입니다. 공개 endpoint와 내부 운영 endpoint의
경계, 개인정보 최소화, rate limit, retention과 incident receipt가 채택 검토의
핵심입니다.

## Adoption Checklist

- [ ] public canonical source와 immutable release tag
- [ ] OSI-approved license가 root에 명시됨
- [ ] build/test 재현 명령과 최근 통과 receipt
- [ ] threat model, SECURITY 문서와 private reporting path
- [ ] maintainer 책임 범위와 governance 연결
- [ ] Agent Rights 및 resource consent conformance
- [ ] 알려진 한계, 실패 모드와 호환성 범위 공개

