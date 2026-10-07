# 공개 저장소 라이선스 적용 — 2026-10-07

**gj3447 공개 저장소 63개를 확인했다. 61개에 변경을 커밋하고, 이미 MHL인 2개는 그대로 검증했다.**
59개는 권리자가 허락할 수 있는 원저작물의 루트 기본 조건을 MHL 1.2로 갱신했다.
2개는 기존 AGPL 결합물 조건을 유지하면서 독립적으로 허락할 수 있는 새 저작물에만
MHL을 적용하는 범위를 명시했다. 마지막 목록 확인에서 발견한 `bhgman`과 `spacegirl`은
이미 정본과 같은 MHL 1.1을 사용하고 있어 기존 공개·출처 고정을 유지했다.
모든 기존 코드가 MHL 전용으로 전환됐다는 뜻은 아니다.

## 요청과 해석

[사용자 원문](user-verbatim.txt)은 “우리 모든 publci 을 메타휴모토닉 라이센스로 변경해줘 ㅇ”다.
사용자 원문은 일차 출처이며, gj3447 계정의 과거 개인·실습 프로젝트까지 포함한다는
범위 해석과 라이선스 문안은 OpenAI Codex의 이차 해석·작성이다.
비공개 저장소와 dashboard의 공개 범위는 변경하지 않았다.

## 적용 조건

- 1.2는 [재단 LICENSE](../../../LICENSE)의 공통판이다. 1.1의 **CHU의 일부가 된다**는 참여 원칙과
  대상·목적·수신자·상한·만료·철회·별도 접근 승인 조건을 유지했다.
- 제1.3·1.4·6.1조의 재단 전용 과거 파일 경로를 저장소별 LICENSE-NOTICE로 일반화했다.
  재단의 이전 1.0·1.1·MIT와 각 저장소의 이전 허가문은 보존했다.
- 이미 MIT·Apache·AGPL·CC 등의 조건으로 허락된 부분은 그 조건을 선택해 사용할 수 있다.
  이번 변경만으로 과거 허락을 회수하거나 기존 사용자에게 공유 의무를 소급 부과하지 않는다.
- 제3자 코드·모델·데이터·인용·별도 고지의 조건과 저작자 표시를 유지했다.
  공개 관리자 권한을 타인의 저작권 소유나 재허락 동의로 간주하지 않는다.
- `333`과 `metahumotonic_web_back`의 기존 루트 LICENSE는 그대로다. 추가한
  METAHUMOTONIC-LICENSE는 기존 AGPL 결합물을 전환하지 않는다.
- MHL은 소스 공개형이며 OSI 승인 오픈소스 라이선스가 아니다. 별도 재단 채택 절차,
  법인 설립, 법률 검토 또는 완전한 저작권 감사를 완료했다는 뜻은 아니다.
- 실제 하드웨어 연결·접근권한 부여·자원 공유·토큰 이전은 수행하지 않았다.

## 변경과 검증

