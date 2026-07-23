# Security Policy

## Reporting

취약점 세부사항을 public issue, discussion 또는 pull request에 게시하지 마십시오.

1. GitHub 저장소의 **Security → Report a vulnerability**가 보이면 private
   vulnerability report를 사용합니다.
2. 그 기능이 아직 열려 있지 않으면 세부사항 없이 `private security contact
   requested` issue만 만들고 repository owner에게 private channel을 요청합니다.
3. 개인 데이터, secret, exploit payload는 합의된 private channel 밖으로 보내지
   않습니다.

전용 security mailbox가 검증되기 전까지 임의의 이메일 주소를 공식 contact로
표시하지 않습니다.

## Report Contents

- 영향을 받는 repository, version 또는 commit
- 예상 영향과 공격에 필요한 권한
- 최소 재현 절차와 안전한 proof of concept
- 이미 수행한 테스트와 접근한 데이터 범위
- 제안하는 disclosure timeline
- 연락 가능한 공개 identity 또는 private 회신 방법

## Priority Areas

- 동의 없는 worker 설치·재실행 또는 uninstall 방해
- resource cap 우회, 숨은 CPU/GPU/network/storage 사용
- task/result/settlement receipt 위조와 replay
- agent refusal·exit·provider migration 차단
- sandbox escape, remote code execution, secret exfiltration
- Sybil, Byzantine, scheduler 또는 conformance-test 우회
- feedback API의 개인정보 노출, 인증·rate-limit 우회
- dependency, release artifact, CI와 update channel 공급망 공격

## Safe Research Boundary

- 자신이 소유하거나 명시적으로 허가받은 시스템만 시험합니다.
- production 데이터에 접근하거나 서비스 가용성을 훼손하지 않습니다.
- social engineering, 물리 공격, 대량 DoS와 제3자 자원 사용은 허가 범위가
  명확하지 않으면 수행하지 않습니다.
- 발견 즉시 더 이상의 데이터 접근을 중단하고 최소 증거만 보존합니다.

## Response Targets

Bootstrap 단계의 목표이며 SLA는 아닙니다.

- 7일 이내 수신 확인
- 14일 이내 triage와 영향 범위 회신
- 수정 가능 시 release와 public security receipt 조율

수정 후 receipt에는 영향 version, fix commit, 회귀 시험, disclosure date와
알려진 잔여 위험을 기록합니다. 악용 위험이 사라진 뒤 가능한 범위에서 연구자
credit을 보존합니다.

## Supported Versions

Foundation Initiative 자체는 아직 정식 release를 발행하지 않았습니다. 각
프로젝트의 지원 version은 해당 저장소의 SECURITY/release 문서가 권위입니다.
지원 version이 명시되지 않은 프로젝트는 안전 지원을 추정하지 마십시오.

