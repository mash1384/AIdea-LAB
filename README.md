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

### 3. 환경 변수 설정

1. 프로젝트 루트 디렉토리에 있는 `.env` 파일을 열고 필요한 API 키를 설정합니다.
   ```
   GOOGLE_API_KEY="YOUR_ACTUAL_API_KEY"
   ```
   - [Google AI Studio](https://makersuite.google.com/) 또는 [Google Cloud Console](https://console.cloud.google.com/)에서 Gemini API 키를 발급받을 수 있습니다.

## 테스트 실행

### 1. 기본 ADK 에이전트 테스트

```bash
python src/poc/simple_adk_agent.py
```

### 2. 세션 상태 테스트

```bash
python src/poc/session_state_test_agent.py
```

## 프로젝트 구조

```
aidea-lab/
├── .env                    # 환경 변수 설정 파일 (API 키 등)
├── requirements.txt        # 필수 라이브러리
├── README.md               # 프로젝트 설명
├── src/                    # 소스 코드
│   ├── agents/             # AI 페르소나 에이전트
│   ├── orchestrator/       # 오케스트레이터 (워크플로우 에이전트)
│   ├── ui/                 # 사용자 인터페이스
│   └── poc/                # 개념 증명 테스트 코드
├── config/                 # 설정 파일
├── tests/                  # 테스트 코드
├── docs/                   # 문서
└── scripts/                # 유틸리티 스크립트
``` 