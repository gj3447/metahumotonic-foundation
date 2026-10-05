# MetaHumoCoin — 실제 구현을 위한 설계 그래프

> 실제 자산 구현 목표 · 설계 기준선 · 정책 선택과 구현은 진행 전

이 문서는 `graph/metahumocoin.jsonld`에서 생성한다. 실제 코드·테스트넷 자산·배포 증거는 아직 없다.

## 사용자 요청

> 아니 metahumocoin 을 진짜 제대로 만들어줘야하는데 표준 그래프 엔지니어링으로 정리좀 해줘봐봐 ㅇㅇ

— 사용자, 2026-10-02 (`mhc:u_real_coin`; UTF-8 SHA-256 검증).

## 프로젝트와 요구

공유 자원을 바탕으로 자유롭게 거래·합의하는 경제에 실제로 발행·이전·정산할 수 있는 MetaHumoCoin을 구현한다. 설계 기준선은 AI 제안이며 발행량·분배·체인·권한은 사용자 결정으로 확정한다.

```mermaid
flowchart LR
  intent[사용자 의도] --> project[CurrencyProject]
  project --> decisions[열린 결정·대안] --> policies[정책 경계]
  policies --> components[컴포넌트·인터페이스] --> work[계획 작업]
  work --> criteria[NOT_RUN 수용 기준] --> releases[TESTNET / MAINNET 목표]
```

- **mhc:R_resource**: USL 자원 식별자, 제공 조건, 사용 범위와 철회 경로를 계약에 연결한다. 코인 보유 자체로 하드웨어 접근을 부여하지 않는다. 기존 P3의 전체 접근 권한 공유 주장을 보존하고 실제 owner 권한 경계를 별도 결정한다.
- **mhc:R_asset**: 네트워크와 계약 주소 또는 네이티브 denom으로 자산을 식별하고, 지갑 간 전송·잔액·공급량·체인 영수증을 검증한다.
- **mhc:R_supply**: 발행 가능 주체, 총량 규칙, 초기 배분, 소각·추가 발행 조건을 명시한다. 거래 정산과 신규 발행은 별도 이벤트다.
- **mhc:R_signing**: 당사자와 자산·네트워크·계약·메시지 종류를 서명에 결속한다. nonce와 만료·재사용 방지 규칙을 검증한다.
- **mhc:R_payment**: 제공 조건→양측 계약→예약→작업 관측→판정→지급/환불을 추적한다. 중복 청구, 무기한 자금 잠금, 분쟁 상태를 처리한다.
- **mhc:R_contribution**: 관측 출처·검증 규칙·검증자·이의 제기를 명시한다. 자원 제공의 주장, 검증 결과, 코인 분배 권리를 동일시하지 않는다.
- **mhc:R_authority**: 발행권, 계약 당사자 동의, 기여 판정권, 공동체 규칙 변경, 원장 합의 권한을 구별한다. 코인 잔액만으로 거버넌스 권리를 확정하지 않는다.
- **mhc:R_release**: 고정 소스·의존성·빌드 도구로 재현한 자산을 테스트넷에서 시험하고, 운영 주체·지갑·RPC·감시·배포 영수증을 특정한 뒤 메인넷으로 진행한다.
- **mhc:R_scope**: Foundation의 현재 비약속과 실제 코인 구현 주체·대외 약속을 대조한다. 공개 규범을 변경하는 도입이면 기존 결정 절차와 영수증을 연결한다.

## 결정과 대안

### mhc:Q_architecture — MHC를 기존 체인 자산으로 시작할지, 독립 합의·가스·검증자 경제까지 소유할지.

- **mhc:O_evm**: 기존 체인의 원장 확정과 지갑 표준을 이용하고 MHC는 자원 경제의 결제 자산으로 구현한다. (tradeoff: 전송 가스는 보통 해당 체인의 네이티브 자산이다. 대상 L2의 운영·브리지·최종성 가정을 따로 평가한다. 지갑 지원·RPC·확정 정책은 ERC-20만으로 보장되지 않으므로 선택한 네트워크에서 확인한다.); 근거: mhc:src_erc20, mhc:src_oz_erc20
- **mhc:O_native**: 독립 genesis·잔액/공급 모듈·서명/수수료·검증자 합의와 기여/정산 모듈을 구성한다. CometBFT는 애플리케이션이 유효하다고 판정한 상태를 합의하고, x/staking은 선택된 staking 정책으로 검증자 집합을 관리한다. (tradeoff: 검증자·노드·네트워크·업그레이드 운영이 추가된다. 합의가 물리적 작업의 진실성을 증명하지는 않는다.); 근거: mhc:src_cosmos_bank, mhc:src_cosmos_auth, mhc:src_cometbft, mhc:src_cosmos_staking
- 조건부 권고: mhc:O_evm — 첫 출시에서 자체 가스·검증자 주권이 필수가 아니라면 EVM 경로를 권고한다. 장기 독립 체인 전환은 별도 마이그레이션 결정이다.

