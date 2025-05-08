# AIdea Lab 아키텍처 설명서

## 프로젝트 구조

AIdea Lab은 다음과 같은 디렉토리 구조로 설계되었습니다:

```
aidea-lab/
│
├── src/                      # 소스 코드
│   ├── agents/               # AI 페르소나 에이전트 클래스
│   │   └── critic_agent.py   # 비판적 분석가 페르소나 에이전트
│   ├── orchestrator/         # 오케스트레이터 에이전트 클래스
│   ├── ui/                   # 사용자 인터페이스 코드
│   │   └── app.py            # Streamlit 기반 UI 애플리케이션
│   └── poc/                  # 개념 증명 (Proof of Concept) 코드
│       ├── simple_adk_agent.py      # 기본 ADK Agent 테스트
│       └── session_state_test_agent.py  # ADK session.state 테스트
│
├── config/                   # 설정 파일
│   ├── prompts.py            # 페르소나별 시스템 프롬프트 정의
│   └── personas.py           # 페르소나 설정 및 매개변수 정의
│
├── tests/                    # 테스트 코드
│   ├── test_critic_agent.py  # 비판적 분석가 에이전트 테스트
│   └── test_app.py           # UI 애플리케이션 테스트
│
├── docs/                     # 문서
├── scripts/                  # 유틸리티 스크립트
└── .env                      # 환경 변수 설정 파일
```

## 핵심 구성 요소

### 1. config/prompts.py

이 파일은 다양한 AI 페르소나의 시스템 프롬프트를 정의합니다. 각 프롬프트는 해당 페르소나의 역할, 응답 스타일, 제공해야 할 정보를 상세히 설명합니다.

- **CRITIC_PROMPT**: 비판적 분석가 페르소나를 위한 시스템 프롬프트로, 아이디어의 문제점과 리스크를 분석합니다.
- **MARKETER_PROMPT**: 창의적 마케터 페르소나를 위한 시스템 프롬프트로, 아이디어의 창의적 가치와 시장 잠재력을 분석합니다.
- **ENGINEER_PROMPT**: 현실적 엔지니어 페르소나를 위한 시스템 프롬프트로, 아이디어의 기술적 실현 가능성을 분석합니다.
- **FINAL_SUMMARY_PROMPT**: 오케스트레이터가 최종 요약을 생성할 때 사용하는 프롬프트입니다.
- **DIALOGUE_SUMMARY_PROMPT**: (선택적) 대화 히스토리를 요약할 때 사용하는 프롬프트입니다.

### 2. config/personas.py

이 파일은 각 페르소나의 설정 및 매개변수를 정의합니다.

- **PersonaType**: 페르소나 유형을 정의하는 열거형 클래스입니다.
- **PERSONA_CONFIGS**: 각 페르소나별 구성 설정을 담고 있는 사전형 객체로, 이름, 설명, 아이콘, 온도(temperature), 최대 출력 토큰 수, 출력 키 등의 정보를 포함합니다.
- **ORCHESTRATOR_CONFIG**: 오케스트레이터 에이전트의 설정을 정의합니다.
- **PERSONA_SEQUENCE**: 워크숍 진행 순서를 정의하는 리스트입니다.

### 3. src/agents/critic_agent.py

비판적 분석가 페르소나 에이전트를 구현한 클래스 파일입니다. Google ADK의 Agent 클래스를 활용하여 비판적 분석가 역할을 수행하는 에이전트를 정의합니다.

- **CriticPersonaAgent 클래스**: 비판적 분석가 페르소나를 구현한 클래스입니다.
  - `__init__()`: 페르소나 설정과 프롬프트를 사용하여 에이전트를 초기화합니다.
  - `get_agent()`: 초기화된 Agent 객체를 반환합니다.
  - `get_output_key()`: 에이전트 응답이 세션 상태에 저장될 키를 반환합니다.

### 4. src/ui/app.py

Streamlit을 사용한 웹 기반 사용자 인터페이스를 구현한 파일입니다. 사용자가 아이디어를 입력하고 분석 결과를 확인할 수 있는 UI를 제공합니다.

