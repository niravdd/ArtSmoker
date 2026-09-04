# ArtSmoker
> *아트워크를 스모크 테스트하세요!*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon-Bedrock-orange?logo=amazonaws&logoColor=white)
![License](https://img.shields.io/badge/License-MIT--0-yellow)

![ArtSmoker 워크스루 — 텍스트 프롬프트에서 프로덕션급 2D 아트, 완전히 텍스처링된 게임 엔진용 3D 모델까지](docs/images/artsmoker-walkthrough.gif)

## 📌 0. 개요

**ArtSmoker는 아이디어를 게임 엔진에 바로 사용할 수 있는 아트로 바꿉니다 — 관리할 파이프라인 없이, 단 몇 분 만에.** 캐릭터, 소품, 환경, 키 아트를 자연어로 설명하기만 하면 프로덕션 대응의 2D 아트, 완전 텍스처링된 3D 모델, 동영상을 얻을 수 있습니다 — 모두 프로젝트의 비주얼 아이덴티티에 맞춰지고, 모두 자체 환경 내에 유지됩니다. 최신 AI 이미지·편집·3D·동영상 모델이 실질적인 크리에이티브 컨트롤을 갖춘 하나의 깔끔한 아티스트 우선 인터페이스 뒤에 자리합니다: ArtSmoker가 전체 제작 파이프라인을 대신 실행하므로, 팀은 기계 장치를 다루는 대신 룩을 디렉팅하는 데 집중합니다.

### 📝 문제

게임 및 미디어 스튜디오의 크리에이티브 팀은 생성형 AI의 레버리지를 원합니다 — 하지만 오늘날 그 힘은 애초에 그들이 다룰 대상이 아니었던 개발자 도구 뒤에 갇혀 있습니다:

- **아티스트가 아니라 엔지니어를 위해 만들어졌습니다** — 최고의 모델들은 클라우드 콘솔, 커맨드라인, SDK, REST API 뒤에 있습니다. 어떤 디렉터나 컨셉 아티스트도 아트 한 점을 만들기 위해 터미널을 다뤄야 할 필요는 없어야 합니다.
- **명확한 아이디어, 난해한 프롬프트** — 아티스트는 자신이 원하는 것을 정확히 알지만, 모델은 평범한 크리에이티브 언어로 된 지시를 받아들이지 않습니다; 일관되고 브리프에 맞는 결과는 여전히 브리프와 출력 사이에 놓인 프롬프트 구조, 네거티브 프롬프트, 모델별 표현에 좌우됩니다.
- **최고의 AI 모델들은 흩어져 있고 실행하기 어렵습니다** — 이미지, 편집, 3D, 동영상을 위한 강력한 AI 모델이 서로 다른 제공업체와 포맷으로 끊임없이 출시됩니다; 각각을 세우는 일(패키징, GPU, 양자화, 스케일링)은 그 자체로 하나의 완전한 엔지니어링 프로젝트입니다.
- **편집과 3D는 별개의 세계입니다** — 인페인팅, 아웃페인팅, 색상 변경, 레퍼런스 가이드 편집, 그리고 2D 컨셉을 텍스처링된 3D 모델로 바꾸는 일은 각각 보통 자체 도구, API, 전문가가 필요합니다.
- **브랜드 일관성 유지는 수작업입니다** — 모든 에셋을 확립된 룩에 충실하게 유지하려면 대개 각 생성을 일일이 손으로 챙겨야 합니다.

### 📝 솔루션

ArtSmoker는 오늘날 최고의 생성형 모델들을 하나의 아티스트 우선 인터페이스 뒤에 두는 셀프 호스팅 크리에이티브 스튜디오입니다 — 게임 에셋 제작을 위해 특별히 구축되었으며, 영화, 광고, 전자상거래, 출판, 그리고 오리지널 시각 콘텐츠로 살아가는 모든 팀에도 똑같이 잘 어울립니다.

- **자연어로 설명하세요** — ArtSmoker가 프롬프트 분해, 강화, 모델별 최적화를 뒷단에서 처리합니다. 가이드형 **Prompt Designer**를 통해 개별 시각 요소(주체, 씬, 조명, 색상)를 잠금/변형 컨트롤로 다듬어, 이미 잘 작동하는 것을 잃지 않으면서 진정으로 다른 방향을 탐색할 수 있습니다.
- **기본적으로 브랜드에 맞춤** — ArtSmoker에 기존 아트를 공급하면 비전 모델이 비주얼 아이덴티티를 학습하여, 모든 에셋이 프로젝트의 룩 앤 필에 맞춰 나옵니다.
- **2D, 편집, 그리고 3D — 엔드투엔드** — 생성한 뒤 인페인팅, 아웃페인팅, 색상 변경, 검색 및 교체, 레퍼런스 가이드 편집으로 제자리에서 다듬고; 모든 2D 에셋을 Unity, Unreal, Blender에 바로 들어가는 **완전 텍스처링된, 게임 엔진 대응 3D 모델**로 변환합니다 — 수동 모델링, UV 언래핑, 텍스처 페인팅이 필요 없습니다. 여기에 영화적 동영상과 아이디어 발상을 위한 멀티 모델 채팅 스튜디오까지.
- **모든 모델, 원클릭** — 여러 리전에 걸친 최신 호스팅 모델을 사용하거나, 큐레이션된 오픈소스 모델(Qwen-Image, FLUX.2, HunyuanImage, TripoSG, TRELLIS.2 등)을 원클릭으로 자체 GPU에 배포하세요 — 패키징, 양자화, 오토 스케일링, 작업 추적이 모두 처리되고, 모든 모델이 출시 전 엔드투엔드로 검증됩니다.
- **원하는 곳에서 실행 — 그리고 IP는 당신의 것으로 유지** — 아티스트 한 명의 데스크톱이나 팀 전체를 위한 공유 인스턴스에 설치하세요; **자체 GPU가 필요 없습니다**(무거운 연산은 관리형 AWS 서비스에서, 또는 ArtSmoker가 대신 띄우고 제로로 다시 스케일하는 오토 스케일링 엔드포인트에서 실행됩니다). 오직 당신 자신의 AWS 계정에만 연결됩니다 — 아트워크, 프롬프트, 스타일, 생성된 에셋이 당신의 환경 내에 머물고, 아무것도 서드파티 서비스로 나가지 않으며, 크리에이티브 IP에 대한 완전한 소유권을 유지합니다.

**Amazon Bedrock 모델**: Claude Sonnet/Opus(프롬프트 엔지니어링 및 채팅), Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core, Stability AI 서비스(이미지 편집), Nova Reel, Luma AI Ray(동영상 생성), 그리고 Chat Studio용 16개 제공업체의 80개 이상의 LLM. **셀프 호스팅 모델**: Qwen-Image(텍스트-이미지) 및 Qwen-Image-Edit(레퍼런스 가이드 + 지시 편집, Apache-2.0), HunyuanImage 3.0(BF16/NF4), FLUX.2, FLUX.1, TripoSG 및 TRELLIS.2(이미지-투-3D) 등, Amazon SageMaker 경유 — 새 모델을 추가할 수 있는 확장 가능한 카탈로그 포함.

**[지금 시작하기 — 사전 요구사항 및 설치로 이동 ▸](#get-started)**

### Language / 言語 / 语言 / 언어 / हिन्दी / Язык / Langue / Idioma

ArtSmoker는 9개 언어를 지원합니다. 상단 내비게이션 바의 언어 버튼(EN | 日 | 中 | 한 | हिं | РУ | FR | ES | DE)으로 UI 언어를 전환할 수 있습니다. 선택은 자동으로 저장됩니다.

| 언어 | README |
|------|--------|
| English | [README.md](README.md) |
| 日本語 (Japanese) | [README.ja.md](README.ja.md) |
| 中文 (Chinese) | [README.zh.md](README.zh.md) |
| 한국어 (Korean) | 이 문서 |
| हिन्दी (Hindi) | [README.hi.md](README.hi.md) |
| Русский (Russian) | [README.ru.md](README.ru.md) |
| Français (French) | [README.fr.md](README.fr.md) |
| Español (Spanish) | [README.es.md](README.es.md) |
| Deutsch (German) | [README.de.md](README.de.md) |

**다국어 프롬프트 지원:**
- 영어가 아닌 프롬프트(일본어, 중국어, 한국어, 힌디어, 러시아어, 프랑스어, 스페인어 등)는 자동으로 감지되어 생성 전에 영어로 번역됩니다
- 프롬프트 영역에 이중 언어 미리보기가 표시됩니다: 원본 텍스트와 영어 번역을 전환하여 모델이 실제로 받게 될 내용을 정확히 확인할 수 있습니다
- 원본 프롬프트, 감지된 언어, 영어 번역은 모두 에셋 메타데이터에 보존됩니다
- 파일명은 번역된 영어 프롬프트로부터 생성됩니다(예: "病院の建物" → `hospital-building_opt1_var1.png`)
- Chat Studio는 LLM에 프롬프트를 직접 전달합니다(번역 없음) — Claude 같은 모델이 기본적으로 다국어를 지원하기 때문입니다
- Type Studio의 텍스트는 사용자의 언어 그대로 유지됩니다(이미지에 그대로 렌더링됩니다)
- 모든 사전 검토 및 콘텐츠 스크리닝은 일관성을 위해 번역된 영어 프롬프트에 대해 작동합니다

## 📌 1. 기능 개요

ArtSmoker는 두 가지 모드로 작동합니다 — **독립 모드**(아트 스타일이나 테마 설정 불필요, 설명하고 생성하기만 하면 됩니다)와 **스타일 가이드 모드**(기존 아트를 업로드하면 모든 생성이 비주얼 아이덴티티에 맞춰집니다). 두 모드 모두 동일한 스튜디오와 생성 파이프라인을 사용합니다.

### 📝 독립 모드(빠른 시작)

스타일이나 테마 설정이 필요 없습니다 — 2D Image Studio, Video Studio 또는 Type Studio를 열고 바로 제작을 시작하세요.

1. **필요한 것을 설명** — "hospital building"이나 "fire mage character"와 같은 프롬프트를 입력하거나 음성 입력을 사용합니다. AI가 아이디어를 시각 컴포넌트로 분해하고, 모델별 최적화로 강화하며, 스마트 잠금/변형 컨트롤로 크리에이티브 의도를 존중합니다. 어떤 언어로든 작성 가능 — 비영어 프롬프트는 자동 번역됩니다.
2. **모델과 설정 선택** — 사용 가능한 모든 텍스트-이미지 모델(Amazon Bedrock + SageMaker 셀프 호스팅)에서 멀티 선택하고, 크기, 품질 티어, 리전을 선택합니다. 여러 모델을 체크하여 나란히 비교하거나, 하나를 선택하여 집중 생성합니다. 비용 추정은 실시간으로 업데이트됩니다.
3. **진정으로 다른 옵션 얻기** — 시스템이 최대 5개의 명확히 구별되는 크리에이티브 컨셉(의상, 분위기, 조명, 구도를 변형 — 단순히 카메라 앵글만이 아닌)을 생성하며, 각각 최대 5개의 시드 배리에이션(총 25개 이미지)을 갖습니다. 사용자가 지정한 세부사항은 잠기고, AI가 추론한 세부사항은 과감하게 변형됩니다. 눈에 보이는 **시드** 컨트롤로 배치를 재현할 수 있습니다 — 같은 시드에 최종 프롬프트와 설정까지 같으면 같은 이미지가 다시 생성되고, 아무 결과나 클릭하면 그 시드로 고정되어 한 가지만 바꿔 마음에 드는 결과에서 분기할 수 있습니다.
4. **편집과 개선** — Asset Viewer에서 직접 인페인팅, 아웃페인팅, 지우기, 검색 및 교체, 리컬러를 사용합니다. 각 편집은 새 버전을 생성합니다 — 원본은 항상 보존됩니다.
5. **게임용 파일 다운로드** — 투명 배경 PNG + SVG, 설명적 이름 포함(예: `hospital-building_opt2_var3.png`). 동영상은 MP4로 내보내집니다.

### 📝 스타일 가이드 모드(아트 스타일과 테마에 맞추기)

생성되는 모든 에셋을 기존 아트 스타일에 맞추고 싶은 팀을 위해 — 레퍼런스 이미지를 업로드하고 AI에게 먼저 비주얼 아이덴티티를 학습시킵니다.

1. **게임의 아트 업로드** — 로컬 디렉터리(재귀 스캔, 중복 방지를 위한 심볼릭 링크) 또는 S3 버킷(페이지네이션 포함 재귀 목록)에서 레퍼런스 이미지를 가져옵니다. **스마트 중복 제거**가 자동 실행됩니다 — 회전 변형(barrel_N/E/S/W.png에서 barrel_S.png만 유지)과 애니메이션 프레임(Idle0-Idle8에서 Idle만 유지)을 제거합니다. 예를 들어, 747개 파일의 아이소메트릭 에셋 팩이 약 99개의 고유 오브젝트로 중복 제거됩니다. 지원 형식: .png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg, 그리고 3D 모델(.glb, .gltf)에서의 자동 텍스처 추출.
2. **AI가 스타일 학습** — 2단계 응집도 인식 분석: 먼저 컬렉션이 통일적인지, 구조적으로 일관성이 있는지, 다양한지를 판단하는 빠른 검사. 그 다음 전체 레퍼런스 세트에 대한 심층 분석이 메타데이터가 풍부한 스타일 프로필 — 컬러 팔레트, 선 굵기, 조명 패턴, 구도 규칙, 제작 관례 — 을 생성합니다. 생성 힌트를 제공하면 AI가 이를 "아티스트의 가이던스"로 받아들여, 분석이 눈에 보이는 것뿐만 아니라 의도까지 이해합니다.
3. **스타일 적용하여 생성** — Image Studio에서 스타일을 선택하면 모든 프롬프트가 스타일의 시각 지시로 자동 강화됩니다. "hospital building"과 같은 프롬프트가 게임의 컬러 팔레트, 원근법 관례, 렌더링 스타일을 포함하는 상세한 생성 지시가 됩니다.
4. **독립 모드의 모든 기능이 적용됩니다** — 여러 옵션, 모델 비교, 편집, 버전 관리, 게임용 다운로드가 모두 동일하게 작동하며, 이제 당신의 아트 스타일에 의해 가이드됩니다.

> [!NOTE]
> 생성되는 모든 콘텐츠는 AI 모델에 의해 만들어지며, 제공하는 프롬프트와 레퍼런스에 따라 달라집니다. 프로덕션 환경에서 생성 에셋을 사용하기 전에 콘텐츠 품질, 지적 재산, 적용되는 서비스 약관에 관한 [면책 조항](#disclaimer)을 확인하세요.

### 📝 1.1 기능 한눈에 보기

- 🎨 **Style Library** — 아트를 업로드하면 AI가 비주얼 아이덴티티를 학습
- 🖼️ **2D Image Studio** — 옵션 x 배리에이션으로 이미지 생성, 가이드형 3단계 프롬프트 워크플로
- 🎨 **Prompt Designer** — AI가 프롬프트를 편집 가능한 시각 컴포넌트(주체, 씬, 조명, 색상)로 분해, 필드별 잠금/변형 토글, 스타일 통합, 스마트 에셋 타입 분류. Photorealistic, Character, Environment 등
- 🎬 **Video Studio** — 모델별 프롬프트 가이던스(Nova Reel 카메라 컨트롤, Luma Ray 자연어)를 갖춘 텍스트-투-비디오, 멀티숏, 이미지-투-비디오
- ✍️ **Type Studio** — 폰트 피커가 포함된 AI 디자인 텍스트 오버레이
- 💬 **Chat Studio** — 스트리밍, 마크다운, 코드 하이라이팅, 비전, 세션, 컨텍스트 압축을 지원하는 멀티 모델 LLM 채팅
- 📁 **통합 갤러리** — 각 에셋을 실제 종횡비(세로, 정사각형, 가로 — 절대 잘리지 않음)로 표시하는 메이슨리 레이아웃. 이미지 + 동영상 탐색, 미디어 필터(전체 / 2D 아트워크 / 3D 모델 / 동영상), 검색, 전체 날짜-시간-시간대 스탬프, 다운로드, 삭제. 이미 3D 모델이 생성된 에셋에는 **3D 배지**가 붙으며, **3D 모델** 필터는 그런 에셋만 표시합니다
- 📥 **이미지 가져오기** — 기존 이미지(모든 형식)를 갤러리에 일급 에셋으로 가져옵니다. 자동으로 PNG로 변환되고, 선택한 에셋 타입으로 태그되며, 즉시 편집·3D 변환이 가능합니다 — 모든 기능(버전 관리, 편집, 이미지-투-3D)이 생성 이미지와 정확히 동일하게 작동합니다
- ✏️ **이미지 편집** — 인페인팅, 아웃페인팅, 지우기, 검색 및 교체, 리컬러(AssetViewer 내). 각 모드에는 AI **프롬프트 생성** 버튼이 있어, 비전 모델이 이미지와 원본 프롬프트를 읽고 해당 모드와 선택한 편집 모델에 맞춘 편집 프롬프트를 제안합니다(Stability 편집 모델에는 설명형 캡션, Qwen-Image-Edit에는 지시문). 확장/아웃페인트는 확정 전에 픽셀 눈금자와 함께 캔버스가 얼마나 확장될지 실시간 성장 프레임 미리보기로 보여줍니다. 지시형 에디터(Qwen-Image-Edit)는 **5가지 모드 전부를 마스크 없이** 지원합니다 — 진정한 캔버스 확장 포함: ArtSmoker가 캔버스를 사전 패딩하고, 모델이 새 영역만 완성하게 한 뒤, 원본 픽셀을 그대로 블렌딩해 되돌립니다. 편집된 각 버전에는 원본 생성 모델과 해당 버전을 편집한 에디터 **두 개의 태그**가 함께 표시됩니다
- 📤 **내보내기 및 컷아웃** — AssetViewer에서 버전별 내보내기 산출물: 배경이 제거된 투명 PNG 컷아웃과 진정한 벡터 SVG 트레이스(배경 포함/미포함). 배경 제거 방식은 실행마다 선택 가능: **무료 온디바이스**(rembg/u2net, 클라우드 비용 없음) 또는 **유료 Amazon Bedrock** 리무버 — 3D 생성용 이미지 준비 시에도 동일한 선택지를 제공합니다
- 🔄 **실시간 진행률** — 재시도/스로틀 가시성이 포함된 SSE 스트리밍
- 🛡️ **스마트 콘텐츠 검토** — 카나리아 테스트, 자동 모델 전환, AI 보조 리라이트
- ⚙️ **Model Registry** — 스튜디오별로 정리된 관리 UI(Image, Video, Chat, Type, Shared), Bedrock 검색, 커스텀 모델 지원
- 📝 **Prompt Templates** — 28개의 편집 가능한 LLM 지시 프롬프트, AI 보조 개선, 자동 수정이 포함된 변수 검증
- 📦 **에셋 버전 관리** — 버전 기록(v1, v2…)과 버전 탐색을 지원하는 제자리 편집, 그리고 버전별 삭제: 하나의 버전만 제거(다른 버전은 번호 유지)하며, 뷰어는 이전 버전으로 전환 — 마지막 버전을 삭제하면 에셋 전체가 제거됩니다
- 💰 **비용 추적** — 요청, 세션, 에셋별 추정 AWS 지출로, 지역별 실시간 AWS 가격에서 계산. 자체 호스팅 모델은 (오해를 부르는 이미지당 가격이 아니라) GPU 인스턴스의 시간당 실행 요금 + 일반적인 생성 시간을 표시
- 🌐 **9개 언어 i18n** — 완전한 UI 번역(EN, JA, ZH, KO, HI, RU, FR, ES, DE), 비영어 프롬프트 자동 감지(영어 UI는 감지를 완전히 건너뜀), 이중 언어 미리보기
- 🔍 **커스텀 모델 지원** — 파인튜닝, 임포트, 배포된 커스텀 Bedrock 모델을 자동으로 검색
- 🔧 **셀프 호스팅 모델 — 원클릭 배포** — 사전 테스트된 오픈소스 모델(Qwen-Image, Qwen-Image-Edit, HunyuanImage 3.0, FLUX.2, FLUX.1, TripoSG, TRELLIS.2 등)의 큐레이션 카탈로그를 탐색하고, GPU 인스턴스를 선택한 후 Deploy를 클릭합니다. ArtSmoker가 추론 핸들러 패키징, 양자화 구성, 올바른 CUDA 툴킷 선택, 오토 스케일링 설정, CloudWatch 알람 등록, 비동기 작업 추적 연결까지 모든 것을 처리합니다. 카탈로그의 모든 모델은 콜드 스타트부터 생성, 갤러리 전달까지 엔드투엔드로 검증되었으므로 — GPU 드라이버, 메모리 오버플로, 컨테이너 호환성을 디버깅할 필요가 없습니다. 최고 품질을 위한 BF16 + FlashInfer, 비용 효율을 위한 NF4, 멀티 GPU 자동 감지를 지원하고, 유휴 시 제로로 오토 스케일링($0 유휴 비용)되며, 동일 모델이 재구성 없이 다른 인스턴스 유형에서 실행됩니다
- 🧊 **이미지-투-3D 생성** — 모든 Game Asset 또는 Character 이미지를 원클릭으로 텍스처링된 3D 메시(GLB)로 변환합니다. 멀티뷰 합성 + 텍스처 베이킹으로 게임 엔진에 바로 사용할 수 있는 에셋을 생성합니다. 오빗/줌/팬이 가능한 인터랙티브 3D 뷰어
- 🩹 **3D용 스마트 소스 완성** — 이미지-투-3D는 보이는 부분만 생성할 수 있어, 잘린 캐릭터(다리가 잘림)는 다리 없는 메시가 됩니다. 생성 전에 ArtSmoker가 소스를 비전으로 확인하고, 잘려 있으면 아웃페인팅으로 **완성할 것을 제안**합니다(AI가 제안하고 완전히 편집 가능한 프롬프트) — 전/후를 미리 보고, 결과를 재검토하며, 다시 확장하거나 버릴 수 있고, 새 이미지 버전으로 저장됩니다. 옵트인이며 비차단형이고, 잘 구성된 이미지는 그대로 생성됩니다
- 🔄 **Auto-Update** — 시작 시 버전 게이트 확인 + 24시간 주기 확인, `git`(checkout)로 업데이트하거나 git이 없는 설치 환경에서는 **tarball 다운로드 후 교체** 방식으로 업데이트한 뒤, 그 자리에서 재시작(감독 프로세스 재기동 / gunicorn reload)하거나 원클릭 **Restart**를 제공합니다 — `data/`나 `.env`는 절대 덮어쓰지 않습니다(`ARTSMOKER_AUTO_UPDATE=false`로 비활성화)

### 📝 1.2 스크린샷

**2D Image Studio** — 왼쪽에 멀티 선택 모델 드롭다운, 에셋 타입, 크기, 후처리 옵션이 있는 설정. 오른쪽에 Prompt Designer와 Generate Enhanced Prompt 버튼이 포함된 3단계 프롬프트 워크플로. 하단에 IP 선언과 비용 추정.

![2D Image Studio — 설정, 프롬프트 워크플로, 생성 컨트롤](docs/images/image-studio-top.png)

**2D Image Studio — 생성 결과** — 상단에 강화된 프롬프트, 하단에 멀티 모델 비교 결과. 각 모델은 모델별 프롬프트 최적화로 독립적으로 생성. 결과에 모델명, 크기, 생성 비용이 표시됩니다.

![2D Image Studio — 강화된 프롬프트와 생성 결과](docs/images/image-studio-results.png)

**2D Image Studio — 모델 비교** — 선택한 모든 모델(8개 표시 — Amazon Bedrock과 셀프 호스팅 모델 모두)의 나란히 비교 그리드. 각 옵션 카드는 자체 배리에이션 필름스트립을 가지며, 선택한 옵션에는 모델별 네거티브 프롬프트가 표시됩니다. 후처리 토글(배경 제거, SVG 변환, 업스케일)은 재생성 없이 기존 결과에 적용됩니다.

![2D Image Studio — 멀티 모델 비교 그리드와 배리에이션](docs/images/image-studio-comparison.png)

**Image Inspiration(참조 이미지 기반)** — 1~3장의 참조 이미지를 드롭하고, 원하는 것을 설명한 뒤, 사용 방식을 선택하세요: **참조에 충실하게**(배포된 이미지 편집 모델에서 픽셀 단위로 충실한 편집) 또는 **참조에서 영감받기**(비전 AI가 향상된 프롬프트를 작성 — 어떤 모델 선택, 옵션, 배리에이션과도 작동). 도출된 프롬프트는 생성 전에 미리 보고 자유롭게 편집할 수 있습니다.

![Image Inspiration — 참조 이미지, 지시문, 편집 가능한 향상된 프롬프트 미리보기](docs/images/image-inspiration.png)

**Image Inspiration — 결과** — 참조가 새로운 창작물이 됩니다(여기서는 참조 사진으로 그린 캐리커처). 모델에 전송된 정확한 프롬프트와 이미지당 비용이 기록됩니다.

![Image Inspiration — 참조 이미지에서 생성된 캐리커처 결과](docs/images/image-inspiration-results.png)

**Prompt Designer** — AI가 프롬프트를 편집 가능한 시각 컴포넌트(주체, 씬, 구도, 조명, 스타일 및 색상)로 분해. 각 필드는 잠금/변형 컨트롤로 개별 편집이 가능하여 진정으로 구별되는 크리에이티브 옵션을 만듭니다.

![Prompt Designer — 편집 가능 필드가 포함된 구조화된 시각 분해](docs/images/prompt-designer-top.png)

**Prompt Designer — 컬러 팔레트** — 16진수 색상 스와치가 포함된 이름 지정 컬러 팔레트, 스타일 키워드, 품질 레벨 컨트롤. AI가 비주얼 아이덴티티를 학습하고 모든 생성에 일관되게 적용합니다.

![Prompt Designer — 컬러 팔레트, 스타일 키워드, 품질 컨트롤](docs/images/prompt-designer-bottom.png)

**Style Library** — 게임의 기존 아트를 업로드하면, AI가 비주얼 스타일을 분석하여 메타데이터가 풍부한 프롬프트 가이드를 생성합니다. 레퍼런스 이미지는 완전한 AI 분석 및 JSON 스타일 프로필과 함께 표시됩니다.

![Style Library — 레퍼런스 이미지와 함께하는 AI 스타일 분석](docs/images/style-library-top.png)

![Style Library — 레퍼런스 이미지, 가져오기 옵션, 분석 데이터](docs/images/style-library-bottom.png)

**갤러리** — 미디어 타입 필터, 스타일 필터, 검색, 정렬이 포함된 생성 이미지와 동영상의 통합 뷰. 에셋을 클릭하면 전체 뷰어가 열립니다. **이미지 가져오기** 버튼은 기존 이미지를 갤러리에 가져옵니다 — 에셋 타입을 선택하면(Character/Game Asset은 3D 지원) PNG로 변환되어 즉시 편집·3D 변환이 가능해집니다.

![갤러리 — 필터가 포함된 생성 에셋 그리드](docs/images/gallery.png)

**Asset Viewer** — 탭 인터페이스(PNG, Edit, Export & Cutouts, Metadata, 3D Model), 이미지 버전 바, PNG/SVG 직접 다운로드가 포함된 전체 크기 미리보기. 체커보드 합성 이미지 위에 확대/맞춤/측정 컨트롤 제공.

![Asset Viewer — 다운로드 옵션이 포함된 전체 크기 미리보기](docs/images/asset-viewer.png)

**Asset Viewer — 이미지 편집** — 다섯 가지 편집 모드: 채우기/교체, 제거, 확장, 찾아 바꾸기, 색상 변경. 표시된 화면: 측정 눈금자, 변별 픽셀 값, 이미지를 읽고 편집 프롬프트를 대신 써 주는 ✨ 프롬프트 생성 버튼을 갖춘 **확장** 모드. 버전 히스토리가 보존됩니다 — 원본은 절대 덮어쓰이지 않습니다.

![Asset Viewer — 측정 눈금자와 AI 제안 프롬프트를 사용한 확장 편집](docs/images/asset-viewer-edit.png)

**Asset Viewer — Export & Cutouts** — 게임, 엔진, 디자인 도구에 바로 쓸 수 있는 버전별 아티팩트: 전체 이미지 벡터 SVG, 배경 제거된 컷아웃 PNG, 컷아웃 SVG. 배경 제거는 기기에서 무료로 실행됩니다(유료 Amazon Bedrock 처리도 선택 가능).

![Asset Viewer — 벡터 SVG와 배경 제거 컷아웃의 Export & Cutouts](docs/images/asset-viewer-export-cutouts.png)

아웃페인팅 후(아래 v3), 같은 탭이 개선된 전신 버전에 대해 세 가지 아티팩트를 모두 재생성합니다.

![Asset Viewer — 아웃페인팅된 전신 버전의 Export & Cutouts](docs/images/asset-viewer-export-cutouts-outpainted.png)

**Asset Viewer — Metadata** — 전체 프롬프트 계보(내 프롬프트 → Prompt Designer 분해 → 재구성 프롬프트 → 모델 맞춤 정제 프롬프트), 생성 세부 정보, 비용 내역, 전체 버전 히스토리.

![Asset Viewer — 전체 프롬프트 계보와 버전 히스토리가 포함된 Metadata](docs/images/asset-viewer-metadata.png)

*3D 파이프라인의 스크린샷 — 생성, 소스 검토, 엔진 대응 내보내기, 배리언트 — 은 아래 1.9절(3D 모델 생성)에서 해당 기능과 함께 보여드립니다.*

**Video Studio** — 왼쪽에 설정(모델, 생성 모드, 길이, 리전, 비용 추정), 오른쪽에 프롬프트. Nova Reel(싱글 숏, 최대 2분 멀티숏 자동/수동)과 Luma AI Ray(종횡비, 루핑)를 지원합니다.

![Video Studio — 설정과 프롬프트](docs/images/video-studio.png)

![Video Studio — AI 강화 프롬프트와 함께 생성 중](docs/images/video-studio-generating.png)

![Video Studio — 썸네일과 최근 동영상이 포함된 완료 동영상](docs/images/video-studio-completed.png)

**동영상 플레이어** — 동영상을 클릭하면 전체 메타데이터(원본 프롬프트, AI 강화 프롬프트, 모델, 길이, 리전)와 함께 인라인으로 재생합니다.

![동영상 플레이어 — 메타데이터와 함께하는 생성 동영상 재생](docs/images/video-player.png)

### 📝 1.3 2단계 생성

각 프롬프트에 대해 AI는 **옵션(Options)** — 근본적으로 다른 디자인 해석(예: "a warrior"의 경우: 바이킹 버서커, 일본 사무라이, 부족 전사, 사이버 솔저, 그리스 호플리테스)을 만듭니다. 각 옵션에 대해 이미지 모델은 **배리에이션(Variations)** — 미묘한 시각적 차이를 주는 서로 다른 랜덤 시드 — 를 생성합니다. 이를 통해 아티스트는 폭넓은 크리에이티브 팔레트에서 선택할 수 있습니다.

### 📝 1.4 멀티 모델 선택

모델 드롭다운은 **체크박스 기반 멀티 선택**을 지원합니다 — 단일 생성 실행에서 모든 모델 조합을 선택할 수 있습니다:

- **단일 모델** — 하나의 모델을 체크하여 집중 생성(가장 빠르고 저렴)
- **여러 모델** — 2-3개의 특정 모델을 체크하여 타깃 비교(예: SD 3.5 + FLUX.2만)
- **All Available Models** — 하단 토글로 모든 활성화된 모델을 선택/해제하여 전체 나란히 비교

각 모델은 독립적으로 실행됩니다: 더 엄격한 모델이 프롬프트를 차단해도, 각 옵션 카드에 명확한 상태 라벨(성공, 모더레이션에 의한 차단, 실패)과 함께 프롬프트를 수락한 모델의 결과는 여전히 받을 수 있습니다. 비용 추정은 모델을 체크/해제할 때 실시간으로 업데이트됩니다.

선택적 **"Model-optimized prompts"** 토글은 각 모델의 강점에 맞게 프롬프트를 조정합니다 — 프롬프트는 모델별로 재작성됩니다(예: SD 3.5에는 품질 부스터, FLUX.2에는 자연어, Qwen-Image에는 동급 최고의 텍스트 렌더링 큐).

### 📝 1.5 레퍼런스 가이드 생성

프롬프트를 처음부터 작성하는 것 외에도, **1~3장의 레퍼런스 이미지와 지시문으로** 생성할 수 있습니다 — Image Studio 프롬프트 영역 상단의 세그먼트 컨트롤로 모드를 선택하세요:

- **레퍼런스에 맞추기(Match the reference)** — 레퍼런스의 주체, 제품, 캐릭터는 유지하고 나머지(테마, 배경, 의상, 조명)를 지시문 그대로 변경합니다. 여러 장면에 걸친 일관된 캐릭터나 제품 샷에 이상적입니다. 이 모드는 셀프 호스팅 지시형 에디터(Qwen-Image-Edit)에서 실행되며 **배포되어 있을 때** 나타납니다 — 배포되어 있지 않으면 ArtSmoker가 Custom Models에서 바로 배포하도록 안내합니다(원클릭, 3D 파이프라인과 동일한 흐름). 상업적으로 안전(Apache-2.0)합니다.
- **레퍼런스에서 영감받기(Inspired by the reference)** — ArtSmoker의 비전 AI가 레퍼런스와 지시문을 읽고 강화된 프롬프트를 작성한 뒤(먼저 사용자에게 표시), 평소의 텍스트-이미지 모델로 생성합니다. **항상 사용 가능** — 배포가 필요 없습니다. 주체를 복제하지 않고 룩, 팔레트, 구도를 빌려오는 데 좋습니다.

- **참조 리믹스(Remix the reference)** — 고전적인 강도 기반 image-to-image: 레퍼런스의 *픽셀*이 Bedrock 모델(Stable Diffusion 3.5 Large 또는 Stable Image Ultra — 레지스트리 기능 플래그로 판별)로 곧장 전달되며 **강도 다이얼**로 조절합니다. 미묘하게는 구도·색감·분위기를 거의 유지하고, 과감하게는 느슨한 영감으로 취급합니다. 옵션을 2 이상으로 하면 **강도 사다리**가 되어 미묘함부터 과감함까지 강도별 카드가 나란히 생성됩니다. *레이아웃은 유지하지만 신원은 유지하지 않습니다*(얼굴·제품이 달라집니다 — 신원 보존이 필요하면 Match 사용). 출력 크기는 참조 이미지를 따릅니다. **항상 사용 가능** — 배포도, 비전 분석 호출도 없습니다.

세 모드 모두 지시문이 필요하므로, 레퍼런스가 *무엇을 위한 것인지*에 대한 통제권을 유지할 수 있습니다. 레퍼런스 가이드 생성은 Style Library(여러 이미지를 재사용 가능한 스타일 프로필로 분석)와는 별개입니다 — 일회성, 이미지 주도 생성에 사용하세요.

### 📝 1.6 Video Studio

텍스트 프롬프트로 AI 동영상과 애니메이션을 생성합니다. **Amazon Nova Reel**(v1.0, v1.1)과 **Luma AI Ray**(v2.0)를 지원합니다.

| 기능 | Nova Reel | Luma Ray v2 |
|------|-----------|-------------|
| **최대 길이** | 120초(2분) | 9초 |
| **해상도** | 1280x720 | 720p / 540p |
| **종횡비** | 16:9만 | 7가지 옵션(1:1, 16:9, 9:16 등) |
| **이미지-투-비디오** | 예(시작 프레임) | 예(시작 + 종료 프레임) |
| **루핑 동영상** | 아니오 | 예 |
| **멀티숏 컨트롤** | 예(자동 + 수동) | 아니오 |
| **가격** | ~$0.08/초 | ~$1.50/초 |

**작동 방식:**
1. 동영상 모델을 선택하고 길이, 종횡비, 리전을 설정
2. 프롬프트 입력 — AI가 영화적 어휘, 카메라 무브먼트, 시간적 일관성 큐로 강화
3. Generate 클릭 — 작업이 `StartAsyncInvoke`를 통해 비동기 실행되고, 출력은 설정된 S3 버킷으로 전송
4. 5초마다 상태를 폴링 — 완료 시 (ffmpeg를 통해) 썸네일이 추출되고 MP4가 로컬에 다운로드(또는 S3에서 스트리밍)
5. 동영상은 Video Studio의 "Recent Videos" 섹션과 통합 갤러리 모두에 표시

**S3 버킷 필요**: 동영상 생성은 S3에 출력합니다. UI의 Video Settings에서 설정(기존 버킷 탐색 또는 새로 생성)하거나, CLI로 생성할 수 있습니다:

```bash
# Create an S3 bucket for video storage (replace REGION and YOUR_ORG)
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-east-1

# For regions other than us-east-1, add the LocationConstraint:
aws s3api create-bucket --bucket artsmoker-video-YOUR_ORG --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2
```

저장 모드: 로컬 다운로드(기본값) 또는 S3에서 온디맨드 스트리밍.

**동영상 프롬프트 강화**: LLM이 카메라 무브먼트(팬, 줌, 돌리, 트래킹), 조명 세부사항, 시간적 큐를 추가합니다. 동영상 모델은 네거티브 프롬프트를 지원하지 않으므로, 회피할 컨셉이 자연스럽게 포지티브 프롬프트에 녹아듭니다.

### 📝 1.7 Chat Studio

풀 기능 LLM 채팅 인터페이스 — 셀프 호스팅 대화형 AI처럼, 서드파티 데이터 접근 없이 자체 AWS 계정에서 실행됩니다.

**16개 제공업체의 80개 이상 모델** — Claude(Sonnet, Opus, Haiku), Amazon Nova, Meta Llama, Mistral, Cohere, Qwen, DeepSeek, Google Gemma, NVIDIA Nemotron 등. 계정 내 커스텀/임포트 모델도 포함. 모두 Sync from AWS로 자동 검색됩니다.

**핵심 기능:**
- **스트리밍 응답** — Bedrock ConverseStream을 통한 실시간 토큰 단위 렌더링
- **마크다운 렌더링** — 제목, 굵게/기울임꼴, 목록, 테이블, 인용문, 수평선
- **코드 블록** — 언어 배지 + 복사 버튼이 포함된 구문 하이라이팅(highlight.js)
- **메시지별 메트릭** — 입력/출력 토큰, 레이턴시, 추정 비용, 사용 모델
- **컨텍스트 윈도우 바** — 사용/최대 토큰 수가 표시된 시각적 채움 표시기(녹색/노란색/빨간색)
- **리전 전환** — 각 모델이 사용 가능한 모든 리전 표시, 가장 가까운 리전 또는 가장 저렴한 리전 선택

**세션 관리:**
- 자동 저장이 포함된 다중 동시 세션
- 사이드바에서 인라인 이름 변경, 복제, 삭제, 검색/필터
- 대화를 마크다운으로 내보내기
- 세션 합계: 토큰 수, 추정 비용, 메시지 수

**고급 기능:**
- **시스템 프롬프트 템플릿** — General Assistant, Coding Expert, Creative Writer, Game Designer, Data Analyst, Technical Writer
- **비전/멀티모달** — 비전 지원 모델용 드래그 앤 드롭, 파일 피커, Ctrl+V 이미지 붙여넣기
- **컨텍스트 압축** — AI가 오래된 메시지를 요약하여 컨텍스트 윈도우 공간 확보
- **재생성** — 동일한 프롬프트로 임의의 AI 응답을 재실행
- **편집 및 재전송** — 임의의 사용자 메시지를 수정하고 해당 지점부터 리플레이
- **포크** — 임의의 메시지에서 대화를 새 세션으로 분기

**요금 투명성:** 모델 피커가 1K 토큰당 비용을 표시하며, 요금 정보 바가 10K 및 100K 토큰 대화의 추정 비용을 표시합니다.

### 📝 1.8 에셋 타입 인식

선택된 **에셋 타입**은 AI가 프롬프트를 해석하는 방식을 근본적으로 바꿉니다 — 이미지 모델뿐만 아니라 파이프라인의 모든 단계에서. "hospital"이라고 입력하고 서로 다른 에셋 타입을 선택하면 완전히 다른 출력을 얻게 됩니다:

| 타입 | 구도 | 프레이밍 | 기술적 접근 |
|------|------|---------|------------|
| **Photorealistic Image** *(기본값)* | 자연스러운 사진 같은 구도 — 맥락에 맞는 실제 환경 속의 피사체. | 실제 카메라 시점: 아이레벨, 인물은 얕은 심도, 풍경은 와이드. | 사진 용어로 지시(골든아워, 스튜디오 소프트박스, 초점거리 느낌)하고 자연스러운 불완전함 — 피부 질감, 옷감 주름, 풍화 — 을 담습니다. 일러스트 용어나 렌더링 엔진 전문 용어는 절대 사용하지 않습니다. |
| **Game Asset** | 투명 배경에 단일 분리된 오브젝트. 장면, 텍스트, UI 없음. | 정면 또는 아이소메트릭, 오브젝트가 프레임의 70-80%를 차지. | 배경 제거를 위한 깔끔하고 선명한 에지, 일관된 좌상단 조명, 바닥 그림자 없음. 다양한 스케일에서 다른 게임 에셋과 합성하도록 설계. |
| **Character** | 깔끔한 배경에 분리된 풀바디 또는 3/4 바디 피겨. 캐릭터 1명만. | 캐릭터가 세로의 60-75%를 차지, 머리부터 발끝까지, 약간 중심에서 벗어남. | 강력하고 읽기 쉬운 실루엣(실루엣만으로 식별 가능), 개성을 전달하는 표현력 있는 포즈, 명확한 얼굴 특징과 의상 디테일. |
| **Icon** | 단일한 대담하고 인식하기 쉬운 심볼, 넉넉한 패딩으로 중앙 배치. 최대한 심플하게. | 정면 또는 약간의 3/4 기울기, 가장자리에 여유. | 64x64 픽셀에서 명확하게 읽히는 것이 필수. 높은 대비, 최대 3-5색, 대담한 형상, 얇은 선이나 세밀한 디테일 없음. |
| **Marketing Banner** | 극적인 구도의 풀 씬 일러스트레이션. 한쪽에 깔끔한 텍스트 안전 영역 확보 — 렌더링된 텍스트나 타이포그래피 없음. | 와이드 시네마틱 느낌, 장면을 보여주기 위해 카메라를 뒤로. | 풍부한 채도의 색상, 극적인 조명(림 라이트, 볼류메트릭 레이), 피사계 심도. AI가 텍스트를 렌더링하지 않도록 명시적으로 지시되며, 텍스트 안전 영역은 디자인 도구(Figma, Canva 등)에서의 후처리 오버레이를 위해 깨끗하게 유지됩니다. |
| **Environment** | 전경/중경/배경의 깊이 레이어와 리딩 라인이 있는 풀 랜드스케이프. | 와이드 이스태블리싱 숏, 수평선은 상단 또는 하단 1/3 지점. | 대기 원근법(먼 오브젝트는 더 밝고/흐릿), 디테일을 통한 환경 스토리텔링, 분위기를 만드는 조명. |

이것은 모든 단계에서 중요합니다:

- **"Preview Enhanced Prompt" 버튼** — Compose를 클릭하면 AI가 에셋 타입을 사용하여 당신의 간단한 브리프를 상세한 생성 프롬프트로 재구성하며, 사용자의 말을 스타일 가이드라인과 에셋 타입 지시와 결합합니다. 사용자의 명시적 의도는 항상 스타일 기본값보다 우선합니다. 생성 전에 구성된 버전을 검토할 수 있습니다.
- **컨셉 생성** — 여러 옵션을 생성할 때, AI는 에셋 타입의 구조 규칙을 모두 준수하는 N개의 서로 다른 디자인 해석을 만듭니다. Character 옵션은 항상 읽기 쉬운 실루엣을 가지며, Marketing Banner 옵션은 항상 렌더링된 텍스트가 없는 텍스트 안전 영역을 갖습니다.
- **결과** — 동일한 프롬프트에서 서로 다른 에셋 타입의 두 이미지는 전혀 다르게 보입니다. Game Asset의 "warrior"는 중앙에 배치된 단일 캐릭터 스프라이트. Marketing Banner의 "warrior"는 헤드라인 오버레이를 위한 깨끗한 영역이 있는 에픽 전투 장면입니다.

### 📝 1.9 3D 모델 생성(이미지-투-3D)

임의의 2D 이미지에서 완전 텍스처링된 3D 메시를 생성합니다 — Asset Viewer에서 직접 수행합니다. **Game Asset** 또는 **Character** 이미지를 선택하고, **3D Model** 탭을 열어 Generate를 클릭합니다. 결과물은 게임 엔진에 바로 사용할 수 있는 GLB로, 오빗·줌·다운로드가 가능하며 — 수작업 모델링, UV 언래핑, 텍스처 페인팅이 전혀 필요 없습니다.

**최종 결과를 먼저:** ArtSmoker로 생성한 캐릭터를 엔진 대응 FBX로 내보내 순정 Blender에서 연 모습 — LOD 체인(LOD0–LOD3)이 아웃라이너에 그대로 유지되고 텍스처도 바인딩된 상태로, 리깅을 다시 하거나 손으로 고칠 것이 없습니다. 아래에서는 텍스트 프롬프트에서 여기까지 도달하는 방법을 차례로 보여줍니다.

![ArtSmoker FBX를 Blender에서 연 모습 — LOD 그룹 계층과 텍스처가 그대로 유지](docs/images/fbx-in-blender.png)

**생성된 모델 — 오빗, 검사, 다운로드:**

![3D 모델 생성 — 생성된 군인 메시를 인터랙티브 3D 뷰어에서 여러 각도로 표시](docs/images/3d-model-result.png)

한 장의 2D 캐릭터 이미지(왼쪽, PNG 탭)가 브라우저에서 자유롭게 회전할 수 있는 완전 텍스처링된 3D 메시가 됩니다. **3D Model** 탭은 이제 각 에셋 생성에 사용된 정확한 **모델 및 도구**(지오메트리 모델, 텍스처링 백엔드, 출력 타입, 인스턴스, 생성 파라미터)도 나열하며 — 에셋 메타데이터에 저장되어 완전한 출처 추적을 제공합니다.

**생성하기** — Asset Viewer의 3D Model 탭: 배포된 파이프라인 엔드포인트, 품질 등급(예상 시간·비용 포함), 고급 파라미터를 선택합니다. 라이선스 패널에 각 파이프라인의 조건이 표시되고, **소스 개선**이 GPU 시간을 쓰기 전에 이미지를 비전 검사합니다.

![3D 모델 생성 — Asset Viewer에서의 설정 및 생성](docs/images/3d-model-generation.png)

**소스 개선** — 생성 전에 ArtSmoker가 피사체의 실루엣을 측정해 잘림(여기서는 하단 가장자리)을 감지하고, 확장 값과 AI가 작성한 아웃페인트 프롬프트를 제안합니다 — 확장, 채우기 또는 그대로 사용할 수 있습니다.

![3D 소스 검토 — 자동 잘림 감지와 제안된 확장 값](docs/images/3d-source-review.png)

**두 가지 파이프라인 — 직접 선택하세요.** ArtSmoker는 이미지를 텍스처링된 3D 모델로 변환하는 두 가지 방법을 제공합니다. Custom Models에서 둘 중 하나(또는 둘 다)를 배포하세요. 둘 다 활성화되어 있으면, Asset Viewer에서 생성할 때마다 선택할 수 있으며 — 각각 추정 비용, 시간, 라이선스를 표시하여 정보에 입각해 결정할 수 있습니다:

| 파이프라인 | 작동 방식 | 라이선스 | 상업적 사용 | 적합한 용도 |
|------------|-----------|----------|-------------|-------------|
| **TripoSG + 텍스처 백엔드** | TripoSG가 메시를 생성하고, 선택한 텍스처 백엔드(TRELLIS.2 / Hunyuan3D-Paint)가 페인팅 | 백엔드별(아래) | 백엔드별 | 지오메트리 + 특정 텍스처러 조합 |
| **TRELLIS.2 (Full)** | 하나의 모델이 지오메트리와 PBR 텍스처(SLAT)를 **모두** 생성 | MIT | ✅ 가능 — "Built with DINOv3" 출처 표기 | 프로덕션, 상업용 에셋, 가장 간단한 경로 |

**3D 배리언트** — 이미지 버전마다 여러 3D 결과물을 보관(여기서는 TripoSG와 TRELLIS.2 전체 파이프라인)하고 언제든 전환하거나 기본값으로 설정할 수 있습니다. 각 배리언트는 생성에 사용된 정확한 모델과 도구를 기록합니다.

![3D 배리언트 — TripoSG와 TRELLIS.2 결과물 비교 및 전체 이력](docs/images/3d-model-variants.png)

**TripoSG 파이프라인 작동 방식:**

1. **지오메트리 추출** — 정류 플로우 트랜스포머(TripoSG, 15억 파라미터, MIT 라이선스)가 부호 거리장(SDF) 표현을 사용하여 단일 2D 이미지를 고충실도 3D 메시로 변환합니다. 메시 밀도는 품질 프리셋에 따라 조정되어(최고 옥트리 해상도에서 최대 약 100만 면) 얼굴과 장비의 선명한 디테일을 얻습니다.
2. **텍스처링** — 메시는 **배포 시 선택하는 텍스처 백엔드**로 페인팅됩니다(기본값 **TRELLIS.2**, Microsoft, MIT — 4096² 아틀라스에서 완전한 PBR 머티리얼을 생성하는 SLAT/복셀 조건부 텍스처러).
3. **PBR 출력** — PBR 맵이 내장된 GLB로 내보내져, 모든 최신 엔진에서 물리 기반 렌더링에 바로 사용할 수 있습니다.

**TRELLIS.2 (Full)** 파이프라인은 동일한 작업을 단일 모델에서 엔드투엔드로 수행합니다 — 별도의 텍스처링 단계가 없습니다.

**라이선스를 명확하게 — 배포 시 그리고 생성 시에도.** 배포 가능한 각 옵션은 배포 대화상자에서 **전체 라이선스 및 의존성 내역**을 표시합니다 — 가져오는 모든 모델, 해당 모델의 라이선스, 상업적 사용 가능 여부 또는 게이팅 여부까지 — 그리고 배포 전에 읽고 동의해야 합니다. 생성 시에는 Asset Viewer가 라이선스를 다시 표시하고 *"`<date>`에 배포 시 동의함"* 을 확인해 줍니다(추가 클릭 불필요):

| 텍스처 백엔드 | 라이선스 | 상업적 사용 | 적합한 용도 |
|---------------|----------|-------------|-------------|
| **TRELLIS.2** *(기본값)* | MIT | ✅ 가능 — 제품에 "Built with DINOv3" 출처 표기 필요 | 프로덕션, 상업용 에셋, 최고 품질 |
| **Hunyuan3D-Paint** | Tencent Community | ❌ 비상업용 | 연구/비상업용, 뛰어난 얼굴 표현 |

배경 제거(컷아웃 단계)는 기본적으로 **BiRefNet(MIT)** 을 사용합니다 — 완전히 상업적 사용 가능 — 비상업용 대안(RMBG)은 공개된 옵트인으로 제공됩니다. ArtSmoker는 제한된 의존성을 절대 조용히 가져오지 않습니다: 게이팅되거나 비상업용인 모든 것은 이름이 명시되고, 배지가 표시되며, 명시적 동의 뒤에 게이팅됩니다.

**출력:** PBR 텍스처가 내장된 표준 GLB — Unity, Unreal Engine, Blender 등 다른 게임 엔진에 직접 임포트됩니다. 인터랙티브 3D 뷰어는 즉각적인 검사를 위해 오빗·줌·팬을 지원하며, **3D Model** 탭은 완전한 출처 추적을 위해 사용된 정확한 모델 및 도구(지오메트리 모델, 텍스처링 백엔드, 의존성, 인스턴스, 파라미터)를 나열합니다.

**인프라:** 두 파이프라인 모두 동일한 원클릭 Custom Models 플로우로 배포하며, 배포 시 피커가 각 옵션의 라이선스, 의존성 표, 인스턴스 베이스라인, 추정 비용/시간을 표시합니다. 전체 TRELLIS.2 파이프라인의 적정 베이스라인은 **`ml.g6e.xlarge`**(~$2.61/시간, 측정된 피크는 ~6.5 GB VRAM + ~22 GB 호스트 RAM — GPU가 아니라 호스트 RAM이 제약 조건)입니다. 더 큰 `g6e` 크기는 RAM 여유 확보용 업셀로 제공됩니다. 엔드포인트는 유휴 시 제로로 스케일됩니다 — 작업 사이 비용 $0. 첫 콜드 스타트에서 CUDA 익스텐션을 한 번 빌드한 후(그다음 빠른 재시작을 위해 S3에 캐시됩니다). 게이팅된 모델을 배포하기 전에, 대화상자가 **모델이 가져오는 모든 repo에 대한 HuggingFace 접근 권한을 사전 점검**하고 repo별로 ✓/✗와 정확한 다음 단계를 표시합니다 — 따라서 콜드 스타트가 몇 분간 진행된 뒤에야 누락된 라이선스 동의를 발견하는 일이 절대 없습니다.

> **GLB 보기:** 텍스처는 파일을 작게 유지하기 위해 WebP(`EXT_texture_webp`)로 인코딩됩니다 — 인앱 뷰어, Blender 4.x, three.js, 최신 Unity/Unreal 임포터에서 완벽하게 렌더링됩니다. macOS Preview/QuickLook은 WebP-in-glTF를 지원하지 않아 모델이 검게 표시되므로, 인앱 뷰어나 최신 glTF 도구를 사용하세요.

| 지표 | 값 |
|------|-----|
| 메시 품질 | 최대 약 100만 면, 완전한 버텍스 노멀 |
| 텍스처 해상도 | 4096² PBR 아틀라스(베이스 컬러 + 메탈릭-러프니스 + 알파) |
| 라이선스 | 기본적으로 상업적으로 안전(TRELLIS.2 MIT + BiRefNet MIT); 비상업용 백엔드는 완전한 공개와 함께 제공 |
| 지원 에셋 타입 | Game Asset, Character |

### 📝 1.9.1 엔진 대응 내보내기(GLB · FBX · USD)

![3D 모델 뷰어 — 배리언트별 도구와 엔진 대응 FBX/USD 내보내기 옵션](docs/images/3d-model-viewer-export.png)

생성된 모든 3D 모델은 Asset Viewer의 3D 탭에서 곧바로 **사용할 게임 엔진에 맞게 준비된 상태로** 내보낼 수 있습니다:

- **타깃 엔진** — Generic(glTF, Y-업), Unreal Engine(Z-업), Unity, Godot, Maya, 3ds Max 중에서 선택합니다. FBX와 USD 내보내기는 해당 엔진에 맞는 업/포워드 축으로 방향이 맞춰져 있어, 모델이 똑바로 선 상태로 임포트됩니다 — 수동 회전 보정이 필요 없습니다.
- **선택적 준비 작업, 원하는 대로** (각각 독립적인 드롭다운 — 아무것도 강제되지 않습니다):
  - **텍스처 패킹** — 엔진별 텍스처 세트: Unreal **ORM**(AO/러프니스/메탈릭), Unity **메탈릭 + 알파 채널의 스무스니스**, Unity **HDRP 마스크 맵**. 선택하면 내보내기가 모델과 `textures/` 폴더를 포함한 ZIP이 됩니다.
  - **LOD** — 데시메이션된 **LOD0–LOD3 체인**(100/50/20/5%)과 Unreal이 자동 임포트하는 실제 FBX LOD 그룹이 포함되며, `_LOD0…_LOD3` 네이밍은 Unity의 컨벤션으로도 그대로 통합니다.
  - **콜리전** — 볼록 껍질(convex hull) 또는 **CoACD 볼록 분해**를 엔진 컨벤션에 따라 명명해 제공합니다(Unreal 자동 임포트용 `UCX_*`, Godot용 `-convcolonly` 접미사).
  - **라이트맵 UV2** — 베이크드 라이팅을 위한 스마트 프로젝션된 두 번째 UV 채널.
- **2단계 플로우** — 아직 존재하지 않는 조합에는 버튼이 **Generate FBX/USD/GLB**로 표시되고, 클릭하면 서버 측에서 변환됩니다(상태 표시줄이 진행 상황을 알려줍니다 — 큰 모델은 1~2분 걸릴 수 있습니다). 한 번 생성되면 버튼이 ✓와 함께 **Download**로 바뀌어 즉시 전달됩니다. 서로 다른 모든 조합이 캐시되므로 — 어떤 것도 다시 생성되지 않습니다.
- **다운로드 준비 완료 칩** — 3D 탭이 현재 버전에 대해 이미 생성한 모든 조합을 나열하며, 클릭 한 번으로 그중 어느 것이든 다시 다운로드할 수 있습니다.
- **원본 GLB는 신성불가침** — "Download GLB (original)"은 항상 생성 파이프라인의 손대지 않은, 바이트 단위로 동일한 출력을 반환합니다. 가공된 내보내기(LOD/콜리전이 포함된 가공 GLB 포함)는 그 옆에 별도의 이름을 가진 파일로 제공됩니다.
- **설정 제로** — 변환은 관리형 헤드리스 Blender를 통해 서버 측에서 실행됩니다: 기존 설치가 있으면 재사용하고, 없으면 첫 사용 시 포터블 사본이 자동으로 다운로드됩니다(버전 및 업데이트는 Model Settings → Maintenance 탭 참조). 최종 사용자는 아무것도 설치하지 않습니다.

### 📝 1.9.2 AI 생성 3D에서 기대할 수 있는 것 — 솔직한 가이드

이미지-투-3D는 아직 젊은 기술이며, 오늘날 최고의 모델들(ArtSmoker가 실행하는 모델 포함)이 실제로 무엇을 제공하고 무엇을 제공하지 못하는지 알아둘 가치가 있습니다. 출력물은 **스캔된 물체 스타일의 조밀한 메시**입니다: 최대 약 100만 개의 비정형 삼각형과 베이크된 PBR 텍스처. 가까이에서 보면 특유의 울퉁불퉁한 표면 질감이 눈에 띄고, 얇은 형상(머리카락 가닥, 스트랩, 천의 술 장식)은 AI 지오메트리가 가장 취약한 부분입니다. **깨끗한 쿼드 토폴로지도, 애니메이션 친화적인 에지 루프도, 리그도 없습니다** — 이는 특정 도구만의 한계가 아니라 업계 전반에 걸친 현재 기술 수준입니다.

**이 에셋들이 빛나는 곳 — 그리고 아티스트가 필요한 곳:**

| 사용 사례 | 바로 사용 가능? |
|-----------|-----------------|
| 소품, 환경 클러터, 세트 드레싱 | ✅ 예 — 그대로 사용 가능 |
| 배경/중거리 캐릭터, 군중 | ✅ 예 — 거리가 멀어지면 표면 노이즈가 사라집니다; LOD 체인을 사용하세요 |
| 프로토타이핑, 블록아웃, 프리비즈, 피치 데모 | ✅ 예 — 단연 가장 강력한 사용 사례 |
| 모바일/스타일라이즈드 게임 | ✅ 대체로 — 데시메이션된 LOD가 도움이 됩니다 |
| 히어로 캐릭터, 클로즈업, 애니메이션 캐릭터 | ⚠️ 출발점 — 아티스트의 리토폴로지, 정리, 리깅을 계획하세요 |

ArtSmoker가 원시 메시 위에 더하는 가치는 모든 것이 **사용할 엔진에 맞게 올바르게 패키징되어** 도착한다는 점입니다 — 타깃별 올바른 업 축, LOD 체인, 콜리전 프록시, 엔진별 텍스처 패킹 — 그래서 남은 작업은 배관 작업이 아니라 창작입니다.

**Blender(또는 다른 DCC 도구)에서 내보내기를 검사하시나요? 두 가지가 이상하게 보일 텐데 — 둘 다 정상입니다:**

- **LOD를 포함해 생성했나요?** 파일에는 모델의 **겹쳐진 사본 4개**(LOD0–3)가 들어 있습니다. 함께 보면 깜빡거리고(z-파이팅) 지저분해 보입니다 — Outliner에서 LOD1–3을 숨기고 LOD0만으로 품질을 판단하세요. 게임 엔진은 한 번에 정확히 하나의 LOD만 표시하므로, 엔진 안에서는 이런 일이 절대 발생하지 않습니다.
- **콜리전을 포함해 생성했나요?** 흰색의 각진 `UCX_*` 메시 껍데기가 **모델을 감싸고** 있습니다 — 이는 물리 프록시이지 에셋이 아닙니다. 해당 오브젝트들을 숨기면 안쪽의 텍스처링된 모델이 보입니다. 엔진은 이를 자동으로 보이지 않는 콜리전으로 임포트합니다.

### 📝 1.9.3 모델을 상업적으로 사용하기 — 누구에게, 어떻게 지불하나

어떤 모델의 출력물이 마음에 들어 상업적으로 사용하고 싶다면, 그 경로는 **제작자가 어떻게 수익화하는지**에 따라 달라집니다. ArtSmoker는 배포 시점에 모든 모델의 라이선스를 보여 줍니다. 이 절은 "그다음엔 뭘 해야 하지?"에 답하는 안내서입니다. *(2026년 8월에 벤더 사이트와 HuggingFace 라이선스 파일을 대조해 확인했습니다 — 라이선스는 빠르게 바뀌므로 항상 벤더의 최신 약관을 확인하세요. 참고용 정보일 뿐입니다 — [면책 조항](#disclaimer)을 참조하세요.)*

마주치게 될 네 가지 패턴:

1. **이미 당신의 것(Apache-2.0 / MIT)** — 상업적 사용이 무료로 포함되어 있습니다. 구매할 라이선스 상품 자체가 없으며, 제작자는 대신 자체 호스팅 API로 수익을 냅니다. 유일한 의무는 고지/저작자 표시 준수입니다.
2. **규모가 커지기 전까지 무료(커뮤니티 라이선스)** — 상업적 사용이 **일정 기준(매출 또는 월간 활성 사용자 수) 이하에서** 포함됩니다. 기준을 넘으면 라이선스 자체가 벤더에게 엔터프라이즈 그랜트를 요청하라고 명시합니다 — 스토어 구매가 아니라 영업 상담입니다.
3. **라이선스를 구매하고 가중치는 그대로** — HuggingFace 가중치는 비상업용이지만, 제작자가 별도의 **셀프 호스팅 상업 라이선스**를 판매합니다. 라이선스를 보유하는 순간 *이미 배포해 둔 바로 그 가중치*가 상업적 사용에 합법이 됩니다 — ArtSmoker에서는 기술적으로 아무것도 바뀌지 않습니다.
4. **게이트가 곧 페이월** — HuggingFace 리포지토리 자체가 게이트되어 있으며, 벤더와의 상업 계약이 당신의 HF 계정 접근을 열어 줍니다. 그다음에는 ArtSmoker의 HuggingFace 토큰 + 게이트 리포 사전 점검 플로우가 그대로 작동합니다.

| 제작자 / 모델 | 패턴 | 상업적 셀프 호스팅을 위한 다음 단계 |
|---|---|---|
| **Alibaba** — Qwen-Image, Qwen-Image-Edit | 1 | 구매할 것 없음(Apache-2.0). 라이선스 고지문을 유지하세요. |
| **Microsoft** — TRELLIS.2 · **VAST** — TripoSG | 1 | 구매할 것 없음(MIT). 참고: 업스트림 의존성(예: Meta DINOv3)에는 자체 게이트/약관이 있습니다. |
| **Black Forest Labs** — FLUX.2 [klein] 4B | 1 | 구매할 것 없음 — Apache-2.0, 상업적 사용 무료. |
| **Stability AI** — SD 3.5(셀프 호스팅) | 2 | **연간 총매출 $1M 미만**이면 상업적 사용 포함 무료(HF 게이트 동의가 *곧* 라이선스입니다). 초과 시 라이선스는 **자동 종료**됩니다 — stability.ai/enterprise 에서 Enterprise 라이선스를 요청하세요. **"Powered by Stability AI" 저작자 표시는 모든 티어에서 필수입니다.** |
| **Tencent** — HunyuanImage 3.0 / Hunyuan3D | 2 | 기준 이하에서는 상업적 사용 포함 무료 — **기준이 모델별**임에 유의하세요: HunyuanImage 3.0 = 100M MAU, **Hunyuan3D-2.1 = 단 1M MAU**(초과 시 hunyuan3d@tencent.com 으로 이메일). **EU, 영국, 대한민국에서는 규모와 무관하게 그랜트가 아예 제공되지 않습니다.** |
| **Black Forest Labs** — FLUX.1/.2 [dev], Kontext | 3 | **FLUX Commercial Weights License**를 구매하세요(dashboard.bfl.ai/licensing 에서 셀프 서비스; 티어는 이미지 볼륨 상한이 있는 구독제). 사용하던 동일한 HF 가중치를 계속 사용합니다. 의무 사항에 유의하세요: 사용량 보고, 출력 필터링, **모델을 API로 노출/재판매 금지**; 새 모델 버전은 Enterprise 외에는 자동으로 커버되지 **않습니다**. |
| **Bria** — FIBO, RMBG-2.0 | 4 | HF 게이트는 **비상업용** 접근을 즉시 부여합니다; 상업적 셀프 호스팅에는 **Bria와의 유료 계약**이 필요합니다(각 모델 카드 / bria.ai 에 구매 양식 링크). 무료 상업 기준선은 존재하지 않습니다. 승인되면 이전과 똑같이 ArtSmoker를 통해 배포하면 됩니다. |

**ArtSmoker와는 어떻게 맞물리나:** 라이선스 조달로 기술적으로 바뀌는 것은 거의 없습니다. 패턴 1–3에서는 배포하는 가중치가 계약 전후로 완전히 동일하며, 바뀌는 것은 당신이 보유한 계약뿐입니다(라이선스 기록을 보관하세요; ArtSmoker의 배포 대화상자는 *가중치* 라이선스에 대한 동의를 기록하지만, 상업 그랜트는 벤더와 당신을 직접 구속합니다). 패턴 4에서는 벤더가 당신의 HuggingFace 계정을 승인하는 순간 ArtSmoker의 기존 게이트 리포 접근 점검이 초록불로 바뀌고 배포가 정상적으로 진행됩니다. 벤더가 새 모델 버전을 출시하면 보유한 그랜트가 그 버전을 커버하는지 다시 확인하세요(Stability는 자동으로 커버합니다; BFL은 Enterprise 외에는 일반적으로 커버하지 않습니다; Tencent는 버전마다 새 라이선스 문서를 발행합니다).

<a id="get-started"></a>

## 📌 2. 사전 요구사항

- **Python 3.11+**(3.12, 3.13, 3.14 모두 작동)
- 유효한 인증 정보로 구성된 **AWS CLI**
- Bedrock 접근을 위한 **IAM 권한**(아래 참조)

### 📝 2.1 AWS 인증 정보

ArtSmoker는 [boto3의 표준 인증 정보 해석](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials)을 사용하므로 다음 중 어떤 방법이든 작동합니다:

| 방법 | 최적 용도 | 방식 |
|------|----------|------|
| **환경 변수** | CI/CD, 컨테이너 | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` |
| **공유 인증 정보 파일** | 로컬 개발 | `~/.aws/credentials`(`aws configure` 사용) |
| **명명된 프로필** | 다중 계정 | `ARTSMOKER_AWS_PROFILE=myprofile` 또는 `AWS_PROFILE` 설정 |
| **AWS SSO** | 엔터프라이즈 SSO | `aws configure sso` |
| **IAM Instance Profile** | EC2, ECS, App Runner | 인스턴스에 IAM 역할 연결 — 머신에 인증 정보 불필요 |
| **ECS Task Role** | ECS/Fargate 컨테이너 | 필요한 권한이 있는 태스크 실행 역할 할당 |

인증 정보가 작동하는지 빠른 확인:

```bash
aws sts get-caller-identity
```

> [!NOTE]
> EC2 및 기타 AWS 컴퓨팅 서비스에서는 명시적 인증 정보를 구성할 필요가 없습니다. 필요한 권한이 있는 [IAM Instance Profile](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html)을 연결하면 boto3가 인스턴스 메타데이터 서비스를 통해 자동으로 감지합니다.

### 📝 2.1.1 Bedrock 접근 확인

인증 정보가 작동함을 확인(`sts:GetCallerIdentity`)하는 것은 신원만 검증할 뿐 — Bedrock 권한이 있는지는 확인하지 않습니다. ArtSmoker는 여러 Bedrock API를 사용하므로, 간단한 목록 테스트만으로는 충분하지 않습니다. 가장 신뢰할 수 있는 확인 방법:

```bash
# Test 1: Can you list models? (requires bedrock:ListFoundationModels)
aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[0].modelId" --output text

# Test 2: Can you invoke an image model? (requires bedrock:InvokeModel)
aws bedrock-runtime invoke-model --region us-west-2 \
  --model-id stability.sd3-5-large-v1:0 \
  --content-type application/json --accept application/json \
  --body '{"prompt":"test","aspect_ratio":"1:1"}' \
  /dev/null 2>&1 && echo "InvokeModel: OK" || echo "InvokeModel: FAILED"

# Test 3: Can you use the Converse API? (authorizes via bedrock:InvokeModel)
# (Substitute any Claude model ID you have access to — e.g. the current Sonnet
#  inference profile from Test 1's list; the exact version rolls over time.)
aws bedrock-runtime converse --region us-west-2 \
  --model-id us.anthropic.claude-sonnet-5 \
  --messages '[{"role":"user","content":[{"text":"hi"}]}]' \
  --inference-config '{"maxTokens":1}' \
  --query "output.message.content[0].text" --output text 2>&1 && echo "Converse: OK" || echo "Converse: FAILED"

# Test 4: Can you list custom models? (requires bedrock:ListCustomModels)
aws bedrock list-custom-models --region us-east-1 \
  --query "modelSummaries[0].modelName" --output text 2>&1 && echo "ListCustomModels: OK" || echo "ListCustomModels: no custom models (or permission denied)"
```

Test 1-3이 통과하면 핵심 권한이 설정된 것입니다. Test 4는 커스텀 모델 검색에만 필요합니다. Test 1은 통과하지만 Test 2-3이 실패하면, IAM 정책이 목록 조회는 허용하지만 호출은 허용하지 않는 것입니다 — 아래 권한 표를 사용하여 업데이트하세요.

### 📝 2.2 IAM 권한

IAM 사용자, 역할, 인스턴스 프로필에는 다음 권한이 필요합니다:

| 권한 | 용도 |
|------|------|
| `bedrock:InvokeModel` | 이미지 생성, 이미지 편집, 후처리(모든 이미지 모델) |
| `bedrock:InvokeModelWithResponseStream` | 스트리밍 LLM 응답(Chat Studio) — ConverseStream API는 이 액션으로 인가됩니다. 비스트리밍 Converse API(프롬프트 정제, 스타일 분석, 컨셉 생성)는 `bedrock:InvokeModel`로 인가됩니다 — 별도의 `bedrock:Converse` 액션은 존재하지 않습니다 |
| `bedrock:InvokeModelWithBidirectionalStream` | 음성 전사(선택 — 없어도 앱 작동) |
| `bedrock:StartAsyncInvoke` | 동영상 생성(비동기 호출) |
| `bedrock:GetAsyncInvoke` | 동영상 생성 작업 상태 폴링 |
| `bedrock:ListAsyncInvokes` | 동영상 생성 작업 목록 조회 |
| `bedrock:ListFoundationModels` | 기반 모델 검색(Sync from AWS) |
| `bedrock:ListCustomModels` | 계정 내 파인튜닝된 커스텀 모델 검색 |
| `bedrock:ListImportedModels` | 계정 내 임포트된 모델 검색 |
| `bedrock:GetCustomModel` | 커스텀 모델 세부정보 읽기(베이스 모델, 상태) |
| `bedrock:GetImportedModel` | 임포트된 모델 세부정보 읽기(아키텍처, 상태) |
| `bedrock:ListProvisionedModelThroughputs` | 프로비저닝된 처리량으로 호출 가능한 커스텀 모델 찾기 |
| `bedrock:ListCustomModelDeployments` | 온디맨드 배포가 있는 커스텀 모델 찾기 |
| `bedrock:CreateInference` *(또는 정책 `AmazonBedrockMantleInferenceAccess`)* | **Amazon Bedrock Mantle** — Mantle 엔드포인트를 통해서만 도달 가능한 프런티어 모델(OpenAI GPT‑5.x, Claude Mythos, GLM, Grok, Qwen, Gemma…). 없으면 해당 모델에만 영향을 미치며, Converse를 통한 Claude는 계속 작동합니다. |
| `account:ListRegions` | Sync 중 계정의 **활성화된** 리전만 스캔(빠르고, 옵트인 리전에서 오류 없음). 선택 — 없으면 모든 리전 스캔으로 폴백. |
| `account:GetRegionOptStatus` | 리전별 옵트인 상태 읽기(`account:ListRegions`의 동반 권한). 선택. |
| `s3:CreateBucket` | 동영상 저장용 S3 버킷 생성(선택, UI 경유) |
| `s3:PutObject` / `s3:GetObject` / `s3:DeleteObject` / `s3:ListBucket` | 동영상 출력 저장 및 검색 |
| `aws-marketplace:Subscribe` | 서드파티 모델(서드파티 Mantle 모델 포함) 최초 사용 시 자동 구독 |
| `aws-marketplace:ViewSubscriptions` | 기존 모델 구독 확인 |
| `sts:GetCallerIdentity` | 시작 시 인증 정보 검증; 로컬 서명 Mantle 베어러 토큰의 기반이기도 함 |
| `pricing:GetProducts` | Sync from AWS 중 모델 요금 조회(선택) |
| `sagemaker:*` | Amazon SageMaker의 셀프 호스팅 커스텀 모델(선택 — Custom Models 사용 시에만) |
| Custom Models 런타임 세트: `application-autoscaling:*`(타깃/정책), `cloudwatch:PutMetricAlarm`/`DeleteAlarms`/`DescribeAlarms`, `logs:`(읽기+보존 설정), `servicequotas:GetServiceQuota`/`RequestServiceQuotaIncrease`, `ecr:DescribeRepositories`, `iam:CreateServiceLinkedRole`(최초 오토스케일링 시 1회) | 엔드포인트 스케일-투-제로/프롬-제로, 백로그 알람, 준비 상태 스캔, GPU 쿼터 확인, DLC 이미지 결정(선택 — Custom Models 전용; 전체 목록은 아래 범위 지정 정책 참조) |
| `iam:PassRole` | Amazon SageMaker가 역할을 사용하도록 허용(선택 — Custom Models 전용) |
| `iam:CreateRole` / `iam:AttachRolePolicy` | 최초 배포 시 Amazon SageMaker 실행 역할 자동 생성(선택 — Custom Models 전용) |
| `iam:GetRole` / `iam:UpdateAssumeRolePolicy` | Amazon SageMaker 신뢰를 위해 기존 역할 자동 구성(선택) |
| `secretsmanager:CreateSecret` / `secretsmanager:GetSecretValue` / `secretsmanager:DeleteSecret` | 게이팅된 모델의 HuggingFace 토큰 암호화 저장(선택 — 티어다운 시 자동 정리) |

**가장 빠른 설정**(관리형 정책 — 가장 넓은 접근):

```bash
# Option A: Attach managed policies to your IAM user (simplest for local development)
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# Amazon Bedrock Mantle endpoint — needed for frontier models (OpenAI GPT-5.x,
# Claude Mythos, GLM, Grok, etc.). Skip only if you won't use Mantle-only models.
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockMantleInferenceAccess

# Add S3 access for video storage
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

**범위 지정 설정**(더 엄격한 권한 — 프로덕션 권장):

```bash
# Create a scoped IAM policy with only the permissions ArtSmoker needs
aws iam create-policy --policy-name ArtSmokerAccess --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Bedrock",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:InvokeModelWithBidirectionalStream",
        "bedrock:StartAsyncInvoke",
        "bedrock:GetAsyncInvoke",
        "bedrock:ListAsyncInvokes",
        "bedrock:ListFoundationModels",
        "bedrock:ListCustomModels",
        "bedrock:ListImportedModels",
        "bedrock:GetCustomModel",
        "bedrock:GetImportedModel",
        "bedrock:ListProvisionedModelThroughputs",
        "bedrock:ListCustomModelDeployments"
      ],
      "Resource": "*"
    },
    {
      "Sid": "BedrockMantleInference",
      "Effect": "Allow",
      "Action": ["bedrock:CreateInference", "bedrock:GetInference", "bedrock:ListInferences", "bedrock:GetInferenceProfile"],
      "Resource": "*"
    },
    {
      "Sid": "EnabledRegions",
      "Effect": "Allow",
      "Action": ["account:ListRegions", "account:GetRegionOptStatus"],
      "Resource": "*"
    },
    {
      "Sid": "S3VideoStorage",
      "Effect": "Allow",
      "Action": ["s3:CreateBucket", "s3:PutObject", "s3:GetObject", "s3:ListBucket", "s3:DeleteObject", "s3:HeadBucket", "s3:GetLifecycleConfiguration", "s3:PutLifecycleConfiguration"],
      "Resource": ["arn:aws:s3:::artsmoker-*", "arn:aws:s3:::artsmoker-*/*"]
    },
    {
      "Sid": "Marketplace",
      "Effect": "Allow",
      "Action": ["aws-marketplace:Subscribe", "aws-marketplace:ViewSubscriptions"],
      "Resource": "*"
    },
    {
      "Sid": "Utility",
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity", "pricing:GetProducts", "s3:ListAllMyBuckets"],
      "Resource": "*"
    },
    {
      "Sid": "SageMakerCustomModels",
      "Effect": "Allow",
      "Action": [
        "sagemaker:CreateModel", "sagemaker:CreateEndpointConfig", "sagemaker:CreateEndpoint",
        "sagemaker:UpdateEndpoint", "sagemaker:DeleteModel", "sagemaker:DeleteEndpointConfig",
        "sagemaker:DeleteEndpoint", "sagemaker:DescribeEndpoint", "sagemaker:DescribeEndpointConfig",
        "sagemaker:InvokeEndpoint", "sagemaker:InvokeEndpointAsync"
      ],
      "Resource": "arn:aws:sagemaker:*:*:*artsmoker*"
    },
    {
      "Sid": "SageMakerList",
      "Effect": "Allow",
      "Action": ["sagemaker:ListModels", "sagemaker:ListEndpointConfigs"],
      "Resource": "*"
    },
    {
      "Sid": "CustomModelsRuntime",
      "Effect": "Allow",
      "Action": [
        "application-autoscaling:RegisterScalableTarget", "application-autoscaling:DeregisterScalableTarget",
        "application-autoscaling:DescribeScalableTargets", "application-autoscaling:PutScalingPolicy",
        "application-autoscaling:DeleteScalingPolicy", "application-autoscaling:DescribeScalingPolicies",
        "cloudwatch:PutMetricAlarm", "cloudwatch:DeleteAlarms", "cloudwatch:DescribeAlarms",
        "logs:DescribeLogStreams", "logs:FilterLogEvents", "logs:GetLogEvents", "logs:PutRetentionPolicy",
        "servicequotas:GetServiceQuota", "servicequotas:RequestServiceQuotaIncrease",
        "ecr:DescribeRepositories"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AutoScalingServiceLinkedRole",
      "Effect": "Allow",
      "Action": "iam:CreateServiceLinkedRole",
      "Resource": "arn:aws:iam::*:role/aws-service-role/sagemaker.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_SageMakerEndpoint",
      "Condition": {"StringLike": {"iam:AWSServiceName": "sagemaker.application-autoscaling.amazonaws.com"}}
    },
    {
      "Sid": "SageMakerRoleManagement",
      "Effect": "Allow",
      "Action": ["iam:CreateRole", "iam:AttachRolePolicy", "iam:PutRolePolicy", "iam:GetRole", "iam:UpdateAssumeRolePolicy", "iam:PassRole"],
      "Resource": ["arn:aws:iam::*:role/ArtSmoker*"]
    },
    {
      "Sid": "SecretsManagerHFTokens",
      "Effect": "Allow",
      "Action": ["secretsmanager:CreateSecret", "secretsmanager:UpdateSecret", "secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret", "secretsmanager:DeleteSecret"],
      "Resource": "arn:aws:secretsmanager:*:*:secret:artsmoker/*"
    }
  ]
}'

# Attach to your IAM user (replace YOUR_ACCOUNT_ID and YOUR_USERNAME)
aws iam attach-user-policy --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/ArtSmokerAccess
```

> [!NOTE]
> **계정에 맞게 조정할 두 가지:** (1) S3 문(statement)은 `artsmoker-*` 이름의 버킷으로 범위가 지정되어 있습니다 — 다른 이름의 버킷을 사용한다면(Video Settings에서 기존 버킷을 자유롭게 선택 가능) 해당 `Resource`를 그 버킷의 ARN으로 넓히세요. (2) ArtSmoker가 생성하는 SageMaker 리소스는 `artsmoker-*`로 명명되므로 범위 지정된 `Resource`가 그대로 작동합니다. `sagemaker:List*` 액션은 리소스 범위 지정을 지원하지 않아 별도의 문으로 분리되어 있습니다.
>
> **실행 중에 권한이 부족하다면?** ArtSmoker는 모든 AWS 호출을 모니터링합니다. 호출이 거부되면 실패한 정확한 `service:Operation`을 로그에 기록하고, 추가해야 할 액션을 명시한 지속적인 인앱 알림을 표시합니다 — 권한 공백이 조용히 실패하는 일은 없습니다.

> [!TIP]
> **EC2/ECS/App Runner의 경우** — 사용자에 연결하는 대신 IAM 역할을 생성하세요. 전체 역할 생성 명령은 [EC2 배포](#43-ec2--cloud-deployment) 섹션을 참조하세요. 액세스 키가 필요 없습니다 — boto3가 인스턴스 메타데이터 서비스에서 역할을 자동으로 검색합니다.

> [!NOTE]
> Bedrock 모델은 모든 상업용 AWS 리전에서 기본적으로 사용 가능합니다 — 수동 활성화 단계가 필요 없습니다. 서드파티 모델(Anthropic, Stability AI)을 처음 호출할 때, AWS가 백그라운드에서 마켓플레이스 구독을 자동으로 시작합니다(위의 `aws-marketplace` 권한 필요). Anthropic 모델은 일회성 [First Time Use 양식](https://console.aws.amazon.com/bedrock/home#/modelaccess) 작성이 필요합니다.

### 📝 2.3 선택: SVG 변환 도구

SVG 변환은 외부 CLI 도구(Python 패키지가 아님)를 사용합니다. 이 도구가 없으면 SVG 출력이 Pillow 기반 래스터-인-SVG 래퍼로 폴백됩니다 — 작동은 하지만 진정한 벡터 출력은 아닙니다.

| 도구 | 목적 | macOS | Linux (Debian/Ubuntu) | Windows |
|------|------|-------|-----------------------|---------|
| **vtracer** | 기본 SVG(컬러 벡터 트레이싱) | `pip install vtracer` or `cargo install vtracer` | `pip install vtracer` or `cargo install vtracer` | `pip install vtracer` or `cargo install vtracer` or [pre-built binaries](https://github.com/visioncortex/vtracer/releases) |
| **potrace** | 폴백 SVG(모노크롬 트레이싱) | `brew install potrace` | `sudo apt install potrace` | [potrace.sourceforge.net](http://potrace.sourceforge.net/#downloading)에서 다운로드 |

설치 확인:

```bash
# Check SVG conversion tools
which vtracer && echo "vtracer: OK" || echo "vtracer: not installed (optional)"
which potrace && echo "potrace: OK" || echo "potrace: not installed (optional)"
```

### 📝 2.4 선택: 동영상 썸네일 및 메타데이터 도구

Video Studio는 Amazon Nova Reel과 Luma AI Ray를 통해 MP4 동영상을 생성합니다. 썸네일(첫 프레임을 JPEG로)과 동영상 메타데이터(길이, 해상도, FPS)를 추출하려면, ArtSmoker 백엔드를 실행하는 머신에 **ffmpeg**와 **ffprobe**가 설치되어 있어야 합니다.

ffmpeg 없이:
- 동영상은 여전히 올바르게 생성되고 재생됩니다(S3에서 스트리밍 또는 MP4로 다운로드)
- 썸네일이 누락됩니다 — 갤러리와 Video Studio가 미리보기 이미지 대신 검은색 플레이스홀더를 표시합니다
- 동영상 메타데이터(길이, 해상도)가 표시되지 않습니다

| 도구 | 목적 | macOS | Linux (Debian/Ubuntu) | Windows |
|------|------|-------|-----------------------|---------|
| **ffmpeg** | 썸네일 추출 + 동영상 메타데이터 | `brew install ffmpeg` | `sudo apt install ffmpeg` | [ffmpeg.org/download](https://ffmpeg.org/download.html)에서 다운로드 또는 `winget install ffmpeg` |

> [!NOTE]
> `ffprobe`는 ffmpeg에 포함되어 있습니다 — 별도 설치가 필요 없습니다. ArtSmoker는 런타임에 ffmpeg를 확인하고 없으면 우아하게 폴백합니다 — 동영상 생성은 어느 쪽이든 작동하며, 단지 썸네일을 얻지 못할 뿐입니다.

설치 확인:

```bash
ffmpeg -version 2>&1 | head -1 && echo "ffmpeg: OK" || echo "ffmpeg: not installed (optional)"
ffprobe -version 2>&1 | head -1 && echo "ffprobe: OK" || echo "ffprobe: not installed (optional)"
```

## 📌 3. 설치

### 📝 3.1 macOS

```bash
git clone https://github.com/niravdd/ArtSmoker.git && cd ArtSmoker

# Option A: With virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Option B: Without virtual environment (system-wide install)
pip3 install -r backend/requirements.txt
```

> [!NOTE]
> macOS에서는 `python3`와 `pip3`가 Homebrew(`brew install python`) 또는 Xcode 커맨드라인 도구를 통해 사용 가능합니다. "command not found"가 표시되면 [python.org](https://www.python.org/downloads/)에서 Python을 설치하거나 `brew install python@3.12`를 사용하세요.

### 📝 3.2 Linux (Debian/Ubuntu)

```bash
# Install Python if needed
sudo apt update && sudo apt install python3 python3-pip python3-venv

git clone https://github.com/niravdd/ArtSmoker.git && cd ArtSmoker

# Option A: With virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Option B: Without virtual environment
pip3 install --user -r backend/requirements.txt
```

> [!NOTE]
> 일부 Linux 배포판에서는 venv 외부의 `pip install`에 `--user` 플래그 또는 `--break-system-packages`(PEP 668)가 필요합니다. venv를 사용하면 이 문제를 완전히 피할 수 있습니다.

### 📝 3.3 Windows

```powershell
git clone https://github.com/niravdd/ArtSmoker.git
cd ArtSmoker

# Option A: With virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt

# Option B: Without virtual environment
pip install -r backend\requirements.txt
```

> [!NOTE]
> Windows에서는 (`python3`가 아니라) `python`을 사용하세요. [python.org](https://www.python.org/downloads/)에서 Python을 설치하고 — 설치 중 "Add to PATH"를 체크하세요. Type Studio 폰트 피커는 `C:\Windows\Fonts`에서 폰트를 감지합니다(시스템 폰트 감지는 현재 macOS/Linux 전용 — Windows 사용자는 글로벌 또는 스타일별 커스텀 폰트를 사용할 수 있습니다).

## 📌 4. 실행

### 📝 4.1 단독 개발(모든 플랫폼)

파일 변경 시 자동 재로드되는 단일 프로세스 — 로컬에서 작업하는 개발자 한 명에게 이상적입니다:

```bash
# With venv (activate first)
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\activate             # Windows

uvicorn backend.main:app --reload
```

```bash
# Without venv (if installed system-wide)
uvicorn backend.main:app --reload

# Or if uvicorn isn't on PATH
python3 -m uvicorn backend.main:app --reload     # macOS / Linux
python -m uvicorn backend.main:app --reload       # Windows
```

**http://localhost:8000** 을 여세요 — 프론트엔드는 FastAPI가 서빙하므로 별도의 웹 서버가 필요 없습니다.

시작 시 콘솔에 AWS 인증 정보 검증 결과가 표시됩니다. 문제가 있으면 명확한 오류 상자가 표시됩니다. `http://localhost:8000/api/health`에서도 상태를 확인할 수 있습니다.

**로그.** 콘솔 외에도, ArtSmoker는 **기본적으로** 전체 **추가 전용** 로그를 `logs/artsmoker.log`에 기록하므로, 앱이 닫힌 후에도 지난 세션을 검토할 수 있습니다. 각 실행은 세션 배너(실행 시간, 버전, pid, 호스트)로 시작되고 종료 배너(중지 시간, 지속 시간)로 마무리됩니다. 경로를 변경하거나 끄려면:

```bash
ARTSMOKER_LOG_FILE=/var/log/artsmoker/app.log uvicorn backend.main:app   # custom path
ARTSMOKER_LOG_TO_FILE=false uvicorn backend.main:app                      # disable file logging
```

(또는 로컬 `.env`에 `log_to_file` / `log_file`을 설정하세요. 여러 워커가 있는 경우, 모든 워커가 동일한 파일에 추가합니다.)

**자동 재시작(선택 사항, 모든 플랫폼).** 위 명령들은 모두 그대로 작동합니다. ArtSmoker가 **그 자리에서 스스로 재시작**하도록 — 자동 업데이트나 앱 내 **Restart** 버튼이 다시 실행하지 않아도 새 코드를 로드하도록 — 하려면, 대신 내장된 크로스 플랫폼 감독 프로세스로 실행하세요:

```bash
python -m backend.main            # 필요하면 --host / --port 추가; Ctrl-C로 깔끔하게 중지
```

이 방식은 **Windows를 포함한 모든 OS**에서 작동합니다. 감독 프로세스는 앱을 자식 프로세스로 실행하고, 재시작 요청이 있으면 다시 기동합니다. (gunicorn이나 systemd 같은 서비스 매니저로 실행해도 동일한 그 자리 재시작이 가능합니다 — §4.2 및 §6 참조.)

### 📝 4.2 멀티 유저 / 공유 테스트 박스 / 프로덕션(macOS / Linux)

동시 사용자가 두 명 이상인 모든 환경 — 공유 개발/테스트 박스, 스테이징, 프로덕션 — 에서는 여러 워커가 있는 **gunicorn**을 사용하세요:

```bash
# Install gunicorn (one-time, in addition to requirements.txt)
pip install gunicorn

# Run with gunicorn (multi-worker, handles concurrent users)
gunicorn backend.main:app \
  -w 2 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300
```

| 플래그 | 목적 |
|------|------|
| `-w 2` | 2개 워커 프로세스(더 무거운 부하에는 증가) |
| `-k uvicorn.workers.UvicornWorker` | uvicorn의 비동기 워커 클래스 사용 |
| `--bind 0.0.0.0:8000` | 모든 인터페이스에서 수신(localhost뿐 아니라) |
| `--timeout 300` | 재시도가 있는 대규모 배치 생성을 위한 5분 타임아웃 |

> [!TIP]
> **gunicorn**은 Linux/macOS 전용입니다. Windows에서는 멀티 워커 서빙에 `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2`를 사용하세요.

> [!NOTE]
> **동시 사용자에 안전.** 모든 서버 쓰기 — 이미지/버전 메타데이터와 모델 및 프롬프트 레지스트리 — 는 원자적으로 기록되고 **워커 프로세스 전반에 걸쳐** 직렬화(POSIX 파일 락)되므로, 공유 박스에서 여러 협업자의 동시 편집이 파일을 손상시키거나 업데이트를 잃는 일이 절대 없습니다. 파일 로깅도 워커 전반에서 동일하게 작동합니다 — 각각 하나의 `logs/artsmoker.log`에 추가합니다.

<a id="43-ec2--cloud-deployment"></a>

### 📝 4.3 EC2 / 클라우드 배포

권장: 동시 사용자 1-2명에 **t3.small**(~$15/월).

**1단계: EC2 인스턴스용 IAM 역할 생성**(로컬 머신에서 실행):

```bash
# Create the IAM role with EC2 trust policy
aws iam create-role --role-name ArtSmokerEC2Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach the ArtSmoker policy (use the scoped policy from section 2.2, or the managed policy)
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Create an instance profile and attach the role
aws iam create-instance-profile --instance-profile-name ArtSmokerEC2Profile
aws iam add-role-to-instance-profile \
  --instance-profile-name ArtSmokerEC2Profile \
  --role-name ArtSmokerEC2Role
```

**2단계: EC2 인스턴스 시작**(또는 기존 인스턴스에 프로필 연결):

```bash
# Attach to an existing running instance
aws ec2 associate-iam-instance-profile \
  --instance-id i-YOUR_INSTANCE_ID \
  --iam-instance-profile Name=ArtSmokerEC2Profile
```

**3단계: 인스턴스에 설치 및 실행**(인스턴스에 SSH 접속):

```bash
# Install (one-time)
sudo yum install -y python3 python3-pip git   # Amazon Linux
# sudo apt install -y python3 python3-pip python3-venv git   # Ubuntu

git clone https://github.com/niravdd/ArtSmoker.git && cd ArtSmoker
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install gunicorn

# Optional: install ffmpeg for video thumbnails
sudo yum install -y ffmpeg   # Amazon Linux
# sudo apt install -y ffmpeg   # Ubuntu
```

**4단계: systemd 서비스로 실행**(영구적, 자동 재시작):

```bash
# Create the service file
sudo tee /etc/systemd/system/artsmoker.service > /dev/null << 'EOF'
[Unit]
Description=ArtSmoker
After=network.target

[Service]
WorkingDirectory=/home/ec2-user/ArtSmoker
ExecStart=/home/ec2-user/ArtSmoker/.venv/bin/gunicorn backend.main:app \
  -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 300
Restart=always
User=ec2-user

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable artsmoker
sudo systemctl start artsmoker

# Verify it's running
sudo systemctl status artsmoker

# View logs
sudo journalctl -u artsmoker -f
```

**http://YOUR_INSTANCE_IP:8000** 을 여세요 — EC2 보안 그룹이 인바운드 TCP 8000을 허용하는지 확인하세요.

### 📝 4.4 설정 후 첫 단계

ArtSmoker가 실행되면, 최상의 결과를 얻기 위해 다음 단계를 완료하세요:

**1. AWS에서 모델 동기화** — **Model Settings**(모든 스튜디오의 톱니바퀴 아이콘) 열기 → **Sync from AWS** 클릭. 이는 모든 Bedrock 리전에 걸쳐 사용 가능한 모든 이미지, 동영상, 채팅 모델을 검색합니다. 30-60초 소요. 한 번만 하면 되며, AWS가 새 모델을 추가할 때만 다시 하면 됩니다.

**2. 프롬프트 템플릿 검토 및 커스터마이징** — 이것은 할 수 있는 가장 영향력 있는 설정입니다. **Model Settings → Prompt Templates** 탭을 여세요. ArtSmoker는 AI의 동작을 제어하는 28개의 편집 가능한 지시 프롬프트를 사용합니다:

| 템플릿 | 제어 내용 |
|--------|-----------|
| Image Prompt Refinement | 텍스트 설명이 상세한 이미지 생성 프롬프트로 변환되는 방식 |
| Multi-Concept Generation | 하나의 아이디어에서 여러 크리에이티브 옵션이 생성되는 방식 |
| Style Analysis | 레퍼런스 이미지를 분석하여 아트 스타일을 학습하는 방식 |
| Content Moderation | 사전 검토 및 리라이트 시스템의 엄격도 |
| Video Enhancement | 동영상 프롬프트가 카메라 무브먼트와 조명으로 풍부해지는 방식 |
| Text Layout | Type Studio가 이미지 위 텍스트 위치를 디자인하는 방식 |

각 템플릿은:
- **직접 편집** — 팀의 요구에 맞게 지시를 수정
- **AI로 강화** — 임의의 LLM 모델을 선택하고, 선택적으로 지시(예: "픽셀 아트에 최적화")를 추가한 뒤 "Enhance with AI"를 클릭. 제안을 검토한 다음 Accept 또는 Dismiss
- **기본값으로 재설정** — 언제든지 원본 복원

템플릿은 스튜디오별로 정리되어 있으며(Image Studio, Style Library, Content Safety, Video Studio, Type Studio, Chat Studio, Translation), 각각이 제어하는 내용에 대한 친절한 설명이 포함됩니다.

**변수 안전성:** 템플릿은 런타임에 치환되는 `{curly_brace}` 변수(예: `{user_prompt}`, `{model_name}`)를 사용합니다. 필수 변수를 실수로 제거하면, ArtSmoker는:
1. 저장을 차단하고 어떤 변수가 누락되었는지 표시
2. **"Fix & Save"** 제공 — LLM이 누락된 변수를 편집된 텍스트의 올바른 위치에 자동으로 다시 삽입
3. 저장 전에 수정 사항 검증

템플릿은 `backend/prompt_templates.json`에서 로드됩니다 — 런타임 진실의 원천입니다. 편집 내용은 `backend/prompt_templates.user.json`(gitignore)에 저장되어 위에 오버레이되므로, 업데이트나 `git pull`이 커스터마이징을 절대 덮어쓰지 않습니다. JSON이 누락되거나 손상되었거나, 코드에 새 템플릿이 출시되면, 자가 치유됩니다: 내장 코드 시드가 누락된 항목만 재생성/백필하며, 기존 항목을 절대 덮어쓰지 않습니다.

> [!TIP]
> **Image Prompt Refinement**와 **Creative Options** 템플릿을 검토하는 것부터 시작하세요. 이들이 출력 품질에 가장 큰 영향을 미칩니다. 팀이 특정 아트 스타일(예: 픽셀 아트, 수채화, 아이소메트릭)을 전문으로 한다면, 그 선호도를 템플릿에 직접 추가하여 모든 생성이 혜택을 받도록 하세요.

**3. 스타일 프로필 설정**(선택) — **Style Library**로 가서 새 스타일을 만들고, 레퍼런스 이미지를 업로드한 뒤 **Analyze**를 클릭하세요. 이는 ArtSmoker에게 당신의 비주얼 아이덴티티를 가르칩니다.

**4. 언어 선택** — 비영어 인터페이스를 선호한다면 내비게이션 바의 언어 버튼(EN | 日 | 中 | 한 | हिं | РУ | FR | ES | DE)을 클릭하세요.

## 📌 5. 아키텍처

```
┌─────────────────────────────────────────────┐
│  Browser (SPA)                              │
│  Vanilla JS + Tailwind CSS                  │
└──────────────────────┬──────────────────────┘
                       │ HTTP / SSE
                       ▼
┌─────────────────────────────────────────────┐
│  FastAPI Backend (Python)                   │
│                                             │
│  /api/styles      Style CRUD + import       │
│  /api/generate    Two-level generation      │
│  /api/type-studio Text overlay + fonts      │
│  /api/video       Video generation + jobs   │
│  /api/chat        LLM chat + sessions       │
│  /api/gallery     Asset browsing + export   │
│  /api/browse      File/S3 browser           │
│  /api/admin       Model registry + templates│
│  /api/refine-prompt  Prompt + translate      │
│  /api/transcribe  Voice-to-text             │
└────────────┬────────────────────┬───────────┘
             │                    │
             ▼                    ▼
┌──────────────────────┐  ┌──────────────────────────┐
│  us-west-2           │  │  us-east-1               │
│                      │  │                          │
│  Claude Sonnet       │  │  Nova Sonic (voice)      │
│  Claude Opus         │  │  Nova Reel (video)       │
│  SD 3.5 Large        │  │                          │
│  Stable Image Ultra  │  │                          │
│  Stable Image Core   │  │                          │
│  Stability AI (post) │  │                          │
└──────────────────────┘  └──────────────────────────┘ ... (other regions)
             │
             ▼
┌──────────────────────┐
│  Local Storage        │
│  data/styles/         │
│  data/generated/      │
│  data/video/          │
│  data/chat/           │
└──────────────────────┘
```

## 📌 6. 사용법

### 📝 6.1 워크플로 개요

```
                            ┌─────────────────┐
                            │   ArtSmoker     │
                            └────────┬────────┘
                                     │
       ┌───────────┼───────────┼───────────┼───────────┐
       │           │           │           │           │
       ▼           ▼           ▼           ▼           ▼
  ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────┐
  │  Style   │ │  2D    │ │ Video  │ │   Type   │ │  Chat  │
  │ Library  │ │ Image  │ │ Studio │ │  Studio  │ │ Studio │
  │          │ │ Studio │ │        │ │          │ │        │
  │ Upload   │ │Generate│ │Generate│ │ Add text │ │ Multi- │
  │ Analyze  │ │ images │ │ videos │ │ to imgs  │ │ model  │
  │ Set fonts│ │        │ │        │ │          │ │ LLM    │
  │          │ │        │ │        │ │          │ │ chat   │
  └────┬─────┘ └───┬────┘ └───┬────┘ └────┬─────┘ └────────┘
             │              │            │               │
             │    ┌─────────┴────────────┴─────────┐     │
             │    │  Style selected? (optional)    │     │
             └───►│  Enhances output               │◄────┘
                  └─────────┬──────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │    Gallery      │
                          │                 │
                          │ Browse all      │
                          │ Search/filter   │
                          │ Select & delete │
                          └────────┬────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
            ┌──────────────┐ ┌──────────┐ ┌──────────────┐
            │ Download     │ │ Reload   │ │ Add Text     │
            │ PNG / SVG    │ │ in 2D    │ │ in Type      │
            │              │ │ Image    │ │ Studio       │
            │              │ │ Studio   │ │              │
            │              │ │ (refine &│ │ (overlay     │
            │              │ │  regen)  │ │  text)       │
            └──────────────┘ └──────────┘ └──────────────┘
```

**세 개의 진입점, 하나의 통합 갤러리:**

- **스타일로 시작** — Style Library에 레퍼런스 아트를 업로드하고, AI가 분석하게 한 뒤, 임의의 스튜디오에서 생성하세요. 스타일이 모든 출력을 가이드합니다.
- **스타일 없이 시작** — 2D Image Studio, Video Studio 또는 Type Studio로 바로 진입하세요. AI가 최선의 판단을 사용합니다.
- **갤러리에서 시작** — 이전에 생성한 임의의 에셋을 골라 적절한 스튜디오에서 다시 로드하여 개선하거나, 텍스트를 추가하거나, 동영상을 재생하거나, PNG/SVG/MP4로 다운로드하세요.

생성된 모든 에셋(이미지, 동영상, 텍스트 오버레이, 독립 텍스트)은 통합 갤러리에 도착합니다. 아무것도 덮어쓰이지 않습니다 — 각 생성은 새 에셋을 만듭니다.

### 📝 6.2 생성 파이프라인

```
User prompt: "hospital building"
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 1. Prompt Composition            Claude Sonnet (1 opt) │
│    (optional "Compose" button)   or Opus (2-5 options) │
│    + style + asset type                                │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 2. Canary Test                                         │
│    Single image tests moderation                       │
│    Pass? ──► Full batch    Fail? ──► Model switch      │
│                                  or rewrite suggestion │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 3. Parallel Image Generation                           │
│    Up to 5 options × 5 variations = 25 images          │
│    ThreadPool (3-5 workers)                            │
│    Retry with exponential backoff (3 attempts)         │
│    SSE progress streaming to browser                   │
│    Cooperative cancellation on moderation block        │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 4. Post-Processing (per image, optional)               │
│    Remove Background ──► Stability AI ($0.07/img)      │
│    Upscale ──► Stability AI Creative Upscale ($0.60)   │
│    SVG ──► vtracer / potrace / Pillow (free, local)    │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 5. Storage                                             │
│    data/generated/{asset_id}/                          │
│    ├── asset.png (transparent background)              │
│    ├── asset.svg (optional)                            │
│    └── metadata.json (full prompt lineage)             │
│    Smart filenames: prompt-slug_opt1_var2.png          │
└────────────────────────────────────────────────────────┘
```

### 📝 6.3 콘텐츠 모더레이션 흐름

```
User clicks Generate
         │
         ▼
┌──────────────────────┐
│ Pre-Check enabled?   │
│ (Prompt Pre-Check    │
│  toggle, on by       │
│  default)            │
└───┬────────────┬─────┘
  Yes            No
    │            │
    ▼            │
┌──────────┐     │
│ Claude   │     │
│ Sonnet   │     │
│ screens  │     │
│ prompt   │     │
└───┬────┬─┘     │
 Issues? No      │
    │    └──────►│
    ▼            │
┌──────────────┐  │
│ Indigo       │  │
│ dialog:      │  │
│ • Switch     │  │
│ • Rewrite    │  │
│ • Proceed    │  │
│ • Cancel     │  │
└──┬───────────┘  │
   │◄────────────┘
   ▼
┌──────────────────────┐
│ Canary test          │
│ (1 image to model)   │
└───┬────────────┬─────┘
 Blocked        Pass
    │            │
    ▼            ▼
┌──────────┐  ┌──────────┐
│ Try alt  │  │ Full     │
│ models   │  │ batch    │
└───┬────┬─┘  │ runs     │
 Works?  No   └──────────┘
    │    │
    ▼    ▼
Emerald    Amber
dialog     dialog
(switch    (rewrite →
 or         enhanced
 rewrite)   prompt area)
```

### 📝 6.4 2D Image Studio(에셋 생성)

2D Image Studio는 가이드형 3단계 워크플로를 사용합니다:

**1단계 — 아이디어 설명**: 텍스트 영역에 프롬프트를 입력합니다. 플레이스홀더는 선택한 에셋 타입에 따라 바뀌는 현실적인 예시를 보여줍니다(예: Character에는 "A young female warrior in ornate silver armor...", Environment에는 "A misty Japanese garden at dawn..."). 입력 대신 음성 입력(마이크 버튼)으로 받아쓰게 할 수 있습니다.

**2단계 — Prompt Designer** *(선택)*: **🎨 Prompt Designer**를 클릭하여 프롬프트를 구조화된 시각 컴포넌트로 분해합니다. AI가 프롬프트를 분석하여 편집 가능한 섹션으로 나눕니다:

- **Subject** — 캐릭터 설명, 의상, 액세서리, 포즈, 표정
- **Scene** — 세팅, 배경, 소품, 시간대
- **Composition** — 카메라 앵글, 프레이밍, 피사계 심도
- **Lighting** — 키 라이트, 필/림 라이트, 분위기
- **Style & Colors** — 아트 스타일, 품질 레벨, 그리고 16진수 스와치가 포함된 이름 지정 컬러 팔레트

각 필드는 개별적으로 편집할 수 있습니다. **Generate Enhanced Prompt**는 편집 내용을 하나의 평문 재구성 프롬프트로 재조합하고(2단계에 읽기 전용으로 표시), 그다음 자동으로 3단계용 Enhanced AI Prompt를 생성합니다.

Prompt Designer가 열리기 전에, **AI 에셋 타입 분류**가 실행됩니다 — 프롬프트가 장면을 설명하는데 "Game Asset"을 선택했다면, 대화상자가 "Environment"나 "Character"로 전환할 것을 제안합니다. 이는 Prompt Designer가 올바른 컨텍스트로 분해하도록 보장합니다.

**3단계 — 강화된 프롬프트 미리보기** *(선택)*: **Generate Enhanced Prompt**를 클릭하여 생성 전에 모델 최적화 프롬프트를 확인합니다. AI가 2단계의 재구성 프롬프트를 가져와 모델별 가이던스(해부학, 재질, 조명, 프롬프트 구조)로 강화합니다. 생성 전에 강화된 프롬프트를 편집할 수 있습니다. 2단계에서 Prompt Designer를 사용했다면, 이것은 자동으로 채워집니다.

**프롬프트 파이프라인**: User Prompt → Decompose → Recompose(`recomposed_prompt`) → 모델 가이던스로 Enhance(`enhanced_prompt`) → Image Model. 여러 옵션의 경우, 강화 단계가 동일한 재구성 베이스에서 N개의 구별되는 해석을 생성합니다. 세 레벨 모두 메타데이터에 저장됩니다.

**생성**: 언제든 Generate를 클릭하세요 — 2단계와 3단계는 선택입니다. 이를 건너뛰면, Generate가 진행 전에 프롬프트를 자동으로 분해, 재구성, 강화합니다. **Prompt Pre-Check**(기본값 켜짐)는 생성 전에 프롬프트의 모더레이션 이슈를 검토합니다.

**추가 컨트롤:**
- **Asset Type** — 사이드바에서 선택. 프롬프트 플레이스홀더를 바꾸고 AI가 프롬프트를 해석하는 방식에 영향을 줍니다. 불일치를 감지하면 시스템이 전환을 제안합니다.
- **Art Style** — 비주얼 아이덴티티로 생성을 가이드할 스타일 프로필을 선택.
- **Dimensions, Options, Variations** — 출력 크기와 생성할 크리에이티브 컨셉의 개수를 구성.
- **Post-Processing** — 배경 제거, 업스케일, SVG 변환(생성 후 적용).
- **IP Declaration** — 엄격한 모델 호환을 위해 소유권 또는 라이선스를 명시.
- **Model Settings** — 모델 구성 보기/편집, 사용 가능한 Amazon Bedrock 모델 검색.

생성 진행률은 SSE를 통해 실시간으로 스트리밍됩니다 — UI에 어떤 이미지가 생성 중인지(예: "Generating images... 12/25"), 경과 시간, 현재 파이프라인 단계가 표시됩니다. API가 스로틀링되면 지연 시간과 함께 "API throttled — waiting to retry..."가 표시되고, 그다음 "Retrying... (attempt 2/3)" — 각 이미지는 지수 백오프로 최대 3회 재시도하므로 대규모 배치가 일시적 스로틀링으로 배리언트를 잃지 않습니다.

생성된 결과는 내비게이션에도 살아남습니다 — 탭을 전환했다 돌아와도 2D Image Studio의 DOM 상태가 보존됩니다. 리셋 버튼만이 이를 지웁니다.

**스마트 콘텐츠 모더레이션**: 프롬프트가 모델의 콘텐츠 모더레이션 필터에 의해 차단되면, ArtSmoker는 세 개의 색상 코드 대화상자를 통해 점진적으로 처리합니다:

- **Indigo(Pre-Check)** — 생성 전에 AI가 선택된 모델의 알려진 민감도에 대해 프롬프트를 사전 검토합니다. 이슈가 감지되면, 구체적인 우려사항을 보고 다음을 할 수 있습니다: 권장 모델로 전환, 현재 모델용으로 **프롬프트 리라이트**, 그대로 진행, 또는 취소.
- **Emerald(Model Switch)** — 생성 차단 후, 대체 모델이 프롬프트를 그대로 수락하면, ArtSmoker가 어떤 모델이 작동하는지와 그 이유를 보여줍니다. 원클릭으로 전환. 전체 시도 로그 확인 가능("View N model tests").
- **Amber(Rewrite)** — 모든 모델이 거부하면, 구체적인 이슈가 나열된 편집 가능한 텍스트 영역에 AI 생성 리라이트가 제공됩니다. 검증됨/미검증됨 배지가 리라이트가 카나리아 테스트를 통과했는지 나타냅니다.

**프롬프트 리라이트 동작**: 세 대화상자 모두에서, "Rewrite"를 선택해도 원본 프롬프트를 절대 덮어쓰지 않습니다. 재작성된 버전은 원본 텍스트 아래의 **강화된 프롬프트 영역**에 나타나며, 지속적인 앰버 고지가 함께 표시됩니다: *"이 리라이트는 프롬프트를 호환되게 만들려는 시도입니다 — 여전히 모델 자체의 모더레이션 평가 대상이며 거부될 수 있습니다."* 강화된 프롬프트를 검토하고 편집한 다음, 만족스러우면 Generate를 클릭하세요. 원본 프롬프트는 항상 히스토리와 메타데이터에 보존됩니다.

일반적인 트리거로는 저작권 IP 이름과 캐릭터 레퍼런스, 폭력/무기 언어, 성인 콘텐츠 레퍼런스가 있습니다. 팁: **"Preview Enhanced Prompt"** 버튼은 AI가 설명적 용어로 재표현하기 때문에 모더레이션을 자연스럽게 통과하는 프롬프트를 자주 생성합니다.

**스마트 카나리아 테스트**: 전체 배치를 생성하기 전에, ArtSmoker는 모델의 모더레이션 필터에 대해 프롬프트를 테스트하기 위해 단일 "카나리아" 이미지 요청을 보냅니다. 카나리아가 차단되면, 배치가 즉시 중단됩니다(N×M×3 대신 1회 낭비 API 호출). 카나리아가 통과하면, 나머지 작업이 협력적 취소와 함께 병렬로 실행됩니다 — 어떤 작업이 모더레이션 차단에 부딪히면, 나머지는 자동으로 API 호출을 건너뜁니다.

### 📝 6.5 스타일 프로필 사용

1. **Style Library** 탭으로 이동합니다.
2. **Create New Style**을 클릭 — 이름을 입력하고 선택적으로 생성 힌트를 추가합니다. 생성 모달에서 **Local**과 **S3** 탐색 버튼이 있는 **"Import References From"** 섹션을 사용하여 소스 디렉터리나 버킷 경로를 선택합니다. 탐색은 서버 사이드 파일/디렉터리 브라우저 모달을 엽니다(싱글 클릭으로 항목 선택, 더블 클릭으로 디렉터리 진입). 가져온 레퍼런스는 생성 시 자동 분석됩니다.
3. 로컬 디렉터리 가져오기는 모든 하위 디렉터리를 통해 **재귀적으로** 이미지(.png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff, .tif, .tga, .ico, .svg)와 3D 모델(.glb, .gltf)을 스캔합니다. 이미지 파일은 **상대 심볼릭 링크**를 사용하여 **심볼릭 링크**됩니다(중복 없음, 머신 간 이식성). 3D 모델 파일(.glb/.gltf)은 내장 텍스처가 **자동으로 추출**됩니다 — base64 데이터 URI, 바이너리 버퍼 청크, 외부 텍스처 레퍼런스 모두 처리됩니다. 추출된 텍스처는 사본으로 저장됩니다(충돌 방지를 위해 모델명이 접두사로 붙음). S3 가져오기는 페이지네이션으로 재귀 목록을 조회하고 파일을 로컬로 **다운로드**합니다. 스타일당 최대 **100개의 레퍼런스 이미지**가 가져와집니다. 지원 확장자는 `backend/config.py`(`IMAGE_EXTENSIONS` 및 `MODEL_EXTENSIONS_WITH_TEXTURES`)에 중앙화되어 있습니다.
4. **2단계 응집도 인식 분석**: 1단계는 8개 이미지를 Claude Sonnet에 보내 응집도 레벨(high/medium/low)을 판단합니다 — high는 통일된 스타일, medium은 다른 테마를 가진 공유 구조, low는 다양한 스타일을 의미합니다. 2단계는 응집도 평가를 레퍼런스 이미지와 함께 Claude Opus에 공급하여, 컬렉션 유형에 맞게 적절히 분석하도록 가이드합니다. 스타일에 레퍼런스가 20개를 초과하면, 분석기는 Opus 비전 호출을 위해 다양한 대표 부분집합 20개를 선택합니다 — 파일명 그룹과 파일 크기 다양성 전반의 커버리지를 보장합니다. AI는 총 몇 개의 이미지가 존재하는지 대비 몇 개를 보고 있는지를 전달받습니다. 분석 프롬프트는 투명 배경의 게임 에셋용으로 특별히 설계되어 — 재질별 렌더링 세부사항, 비율 시스템, 그림자/조명 세부사항을 요청합니다. `materials`(돌, 나무, 금속이 렌더링되는 방식)와 `detail_level`(어떤 표면 디테일이 보이는지 대 단순화되는지)을 포함한 9개 스타일 속성을 추출합니다. 생성 힌트는 8개 차원을 다루는 200단어로 확장됩니다: 원근법, 렌더링, 재질, 컬러 팔레트, 비율, 에지 처리, 그림자/조명, 디테일 레벨, 배경 — 생성된 에셋이 기존 레퍼런스와 시각적으로 어우러질 만큼 구체적입니다.
5. 스타일 상세 뷰에서, **"Import & Analyze"**를 사용하여 레퍼런스를 더 추가하고 한 번에 분석을 트리거합니다. 드래그 앤 드롭 업로드도 지원되며 새 이미지가 추가되면 **자동 재분석**됩니다.
6. **"Re-Analyze Style"**은 초기 분석 후 나타나, 언제든 수동으로 분석을 다시 실행할 수 있게 합니다.
7. **생성 힌트**는 분석 컨텍스트의 일부입니다 — AI는 분석 시 레퍼런스 이미지와 힌트를 모두 "아티스트의 가이던스"로 받아들이므로, 스타일 프로필이 시각적 외관뿐만 아니라 의도를 이해합니다. 생성 힌트를 편집하면 **자동 재분석**도 트리거됩니다.
8. **2D Image Studio**로 돌아가서, 드롭다운에서 스타일을 선택하세요 — 생성된 모든 에셋이 그 비주얼 아이덴티티(팔레트, 원근법, 렌더링 스타일, 분위기)에 맞춰집니다.

### 📝 6.6 스타일 분석 흐름

```
┌──────────────────────────────────────────┐
│ Create / Import style                    │
│ (reference images uploaded or imported)  │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Phase 1: Cohesion Check                  │
│ Claude Sonnet — 8 images — ~$0.01        │
│ Determines: high / medium / low          │
│   high   = unified style                 │
│   medium = shared structure, diff themes │
│   low    = diverse collection            │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Phase 2: Full Analysis                   │
│ Claude Opus — up to 20 images            │
│ Guided by cohesion level                 │
│ + Artist's Guidance (user hints)         │
│ Extracts 9 style attributes              │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Phase 3: Hint Generation                 │
│ Claude Sonnet — 200-word hints           │
│ 8 dimensions: perspective, rendering,    │
│ materials, palette, proportions, edges,  │
│ shadow/lighting, detail level            │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│ Stored in profile.json                   │
│ ~$0.14 total per style analysis          │
│ Used in all future generation            │
└──────────────────────────────────────────┘
```

### 📝 6.7 Type Studio

AI가 디자인한 타이포그래피로 이미지에 텍스트를 추가하거나 독립형 텍스트 에셋을 생성합니다.

- **두 가지 모드**: "On Image"는 텍스트를 갤러리 이미지에 합성하고, "Standalone"은 투명 배경에 텍스트를 렌더링합니다.
- **멀티 라인 텍스트 에디터** — 라인별 폰트 선택, 위치 컨트롤, **음성 입력**(라인별 마이크 버튼 — Nova Sonic 전사로 텍스트 받아쓰기).
- **AI 디자인 레이아웃** — AI가 색상, 크기, 위치, 효과(그림자, 아웃라인, 글로우)를 제안합니다. 서로 다른 크리에이티브 방향을 위해 1~5개의 레이아웃 옵션을 요청하세요. 레이아웃에 사용되는 **LLM 모델**은 구성 가능합니다(최고 품질에는 Complex LLM, 더 저렴하게는 Fast LLM) — 레지스트리 카테고리에서 읽습니다.
- **라이브 미리보기가 있는 폰트 피커** — 스타일 폰트, 8개 번들 폰트(Roboto, Open Sans, Lato, Montserrat, Playfair Display, Oswald, Raleway, Source Code Pro), 시스템 폰트, 그리고 **클라이언트 사이드 감지 폰트**(Local Font Access API 또는 캔버스 프로빙 경유).
- **전처리 / 후처리** — 2D Image Studio와 동일한 워크플로, 후처리용 "Apply" 버튼 포함. SVG 변환은 기본값으로 켜져 있습니다.
- **클릭하여 확대** — 결과 미리보기를 클릭하면 전체 줌/팬, 메타데이터, 다운로드, 이미지 편집 도구가 있는 AssetViewer가 열립니다.
- 결과는 새 갤러리 에셋으로 저장됩니다(원본은 절대 덮어쓰이지 않습니다).

### 📝 6.8 갤러리

- 모든 생성 이미지와 동영상의 **메이슨리 레이아웃** **통합 뷰**(각 에셋을 실제 종횡비 — 세로, 정사각형, 가로 — 로 표시, 절대 중앙 크롭 안 함), **미디어 필터**(전체 / 2D 아트워크 / 3D 모델 / 동영상) 포함. **3D 모델** 필터는 이미 3D 모델이 생성된 에셋만 표시하며, 그런 에셋은 타일에 **3D 배지**를 답니다.
- 모든 에셋(프롬프트, 스타일, 모델)에 걸쳐 즉시 필터링하는 **검색 바**.
- 일괄 삭제를 위한 체크박스 **멀티 선택**(이미지와 동영상 에셋 모두 처리). 삭제는 **배치 인식** — 살아남은 형제들이 몇 개의 배리언트가 제거되었는지 추적하므로, Image Studio에서 부분 배치를 다시 로드하면 "X of Y images remaining (Z deleted)"가 표시됩니다.
- 에셋은 인메모리 메타데이터 캐시로 즉시 로드됩니다. 최신순 정렬.
- 대규모 컬렉션을 위한 페이지네이션 지원(limit/offset).
- 갤러리는 다시 탐색해 돌아올 때, 그리고 편집이나 동영상 생성이 완료된 후 자동으로 새로고침됩니다.
- **동영상 카드**는 재생 오버레이, VIDEO 배지, 길이 표시기가 있는 썸네일을 표시합니다. 클릭하면 동영상 플레이어 모달이 열립니다.
- 타입에 따른 에셋별 **컨텍스트 액션 버튼**: 이미지 스튜디오에서 다시 로드하는 **"2D Studio"**(인디고), Type Studio에서 열기 위한 **"Add Text"**(에메랄드), 텍스트 에셋용 **"Edit in Type Studio"**(퍼플).
- 임의의 이미지를 클릭하면 다음이 있는 **AssetViewer** 모달이 열립니다:
  - **줌/팬** — 마우스 휠로 줌, 드래그로 팬, 활성 모드 하이라이팅이 있는 Fit/1:1 버튼.
  - **Edit 탭** — 이미지를 직접 인페인트, 지우기, 아웃페인트, 검색 및 교체, 리컬러. 모드별로 두 종류의 에디터가 제공됩니다: **마스크 기반**(Stability) — 브러시 도구로 마스크를 페인트하고, 프롬프트를 입력한 뒤 적용; 그리고 **마스크 없는 지시형 에디터**(Qwen-Image-Edit, 배포 시) — 변경 사항을 말로 설명만 하면 되고 마스크 불필요. 마스크 없는 모델에서는 브러시 컨트롤이 자동으로 숨겨집니다. 편집 모델을 선택하고 적용; 기본값은 원본 이미지를 대체하며, "Replace original" 체크를 해제하면 새 에셋으로 저장(모든 편집은 버전 히스토리를 보존).
  - **Previous / Next** — 뷰어를 닫지 않고 목록을 탐색하는 화살표 버튼과 키보드 좌/우.
  - **전체 메타데이터**: 원본 프롬프트, AI 개선 프롬프트, 생성 프롬프트, 네거티브 프롬프트, 스타일, 에셋 타입, 이미지 모델(친숙한 이름), 크기, 시드, 배치 ID, 옵션/배리에이션 인덱스, IP 선언 상태, 파일명, 생성 날짜.
- **스타일 스냅샷**: 각 에셋은 생성 시점에 사용된 스타일의 스냅샷(이름, 설명, 힌트, 분석)을 저장합니다. 원본 스타일이 나중에 삭제되어도, 에셋은 전체 컨텍스트를 유지합니다. 하위 호환 — 스냅샷이 없는 오래된 에셋도 정상적으로 표시됩니다.

### 📝 6.9 음성 입력

프롬프트 에디터 옆의 마이크 버튼을 클릭하여 프롬프트를 받아쓰게 하세요. 오디오는 전사를 위해 Nova Sonic으로 전송됩니다.

> [!NOTE]
> 음성 전사는 Nova Sonic의 양방향 스트리밍 API가 필요하며, 이는 호환되는 boto3 버전과 us-east-1에서 활성화된 모델 접근에 의존합니다. 스트리밍 API를 사용할 수 없으면, 서비스는 플레이스홀더 확인 응답을 반환합니다. Nova Sonic 스트리밍이 올바르게 구성되면 완전한 실시간 전사가 작동합니다.

### 📝 6.10 뷰 상태 보존

내비게이션 순서: **Style Library → 2D Image Studio → Type Studio → Video Studio → Gallery**. 뷰 간 전환은 각 뷰의 DOM 상태를 보존합니다. 생성된 결과, 폼 입력, 스크롤 위치가 내비게이션에도 살아남습니다. 2D Image Studio와 Video Studio의 앰버 리셋 버튼이 그 상태를 지우는 유일한 방법입니다.

### 📝 6.11 모델 관리

모든 AI 모델 구성은 `backend/model_registry.json`에 중앙화되어 있습니다 — 단일 진실의 원천입니다. 모델, 리전, 요금, 품질 티어, 포맷 템플릿이 모두 여기에 저장되며 UI 또는 API를 통해 관리됩니다:

- 임의의 스튜디오 사이드바에서 **"Model Settings"**를 클릭하면 관리 모달이 열립니다 — 해당 스튜디오와 관련된 탭으로 열립니다.
- 스튜디오별로 정리된 **9개 탭**:
  - **Image Studio** — 이미지 생성 모델(SD 3.5 Large, Stable Image Ultra, Stable Image Core, 그리고 셀프 호스팅 FLUX, HunyuanImage, Qwen-Image), 리전, 품질 티어, 프롬프트 제한, 모더레이션 엄격도
  - **Video Studio** — 동영상 모델(Nova Reel, Luma Ray), S3 버킷 설정, 리전, 요금
  - **Chat Studio** — 검색된 채팅/LLM 모델(16개 제공업체의 80개 이상), 컨텍스트 윈도우, 비전 능력, 1K 토큰당 요금
  - **Type Studio** — 텍스트 레이아웃 생성용 LLM 모델(Complex 또는 Fast LLM)
  - **Shared Studio** — 스튜디오 간 LLM 카테고리(Fast LLM, Complex LLM, Fallback LLM, Voice), 후처리 모델(배경 제거, 업스케일)
  - **Custom Models** — 셀프 호스팅 모델 카탈로그: SageMaker 엔드포인트의 배포, 모니터링, 해제(6.12절 참조)
  - **Prompt Templates** — 6개 워크플로 섹션으로 정리된 28개의 편집 가능한 LLM 지시 프롬프트(4.4절 참조)
  - **Registry JSON** — 전체 모델 레지스트리용 원시 JSON 에디터
  - **Maintenance** — 관리형 도구 상태(예: FBX/USD 내보내기용 헤드리스 Blender — 경로, 버전, 온디맨드 업데이트)
- 모든 섹션은 빠른 내비게이션을 위해 **Show All / Hide All** 토글로 **접을 수 있습니다**.
- LLM 카테고리와 후처리는 **드롭다운 모델 피커**(검색된 모델에서 채워짐)를 사용합니다 — 원시 텍스트 필드가 아닙니다.
- **Sync from AWS**: 모든 Bedrock 지원 AWS 리전(동적으로 검색됨)을 스캔하고, 새 이미지, 동영상, **채팅 모델**을 자동 등록하며, 리전 가용성을 업데이트하고, AWS Pricing API에서 모델별 요금을 조회하며, 더 이상 사용할 수 없는 모델을 비활성화합니다. **라이브 진행 오버레이**가 스캔되는 각 리전을 스트리밍합니다. 이것이 AWS 검색 API를 호출하는 **유일한** 작업입니다 — 다른 모든 작업은 캐시된 레지스트리에서 읽습니다.
- **항상 최신 Claude로**: 각 Sync는 자동으로 **Fast LLM**을 계정에서 사용 가능한 최신 Claude Sonnet으로, **Complex LLM**을 최신 Claude Opus로 롤링하므로, 지원 중단된 모델에 갇히지 않습니다 — 수동 구성 불필요. 카테고리에 특정 모델을 수동으로 선택하면 **고정**되어 자동 롤이 건드리지 않습니다(더 새로운 것이 나타나면 알려줄 뿐입니다).
- **커스텀 모델 검색**: Sync는 **파인튜닝된 커스텀 모델**(`ListCustomModels`), **임포트된 모델**(`ListImportedModels`), 그리고 **온디맨드 배포**(`ListCustomModelDeployments`) 또는 **프로비저닝된 처리량**(`ListProvisionedModelThroughputs`)이 있는 모델도 검색합니다. 커스텀 모델은 베이스 모델로부터 포맷 패밀리를 자동으로 상속합니다.
- **자동 검색**: 새 기반 모델은 `enabled=true`로 등록됩니다 — 관리자가 비활성화할 수 있습니다. 기존 모델은 `available_regions`와 Bedrock 메타데이터(모달리티, 라이프사이클, ARN)가 자동으로 업데이트됩니다.
- **스타일드 확인 대화상자**: 모든 파괴적 작업(Sync, 삭제, 재설정)은 커스텀 스타일드 모달을 사용합니다 — 브라우저 `confirm()` 팝업 없음.
- 변경 사항은 Admin API를 통해 `model_registry.json`에 즉시 저장됩니다.
- 레지스트리는 하위 호환됩니다 — 기존 에셋은 원시 Bedrock 모델 ID가 아니라 모델 키(예: `sd35_large`)를 참조합니다.

### 📝 6.12 셀프 호스팅 모델(Amazon SageMaker의 커스텀 모델)

ArtSmoker는 당신의 AWS 계정에서 **Amazon SageMaker**에 오픈소스 AI 모델을 배포하여, Amazon Bedrock이 제공하는 것 이상으로 역량을 확장할 수 있습니다. 이 모델들은 Bedrock 모델과 나란히 실행되며 동일한 스튜디오 드롭다운에 나타납니다.

**확장 가능한 모델 카탈로그:** 이미지 생성, 업스케일링, 배경 제거, 깊이 추정, 세그멘테이션, 동영상에 걸친 오픈소스 모델의 내장 카탈로그가 함께 제공됩니다. 새 모델 추가에는 카탈로그 항목만 필요합니다 — 코드 변경 없음. UI(+ Add Model)로 커스텀 모델을 추가할 수도 있습니다. 카탈로그와 사용 가능한 모델은 시간이 지남에 따라 진화합니다.

**배포 옵션:**
- **비동기(scale-to-zero)** — 생성할 때만 지불. 유휴 시 제로로 스케일($0 비용), 새 요청 시 자동으로 스케일 업. 콜드 스타트 ~5-10분.
- **Always-On** — 즉각적인 응답, ~$1.41/시간(ml.g5.xlarge)

**배포 방법:** Model Settings → Custom Models 탭 → Deploy 클릭. SageMaker 컨테이너가 시작 시 HuggingFace에서 모델 가중치를 직접 가져옵니다 — 수 GB의 로컬 다운로드가 필요 없습니다.

**CPU 오프로딩:** 대형 디퓨전 모델은 더 작은 GPU 인스턴스에 맞추기 위해 지능형 CPU 오프로딩을 사용합니다. 각 모델의 카탈로그 항목이 전략을 지정합니다 — `model_cpu_offload`(활성 레이어를 GPU에 유지) 또는 `sequential_cpu_offload`(매우 큰 모델을 위한 공격적 레이어별 오프로드). 추론 핸들러가 자동으로 적용합니다.

**Pending Jobs가 있는 비동기 생성:** 셀프 호스팅 모델은 비동기적으로 생성합니다. 진행 표시기와 함께 활성 작업을 보여주는 **Pending Jobs** 패널이 2D Image Studio에 나타납니다. 완료된 이미지는 갤러리에 자동으로 도착합니다 — 폴링이나 페이지 새로고침 불필요.

**HuggingFace 토큰 관리:** 게이팅된 모델은 읽기 전용 HuggingFace 토큰이 필요합니다. 토큰은 당신의 계정 내 **AWS Secrets Manager**에 암호화되어 저장되고, UI를 통해 관리(설정/업데이트/삭제)되며, 이를 필요로 하는 모든 모델에 걸쳐 공유됩니다. 모든 모델을 티어다운하면 토큰이 자동으로 정리됩니다.

**게이팅 접근 사전 점검:** 게이팅된 배포 전에, 대화상자가 저장된 토큰을 사용하여 모델이 가져오는 **모든** HuggingFace repo(자체 가중치와 모든 의존성)를 프로빙하고, repo별로 ✓/✗와 정확한 다음 단계를 표시합니다 — HuggingFace에서 *이* repo의 라이선스를 수락하거나, 토큰을 추가. 모든 필수 repo에 도달할 수 있을 때까지 배포가 차단되므로, 잊어버린 라이선스 동의가 콜드 스타트 몇 분 후가 아니라 대화상자에서 빠르게 실패합니다.

**설정:** 이미 Bedrock에 사용 중인 **동일한 IAM 역할**에 Amazon SageMaker와 Secrets Manager 권한을 추가하세요 — 별도의 역할이나 환경 변수가 필요 없습니다. ArtSmoker는 EC2/ECS에서 역할을 자동 검색하거나, 필요하면 `ArtSmokerSageMakerRole`을 자동 생성합니다.

```bash
# Add Amazon SageMaker permissions to your existing ArtSmoker role (one command)
aws iam attach-role-policy --role-name ArtSmokerEC2Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
```

**Python 의존성:** `huggingface_hub>=0.23`(`pip install huggingface_hub`로 설치)

### 📝 6.13 이미지 및 동영상 생성 모델

모든 모델은 레지스트리에서 **동적으로 검색**됩니다 — 하드코딩되지 않습니다. Image Studio 드롭다운은 페이지 로드 시 `GET /api/admin/models/image-options`에서, Video Studio 드롭다운은 `GET /api/admin/models/video-options`에서 채워집니다. 레지스트리에 등록되고 활성화된 모든 모델이 자동으로 나타납니다.

**Image Model** 드롭다운이 기본 선택입니다. 그 아래에 스마트 요약 줄이 활성 리전, 품질 티어, 이미지당 비용을 표시합니다. 확장 가능한 **Advanced** 섹션에서 다음을 재정의할 수 있습니다:

- **Quality** — 품질 티어를 지원하는 모델(Standard/Premium 가격 분할)은 드롭다운을 표시하고, 티어가 없는 모델은 "Default"를 표시합니다. 티어는 레지스트리의 `quality_options`를 통해 모델별로 선언됩니다.
- **Region** — 선택한 모델이 사용 가능한 리전을 요금과 함께 저렴한 순으로 정렬해 표시합니다. "Auto"는 가장 저렴한 리전을 선택합니다.

**비용 추정**은 모든 선택(모델 × 품질 × 리전 × 옵션 × 배리에이션)에 따라 동적으로 업데이트됩니다.

**포맷 패밀리**: 모델은 레지스트리(`format_families`)에서 요청 템플릿을 읽는 제네릭 인보커를 통해 호출됩니다 — 생성, 편집, 후처리, 동영상 모두 템플릿 기반입니다. 새 Bedrock 이미지 모델 추가에는 **코드 변경이 전혀 필요 없습니다**: 올바른 포맷 패밀리로 (자동 검색 또는 관리 API를 통해) 등록만 하면 됩니다. 전체 패밀리 카탈로그는 [SPEC.md](SPEC.md)에 있습니다.

**모델 최적화 프롬프트 엔지니어링**: 프롬프트는 [AWS 문서](https://docs.aws.amazon.com/nova/latest/userguide/prompting-image-generation.html)에 따라 자동으로 설명적 캡션(명령이 아님)으로 구조화됩니다. 부정 단어는 메인 프롬프트에서 제거되고 제외 용어는 별도의 **네거티브 프롬프트**로 전송됩니다. 프롬프트는 레지스트리의 각 모델별 `prompt_limit`으로 잘립니다.

> [!NOTE]
> **모더레이션 민감도는 모델별로 다르며** 레지스트리(`moderation_strictness`)에 추적됩니다. Amazon Bedrock Stability 모델(SD 3.5 Large, Stable Image Ultra, Stable Image Core)은 AWS 플랫폼 모더레이션을 적용하며 "moderate"로 튜닝됩니다; 셀프 호스팅 모델(FLUX, HunyuanImage, Qwen-Image)은 플랫폼이 강제하는 콘텐츠 필터 없이 당신의 계정에서 실행됩니다. ArtSmoker는 차단을 자동으로 처리합니다 — 프롬프트가 거부되면, 시스템은 리라이트를 제안하기 전에 엄격도 순으로 정렬된 대체 모델을 시도합니다.

## 📌 7. 기술 스택

| 레이어 | 기술 |
|--------|------|
| 백엔드 | FastAPI (Python 3.11+), boto3, Pydantic |
| 프론트엔드 | Vanilla JS, Tailwind CSS (CDN) |
| AI (LLM) | Claude Sonnet(빠른 작업), Claude Opus(복잡한 작업) |
| AI (이미지) | Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core (Amazon Bedrock); FLUX.2/FLUX.1, HunyuanImage 3.0, Qwen-Image (SageMaker 셀프 호스팅) |
| AI (후처리) | Stability AI(배경 제거, Creative Upscale) |
| AI (채팅) | Bedrock ConverseStream을 통한 16개 제공업체의 80개 이상 LLM(Claude, Nova, Llama, Mistral 등) |
| AI (동영상) | Nova Reel v1.0/v1.1(최대 2분), Luma AI Ray v2(최대 9초) |
| AI (음성) | Nova Sonic(양방향 스트리밍을 통한 음성-텍스트 변환) |
| i18n | 커스텀 t() 함수, 약 1,500개 키 × 9개 언어, 역방향 조회 DOM 번역 |
| SVG 변환 | vtracer(기본), potrace(폴백), Pillow(최후 수단) |
| 텍스트 렌더링 | Pillow(그림자, 아웃라인, 글로우 효과) |
| 스토리지 | 로컬 파일 시스템(S3 대응 인터페이스) |
| 개발 | 정적 파일용 노캐시 미들웨어; `POST /api/log`를 통한 클라이언트 사이드 에러 로깅 |

프론트엔드에 빌드 단계가 필요 없습니다.

## 📌 8. 보안 모델

ArtSmoker는 **로컬/신뢰 네트워크 개발 도구**로 설계되었습니다 — 개발자의 로컬 머신이나 프라이빗 EC2 인스턴스에서 실행됩니다. 보안 모델은 이를 반영합니다:

- **인증 없음** — 모든 API 엔드포인트가 개방되어 있습니다. 로컬 개발 및 프라이빗 팀 배포에 적합합니다.
- **파일 시스템 브라우저** — `GET /api/browse/local` 엔드포인트는 서버 프로세스가 접근할 수 있는 모든 디렉터리의 탐색을 허용합니다. 머신에서 레퍼런스 아트를 가져오기 위해 의도된 것입니다.
- **폰트 서빙** — 경로 순회 보호가 폰트 파일 요청이 예상된 디렉터리 내에 머무는지 검증합니다.
- **S3 접근** — S3 탐색과 가져오기는 서버의 AWS 인증 정보를 사용합니다. 사용자는 자신의 IAM 역할이 허용하는 모든 S3 버킷에 접근할 수 있습니다.

> [!WARNING]
> 인증과 경로 제한을 추가하지 않고 신뢰할 수 없는 네트워크에 ArtSmoker를 노출하지 마세요. 프로덕션 강화 가이드는 [SPEC.md의 배포 로드맵](SPEC.md#16-deployment--scaling-roadmap)을 참조하세요(Phase 4에서 Cognito 인증을 추가합니다).

## 📌 9. API

**http://localhost:8000/docs**(Swagger UI)에 인터랙티브 문서가 있습니다.

주요 엔드포인트:

| 엔드포인트 | 목적 |
|----------|------|
| **Generation** | |
| `POST /api/generate/` | SSE 스트리밍으로 에셋 생성(옵션 × 배리에이션) |
| `POST /api/generate/post-process` | 기존 에셋에 처리 적용 |
| `POST /api/generate/edit` | 이미지 편집: 인페인트, 아웃페인트, 지우기, 검색-교체 등. 소스 이미지, 마스크, 프롬프트, 모델을 받습니다. |
| `POST /api/generate/suggest-edit-prompt` | Edit 탭용 AI "Generate Prompt": 이미지 + 원본 프롬프트를 읽고 주어진 모드에 대한 편집 프롬프트를 대상 편집 모델에 맞게(캡션 대 지시문) 반환 |
| `POST /api/generate/analyze-moderation` | 모더레이션 차단된 프롬프트를 분석하고 안전한 리라이트 제안 |
| **Styles** | |
| `POST /api/styles/` | 스타일 프로필 생성 |
| `POST /api/styles/{id}/import` | 로컬 폴더나 S3 URI에서 레퍼런스 일괄 가져오기 |
| `POST /api/styles/{id}/analyze` | AI 스타일 분석 트리거 |
| **Prompt** | |
| `POST /api/refine-prompt/` | 정제된 프롬프트 미리보기 |
| `POST /api/transcribe/` | 음성-텍스트(Nova Sonic) |
| **Gallery** | |
| `GET /api/gallery/` | 생성된 에셋 탐색(limit/offset 페이지네이션 지원) |
| `GET /api/gallery/batch/{batch_id}` | 배치의 전체 옵션 × 배리에이션 구조 재구성 |
| `DELETE /api/gallery/` | 에셋 일괄 삭제 |
| **Type Studio** | |
| `POST /api/type-studio/preview` | 텍스트 오버레이 미리보기 렌더링 |
| `POST /api/type-studio/suggest` | 텍스트용 AI 레이아웃 제안 |
| `GET /api/type-studio/fonts` | 사용 가능한 폰트 목록 |
| **Browse** | |
| `GET /api/browse/local?path=~` | 로컬 디렉터리 콘텐츠 탐색 |
| `GET /api/browse/s3/buckets` | 사용 가능한 S3 버킷 목록 |
| `GET /api/browse/s3?bucket=name&prefix=path` | S3 버킷 콘텐츠 탐색 |
| **Chat** | |
| `POST /api/chat/stream` | SSE를 통한 LLM 응답 스트리밍(Bedrock ConverseStream) |
| `GET /api/chat/models` | 사용 가능한 모든 채팅 모델 목록(foundation + custom + imported) |
| `POST /api/chat/sessions` | 새 채팅 세션 생성 |
| `GET /api/chat/sessions` | 채팅 세션 목록 |
| `GET /api/chat/sessions/{id}` | 전체 세션 로드(메시지 + 메타데이터) |
| `PUT /api/chat/sessions/{id}` | 세션 업데이트(제목, 메시지, 모델, temperature) |
| `DELETE /api/chat/sessions/{id}` | 세션 삭제 |
| `POST /api/chat/sessions/{id}/duplicate` | 세션 복제 |
| `GET /api/chat/sessions/{id}/export` | 세션을 마크다운으로 내보내기 |
| `GET /api/chat/sessions/{id}/search?q=` | 세션 메시지 내 검색 |
| `POST /api/chat/compact` | LLM 요약을 통해 오래된 메시지 압축 |
| `POST /api/chat/generate-title` | 첫 교환에서 세션 제목 자동 생성 |
| **Video** | |
| `POST /api/video/generate` | 비동기 동영상 생성 작업 시작 |
| `GET /api/video/status/{job_id}` | 동영상 생성 작업 상태 폴링 |
| `GET /api/video/jobs` | 모든 동영상 생성 작업 목록 |
| `GET /api/video/{id}/mp4` | 동영상 MP4 파일 서빙 |
| `GET /api/video/{id}/thumbnail` | 동영상 썸네일 서빙 |
| `DELETE /api/video/{id}` | 동영상 삭제 |
| **Admin** | |
| `GET /api/admin/models` | 전체 모델 레지스트리 조회(LLM, 이미지 모델, 후처리) |
| `GET /api/admin/models/image-options` | 드롭다운용 활성화된 텍스트-이미지 모델(요금, 품질 티어, 리전 포함). `?region=` 필터 허용. |
| `GET /api/admin/regions` | Bedrock 지원 AWS 리전의 캐시된 목록(AWS 호출 없음) |
| `PATCH /api/admin/models/category/{name}` | LLM 카테고리 구성 업데이트 |
| `PATCH /api/admin/models/image/{key}` | 이미지 모델 구성 업데이트 |
| `POST /api/admin/models/image` | 새 이미지 모델 추가 |
| `POST /api/admin/discover/refresh-all` | 전체 새로고침: 리전 검색 + 모델 스캔 + 요금 조회 + 오래된 데이터 정리. AWS 검색 API를 호출하는 유일한 엔드포인트. |
| `POST /api/admin/discover/{region}/auto-register` | 단일 리전에서 모델 스캔, 새 모델 등록, 기존 모델의 리전 업데이트 |
| `GET /api/admin/discover/{region}` | 리전에서 사용 가능한 Bedrock 모델 검색(원시 목록) |
| `GET /api/admin/templates` | 28개의 편집 가능한 프롬프트 템플릿 모두 조회 |
| `PATCH /api/admin/templates/{name}` | 템플릿 업데이트(필수 변수 검증) |
| `POST /api/admin/templates/{name}/reset` | 템플릿을 기본값으로 재설정 |
| `POST /api/admin/templates/{name}/enhance` | AI로 템플릿 강화 |
| **System** | |
| `POST /api/log` | 클라이언트 사이드 에러/경고 로깅(서버 콘솔에 `[CLIENT]`로 기록) |
| `GET /api/health` | 헬스 체크 + AWS 인증 정보/Bedrock 검증 |

## 📌 10. 프로젝트 구조

```
ArtSmoker/
├── backend/
│   ├── main.py              # FastAPI app, startup validation, static mount
│   ├── config.py            # Settings (AWS regions, model IDs, paths, limits)
│   ├── model_registry.json  # Single source of truth: models, regions, pricing, format families, quality tiers
│   ├── requirements.txt
│   ├── prompt_templates.json # Editable LLM directive prompts — runtime source of truth (28 templates)
│   ├── routers/
│   │   ├── generate.py      # Two-level asset generation + SSE streaming
│   │   ├── styles.py        # Style profile CRUD + directory/S3 import + analysis
│   │   ├── gallery.py       # Asset browsing + file serving + bulk delete
│   │   ├── typestudio.py    # Type Studio: text overlay, font serving, AI layout
│   │   ├── video.py         # Video generation (async), job polling, MP4/thumbnail serving
│   │   ├── chat.py          # Chat Studio: LLM streaming, sessions, export, context compaction
│   │   ├── browse.py        # Server-side file/S3 browser for reference import
│   │   ├── refine.py        # Prompt refinement preview + translation preview
│   │   ├── transcribe.py    # Voice transcription
│   │   └── admin.py         # Model registry management + Bedrock discovery + prompt templates
│   ├── services/
│   │   ├── bedrock_client.py     # Shared Bedrock client with connection pooling
│   │   ├── model_registry.py     # Model registry: loads/saves model_registry.json
│   │   ├── prompt_engineer.py    # Claude: prompt refinement + concept generation
│   │   ├── image_generator.py    # Routes to Bedrock (SD 3.5 / Ultra / Core) or SageMaker (FLUX / Hunyuan / Qwen)
│   │   ├── style_analyzer.py     # Two-phase style analysis (cohesion + full)
│   │   ├── post_processor.py     # Stability AI: bg removal, upscale; vtracer: SVG
│   │   ├── transcriber.py        # Nova Sonic: streaming speech-to-text
│   │   ├── import_dedup.py       # Smart deduplication (rotations, animations, folders)
│   │   ├── texture_extractor.py  # glTF/GLB texture extraction
│   │   ├── prompt_translator.py  # Auto-detect language + translate to English
│   │   ├── prompt_templates.py   # Editable LLM directive prompts (load/save/validate)
│   │   ├── video_generator.py   # Video: async Bedrock invoke, S3 download, ffmpeg thumbnails
│   │   ├── cost_tracker.py      # Request-scoped cost accumulator
│   │   ├── custom_models.py    # Self-hosted model catalog (extensible)
│   │   ├── async_jobs.py       # Async generation job queue (Pending Jobs panel)
│   │   ├── sagemaker_deployer.py # Amazon SageMaker endpoint management (direct HF pull for HF models)
│   │   └── sagemaker_invoker.py  # Routes inference to Amazon SageMaker endpoints
│   ├── models/
│   │   ├── style_profile.py       # StyleProfile, AnalyzedStyle, Create/Update
│   │   ├── generation_request.py  # GenerationRequest, AssetType, ImageModel enums
│   │   └── generation_result.py   # GenerationResult, OptionResult, VariantResult
│   └── storage/
│       └── local_store.py         # Local filesystem (S3-compatible interface)
├── frontend/
│   ├── index.html           # SPA entry point
│   ├── css/styles.css       # Dark theme + animations
│   └── js/
│       ├── app.js               # SPA router + DOM caching + navigation + showConfirm()
│       ├── i18n/
│       │   ├── i18n.js          # Core: t() function, language switching, reverse lookup
│       │   ├── en.json          # English (base) — ~1,500 keys
│       │   └── ja/zh/ko/hi/ru/fr/es/de.json   # 8개 번역
│       ├── services/api.js      # Backend API client
│       └── components/
│           ├── ImageStudio.js   # 2D Image Studio (options × variations)
│           ├── TypeStudio.js    # Type Studio (text overlay)
│           ├── VideoStudio.js   # Video Studio (text-to-video generation)
│           ├── ChatStudio.js    # Chat Studio (multi-model LLM chat)
│           ├── Gallery.js       # Gallery grid + search + bulk ops
│           ├── StyleLibrary.js  # Style management + file browser
│           ├── AssetViewer.js   # Full-size preview + metadata + download
│           ├── ModelSettings.js # Model registry admin UI (modal)
│           ├── PromptEditor.js  # Two-area prompt editor + compose
│           └── VoiceInput.js    # MediaRecorder + transcription
├── data/
│   ├── styles/              # Style profiles + reference images (symlinked)
│   ├── generated/           # Output assets (PNG + SVG + metadata.json)
│   ├── video/               # Video assets (MP4 + thumbnails + job metadata)
│   └── chat/                # Chat sessions (JSON per session)
├── SPEC.md                  # Full technical specification (rebuild blueprint)
└── README.md                # This file
```

## 📌 11. 구성 가능한 제한값

`backend/config.py`의 설정은 환경 변수(접두사 `ARTSMOKER_`)로 재정의할 수 있습니다:

| 설정 | 환경 변수 | 기본값 | 목적 |
|------|----------|--------|------|
| `max_reference_images` | `ARTSMOKER_MAX_REFERENCE_IMAGES` | 100 | 스타일당 가져오는 최대 이미지 수 |
| `max_analysis_images` | `ARTSMOKER_MAX_ANALYSIS_IMAGES` | 20 | 분석 호출당 AI에 보내는 최대 이미지 수 |
| `aws_region_models` | `ARTSMOKER_AWS_REGION_MODELS` | us-west-2 | Claude + Stability AI 모델용 리전 |
| `aws_region_images` | `ARTSMOKER_AWS_REGION_IMAGES` | us-east-1 | Amazon용 리전(Nova Sonic 음성, Nova Reel 동영상) |
| `aws_profile` | `ARTSMOKER_AWS_PROFILE` | None | AWS 프로필 이름(미설정 시 기본 체인 사용) |
| `auto_update` | `ARTSMOKER_AUTO_UPDATE` | true | 시작 시 버전 게이트 업데이트 + 24시간 주기 확인(git 또는 tarball), 이후 그 자리에서 재시작 |

`max_analysis_images`를 줄이면 분석당 AI 비전 비용이 줄어듭니다. `max_reference_images`를 줄이면 스토리지가 제한됩니다. 둘 다 예산에 따라 조정할 수 있습니다.

## 📌 12. Amazon Bedrock 요금 및 비용 내역

> [!IMPORTANT]
> **모델은 빠르게 지원 중단되고 변경됩니다.** 새 모델이 자주 출시되고 오래된 모델은 자주 폐기되므로, 문서에 하드코딩된 특정 모델 이름이나 요금은 금방 오래된 정보가 됩니다. ArtSmoker는 이를 자동으로 처리합니다 — 각 **Sync from AWS**는 현재 모델 라인업을 다시 검색하고, 공유 LLM 슬롯을 최신 Claude Sonnet/Opus로 자동 롤링하며, AWS Pricing API에서 실시간 모델별 요금을 `model_registry.json`으로 새로 고칩니다. **앱이 진실의 원천**입니다 — 어떤 모델이 존재하는지와 각각이 얼마인지(선택한 모델, 품질 티어, 리전, 배치 크기에 따라 Image Studio 사이드바에 실시간 표시) 모두에 대해. 아래의 모델 이름과 숫자는 **예시일 뿐**입니다 — 항상 앱 내 또는 공식 [Amazon Bedrock 요금 페이지](https://aws.amazon.com/bedrock/pricing/)에서 현재 모델/요금을 확인하세요.

앱의 **기본 리전**은 `us-west-2`(Claude, Stability AI)와 `us-east-1`(Amazon Nova Sonic, Nova Reel)입니다; 가격은 리전별로 다릅니다. 비용 모델은 [SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown)도 참조하세요.

### 📝 12.1 단위당 요금

비용이 발생하는 항목과 과금 단위(현재 단위당 가격은 앱 참조):

| 서비스 | 과금 | 비고 |
|--------|------|------|
| **LLM 프롬프트 엔지니어링 및 채팅**(Claude Sonnet / Opus, Sync 시 최신으로 자동 롤링) | 입력 / 출력 토큰당 | 프롬프트 정제, 컨셉, 채팅, 스타일 분석, 모더레이션 |
| **Bedrock 이미지 생성**(Stable Diffusion 3.5 Large, Stable Image Ultra, Stable Image Core) | 이미지당 | 가격은 Ultra ≫ SD 3.5 ≫ Core; 실시간 수치는 앱 내 표시 |
| **셀프 호스팅 이미지 / 3D**(FLUX, HunyuanImage, Qwen-Image, TripoSG, TRELLIS.2) | SageMaker 인스턴스의 GPU-초당 | 유휴 시 scale-to-zero($0); 이미지당 과금 아님 |
| **후처리**(배경 제거, Creative Upscale) | 이미지당 | Stability AI 서비스 |
| **SVG 변환** | 무료 | 로컬(vtracer/potrace) — $0.00 |

> [!NOTE]
> 2026년 3월 기준 공식 [Amazon Bedrock 요금 페이지](https://aws.amazon.com/bedrock/pricing/)의 가격입니다. 가격은 변경될 수 있습니다 — 예산 책정 전에 항상 공식 출처와 대조하여 확인하세요.

### 📝 12.2 추가 LLM 비용(사용당)

이 LLM 호출들은 생성 워크플로에 포함되지만 아래 배치 비용 표에는 별도로 항목화되지 않습니다:

| 호출 | 모델 | 시점 | 대략적 비용 |
|------|------|------|-------------|
| **Prompt Pre-Check** | Claude Sonnet | 생성 전(토글 활성화 시) | ~$0.005 |
| **Moderation Rewrite** | Claude Sonnet | 모든 모델이 프롬프트를 거부할 때만 | ~$0.005 |
| **Type Studio Layout** | Claude Opus | 각 AI 레이아웃 제안 요청 | ~$0.02–$0.05 |

이들은 작습니다 — 사전 검토와 모더레이션 리라이트는 각각 1센트의 일부입니다. Type Studio 레이아웃은 단일 옵션 프롬프트 정제와 비슷합니다.

### 📝 12.3 스타일 분석 비용(스타일당 일회성)

스타일당 ~**$0.14**(Claude Opus에 보내는 20개 이미지 + Claude Sonnet의 8개 이미지 응집도 검사). 응집도 검사는 ~$0.01을 추가합니다(8개 이미지의 Sonnet은 매우 저렴).

### 📝 12.4 배치 크기별 생성 비용

프롬프트 정제/컨셉 생성 + 이미지 생성 포함:

| 시나리오 | Stable Image Core | Stable Diffusion 3.5 Large | Stable Image Ultra |
|----------|-------------------|-------------|-------------------|
| 1 option × 1 variation | ~$0.05 | ~$0.09 | ~$0.15 |
| 1 option × 5 variations | ~$0.21 | ~$0.41 | ~$0.71 |
| 5 options × 5 variations | ~$1.05 | ~$2.05 | ~$3.55 |

셀프 호스팅 SageMaker 모델(FLUX, HunyuanImage, Qwen-Image)은 이미지당이 아니라 자체 인스턴스의 GPU 시간으로 과금됩니다(유휴 시 scale-to-zero) — 컴퓨팅 비용 모델은 [SPEC.md](SPEC.md#14-amazon-bedrock-pricing--cost-breakdown)를 참조하세요.

### 📝 12.5 후처리 애드온(이미지당)

| 애드온 | 이미지당 | 1개 이미지 | 5개 이미지 | 25개 이미지 |
|--------|-----------|---------|----------|-----------|
| Remove Background | $0.07 | $0.07 | $0.35 | $1.75 |
| Creative Upscale | $0.60 | $0.60 | $3.00 | $15.00 |
| Convert to SVG | $0.00 | $0.00 | $0.00 | $0.00 |

> [!TIP]
> **Creative Upscale 참고**: 내부적으로 JPEG 출력 포맷을 사용한 뒤 PNG로 다시 변환하여 Stability AI의 16MB 응답 페이로드 제한을 자동으로 처리합니다. API 스로틀링에 대한 지수 백오프 재시도를 포함합니다.

### 📝 12.6 실제 예시

| 예시 | 구성 | 총 비용 |
|------|------|--------|
| **가장 저렴** | 1×1, Stable Image Core, 처리 없음 | ~$0.05 |
| **표준** | 1×5, Stable Diffusion 3.5 Large, Remove BG | ~$0.76 |
| **전체 탐색** | 5×5, Stable Diffusion 3.5 Large, Remove BG + SVG | ~$3.80 |
| **프리미엄** | 5×5, Stable Image Ultra, Remove BG + Upscale + SVG | ~$20.30 |

> [!TIP]
> **핵심 포인트**: 이미지 생성 자체는 저렴합니다($0.01–$0.14/이미지). **Creative Upscale이 $0.60/이미지로 가장 큰 비용 요인**입니다 — 전체 배치가 아니라 최종 선택한 에셋에 선별적으로 사용하세요. 배경 제거는 $0.07/이미지로 합리적입니다. SVG 변환은 무료(로컬 실행)입니다.

<a id="disclaimer"></a>

## 📌 13. 면책 조항

> [!IMPORTANT]
> **생성 콘텐츠 품질**: ArtSmoker에 의해 생성되는 모든 이미지, 동영상 및 기타 에셋은 Amazon Bedrock을 통해 이용 가능한 AI 모델에 의해 만들어지며, 여기에는 AWS 자체 모델과 서드파티 모델이 모두 포함됩니다. 생성 콘텐츠의 품질, 정확성, 적절성은 사용자가 제공하는 프롬프트, 선택한 모델, 업로드한 스타일 레퍼런스에 전적으로 의존합니다. ArtSmoker의 저자 및 기여자는 생성된 콘텐츠의 품질, 적합성 또는 목적 적합성에 대해 어떠한 보증도 하지 않습니다.
>
> **지적 재산**: 사용자는 프롬프트, 레퍼런스 이미지, 생성 출력이 저작권, 상표, 초상권을 포함하되 이에 국한되지 않는 제3자의 지적 재산권을 침해하지 않도록 할 전적인 책임을 집니다. ArtSmoker는 도구이며 — 입력이나 출력의 IP 상태를 필터링, 검증 또는 평가하지 않습니다. 도구의 저자 및 기여자는 본 소프트웨어 사용으로 발생하는 어떠한 IP 침해에도 책임을 지지 않습니다.
>
> **AI 모델 및 서비스 약관**: 생성 콘텐츠는 Amazon Bedrock을 통해 접근할 수 있는 기반 AI 모델 제공업체의 서비스 약관 및 허용 사용 정책의 적용을 받습니다. 사용자는 생성 에셋을 프로덕션 또는 상업적 맥락에서 사용하기 전에 [AWS 서비스 약관](https://aws.amazon.com/service-terms/), [Amazon Bedrock SLA](https://aws.amazon.com/bedrock/sla/), 개별 모델 제공업체 약관을 검토해야 합니다.
>
> **모델 라이선스 및 상업적 사용**: ArtSmoker를 통해 배포되는 셀프 호스팅 모델에는 각 제작자의 라이선스 약관이 적용되며, 이 약관은 **사용자 본인**을 직접 구속합니다. ArtSmoker는 배포 시점에 각 모델의 라이선스와 의존성 내역을 표시하고 사용자의 동의를 기록하지만, 사용자의 상업적 사용 권한을 검증, 집행 또는 보증하지는 **않습니다** — 라이선스 조건(매출/사용자 기준선, 지역 제한, 저작자 표시 요건, 사용량 보고) 준수는 전적으로 사용자의 책임입니다. [1.9.3절](#-193-모델을-상업적으로-사용하기--누구에게-어떻게-지불하나)의 상업 라이선스 안내는 참고용 정보일 뿐이며, 작성 시점의 벤더 약관을 반영한 것으로 **법률 자문이 아닙니다**. 라이선스 조건은 자주 변경되므로 항상 벤더의 최신 약관을 확인하고, 상업적 출시 전에는 법률 전문가와 상담하세요. ArtSmoker는 어떤 모델 벤더와도 제휴 관계가 없으며, 그 어떤 대가도 받지 않습니다.
>
> **비용은 추정치일 뿐 — 본인의 지출을 직접 모니터링하세요**: ArtSmoker에 표시되는 모든 비용(이미지·동영상·토큰 단위, 3D 컴퓨팅, 배포, 세션/에셋 합계)은 AWS 공시 가격과 예상 사용량으로 계산한 **참고용 추정치**입니다. 실제 청구액에 대한 **청구서도 보증도 아닙니다**. 실제 비용은 AWS 계정 가격, 리전, 할인, 세금, 데이터 전송, 엔드포인트 가동 시간(유휴/웜 상태의 SageMaker 인스턴스 포함), 오토스케일링 동작 등 본 도구 외의 요인에 따라 달라집니다. **본인의 AWS 지출 모니터링과 관리는 전적으로 사용자 책임입니다** — [AWS 청구 콘솔](https://console.aws.amazon.com/billing/), [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/), [예산/청구 경보](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)로 실제 요금을 추적하고 상한을 설정하세요. 특히 셀프 호스팅 SageMaker 엔드포인트는 배포되거나 웜 상태로 유지되는 동안 유휴 상태에서도 계속 과금됩니다 — 사용을 마치면 반드시 티어다운하세요. 저자와 기여자는 본 소프트웨어 사용으로 발생한 어떠한 AWS 요금에도 책임을 지지 않습니다.
>
> **무보증**: 이 소프트웨어는 어떠한 종류의 보증 없이 "있는 그대로" 제공됩니다. 전체 조건은 [LICENSE](LICENSE)를 참조하세요.

## 📌 14. 전체 사양서

전체 기술 사양은 **[SPEC.md](SPEC.md)**를 참조하세요 — 아키텍처, 컴포넌트 설계, 모델 구성, API 레퍼런스, 보안 모델, 요금, 배포 로드맵, 그리고 프로젝트를 처음부터 다시 구축하기에 충분한 세부 정보가 포함되어 있습니다.