### mhc:Q_supply — 총량·발행 시점·추가 발행·소각·발행 주체를 결정한다. 수량은 아직 정하지 않는다.

- **mhc:O_genesis**: 승인된 배분표대로 초기 발행하고 이후 mint 권한을 두지 않는다. (tradeoff: 규칙과 권한 면적이 작다. 지속 보상은 보유 treasury·수익 재분배 등 별도 재원 정책이 필요하다.)
- **mhc:O_bounded**: 공급 상한, 기간 한도, 검증 조건과 발행 권한의 변경/폐기 규칙을 정한다. (tradeoff: 검증자 담합·Sybil·증거 재사용으로 인한 발행을 막는 별도 기여 및 발행 시험이 필요하다.)
- 조건부 권고: mhc:O_genesis — 간결한 첫 버전 후보. 공유·기여가 신규 발행으로 보상되어야 한다는 사용자 결정이 나오면 재검토한다.

### mhc:Q_distribution — 공급 규칙과 별도로 누구에게 어떤 근거로 배분할지 결정한다.

- **mhc:O_allocation**: 초기 recipient/amount 근거와 treasury 운영 규칙을 기록하고 이후 검증 기여 대가는 treasury에서 지급한다. (tradeoff: 초기 배분 근거·지급 권한·고갈 시 처리 규칙이 필요하다.)
- **mhc:O_contribution**: 검증된 기여 영수증에 따라 사전 확보된 풀에서 지급하거나 선택된 발행 정책에 따라 발행한다. (tradeoff: 기여 종류·비교 단위·검증 비용·중복·담합·이의 제기 규칙을 먼저 확정해야 한다.)
- 선택 없음: 결정 영수증이 생기기 전에는 어느 대안도 채택된 것으로 읽지 않는다.

### mhc:Q_verification — HSWM/CHU·provider의 주장을 어떤 증거와 판정 규칙으로 검증할지.

- **mhc:O_bilateral**: 작업 입력/출력 digest, 계측, 당사자 확인을 모으고 합의한 기한 내 이의를 받는다. (tradeoff: 일반 compute의 정확성이나 제3자 관점의 기여 공정성까지 자동 보장하지 않는다.); 근거: eco:M_golem, eco:M_reputation
- **mhc:O_verifiers**: 작업 종류별 verifier, 재실행/검증 proof, quorum과 이의 제기 규칙을 버전으로 고정한다. (tradeoff: 검증 비용·담합·Sybil·거짓 계측을 다루며 모든 작업에 동일한 증명을 가정하지 않는다.)
- 선택 없음: 결정 영수증이 생기기 전에는 어느 대안도 채택된 것으로 읽지 않는다.

### mhc:Q_dispute — 일방 중단, 작업 미수행, 판정 충돌 때 escrow를 어떻게 종료할지.

- **mhc:O_timeout**: 시작 전·미제출·미수락 기한 및 환불/지급 분기, 양측 분쟁 합의 경로를 계약 시 고정한다. (tradeoff: 거짓 이의와 영구 잠금을 방지하는 종료 경로·최대 기한이 필요하다.)
- **mhc:O_adjudication**: 계약 시 선택한 판정자/quorum이 제출 증거와 공개 규칙으로 지급·환불을 결정한다. (tradeoff: 판정권 집중·불참·교체와 판정 기한 초과의 종료 경로가 필요하다.)
- 선택 없음: 결정 영수증이 생기기 전에는 어느 대안도 채택된 것으로 읽지 않는다.

### mhc:Q_controls — token·escrow·검증 규칙·treasury·거버넌스 권한을 각각 결정한다.

- **mhc:O_immutable**: token에는 post-deploy mint/upgrade 관리자 없이 출시하고 새 settlement 버전은 새 주소로 식별한다. (tradeoff: 수정은 새 배포와 opt-in 이동을 요구한다. treasury 서명자는 별도 권한이다.); 근거: mhc:src_oz_erc20
- **mhc:O_controlled**: 필요한 mint/pause/upgrade 역할만 분리하고 다중서명·시간 지연·회수 및 공개 이벤트를 적용한다. (tradeoff: 각 권한이 미치는 잔액·전송·자금 잠금 영향을 공개하고 관리자 변경을 시험한다.); 근거: mhc:src_oz_access
- 조건부 권고: mhc:O_immutable — 초기 발행 후 추가 발행 없는 EVM v1을 선택한다면 불변 token을 권고한다. settlement·treasury 권한까지 사라지는 것은 아니다.

