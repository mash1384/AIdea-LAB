# AIdea Lab

AIdea Lab은 사용자가 아이디어를 입력하면, 다양한 AI 페르소나 에이전트들이 각자의 관점에서 아이디어를 분석하고 피드백을 제공하는 워크숍 형태의 응용 프로그램입니다.

## 설치 방법

### 1. 프로젝트 클론 및 가상환경 설정

```bash
# 저장소 클론 (git 저장소가 있는 경우)
# git clone https://github.com/your-username/aidea-lab.git
# cd aidea-lab

# 가상환경 생성 및 활성화
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 2. 필수 라이브러리 설치

```bash
pip install -r requirements.txt
```

### 3. 애플리케이션 실행

```bash
streamlit run src/ui/app.py
```

### 4. Google API 키 설정

애플리케이션을 실행한 후, 웹 브라우저에서 다음과 같이 API 키를 설정하세요:

1. **사이드바에서 API 키 입력**: 
   - 애플리케이션 좌측 사이드바의 "🔑 Google API 키 설정" 섹션을 찾으세요.
   - "Google API 키를 입력하세요" 필드에 API 키를 입력합니다.
   - "🔐 API 키 적용" 버튼을 클릭합니다.

2. **API 키 발급**:
   - [Google AI Studio](https://makersuite.google.com/) 또는 [Google Cloud Console](https://console.cloud.google.com/)에서 Gemini API 키를 발급받을 수 있습니다.

3. **API 키 확인**:
   - API 키가 올바르게 설정되면 사이드바에 녹색 체크마크(✅)가 표시됩니다.
   - 설정에 문제가 있으면 빨간색 X 마크(❌)와 함께 오류 메시지가 표시됩니다.

⚠️ **주의**: API 키 없이는 AI 분석 기능을 사용할 수 없습니다. LLM 기능을 시도하면 API 키 설정을 요구하는 메시지가 표시됩니다.

## 사용 방법

1. **아이디어 입력**: 메인 화면 하단의 채팅 입력창에 분석하고 싶은 아이디어를 입력합니다.
2. **상세 정보 입력 (선택사항)**: "아이디어 상세 정보 입력" 버튼을 클릭하여 목표, 제약조건, 가치 등을 추가로 입력할 수 있습니다.
3. **1단계 분석**: AI 페르소나들(마케터, 비판적 분석가, 현실주의 엔지니어)이 각자의 관점에서 아이디어를 분석합니다.
4. **2단계 토론 (선택사항)**: 1단계 완료 후 "💬 2단계 토론 시작하기" 버튼을 클릭하여 AI 페르소나들 간의 심층 토론을 진행합니다.

## 환경 변수 설정 (선택사항)

기본값으로 API 키를 설정하고 싶다면 다음 중 하나의 환경 변수를 설정할 수 있습니다:

```bash
# 사용자 입력용 기본값 (우선순위 높음)
GOOGLE_API_KEY_USER_INPUT="YOUR_ACTUAL_API_KEY"

# 또는 기본 환경 변수
GOOGLE_API_KEY="YOUR_ACTUAL_API_KEY"
```

하지만 **권장하는 방식은 애플리케이션 실행 후 사이드바 UI를 통해 직접 입력하는 것**입니다.

## 테스트 실행

### 1. 기본 ADK 에이전트 테스트

```bash
python src/poc/simple_adk_agent.py
```

### 2. 세션 상태 테스트

```bash
python src/poc/session_state_test_agent.py
```

### 3. API 키 유효성 테스트

```bash
python check_api_key.py
```

## 프로젝트 구조

```
aidea-lab/
├── .env                    # 환경 변수 설정 파일 (선택사항)
├── requirements.txt        # 필수 라이브러리
├── README.md               # 프로젝트 설명
├── check_api_key.py        # API 키 유효성 테스트 스크립트
├── src/                    # 소스 코드
│   ├── agents/             # AI 페르소나 에이전트
│   ├── orchestrator/       # 오케스트레이터 (워크플로우 에이전트)
│   ├── ui/                 # 사용자 인터페이스
│   │   ├── app.py          # 메인 Streamlit 앱
│   │   ├── views.py        # UI 렌더링 함수들
│   │   └── state_manager.py # 애플리케이션 상태 관리
│   └── poc/                # 개념 증명 테스트 코드
├── config/                 # 설정 파일
├── tests/                  # 테스트 코드
├── docs/                   # 문서
└── scripts/                # 유틸리티 스크립트
``` 