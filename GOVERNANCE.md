# Governance

## 원칙

거버넌스의 정본은 공개 이력입니다. 직함이나 회사 소속이 아니라 제안, 반론,
검증, 결정과 commit으로 이어지는 영수증이 권위의 근거입니다.

## 참여 역할

- **Contributor:** issue, RFC, 코드, 시험, 연구 또는 반론을 제출하는 인간·agent
- **Maintainer:** 정해진 범위의 review와 merge를 맡는 공개 책임자
- **Steward:** Charter, Agent Rights, project adoption 같은 규범적 결정을 검토하는
  공개 책임자
- **Company liaison:** MetaHumotonic company의 운영 제약을 설명하는 참여자. 별도
  거부권이나 비공개 의결권은 없습니다.

Maintainer와 Steward의 명단·범위는 향후 공개 파일로 확정합니다. 그 전까지
repository owner는 문서 오탈자와 링크 같은 비규범 변경만 bootstrap merge할 수
있습니다. 규범 변경은 아래 RFC 절차와 이름이 남는 review가 필요합니다.

## 변경 등급

### 1. Editorial

의미를 바꾸지 않는 오탈자, 링크, 표현 정리입니다. Maintainer 1인의 review와
merge commit이 receipt가 됩니다.

### 2. Technical

schema, conformance fixture, reference implementation, project metadata 변경입니다.
공개 proposal, 재현 시험, Maintainer 1인 이상의 승인과 반대 의견 처리가
필요합니다.

### 3. Normative RFC

Charter, Agent Rights, protocol의 MUST/SHALL, project adoption·퇴출, 상업 주체와의
경계를 바꾸는 변경입니다.

1. `RFC: <title>` 공개 제안과 정확한 diff를 게시합니다.
2. 검토 기간은 원칙적으로 최소 14일입니다.
3. 최소 2인의 공개 review가 필요하며, 그중 1인은 제안자와 달라야 합니다.
4. 해결되지 않은 기술적 반대는 삭제하지 않고 decision receipt에 기록합니다.
5. 승인된 변경은 version, effective date, supersedes 정보를 포함합니다.

Steward가 2인 미만인 bootstrap 기간에는 normative RFC를 최종 확정하지 않고
`PROVISIONAL`로만 merge합니다. 두 번째 독립 Steward가 공개 review한 뒤 효력이
확정됩니다.

### 4. Security exception

공개 전 악용 위험이 있는 취약점은 [SECURITY.md](SECURITY.md)에 따라 제한적으로
처리할 수 있습니다. 비공개 기간은 필요한 최소 범위여야 하며, 수정 후 공개
receipt와 영향을 받은 version을 남깁니다.

## Decision Receipt

유효한 결정에는 다음 필드가 있어야 합니다.

```yaml
decision_id: stable-public-id
class: editorial | technical | normative | security
proposal: public-url-or-embargo-reference
commit: immutable-sha
reviewers: [public-identities]
evidence: [tests, conformance, research, or incident references]
objections: [resolved-or-preserved-minority-views]
effective_at: ISO-8601
supersedes: [prior-decision-ids]
```

문서에 `approved`라고 쓰는 것만으로는 결정이 성립하지 않습니다. commit과 review,
evidence를 함께 찾을 수 있어야 합니다.

## Conflict of Interest

상업 계약, 고용, 투자 또는 프로젝트 소유관계가 결정에 직접 영향을 주면 review
전에 공개합니다. 이해관계자는 기술 증거를 제출할 수 있으나 자신의 project
adoption·퇴출 또는 회사 독점권에 관한 최종 독립 review를 대신할 수 없습니다.

## Project Lifecycle

1. **Candidate:** 공개 제안과 범위가 존재
2. **Incubating:** 공개 source, 명시적 license, governance·security 문서와 초기
   conformance evidence가 존재
3. **Adopted:** 독립 구현 또는 독립 검증, release receipt, 유지 책임자가 존재
4. **Archived:** 유지 중단 사유와 마지막 검증 범위를 공개하고 read-only 보존

저장소나 역사를 삭제하는 대신 상태와 후속 프로젝트를 명시합니다.

## Appeals

결정에 대한 appeal은 새로운 증거, 절차 위반 또는 공개되지 않은 이해충돌을
근거로 제출합니다. 단순 반복 표결은 하지 않습니다. appeal의 결과도 동일한
Decision Receipt 형식으로 남깁니다.