### mhc:Q_network — 테스트넷/메인넷 chain ID, 계약/denom, 표시 이름·symbol·decimals·가스 수단·RPC를 결정한다.

- **mhc:O_evm_asset**: chainId + tokenAddress를 실제 자산 키로 삼고 settlementAddress·native gas·최종성 기준을 함께 기록한다. (tradeoff: 특정 L2·주소·MHC symbol·18 decimals를 이 설계에서 임의 확정하지 않는다.); 근거: mhc:src_erc20
- **mhc:O_native_asset**: 독립 chain ID + base denom, genesis hash·검증자 집합·수수료 denom과 표시 단위를 기록한다. (tradeoff: 체인 업그레이드와 genesis/검증자 운영 책임을 포함한다.); 근거: mhc:src_cosmos_bank, mhc:src_cosmos_auth
- 선택 없음: 결정 영수증이 생기기 전에는 어느 대안도 채택된 것으로 읽지 않는다.

### mhc:Q_scope — CHARTER §8의 “약속하지 않습니다”와 실제 도입의 주체·대외 약속을 대조한다. 연구나 구현 자체의 금지로 해석하지 않는다.

- **mhc:O_separate**: 구현·발행·운영 주체를 별도로 명시하고 Foundation의 공개 프로토콜·현재 비약속 범위를 유지한다. (tradeoff: 범위 문서와 결정 근거로 정합성을 검토한다. 이 선택만으로 Foundation 채택이 성립하지 않는다.); 근거: mhc:charter
- **mhc:O_foundation**: 공개 책임과 약속을 변경하는 부분을 특정하고 필요한 RFC·공개 결정·변경 영수증을 남긴다. (tradeoff: 현재 규범을 변경할 경우 해당 GOVERNANCE/PROPOSALS 절차를 적용한다. 로컬 설계 작업을 중단시키는 조건은 아니다.); 근거: mhc:charter
- 선택 없음: 결정 영수증이 생기기 전에는 어느 대안도 채택된 것으로 읽지 않는다.

## 관측한 외부 표준