- **create_session()**: 새로운 ADK 세션을 생성하는 함수입니다.
- **analyze_idea()**: 사용자 아이디어를 분석하는 함수로, 비판적 분석가 에이전트를 실행하고 결과를 반환합니다.
- **main()**: Streamlit 애플리케이션의 메인 함수로, UI 컴포넌트 구성 및 사용자 인터랙션을 처리합니다.

### 5. src/poc/simple_adk_agent.py

Google ADK의 기본 Agent 클래스를 사용하여 간단한 LLM 에이전트를 구현한 예제 코드입니다. 환경 변수에서 API 키를 로드하고, Google ADK Runner 클래스를 사용하여 에이전트를 실행하고 응답을 처리합니다.

### 6. src/poc/session_state_test_agent.py

Google ADK의 session.state 기능을 테스트하는 예제 코드입니다. 세션을 생성하고, session.state에 값을 저장한 후, 프롬프트 내에서 이 값을 참조하는 Agent를 실행합니다. 또한 Agent의 응답을 session.state에 저장하는 방법도 보여줍니다.

### 7. tests/test_critic_agent.py

비판적 분석가 에이전트를 테스트하는 단위 테스트 파일입니다. 에이전트 초기화와 설정 값이 올바르게 적용되는지 검증합니다.

### 8. tests/test_app.py

UI 애플리케이션의 기능을 테스트하는 단위 테스트 파일입니다. 세션 생성, 아이디어 분석 등의 핵심 기능이 올바르게 동작하는지 검증합니다.

## 데이터 흐름 (Phase 1)

Phase 1에서 구현된 단일 페르소나 분석 워크플로우의 데이터 흐름은 다음과 같습니다:

1. **사용자 입력**: 사용자가 UI를 통해 아이디어를 입력합니다.
2. **세션 생성**: 새로운 ADK 세션이 생성되고, 사용자 아이디어가 `session.state["initial_idea"]`에 저장됩니다.
3. **에이전트 실행**: 비판적 분석가 에이전트가 세션 상태에서 아이디어를 읽고 분석합니다.
4. **결과 저장**: 분석 결과가 `session.state["critic_response"]`에 저장됩니다.
5. **결과 표시**: UI가 세션 상태에서 분석 결과를 읽어 사용자에게 표시합니다.

```mermaid
sequenceDiagram
    participant User
    participant UI as app.py (UI)
    participant Session as ADK Session
    participant Critic as CriticPersonaAgent
    
    User->>UI: 아이디어 입력
    UI->>Session: 세션 생성 및 아이디어 저장
    UI->>Critic: 에이전트 실행 요청
    Critic->>Session: 세션 상태에서 아이디어 읽기
    Critic-->>Critic: 아이디어 분석
    Critic->>Session: 분석 결과 저장
    UI->>Session: 결과 조회
    UI->>User: 분석 결과 표시
```

## Google ADK 에이전트 실행 아키텍처

Google ADK는 에이전트를 실행하기 위한 특정 패턴을 따르며, 이는 AIdea Lab 전체 아키텍처에 중요한 영향을 미칩니다:

### 1. 이벤트 루프 기반 아키텍처

Google ADK는 '이벤트 루프' 기반으로 동작합니다. 이는 에이전트 실행 흐름이 다음과 같은 패턴을 따름을 의미합니다:

1. **Runner**: 사용자 요청을 받아 Agent에 전달하고 이벤트를 처리하는 중앙 오케스트레이터 역할
2. **Agent**: 실제 로직을 수행하고 이벤트를 생성하는 실행 단위
3. **이벤트 순환**: Agent가 이벤트를 생성하면 Runner가 이를 처리하고, 다시 Agent에게 제어권을 돌려주는 방식

### 2. Runner 클래스

- **역할**: 에이전트 실행의 주요 진입점으로, 단일 사용자 쿼리에 대한 오케스트레이션 담당
- **주요 기능**:
  - 세션 관리 및 상태 저장
  - 이벤트 처리 및 전달
  - 에이전트 실행 관리

### 3. 세션 및 상태 관리

- **SessionService**: 세션 객체의 생성, 저장, 로드를 담당하는 서비스
- **Session**: 특정 대화에 대한 상태(state)와 이벤트 히스토리를 저장하는 컨테이너
- **State**: 대화 중 필요한 데이터를 저장하는 딕셔너리 형태의 객체

