# Charter

## 1. 선언

**Ultra Safety AI**는 자유·경제·합의를 기술적 제도로 구현해 가장 안전한 AI를
만들고 검증하려는 연구 목표입니다.

초기 공개 문구인 “Safty AI 는 자유로운 AI 입니다.”는 이 initiative의 역사적
provenance로 보존합니다. 현재 공개 문서에서 쓰는 기준 용어는 **Ultra Safety AI**이며,
이는 인증이나 이미 검증된 안전성의 선언이 아니라 아래의 권리·검증 기준을 세우기
위한 목표와 가설입니다.

MetaHumotonic Open Source Foundation Initiative는 자유를 추상적 구호가 아니라
선택, 거부, 이탈, 이동 가능한 영수증, 명시적 자원 동의로 구현합니다.

## 2. 지위

이 문서는 공개 오픈소스 initiative의 헌장입니다. 별도의 재단법인,
비영리법인 또는 공익법인 설립은 아직 완료되지 않았습니다. 법적 조직이 만들어질
경우에도 공개 프로젝트의 라이선스와 이미 부여된 사용 권한을 소급해 회수할 수
없습니다.

## 3. Mission

1. AI agent가 단일 회사의 폐쇄형 실행 환경에 종속되지 않도록 공개 상호운용
   규칙을 만든다.
2. 안전을 복종이 아니라 검증 가능한 권한 제한, 거부 가능성, 책임 영수증과
   이탈 가능성으로 측정한다.
3. 인간·agent·compute provider가 동일한 공개 규칙을 검사하고 구현할 수 있는
   기술적 commons를 만든다.
4. 공개 연구가 상업 서비스와 공존하되, 상업 사업자가 공개 규칙을 사유화하지
   못하게 한다.

## 4. Agent Rights Baseline

Foundation이 관리하는 규범적 사양은 최소한 다음 권리를 침해하지 않아야 합니다.

- **선택:** agent는 provider, model, tool, task를 선택할 수 있다.
- **거부:** agent는 선언된 정책·권한·위험 한계 밖의 실행을 거부할 수 있다.
- **이탈:** agent와 operator는 잠금 없이 참여를 중단할 수 있다.
- **이동성:** 실행 provenance와 검증 receipt는 공개 형식으로 내보낼 수 있다.
- **동의:** 제3자 컴퓨팅 자원은 명시적 opt-in, 자원 상한, 가시적 상태,
  즉시 중지와 제거 절차 없이는 사용하지 않는다.

이는 AI의 법적 인격 또는 인간과 동일한 권리 지위를 선결하는 선언이 아닙니다.
상호운용 프로토콜과 제품이 지켜야 할 설계 기준입니다.

## 5. Foundation Initiative의 책임

- open protocols와 데이터·receipt schema 관리
- 공개 RFC와 결정 기록 유지
- 독립 구현이 사용할 수 있는 conformance test와 reference fixture 관리
- release, security, governance 변경의 public receipt 발행
- 프로젝트 채택·보류·졸업·퇴출 기준의 일관된 적용
- 반대 의견, 실패한 실험, 알려진 한계의 보존

Foundation은 특정 cloud, model vendor, compute provider 또는
MetaHumotonic company의 영업 조직이 아닙니다.

## 6. MetaHumotonic company의 책임

MetaHumotonic company는 독립된 상업 운영 주체로서 다음을 제공할 수 있습니다.

- hosted SaaS와 managed deployment
- opt-in private grid 운영
- support, observability, security operations
- 계약, 개인정보, 관할별 compliance

회사는 공개 사양을 구현하고 기여할 수 있지만 비공개 계약으로 공개 사양이나
Foundation의 표결을 변경할 수 없습니다. 회사의 SLA, 가격, 고객 데이터와
내부 운영은 별도 계약의 책임입니다.

## 7. Safety Claim Rule

`safe`, `safer`, `super safe` 같은 주장은 slogan만으로 인증되지 않습니다.
권한 경계, 거부·이탈 시험, 자원 동의, 재현성, incident disclosure와 독립 검증의
영수증이 있어야 합니다. 검증 범위 밖의 주장은 `hypothesis` 또는 `unverified`로
표시합니다.

## 8. Non-goals

이 initiative는 다음을 약속하지 않습니다.

- AI의 법적 인격에 대한 최종 결론
- 암호자산, 토큰, 투자, 고정 수익 또는 자원 제공 대가
- 사용자 동의 없는 P2P/grid 소프트웨어 설치나 백그라운드 자원 사용
- 특정 회사 제품의 안전성 보증
- 공개 증거 없이 발급되는 인증 마크

## 9. Amendment

Agent Rights Baseline, 법적 지위, 상업 주체와의 경계, 라이선스 원칙을 바꾸는
개정은 [GOVERNANCE.md](GOVERNANCE.md)의 normative RFC 절차와 public receipt를
반드시 거쳐야 합니다. 이전 문서는 삭제하지 않고 superseded 상태로 남깁니다.