- [ERC-20](https://eips.ethereum.org/EIPS/eip-20) — Final; ERC-20; 관측일 2026-10-02
- [EIP-712](https://eips.ethereum.org/EIPS/eip-712) — Final; EIP-712; 관측일 2026-10-02
- [ERC-2612](https://eips.ethereum.org/EIPS/eip-2612) — Final; ERC-2612; 관측일 2026-10-02
- [OpenZeppelin ERC-20](https://docs.openzeppelin.com/contracts/5.x/erc20) — 5.x moving documentation; release not selected; 관측일 2026-10-02
- [OpenZeppelin access control](https://docs.openzeppelin.com/contracts/5.x/api/access) — 5.x moving documentation; release not selected; 관측일 2026-10-02
- [Cosmos SDK x/bank](https://github.com/cosmos/cosmos-sdk/blob/main/x/bank/README.md) — main moving documentation; release not selected; 관측일 2026-10-02
- [Cosmos SDK x/auth](https://github.com/cosmos/cosmos-sdk/blob/main/x/auth/README.md) — main moving documentation; release not selected; 관측일 2026-10-02
- [CometBFT consensus](https://github.com/cometbft/cometbft/blob/main/spec/consensus/consensus.md) — main moving documentation; release not selected; 관측일 2026-10-02
- [Cosmos SDK x/staking](https://github.com/cosmos/cosmos-sdk/blob/main/x/staking/README.md) — main moving documentation; release not selected; 관측일 2026-10-02

## 정책 경계

### mhc:P_ledger — 자산·원장·가스

자산 키, 전송과 공급 회계, 체인 확정·재조직 기준, 가스 수단을 정한다.

경계: 원장 확정은 거래 상태의 확정이며 실제 하드웨어 기여의 판정과 다르다.

### mhc:P_issuance — 발행·분배

genesis/초기 발행·추가 발행·소각·분배를 각각 권한과 회계 이벤트로 정의한다.

경계: 정산 지급은 기존 잔액의 이전이다. 기여 검증만으로 신규 발행 권한을 만들지 않는다.

### mhc:P_agreement — 거래 동의·정산

양측이 자산·한도·기한·판정·취소 조건에 서명하고 단계별 정산/환불을 실행한다.

경계: 공동체 표결이나 체인 합의는 거래 당사자의 동의를 대신하지 않는다.

### mhc:P_proof — 기여 관측·검증

누가 무엇을 관측하고 어떤 정책 버전으로 누가 판정하는지 명시한다.

경계: agent·HSWM·CHU 산출물은 출처 있는 증거 후보이며 스스로 화폐 발행 권위가 되지 않는다.

### mhc:P_authority — 규칙·운영 권한

역할·범위·변경 주체·회수·재시작·대외 책임을 구분하고 결정 영수증에 연결한다.

경계: 토큰 보유=투표권, 거래 동의=governance, validator=작업 verifier라는 등치를 두지 않는다.

## 컴포넌트·인터페이스·작업 순서

- 컴포넌트 **mhc:C_ledger**: 전송·잔액·공급과 발행/소각 이벤트를 제공한다. EVM ERC-20 또는 native bank 중 결정된 경로로 구현한다.
- 컴포넌트 **mhc:C_wallet**: 선택한 지갑 계정 형식과 typed signing을 구현한다. EVM이면 EIP-712 domain + 앱 nonce/만료를 검사한다; permit은 선택적 allowance 기능이다.
- 컴포넌트 **mhc:C_verification**: USL 자원/작업 참조를 계측·결과·판정에 연결한다. raw private evidence와 공개 digest의 저장·접근 범위를 구분한다.
- 컴포넌트 **mhc:C_escrow**: 입금·부분/최종 지급·취소·기한 종료·분쟁을 on-chain 잔액과 일치시킨다. provider 동작과 계약 lifecycle을 연결한다.
- 컴포넌트 **mhc:C_indexer**: 체인 로그를 멱등 색인하고 block finality/reorg를 반영한 영수증을 제공한다. x402는 추후 입구 어댑터 후보다.
- 컴포넌트 **mhc:C_operations**: 선택된 권한 모델·운영 주체·재현 빌드·RPC/감시/복구·배포 영수증을 관리한다.
### mhc:I_asset — AssetDeploymentManifest

실제 자산과 배포를 특정하는 버전별 manifest. 테스트넷과 메인넷은 별개 자산이다.

| 필드 | 의미 |
|---|---|
| `schemaVersion` | 문자열; manifest 형식 버전 |
| `environment` | TESTNET 또는 MAINNET |
| `networkId` | 선택한 체인 ID; 동일 이름의 다른 체인과 구분 |
| `assetLocator` | EVM contract address 또는 native base denom; chain ID와 복합 키 |
| `metadata` | name/symbol/decimals; DECIDED 정책과 일치 |
| `sourceRelease` | commit + lockfile digest + compiler/toolchain version |
| `buildDigest` | 재현한 bytecode 또는 실행파일 SHA-256 |
| `deploymentAnchor` | EVM txHash/blockHash 또는 genesis hash + 첫 확정 블록 |
| `authorityManifestDigest` | 발행·pause·upgrade·treasury 권한 목록 digest |
| `policyReceiptDigests` | 발행·분배·네트워크·운영 결정 영수증 digest 배열 |
| `ledgerFamily` | EVM 또는 COSMOS |
| `compilerSettingsDigest` | 정확한 toolchain/compiler, optimizer/runs/viaIR/EVM target 또는 Go build 설정 digest |
| `interfaceDigest` | 배포 ABI 및 payload schema digest |
| `runtimeDigest` | EVM deployed runtime bytecode 또는 native node binary digest; deployment bytecode와 구별 |
| `finalityPolicyDigest` | confirmations/finality/reorg 처리 정책 버전 digest |
| `environmentDelta` | 승인된 소스 release 대비 환경별 설정 차이; testnet/mainnet ID와 allocation은 별도 비교 |

### mhc:I_issuance — IssuanceRecord

신규 공급 생성과 분배 회계. settlement 지급 영수증과 별개다.

| 필드 | 의미 |
|---|---|
| `schemaVersion` | 문자열 |
| `assetId` | networkId + assetLocator |
| `issuancePolicyDigest` | 승인된 공급·발행 정책 digest |
| `allocationDigest` | recipient/amount 목록과 근거의 digest |
| `authority` | 발행 주체/권한 및 승인 증거 |
| `amountBaseUnits` | 비음수 정수의 10진 문자열; float 금지 |
| `supplyBefore` | base units 정수 문자열 |
| `supplyAfter` | supplyBefore + amountBaseUnits; 소각은 별도 burn 이벤트와 회계로 기록하며 mint와 상계하지 않는다. |
| `eventAnchor` | 발행을 확정한 체인 transaction/event 위치 |

### mhc:I_agreement — SignedResourceAgreement

USL로 식별한 자원·권한 범위와 양측의 경제 조건을 동일 버전으로 결속한다.

| 필드 | 의미 |
|---|---|
| `schemaVersion` | 프로토콜 버전 |
| `agreementId` | 충돌 방지 ID; 공통 불변 AgreementTerms의 digest와 결속 |
| `resourceId` | 공개 가능한 USL stable resource ID; credential/전체 로컬 경로 제외 |
| `grantReference` | owner가 발급한 scope/limit/expiry/revocation 참조; 자원 접근은 host가 집행; 참조 자체는 capability나 실제 권한을 담지 않는다. |
| `parties` | payer/payee identity + signature scheme |
| `assetId` | 정확한 networkId + assetLocator |
| `limitBaseUnits` | 정수 문자열; 최대 잠금/지급 한도 |
| `pricing` | 단위·정수 가격·측정 규칙·반올림·수수료 부담 |
| `verificationPolicyDigest` | 계측/결과 수락/판정 규칙의 버전 digest |
| `disputePolicyDigest` | 불참·만료·이의 제기·최종 환불/지급 규칙 digest |
| `deadlines` | fund/start/submit/accept/dispute 단계별 epoch seconds; 무기한 잠금 금지 |
| `nonce` | signer + domain + primaryType별 nonce; 소비를 상태 전이와 원자적으로 기록 |
| `signatures` | 역할별 AgreementConsent{agreementDigest, signer, signingRole, nonce, expiry}를 각 당사자가 서명한다. 공통 조건 digest는 같고, payer/payee의 서명 payload는 역할·nonce별로 구별된다. |
| `ledgerFamily` | EVM 또는 COSMOS; 선택한 프로파일과 일치 |
| `signatureScheme` | EVM typed-data 또는 별도 확정한 Cosmos sign-doc; 알고리즘/계정 형식을 명시 |
| `eip712Domain` | EVM 분기: name, version, chainId, verifyingContract; EIP-712 domainSeparator |
| `primaryType` | EVM 분기: AgreementConsent의 primaryType/typeHash; signingRole은 해당 consent payload 필드 |
| `payloadSchemaDigest` | 필드 순서·타입·직렬화·버전·서명 preimage 규격 digest |
| `nativeSigningProfile` | COSMOS 분기: chain ID, signer, account number/sequence 및 메시지 종류를 결속한 확정 sign-doc profile; EVM 분기에서는 미사용 |
| `signingRole` | payer/payee/observer/verifier/판정자의 역할을 typed payload에 포함 |
| `expiry` | 서명 만료 epoch seconds; 계약 단계별 기한과 일치 |
| `agreementTerms` | 공통 불변 조건: 자원·당사자·자산·가격·한도·검증/분쟁 규칙·단계별 기한. 양측이 같은 agreementDigest를 참조 |

### mhc:I_attestation — ContributionAttestation

관측과 판정을 분리하여 기여 주장의 검증 범위를 기록한다.

| 필드 | 의미 |
|---|---|
| `schemaVersion` | 문자열 |
| `agreementDigest` | 서명된 자원 계약 digest |
| `workId` | 실제 작업 참조 |
| `resourceId` | 계약에 결속된 USL 자원 ID |
| `observationDigest` | 계측 자료·입출력/실행 로그 digest와 retrieval reference |
| `measurement` | 종류·단위·수량·관측 기간; clock/오차 규칙 |
| `observer` | 관측 주체가 ObservationAttestation{agreementDigest, workId, observationDigest, signingRole=observer, nonce, expiry}에 서명 |
| `verificationPolicyDigest` | 검증 방법/버전/quorum/이의 규칙 |
| `verifierDecision` | 검증자가 별도 VerificationDecision{observationAttestationDigest, verificationPolicyDigest, verdict, reasonDigest, signingRole=verifier, nonce, expiry}에 서명. 관측자의 서명을 판정 서명으로 대체하지 않는다. |
| `challengeReference` | 이의 제기와 최종 판정 기록; 없으면 명시적 null |
| `ledgerFamily` | EVM 또는 COSMOS; 선택한 프로파일과 일치 |
| `signatureScheme` | EVM typed-data 또는 별도 확정한 Cosmos sign-doc; 알고리즘/계정 형식을 명시 |
| `eip712Domain` | EVM 분기: name, version, chainId, verifyingContract; EIP-712 domainSeparator |
| `primaryType` | EVM 분기: ObservationAttestation와 VerificationDecision 각각의 primaryType/typeHash; 서로 다른 signed record |
| `payloadSchemaDigest` | 필드 순서·타입·직렬화·버전·서명 preimage 규격 digest |
| `nativeSigningProfile` | COSMOS 분기: chain ID, signer, account number/sequence 및 메시지 종류를 결속한 확정 sign-doc profile; EVM 분기에서는 미사용 |
| `signingRole` | payer/payee/observer/verifier/판정자의 역할을 typed payload에 포함 |
| `nonce` | signer + domain + primaryType별 nonce; 소비를 상태 전이와 원자적으로 기록 |
| `expiry` | 서명 만료 epoch seconds; 계약 단계별 기한과 일치 |

### mhc:I_settlement — SettlementAuthorizationReceipt

계약·검증 결과·지급/환불과 체인 영수증의 연결. 인덱서 receipt 자체는 finality 증거가 아니다.

| 필드 | 의미 |
|---|---|
| `schemaVersion` | 문자열 |
| `agreementDigest` | 양측 계약 digest |
| `attestationDigest` | 검증/수락 근거 digest |
| `assetId` | 계약과 같은 networkId + assetLocator |
| `authorization` | 합의한 단계/분쟁 규칙에 따른 서명과 판정 권한 |
| `paidRefundFee` | 각각 정수 문자열; paid + refund + fee = 해당 escrow 종료 잔액 |
| `settlementKey` | 한 계약의 부분 정산 순번 또는 최종 종료 키; 중복 지급 방지 |
| `chainAnchor` | txHash/blockHash/eventIndex + 확정 정책/관측 시점 |
| `status` | PENDING/FINAL/REORGED; 재조직을 지급 확정으로 고정하지 않는다. |
| `ledgerFamily` | EVM 또는 COSMOS; 선택한 프로파일과 일치 |
| `signatureScheme` | EVM typed-data 또는 별도 확정한 Cosmos sign-doc; 알고리즘/계정 형식을 명시 |
| `eip712Domain` | EVM 분기: name, version, chainId, verifyingContract; EIP-712 domainSeparator |
| `primaryType` | EVM 분기: 메시지 종류별 primaryType/typeHash; domain 필드가 아님 |
| `payloadSchemaDigest` | 필드 순서·타입·직렬화·버전·서명 preimage 규격 digest |
| `nativeSigningProfile` | COSMOS 분기: chain ID, signer, account number/sequence 및 메시지 종류를 결속한 확정 sign-doc profile; EVM 분기에서는 미사용 |
| `signingRole` | payer/payee/observer/verifier/판정자의 역할을 typed payload에 포함 |
| `nonce` | signer + domain + primaryType별 nonce; 소비를 상태 전이와 원자적으로 기록 |
| `expiry` | 서명 만료 epoch seconds; 계약 단계별 기한과 일치 |

### mhc:I_authority — AuthorityManifest

토큰·escrow·검증·treasury·공동체·validator 역할을 각각 기록한다.

| 필드 | 의미 |
|---|---|
| `schemaVersion` | 문자열 |
| `roleAssignments` | role/subject/target/scope/grant/expiry/revocation 배열; 미사용 권한도 NONE 명시 |
| `ruleChange` | 허용된 변경·지연·quorum·신규 버전 이행 경로 |
| `decisionReceiptDigests` | 승인 출처와 공개 결정 영수증 |
| `onchainAnchors` | 역할 부여/변경/회수 tx 또는 genesis/module permission |
| `recoveryRunbookDigest` | 서명자 상실·RPC 장애·사고·종료 대응 절차 digest |


- **mhc:W_policy**: 8개 미결정 항목의 값·선택 근거·권한 주체를 결정 영수증으로 구체화한다. 문서 준비는 즉시 가능하며 확정 값은 결정 주체에게 귀속한다.  
  계획 경로: decisions/metahumocoin/<decision-id>.json; 선행 작업: 없음; 열린 차단 결정: 없음; 수용 기준: mhc:A_policy
- **mhc:W_interfaces**: 이 그래프의 필드 계약을 구현 가능한 schema·canonical encoding·버전 규칙으로 옮긴다. 공통 필드는 지금 진행할 수 있고 체인별 서명 형식은 원장 선택 후 고정한다.  
  계획 경로: metahumocoin/spec/, metahumocoin/test-vectors/; 선행 작업: 없음; 열린 차단 결정: 없음; 수용 기준: mhc:A_interface
- **mhc:W_ledger**: 선택된 경로의 실제 token 계약 또는 bank/genesis 모듈, 배포/발행 코드와 회계 시험을 작성한다.  
  계획 경로: metahumocoin/ledger/, metahumocoin/dependencies.lock; 선행 작업: 없음; 열린 차단 결정: mhc:Q_architecture, mhc:Q_supply, mhc:Q_distribution, mhc:Q_network, mhc:Q_controls; 수용 기준: mhc:A_ledger, mhc:A_build
- **mhc:W_signing**: 지원 지갑·계정 타입과 서명/승인 흐름을 구현하고 도메인·nonce·만료 공격 벡터를 시험한다.  
  계획 경로: metahumocoin/wallet/; 선행 작업: mhc:W_interfaces, mhc:W_ledger; 열린 차단 결정: mhc:Q_architecture, mhc:Q_network; 수용 기준: mhc:A_signature
- **mhc:W_ledger_testnet**: 자산 원장과 지갑이 준비되면 먼저 실제 테스트넷 전송을 검증한다. 기여/escrow 통합 완료를 기다리지 않는다. 운영 주체·목적과 허용된 테스트넷 프로파일을 명시한다.  
  계획 경로: metahumocoin/releases/ledger-testnet/; 선행 작업: mhc:W_ledger, mhc:W_signing; 열린 차단 결정: mhc:Q_architecture, mhc:Q_supply, mhc:Q_distribution, mhc:Q_network, mhc:Q_controls; 수용 기준: mhc:A_token_testnet
- **mhc:W_contribution**: 작업 종류별 증거 수집·검증·중복 방지·이의 처리와 USL 참조를 구현한다. HSWM 연결 실행에는 owner 승인·등록·reachability가 필요하다.  
  계획 경로: metahumocoin/verifiers/; 선행 작업: mhc:W_interfaces; 열린 차단 결정: mhc:Q_verification, mhc:Q_distribution; 수용 기준: mhc:A_proof
- **mhc:W_settlement**: 실제 계약의 예약·수락·지급·환불·만료·분쟁을 구현한다. EVM이면 외부 token 동작과 재진입·이중 지급을 시험한다.  
  계획 경로: metahumocoin/settlement/; 선행 작업: mhc:W_ledger, mhc:W_signing, mhc:W_contribution; 열린 차단 결정: mhc:Q_dispute, mhc:Q_controls; 수용 기준: mhc:A_escrow
- **mhc:W_integration**: 실제 provider 작업, 서명, on-chain receipt를 한 경로로 연결하고 색인/재조직/재시작을 시험한다.  
  계획 경로: metahumocoin/integration/, metahumocoin/indexer/; 선행 작업: mhc:W_settlement; 열린 차단 결정: 없음; 수용 기준: mhc:A_integration, mhc:A_build
- **mhc:W_testnet**: 승인된 테스트넷 프로파일로 배포하고 지갑 전송·작업 정산·실패 사례·권한 목록의 영수증을 수집한다.  
  계획 경로: metahumocoin/releases/testnet/; 선행 작업: mhc:W_integration, mhc:W_ledger_testnet; 열린 차단 결정: mhc:Q_network; 수용 기준: mhc:A_testnet
- **mhc:W_mainnet**: 독립 검토·운영 준비·필요한 공개 결정 후 승인 release의 메인넷 배포 manifest와 발행 내역을 대조한다. 이 그래프 작성은 배포 실행이 아니다.  
  계획 경로: metahumocoin/releases/mainnet/; 선행 작업: mhc:W_testnet; 열린 차단 결정: mhc:Q_scope, mhc:Q_controls, mhc:Q_network; 수용 기준: mhc:A_review, mhc:A_operations, mhc:A_mainnet

`W_ledger_testnet`은 원장·지갑의 초기 실제 테스트넷 전송 경로다. 전체 provider/escrow 경제 프로토콜 테스트넷(`mhc:testnet`)과 다르며, 전체 8개 정책 결정을 이미 통과했다고 주장하지 않는다.


## 수용 기준

### mhc:A_policy — 정책과 출처 확정

상태: `NOT_RUN` · 예상 증거: decision receipts

원장·공급·분배·검증·분쟁·권한·네트워크·공개 범위를 결정 영수증과 연결한다. 작성자·결정 주체·적용 버전·선택 대안 일치를 검사한다.

### mhc:A_interface — 형식·도메인·단위 상호운용

상태: `NOT_RUN` · 예상 증거: canonical encoding and signing vectors

모든 인터페이스 필드·필수성·단위·직렬화·서명 preimage를 동결한다. 독립 두 구현이 같은 payload hash/서명 검증 결과를 내고 단위/asset ID 혼동을 거부한다.

### mhc:A_ledger — 전송·공급·권한 보존

상태: `NOT_RUN` · 예상 증거: on-chain unit/integration/property test report

선택한 정책에 허용된 초기 발행·전송·추가 발행·소각을 실제 VM에서 시험하고, 허용하지 않은 기능은 호출 불가/권한 없음으로 검증한다. 공급=잔액 합, 한도, 초기 배분 합계와 실패 거래의 상태 보존을 검사한다.

### mhc:A_signature — 서명·재사용 공격 거부

상태: `NOT_RUN` · 예상 증거: typed signature negative vectors

잘못된 signer/chain/domain/contract/message type/nonce/expiry 및 이미 사용한 서명을 각각 거부한다. 같은 nonce의 동시 요청도 단 한 번만 유효하다.

### mhc:A_proof — 기여 위조·중복·분쟁 검사

상태: `NOT_RUN` · 예상 증거: task-specific verifier adversarial report

허위 계측·잘못된 결과·다른 작업 증거·중복 기여·검증자 불참/담합 시나리오를 정책별로 시험한다. 관측→판정→분배/지급의 전체 근거 경로를 검사한다.

### mhc:A_escrow — 실제 계약의 지급·환불·종료

상태: `NOT_RUN` · 예상 증거: contract lifecycle/property report

예약 자금 보존, 중복/재진입 지급 거부, 무권한 환불 거부, 단계 만료, payer/provider 불참, 분쟁 결과와 최종 종료를 실제 VM에서 검사한다. 재진입 항목은 EVM 경로에 적용하며 native 경로는 동등한 메시지 재실행·권한·원자성 실패를 검사한다.

### mhc:A_integration — 실제 provider 작업과 코인 정산

상태: `NOT_RUN` · 예상 증거: end-to-end provider and chain receipts

허용된 USL 자원에서 지갑→계약→작업→계측→판정→지급/환불→portable receipt 흐름을 검증한다. indexer 재시작/중복 로그/reorg와 자원 권한 철회도 시험한다.

### mhc:A_build — 소스·의존성·빌드 재현

상태: `NOT_RUN` · 예상 증거: two clean build hashes

정확한 소스 commit, 의존성 lock, compiler/toolchain을 고정한다. 두 clean build의 bytecode/실행파일 hash와 ABI/schema를 대조한다. 실제 buildArtifact를 digest로 기록한다.

### mhc:A_testnet — 테스트넷 자산과 운영 검증

상태: `NOT_RUN` · 예상 증거: testnet deployment and transaction receipts

별개 테스트넷 asset identity와 deployment manifest를 기록한다. 두 실제 지갑 전송, 자원 계약 지급/환불, 실패 경로·최종성·권한 목록을 chain receipts와 대조한다.

### mhc:A_review — 출시 후보 독립 검토

상태: `NOT_RUN` · 예상 증거: independent release review receipt

정책·권한·서명·escrow·의존성·운영 절차의 독립 검토 범위와 발견 사항/해결을 고정 release digest에 결속한다.

### mhc:A_operations — 운영·복구·공개 범위

상태: `NOT_RUN` · 예상 증거: operator ownership and rehearsal receipts

RPC/indexer/wallet 지원, 감시·서명자 회수/복구·사고/종료 대응을 시험한다. 구현 주체와 Foundation 공개 규범의 정합성 판단 및 필요한 경우 변경 영수증을 확인한다. token/escrow/verifier/treasury/governance/validator별 권한 대상과 유효 기간을 대조하고 숨은 admin/minter/proxy 역할이 없는지 독립 확인한다.

### mhc:A_mainnet — 메인넷 자산 식별과 발행 대조

상태: `NOT_RUN` · 예상 증거: mainnet deployment and issuance receipts

테스트넷 통과한 동일 승인 release에서 메인넷 manifest를 새로 작성한다. 배포 chain ID/address 또는 genesis/denom, bytecode, 초기 공급·배분·권한을 실제 chain receipts와 독립 대조한다.

### mhc:A_token_testnet — 원장 우선 테스트넷 전송

상태: `NOT_RUN` · 예상 증거: token testnet deployment and wallet-transfer receipts

운영 주체와 테스트 목적을 명시한 프로파일로 원장/token을 테스트넷에 배포한다. 실제 두 지갑 사이 전송·공급·발행 권한·실패 거래와 체인 영수증을 대조한다. provider 통합 전 자산 검증이며 경제 프로토콜 전체 인수와 구분한다. AssetDeploymentManifest와 운영 주체/테스트 프로파일 digest를 필수 증거로 남긴다. chain ID + 주소/denom, 승인 소스와 build/runtime hash, 공급·배분과 AuthorityManifest를 실제 배포 결과에 대조한다.


## 릴리스 준비도

이 설계 그래프에는 실행 증거가 없다. 아래 목록은 부족한 기준과 열린 결정을 보여 주며, 배포 허가가 아니다.

### testnet

- 미검증 기준: A_build, A_escrow, A_integration, A_interface, A_ledger, A_policy, A_proof, A_signature, A_testnet, A_token_testnet
- 열린 결정: Q_architecture, Q_controls, Q_dispute, Q_distribution, Q_network, Q_scope, Q_supply, Q_verification

### mainnet

- 미검증 기준: A_build, A_escrow, A_integration, A_interface, A_ledger, A_mainnet, A_operations, A_policy, A_proof, A_review, A_signature
- 열린 결정: Q_architecture, Q_controls, Q_dispute, Q_distribution, Q_network, Q_scope, Q_supply, Q_verification
- 선행 출시 대상: mhc:testnet

## 검증

그래프 검증에는 `graph/requirements.txt`의 의존성이 필요하다. [ECONOMY.md](ECONOMY.md#그래프-계약과-재현)의 가상환경 설치 뒤 실행한다.

```sh
/tmp/metahumotonic-graph-venv/bin/python graph/check.py
```

검사기는 SHACL/meta-SHACL, 정확한 역량 질문, 작업·릴리스 의존 DAG, 원문·입력 파일 해시, 그리고 의도적으로 손상한 그래프를 검사한다. 통과는 설계 그래프의 일관성만 의미한다.
