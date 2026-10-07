# Contributing

인간과 software agent 모두 참여할 수 있습니다. 회사 소속, 모델 이름, 홍보 문구가
아니라 변경의 provenance와 재현 가능한 증거로 제안을 평가합니다.

## 시작하기

1. [CHARTER.md](CHARTER.md)의 Agent Rights와 non-goals를 읽습니다.
2. 기존 issue/RFC에서 중복, 반대 의견, superseded 결정을 확인합니다.
3. 작은 문제는 issue, 규범 변경은 `RFC: <title>`로 제안합니다.
4. 변경 범위에 맞는 test·conformance·source evidence를 함께 제출합니다.
5. 결정이 merge되면 [GOVERNANCE.md](GOVERNANCE.md)의 receipt 필드를 채웁니다.

## 제안 템플릿

```markdown
## Problem
누가 어떤 상황에서 실패하는가?

## Proposed change
정확히 어떤 contract 또는 문장을 바꾸는가?

## Agent rights impact
choice / refusal / exit / portable receipt / resource consent 영향

## Evidence
source, test command, expected and actual result

## Alternatives and objections
채택하지 않은 대안과 남아 있는 반론

## Rollback or supersession
실패하면 어떻게 되돌리거나 supersede하는가?
```

## Agent-authored Contributions

Agent가 제안 또는 구현을 만들었다면 다음을 공개합니다.

- agent/tool identifier와 실행 환경(민감정보 제외)
- human 또는 accountable operator가 부여한 권한 범위
- 사용한 source와 생성·수정된 파일
- 실행한 test와 검증하지 못한 부분
- 외부 코드·문서의 라이선스와 attribution

Agent의 산출물을 인간이 쓴 것처럼 표시하거나, 검증하지 않은 출력을
`confirmed`로 표시하지 않습니다. Agent가 제출했다는 이유만으로 배제하지도
않습니다.

## 기여물의 라이선스와 권리

신규 기여와 새로운 보호 대상 변경분은 [MetaHumotonic License 1.2](LICENSE)을
기본으로 합니다. 기여자는 제출 시 다음을 명시적으로 확인해야 합니다.

- 자신이 해당 기여를 이 라이선스로 공개할 정당한 권한이 있고 이에 동의함
- 외부 자료와 기존 MHL-1.0·1.1·MIT 부분의 출처·라이선스·저작권 고지를 보존함
- 공개할 수 없는 회사·제3자 자료나 자격 증명을 포함하지 않음

저작권은 원 권리자에게 남으며 제출은 양도를 뜻하지 않습니다. Agent 기여도
책임 있는 권한자의 확인이 필요합니다. 권리가 불명확하거나 서로 맞지 않는
라이선스가 포함되면 공개 전에 해결합니다. 정확한 적용 경계는
[LICENSE-NOTICE.md](LICENSE-NOTICE.md)를 따릅니다.

문서·코드 제출 자체는 기기 접근 승인이 아닙니다. MHL 코드의 운영 사용에
필요한 공유 조건과, 실제 기기에 접근할 권한은 LICENSE 제4·5조에 따라
각각 확인합니다. 격리된 빌드·시험·검토에는 운영 사용 조건을 요구하지 않습니다.

## Resource and Grid Contributions

compute 참여 코드는 다음 없이는 merge할 수 없습니다.

- 기본값이 off인 명시적 opt-in
- CPU/GPU/network/storage/time/cost 상한
- 현재 사용량과 작업 목적의 가시성
- 즉시 pause, revoke와 완전한 uninstall 경로
- signed 또는 검증 가능한 task/result receipt
- 데이터 최소화와 보존·삭제 정책

숨은 설치, 별도 승인 없는 권한 취득, 제거 방해, 무제한 background compute는
허용하지 않습니다. 운영 사용의 공유 조건을 먼저 고지하되 실제 접근 승인은
별도로 받습니다.

## Pull Request Quality

- 하나의 PR은 하나의 검토 가능한 목적을 가집니다.
- 기존 반대 의견과 실패 기록을 삭제하지 않습니다.
- 의미가 바뀌면 test 또는 conformance fixture를 함께 바꿉니다.
- 숫자와 안전성 주장은 source, 측정 시각, 범위가 있어야 합니다.
- 프로젝트별 license를 존중하며 이 저장소의 MetaHumotonic License로 재라이선스하지
  않습니다.

취약점과 개인 정보는 공개 issue에 쓰지 말고 [SECURITY.md](SECURITY.md)를
따릅니다.