재단 이외 60개 저장소의 공개 기본 브랜치를 특정 커밋으로 고정해 검토하고,
라이선스·적용 고지·README·관련 패키지 메타데이터 등 389개 파일을 변경했다.
기존 커밋을 부모로 삼아 force 없이 반영했으며, 원격 Git 객체의 해시로 변경 파일과
변경하지 않은 루트 파일·하위 트리가 보존됐는지 대조했다.
`bhgman_essence`는 변경 후 기존 archived 상태로 복구했다.
`github-slideshow`는 기존 브랜치 보호를 유지하고 [PR #13](https://github.com/gj3447/github-slideshow/pull/13)을 통해 병합했다.

| 검증 | 결과와 한계 |
|---|---|
| 60개 공통 정적 점검 | 라이선스 전문 일치, 이전 허가문 바이트·SHA-256 일치, 변경 경로 범위, JSON/TOML 의미 차이, diff 공백 검사 통과 |
| 원격 공개 상태·커밋·파일 대조 | 61개 채택 커밋 및 기존 MHL 1.1 저장소 2개 검증. 변경하지 않은 다른 로컬 checkout의 동기화는 수행하지 않음 |
| 재단 `python graph/check.py` | 11개 도메인의 그래프·출처·SHACL·CQ·negative check·뷰 검증 통과. AI 안전성 실증을 뜻하지 않음 |
| `ooptdd`: `python scripts/dev.py check`, `verify` | check 5단계와 verify 10단계 통과. 단일 실행/xdist 각각 783 passed, 2 skipped; adoption examples 9 passed |
| `ooptdd` wheel/sdist | 빌드 및 LICENSE-NOTICE·이전 허가문 포함 확인 통과 |
| `ooptdd-loop`: `scripts/verify_ooptdd.sh` | **실패**: 변경하지 않은 `tests/test_omd_bridge.py:7,8`의 E402 2건. ruff 0.4.10. 원본 Git blob과 현재 파일의 동일성 확인. 검증 기준이나 테스트를 완화하지 않음 |
| `ooptdd-loop` 관련 테스트 | `tests/test_pytest_plugin.py`, `tests/test_otel.py`: 6 passed |

변경한 Python 배포 설정은 라이선스 고지와 이전 허가문을 배포물에 포함하도록 PEP 639
설정과 필요한 빌드 도구 하한을 맞췄다. 전체 저장소의 런타임 테스트,
전체 CI, 모든 패키지의 빌드 또는 패키지 레지스트리 출시는 수행하지 않았다.

## 저장소별 공개 커밋

아래 커밋은 **라이선스 채택 커밋 또는 기존 적용을 관측한 커밋**이다. 재단에서 이 결과표를 저장한 후속 커밋과 구분한다.
정확한 경로·SHA-256·기준 커밋·검증 상태는 [manifest.json](manifest.json)에 있다.
공개 기본 브랜치 63개와 보관 상태의 마지막 대조는
[원격 재확인 기록](remote-verification.json)에 있다.

| 저장소 | 적용 범위 | 채택 커밋 |
|---|---|---|
| [333](https://github.com/gj3447/333) | 기존 AGPL 유지 · 독립 새 저작물만 MHL | [94907742fa0e](https://github.com/gj3447/333/commit/94907742fa0eb07ae0c275206363d97ed7b7dd8e) |
| [agent-coding-paradigm](https://github.com/gj3447/agent-coding-paradigm) | MHL 기본 · 기존 허락 보존 | [6fc9c58cd67d](https://github.com/gj3447/agent-coding-paradigm/commit/6fc9c58cd67d41d14001ef278ea08b77500b891e) |
| [ant_den](https://github.com/gj3447/ant_den) | MHL 기본 · 기존 허락 보존 | [222d5785a270](https://github.com/gj3447/ant_den/commit/222d5785a2701b643671df2daf65e80f0af0c3b7) |
| [antden](https://github.com/gj3447/antden) | MHL 기본 · 기존 허락 보존 | [9782b183666a](https://github.com/gj3447/antden/commit/9782b183666a6a1236a52bae3976ec532f7f2fa0) |
| [apt-engine](https://github.com/gj3447/apt-engine) | MHL 기본 · 기존 허락 보존 | [eebe20dd22e3](https://github.com/gj3447/apt-engine/commit/eebe20dd22e35bdc480a54fed86fd17e054257de) |
| [Astar-snake](https://github.com/gj3447/Astar-snake) | MHL 기본 · 기존 허락 보존 | [bd7b85600c9d](https://github.com/gj3447/Astar-snake/commit/bd7b85600c9d1da3f3f0f73918e22d3e688b0ef8) |
| [BackupModuleProgram](https://github.com/gj3447/BackupModuleProgram) | MHL 기본 · 기존 허락 보존 | [a84fcd805c89](https://github.com/gj3447/BackupModuleProgram/commit/a84fcd805c89b0427936ccb4caa026ebcb7c095d) |
| [BezierFaceEditor](https://github.com/gj3447/BezierFaceEditor) | MHL 기본 · 기존 허락 보존 | [a3cac8d4652c](https://github.com/gj3447/BezierFaceEditor/commit/a3cac8d4652ccb24dc4abe2856d05e2d18705817) |
| [bhgman](https://github.com/gj3447/bhgman) | 기존 MHL 1.1 확인 · 이번 작업에서 미변경 | [8aab0ab49377](https://github.com/gj3447/bhgman/tree/8aab0ab49377f3fa5eed84f14e28c3ce1ecf75cb) |
| [bhgman_essence](https://github.com/gj3447/bhgman_essence) | MHL 기본 · 기존 허락 보존 | [68c1495279c0](https://github.com/gj3447/bhgman_essence/commit/68c1495279c07c05fe8cb0eb21b03aae2f8b4e61) |
| [bhgman_tool](https://github.com/gj3447/bhgman_tool) | MHL 기본 · 기존 허락 보존 | [8dee567d3b42](https://github.com/gj3447/bhgman_tool/commit/8dee567d3b42368c5f3ac249748f44160474a3cf) |
| [BlackBoxManager](https://github.com/gj3447/BlackBoxManager) | MHL 기본 · 기존 허락 보존 | [5610340597cd](https://github.com/gj3447/BlackBoxManager/commit/5610340597cd136597183da369d90793e3b5c3dd) |
| [BlazorWebAppTest](https://github.com/gj3447/BlazorWebAppTest) | MHL 기본 · 기존 허락 보존 | [c18363e86a85](https://github.com/gj3447/BlazorWebAppTest/commit/c18363e86a855606a1f17a058dfd659bff0dccae) |
| [C--Users-----OneDrive------------VSCODE-hello_django-ant_den](https://github.com/gj3447/C--Users-----OneDrive------------VSCODE-hello_django-ant_den) | MHL 기본 · 기존 허락 보존 | [530a191c89ec](https://github.com/gj3447/C--Users-----OneDrive------------VSCODE-hello_django-ant_den/commit/530a191c89ec2fd44ec4b34e5be23aac1bb2b064) |
| [C-practice](https://github.com/gj3447/C-practice) | MHL 기본 · 기존 허락 보존 | [b41dd5b6938a](https://github.com/gj3447/C-practice/commit/b41dd5b6938aa8d101e1e0f19fd7b5f4e248b84e) |
| [chain-reaction-language](https://github.com/gj3447/chain-reaction-language) | MHL 기본 · 기존 허락 보존 | [f83e712dcaa2](https://github.com/gj3447/chain-reaction-language/commit/f83e712dcaa2a5211478a4e6d2bbbc72c71c1ed4) |
| [CHU](https://github.com/gj3447/CHU) | MHL 기본 · 기존 허락 보존 | [250d417d1275](https://github.com/gj3447/CHU/commit/250d417d12751f62e43e2468e12c31411902e21c) |
| [Coffee_ERP](https://github.com/gj3447/Coffee_ERP) | MHL 기본 · 기존 허락 보존 | [6150c5fe19af](https://github.com/gj3447/Coffee_ERP/commit/6150c5fe19af2ad54df0485b140b944b7cd170cb) |
| [CompressionOverlap](https://github.com/gj3447/CompressionOverlap) | MHL 기본 · 기존 허락 보존 | [8781d12ac49f](https://github.com/gj3447/CompressionOverlap/commit/8781d12ac49fbb1c21a8e257c7ebf563b043f351) |
| [DB](https://github.com/gj3447/DB) | MHL 기본 · 기존 허락 보존 | [34dc1e16e96d](https://github.com/gj3447/DB/commit/34dc1e16e96d4d7596bc6f7a910a53499b4f4300) |
| [EnterpriseBinpickingDT](https://github.com/gj3447/EnterpriseBinpickingDT) | MHL 기본 · 기존 허락 보존 | [344e6e196552](https://github.com/gj3447/EnterpriseBinpickingDT/commit/344e6e196552e190c6e3e348d40ae283019df57d) |
| [EnterpriseBinpickingServer](https://github.com/gj3447/EnterpriseBinpickingServer) | MHL 기본 · 기존 허락 보존 | [2f93bea89bc9](https://github.com/gj3447/EnterpriseBinpickingServer/commit/2f93bea89bc969afd47dce27c4768809ad3fd45a) |
| [firebasetest](https://github.com/gj3447/firebasetest) | MHL 기본 · 기존 허락 보존 | [f273a42b3cbc](https://github.com/gj3447/firebasetest/commit/f273a42b3cbc0227b05c19bd393532607b704b43) |
| [forced-free-explosive](https://github.com/gj3447/forced-free-explosive) | MHL 기본 · 기존 허락 보존 | [ae92755067d4](https://github.com/gj3447/forced-free-explosive/commit/ae92755067d47c9d743cb65e70a690655e080bd4) |
| [fractal-graph](https://github.com/gj3447/fractal-graph) | MHL 기본 · 기존 허락 보존 | [4206f5ca23fd](https://github.com/gj3447/fractal-graph/commit/4206f5ca23fd15a1e98f0ae52865b22fc7d70c32) |
| [github](https://github.com/gj3447/github) | MHL 기본 · 기존 허락 보존 | [bcf27969e3ae](https://github.com/gj3447/github/commit/bcf27969e3aec3ade35f2a20fffb0bf092692224) |
| [github-slideshow](https://github.com/gj3447/github-slideshow) | MHL 기본 · 기존 허락 보존 | [508cd9dc59e2](https://github.com/gj3447/github-slideshow/commit/508cd9dc59e2572a6798088a1d72243f33bbe568) |
| [GithubClass](https://github.com/gj3447/GithubClass) | MHL 기본 · 기존 허락 보존 | [8ce514b36127](https://github.com/gj3447/GithubClass/commit/8ce514b36127e1409d40ff6ac28d7b42715c033f) |
| [HOH-Interface](https://github.com/gj3447/HOH-Interface) | MHL 기본 · 기존 허락 보존 | [7b166152bcdb](https://github.com/gj3447/HOH-Interface/commit/7b166152bcdb22786f438bfef2feb57f7160f071) |
| [HSWM](https://github.com/gj3447/HSWM) | MHL 기본 · 기존 허락 보존 | [27dca376f0e2](https://github.com/gj3447/HSWM/commit/27dca376f0e20b33eef94665f41dad24eba88cdd) |
| [ICE_ORCA_DRAGON](https://github.com/gj3447/ICE_ORCA_DRAGON) | MHL 기본 · 기존 허락 보존 | [6a9d5a3e246e](https://github.com/gj3447/ICE_ORCA_DRAGON/commit/6a9d5a3e246e5608de84c6088635b1f67d95f011) |
| [lakatotree](https://github.com/gj3447/lakatotree) | MHL 기본 · 기존 허락 보존 | [4c764aed4d09](https://github.com/gj3447/lakatotree/commit/4c764aed4d098f0ded344bb687a428d3da5d821d) |
| [LETSBEYOLO](https://github.com/gj3447/LETSBEYOLO) | MHL 기본 · 기존 허락 보존 | [425bf692d38d](https://github.com/gj3447/LETSBEYOLO/commit/425bf692d38d775d187fe9adb218a9daafcaaca2) |
| [line_input_calcurator](https://github.com/gj3447/line_input_calcurator) | MHL 기본 · 기존 허락 보존 | [97bea550e4e9](https://github.com/gj3447/line_input_calcurator/commit/97bea550e4e9f8a9135a8ff897116de45e151fda) |
| [makrov](https://github.com/gj3447/makrov) | MHL 기본 · 기존 허락 보존 | [629bf5972e19](https://github.com/gj3447/makrov/commit/629bf5972e1964fd65f5c4597641d7f8f21cfb4e) |
| [manim_list](https://github.com/gj3447/manim_list) | MHL 기본 · 기존 허락 보존 | [b637d1b69b9f](https://github.com/gj3447/manim_list/commit/b637d1b69b9f7741e0f8887d36d4b114753f88fa) |
| [masterKorea](https://github.com/gj3447/masterKorea) | MHL 기본 · 기존 허락 보존 | [ac77e8077336](https://github.com/gj3447/masterKorea/commit/ac77e8077336313539988c17b2bbf325f7377323) |
| [metahumotonic-foundation](https://github.com/gj3447/metahumotonic-foundation) | MHL 기본 · 기존 허락 보존 | [d5119ffc35dd](https://github.com/gj3447/metahumotonic-foundation/commit/d5119ffc35dd3addce6544b59cef797ff9d880b3) |
| [metahumotonic-web](https://github.com/gj3447/metahumotonic-web) | MHL 기본 · 기존 허락 보존 | [4f1031fef965](https://github.com/gj3447/metahumotonic-web/commit/4f1031fef965eac6316bca550944250bfa0cc9b0) |
| [metahumotonic_web_back](https://github.com/gj3447/metahumotonic_web_back) | 기존 AGPL 유지 · 독립 새 저작물만 MHL | [e36811720fe6](https://github.com/gj3447/metahumotonic_web_back/commit/e36811720fe6e522e8f2535b50f711dcf0b56e60) |
| [NextTimeTsuyu](https://github.com/gj3447/NextTimeTsuyu) | MHL 기본 · 기존 허락 보존 | [ee83ae65b882](https://github.com/gj3447/NextTimeTsuyu/commit/ee83ae65b882044e21249ff071f188014774d10b) |
| [NextTimeTsuyu2](https://github.com/gj3447/NextTimeTsuyu2) | MHL 기본 · 기존 허락 보존 | [b765f9bc28cc](https://github.com/gj3447/NextTimeTsuyu2/commit/b765f9bc28cc10149e1791e81336e543254687bf) |
| [NextTimeTsuyuForever](https://github.com/gj3447/NextTimeTsuyuForever) | MHL 기본 · 기존 허락 보존 | [4179c67aedb5](https://github.com/gj3447/NextTimeTsuyuForever/commit/4179c67aedb5e1c2db6a5f91f4069f84de34d3f0) |
| [ohm](https://github.com/gj3447/ohm) | MHL 기본 · 기존 허락 보존 | [a5b0af58faed](https://github.com/gj3447/ohm/commit/a5b0af58faedf580d5fbbf91fb527ff647036cdb) |
| [omd](https://github.com/gj3447/omd) | MHL 기본 · 기존 허락 보존 | [56c89dc6e512](https://github.com/gj3447/omd/commit/56c89dc6e51293260e9e9a97b52bc0cbd8c0870d) |
| [ooptdd](https://github.com/gj3447/ooptdd) | MHL 기본 · 기존 허락 보존 | [8acdab132535](https://github.com/gj3447/ooptdd/commit/8acdab1325355e1d3bcdd8d07833d464cf778f06) |
| [ooptdd-loop](https://github.com/gj3447/ooptdd-loop) | MHL 기본 · 기존 허락 보존 | [256dc26017ba](https://github.com/gj3447/ooptdd-loop/commit/256dc26017bae8786c62481240de25047fbefca4) |
| [PyRealSenseServer](https://github.com/gj3447/PyRealSenseServer) | MHL 기본 · 기존 허락 보존 | [a47c2427e452](https://github.com/gj3447/PyRealSenseServer/commit/a47c2427e45233bf24f2dd890cc9873ec7561024) |
| [ReactTest](https://github.com/gj3447/ReactTest) | MHL 기본 · 기존 허락 보존 | [680fa97900e6](https://github.com/gj3447/ReactTest/commit/680fa97900e6a36336e9008002d7c5827f981d02) |
| [RealSenseTest](https://github.com/gj3447/RealSenseTest) | MHL 기본 · 기존 허락 보존 | [6057066e46a6](https://github.com/gj3447/RealSenseTest/commit/6057066e46a682fedf4f3a375d56bef35c66cf60) |
| [Regex](https://github.com/gj3447/Regex) | MHL 기본 · 기존 허락 보존 | [c67d030a8a91](https://github.com/gj3447/Regex/commit/c67d030a8a9155b6f112d6f8479fc6be9363ef80) |
| [RSserverV2](https://github.com/gj3447/RSserverV2) | MHL 기본 · 기존 허락 보존 | [1f9de19c44f6](https://github.com/gj3447/RSserverV2/commit/1f9de19c44f6dcb0b64fed6bd55faab6863563dd) |
| [sam6d_enterprise_server](https://github.com/gj3447/sam6d_enterprise_server) | MHL 기본 · 기존 허락 보존 | [2de738af0013](https://github.com/gj3447/sam6d_enterprise_server/commit/2de738af00132338562a1eb473af8867d943e9af) |
| [sam6d_enterprise_serverv2](https://github.com/gj3447/sam6d_enterprise_serverv2) | MHL 기본 · 기존 허락 보존 | [fd6757c93d88](https://github.com/gj3447/sam6d_enterprise_serverv2/commit/fd6757c93d883a713e826dd99ff1a630270bdb1a) |
| [solar-system-3d](https://github.com/gj3447/solar-system-3d) | MHL 기본 · 기존 허락 보존 | [086247a5d408](https://github.com/gj3447/solar-system-3d/commit/086247a5d408c0e9082c422ddf9255a753015c34) |
| [spacegirl](https://github.com/gj3447/spacegirl) | 기존 MHL 1.1 확인 · 이번 작업에서 미변경 | [c76400e3284b](https://github.com/gj3447/spacegirl/tree/c76400e3284bb6bb3e67fea6a2afbdd6150d8fc3) |
| [spacegirl_tool](https://github.com/gj3447/spacegirl_tool) | MHL 기본 · 기존 허락 보존 | [24d4d159fb30](https://github.com/gj3447/spacegirl_tool/commit/24d4d159fb30b824f51f90fdc1f33e230862e4bc) |
| [start](https://github.com/gj3447/start) | MHL 기본 · 기존 허락 보존 | [ffeabfef2898](https://github.com/gj3447/start/commit/ffeabfef28987d71c74ccd87d85e404aff9c577a) |
| [symposium-skills](https://github.com/gj3447/symposium-skills) | MHL 기본 · 기존 허락 보존 | [ad2615b8ad1e](https://github.com/gj3447/symposium-skills/commit/ad2615b8ad1e44bd3637f93ed04544121dfac63d) |
| [Test](https://github.com/gj3447/Test) | MHL 기본 · 기존 허락 보존 | [869854061c81](https://github.com/gj3447/Test/commit/869854061c81b58c0beea1a53bbd9044a6372079) |
| [tissue_anomalib](https://github.com/gj3447/tissue_anomalib) | MHL 기본 · 기존 허락 보존 | [e015bdc11017](https://github.com/gj3447/tissue_anomalib/commit/e015bdc1101715080c9df9d3ff26cbbc4e90eced) |
| [tpa-engine](https://github.com/gj3447/tpa-engine) | MHL 기본 · 기존 허락 보존 | [e62ff681c4d6](https://github.com/gj3447/tpa-engine/commit/e62ff681c4d6d1e4241c9dd401e0e659fe8b4924) |
| [USL](https://github.com/gj3447/USL) | MHL 기본 · 기존 허락 보존 | [2565759c37a1](https://github.com/gj3447/USL/commit/2565759c37a1d3ab9ec87823dac4032c641c024e) |

## 참고한 공식 문서

- [GitHub: Licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository): 루트 허가문과 기존 조건 확인.
- [GNU GPL FAQ](https://www.gnu.org/licenses/gpl-faq.en.html): 기존 자유 소프트웨어 허락과 결합물의 조건을 검토하는 참고 자료.
- [Python packaging: pyproject.toml](https://packaging.python.org/en/latest/specifications/pyproject-toml/): `license-files`와 라이선스 메타데이터.
- [Hatch metadata](https://hatch.pypa.io/latest/config/metadata/): 빌드에 사용할 라이선스 표현과 허가문 경로.