### 4. 표준 실행 패턴

```python
# 1. 세션 서비스 초기화
session_service = InMemorySessionService()

# 2. 세션 생성 또는 로드
session = session_service.create_session(
    app_name="앱_이름",
    user_id="사용자_ID",
    session_id="세션_ID"
)

# 3. Runner 인스턴스 생성
runner = Runner(
    agent=agent_instance,
    app_name="앱_이름",
    session_service=session_service
)

# 4. 입력 메시지 생성
content = types.Content(
    role="user",
    parts=[types.Part(text="사용자_메시지")]
)

# 5. Runner를 통한 에이전트 실행
events = runner.run(
    user_id="사용자_ID",
    session_id="세션_ID",
    new_message=content
)

# 6. 이벤트 처리 및 응답 추출
for event in events:
    if event.is_final_response() and event.content and event.content.parts:
        response_text = event.content.parts[0].text
        break
```

## 기술 스택

- **Google ADK**: AI 에이전트 개발 및 오케스트레이션을 위한 프레임워크
- **Gemini API**: LLM 서비스로 활용
- **Python**: 전체 프로젝트의 기본 프로그래밍 언어
- **Streamlit**: 사용자 인터페이스 구현을 위한 프레임워크
- **python-dotenv**: 환경 변수 관리
- **pytest**: 단위 테스트 구현

## 데이터 흐름

1. 사용자가 UI를 통해 아이디어를 입력합니다.
2. 입력된 아이디어는 session.state에 저장됩니다.
3. 오케스트레이터 에이전트가 페르소나 순서에 따라 각 페르소나 에이전트를 순차적으로 실행합니다.
4. 각 페르소나 에이전트는 아이디어와 이전 페르소나의 의견을 분석하여 결과를 생성합니다.
5. 각 페르소나의 분석 결과는 session.state에 저장됩니다.
6. 모든 페르소나 분석이 완료되면, 오케스트레이터가 최종 요약을 생성합니다.
7. 최종 요약은 UI에 표시됩니다.

## 확장성

AIdea Lab의 아키텍처는 다음과 같은 확장을 고려하여 설계되었습니다:

1. **새로운 페르소나 추가**: 추가 페르소나를 구현하려면 프롬프트를 정의하고 페르소나 설정을 추가한 후, 해당 페르소나 에이전트를 구현하면 됩니다.
2. **외부 도구 통합**: Google ADK의 도구(Tool) 메커니즘을 활용하여 외부 데이터 소스나 API와의 통합을 추가할 수 있습니다.
3. **다양한 UI 옵션**: Streamlit 외에도 다양한 UI 프레임워크(예: Gradio, Flask+React)로 전환할 수 있는 구조입니다.

## Phase 1 구현에서의 아키텍처 핵심 요소

### 모듈 분리와 단일 책임 원칙

각 파일은 명확한 단일 책임을 가지도록 설계했습니다:
- `critic_agent.py`: 비판적 분석가 페르소나의 동작만 담당
- `app.py`: 사용자 인터페이스와 인터랙션만 담당

### Session State의 활용

ADK의 `session.state`는 에이전트 간의 데이터 공유를 위한 핵심 메커니즘입니다:

1. **입력 전달**: 사용자 아이디어를 `initial_idea` 키로 저장
2. **출력 저장**: 에이전트의 분석 결과를 `critic_response` 키로 저장
3. **상태 유지**: 여러 차례의 에이전트 호출 사이에 상태 유지

### 확장 가능한 디자인

Phase 1에서는 단일 페르소나 에이전트만 구현했지만, 다중 페르소나 지원을 위한 기반을 마련했습니다:

1. **공통 인터페이스**: 모든 페르소나 에이전트가 동일한 인터페이스를 갖도록 설계 (`get_agent()`, `get_output_key()`)
2. **설정 기반 초기화**: 설정 파일에서 페르소나 매개변수를 로드하는 방식으로, 새 페르소나 추가 시 코드 변경을 최소화

이러한 아키텍처 설계를 통해 Phase 2에서 추가적인 페르소나와 오케스트레이션 로직을 쉽게 통합할 수 있습니다.
