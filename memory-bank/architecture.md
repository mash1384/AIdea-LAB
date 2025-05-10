# AIdea Lab 아키텍처 설명서

## 프로젝트 구조

AIdea Lab은 다음과 같은 디렉토리 구조로 설계되었습니다:

```
aidea-lab/
│
├── src/                      # 소스 코드
│   ├── agents/               # AI 페르소나 에이전트 클래스
│   │   ├── critic_agent.py   # 비판적 분석가 페르소나 에이전트
│   │   ├── marketer_agent.py # 창의적 마케터 페르소나 에이전트
│   │   └── engineer_agent.py # 현실적 엔지니어 페르소나 에이전트
│   ├── orchestrator/         # 오케스트레이터 에이전트 클래스
│   │   └── main_orchestrator.py # 메인 오케스트레이터
│   ├── ui/                   # 사용자 인터페이스 코드
│   │   └── app.py            # Streamlit 기반 UI 애플리케이션
│   └── poc/                  # 개념 증명 (Proof of Concept) 코드
│       ├── simple_adk_agent.py      # 기본 ADK Agent 테스트
│       └── session_state_test_agent.py  # ADK session.state 테스트
│
├── config/                   # 설정 파일
│   ├── prompts.py            # 페르소나별 시스템 프롬프트 정의
│   ├── personas.py           # 페르소나 설정 및 매개변수 정의
│   └── models.py             # 제미니 모델 설정 및 선택 옵션 정의
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
- **SELECTED_MODEL**: 현재 선택된 제미니 모델을 저장하는 전역 변수입니다. 기본값은 `DEFAULT_MODEL.value`로 설정되며, UI에서 모델 선택 시 이 값이 업데이트됩니다.

### 2-1. config/models.py

이 파일은 사용 가능한 제미니 모델과 모델 설정을 정의합니다.

- **역할**: 사용 가능한 제미니 모델과 모델 설정을 관리합니다.
- **아키텍처**:
    - `ModelType` Enum을 통해 사용 가능한 모델들의 ID 정의
    - `MODEL_CONFIGS` 사전을 통해 각 모델의 메타데이터(이름, 설명, 표시명) 관리
    - `DEFAULT_MODEL` 상수로 기본 모델 지정
    - `get_model_display_options()` 함수로 UI에 표시할 모델 옵션 목록 제공
    - 최신 제미니 모델 지원: Gemini 2.0 Flash, Gemini 2.5 Pro Preview 03-25, Gemini 2.5 Flash Preview 04-17, Gemini 2.5 Pro Preview 05-06

### 3. src/agents/critic_agent.py

비판적 분석가 페르소나 에이전트를 구현한 클래스 파일입니다. Google ADK의 Agent 클래스를 활용하여 비판적 분석가 역할을 수행하는 에이전트를 정의합니다.

- **CriticPersonaAgent 클래스**: 비판적 분석가 페르소나를 구현한 클래스입니다.
  - `__init__()`: 페르소나 설정과 프롬프트를 사용하여 에이전트를 초기화합니다.
  - `get_agent()`: 초기화된 Agent 객체를 반환합니다.
  - `get_output_key()`: 에이전트 응답이 세션 상태에 저장될 키를 반환합니다.

### 4. src/ui/app.py

Streamlit을 사용한 웹 기반 사용자 인터페이스를 구현한 파일입니다. 사용자가 아이디어를 입력하고 분석 결과를 확인할 수 있는 UI를 제공합니다.

- **역할**: Streamlit 기반의 사용자 인터페이스 (UI)를 제공합니다.
- **아키텍처**:
    - 사용자가 아이디어를 입력하고 분석을 요청하는 웹 애플리케이션의 진입점입니다.
    - `AIdeaLabOrchestrator`를 호출하여 아이디어 분석 프로세스를 시작합니다.
    - 챗봇 인터페이스로 구현되어 사용자와 AI 페르소나 간의 자연스러운 대화 흐름을 제공합니다.
    - 주요 구성 요소:
        - **챗봇 UI 레이아웃**: `st.set_page_config(layout="centered")`를 사용한 중앙 정렬 레이아웃
        - **채팅 메시지 표시**: `st.chat_message()`와 `st.container()`를 사용하여 사용자와 AI 응답을 대화 형태로 표시
        - **채팅 입력**: `st.chat_input()`을 사용하여 사용자 아이디어 입력 수집
        - **세션 상태 관리**: `initialize_session_state()` 함수를 통한 체계적인 상태 관리
            - `messages`: 전체 대화 히스토리 저장 리스트
            - `current_idea`: 사용자가 입력한 아이디어
            - `analysis_phase`: 현재 분석 단계 추적 (idle, phase1_running, phase1_complete 등)
            - `phase1_step`: 1단계 분석의 세부 진행 상태 관리 ("awaiting_idea", "idea_submitted", "analysis_started", "marketer_analyzing" 등)
            - `user_goal`, `user_constraints`, `user_values`: 사용자 추가 정보 저장
        - **시스템 메시지 관리**: `SYSTEM_MESSAGES` 딕셔너리와 `show_system_message()` 함수를 통한 일관된 안내 메시지 표시
            - 환영 메시지, 분석 시작 안내, 각 페르소나 소개, 단계 완료 안내 등 다양한 메시지 정의
            - `rerun` 파라미터를 통한 UI 업데이트 제어
        - **분석 흐름 관리**: `run_phase1_analysis_and_update_ui()` 비동기 함수를 통한 분석 실행 및 UI 업데이트 통합
            - 상태 기반 메시지 표시 흐름: 아이디어 입력 → 분석 시작 안내 → 페르소나 소개 → 결과 표시 → 완료 안내
            - 페르소나 분석 간 적절한 지연 및 UI 업데이트로 자연스러운 대화 흐름 제공
    - 각 페르소나의 분석 결과를 순차적으로 챗봇 UI에 스트리밍하여 표시합니다.
    - 1단계 분석 완료 후 2단계 진행 선택을 위한 버튼 UI를 제공합니다.
    - `asyncio`를 사용하여 백엔드 로직(에이전트 실행)을 비동기적으로 처리하여 UI 반응성을 유지합니다.
    - **모델 선택 기능**:
        - "고급 설정" expander 내에 모델 선택 드롭다운 UI 제공
        - 선택된 모델의 정보 표시 및 변경 적용 기능
        - 아이디어 분석 요청 시 선택된 모델 자동 적용

### 5. src/poc/simple_adk_agent.py

Google ADK의 기본 Agent 클래스를 사용하여 간단한 LLM 에이전트를 구현한 예제 코드입니다. 환경 변수에서 API 키를 로드하고, Google ADK Runner 클래스를 사용하여 에이전트를 실행하고 응답을 처리합니다.
- **특징**: 선택 가능한 모델을 사용하도록 수정되어 `config/personas.py`의 `SELECTED_MODEL` 변수를 참조합니다.

### 6. src/poc/session_state_test_agent.py

Google ADK의 session.state 기능을 테스트하는 예제 코드입니다. 세션을 생성하고, session.state에 값을 저장한 후, 프롬프트 내에서 이 값을 참조하는 Agent를 실행합니다. 또한 Agent의 응답을 session.state에 저장하는 방법도 보여줍니다.
- **특징**: 선택 가능한 모델을 사용하도록 수정되어 `config/personas.py`의 `SELECTED_MODEL` 변수를 참조합니다.

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

## 파일별 역할 및 아키텍처 설명

### 핵심 구성 요소

#### 에이전트 모듈 (`src/agents/`)

* **`critic_agent.py`**: 
  * 비판적 분석가 페르소나 에이전트 구현
  * `CriticPersonaAgent` 클래스를 통해 구현, 아이디어의 잠재적 문제점과 리스크를 분석
  * `CRITIC_PROMPT`를 시스템 프롬프트로 사용하여 Google ADK `Agent` 객체 생성
  * `get_agent()` 및 `get_output_key()` 메서드 제공하여 에이전트 객체와 결과 저장 키 접근 지원

* **`marketer_agent.py`**: 
  * 창의적 마케터 페르소나 에이전트 구현
  * `MarketerPersonaAgent` 클래스 통해 구현, 아이디어의 창의적 가치와 시장 잠재력 분석
  * `MARKETER_PROMPT`를 시스템 프롬프트로 사용
  * 다른 에이전트들과 동일한 인터페이스 제공으로 일관된 접근 방식 유지

* **`engineer_agent.py`**: 
  * 현실적 엔지니어 페르소나 에이전트 구현
  * `EngineerPersonaAgent` 클래스 통해 구현, 아이디어의 기술적 실현 가능성 평가
  * `ENGINEER_PROMPT`를 시스템 프롬프트로 사용
  * 모델 이름을 파라미터로 받아 다양한 LLM 모델 지원

#### 오케스트레이터 모듈 (`src/orchestrator/`)

* **`main_orchestrator.py`**: 
  * 다양한 페르소나 에이전트의 실행 조율 담당
  * `AIdeaLabOrchestrator` 클래스가 핵심 로직 제공
  * 페르소나 에이전트 생성 및 관리
  * Google ADK `SequentialAgent`를 사용한 워크플로우 에이전트 구성
  * `get_workflow_agent()`, `get_phase1_workflow()` 등 워크플로우 에이전트 접근 메서드 제공
  * `get_output_keys()` 메서드를 통해 모든 에이전트의 결과 저장 키 목록 제공

#### UI 모듈 (`src/ui/`)

* **`app.py`**: 
  * Streamlit 기반 사용자 인터페이스 제공
  * 챗봇 형태의 대화형 UI 구현
  * 아이디어 입력 및 분석 요청 처리
  * 세션 상태 관리 및 AI 페르소나 응답 표시
  * 시스템 안내 메시지 관리를 위한 `SYSTEM_MESSAGES` 정의 및 `show_system_message()` 함수 구현
  * 사용자 추가 정보(핵심 목표, 제약 조건, 중요 가치) 입력 및 관리
  * 비동기 분석 실행 및 스트리밍 응답 처리

#### 설정 모듈 (`config/`)

* **`prompts.py`**: 
  * 각 페르소나별 시스템 프롬프트 정의
  * 비판적 분석가(`CRITIC_PROMPT`), 창의적 마케터(`MARKETER_PROMPT`), 현실적 엔지니어(`ENGINEER_PROMPT`)의 지침 설정
  * 오케스트레이터 및 요약 생성을 위한 프롬프트(`ORCHESTRATOR_PROMPT`, `FINAL_SUMMARY_PROMPT`) 제공

* **`personas.py`**: 
  * 페르소나 유형(`PersonaType`) 및 설정(`PERSONA_CONFIGS`) 정의
  * 페르소나별 매개변수(temperature, 토큰 제한 등) 구성
  * 워크숍 진행 순서 정의(`PERSONA_SEQUENCE`)
  * 오케스트레이터 설정(`ORCHESTRATOR_CONFIG`) 제공

* **`models.py`**: 
  * 사용 가능한 제미니 모델 정의
  * `ModelType` 열거형으로 지원 모델 정의
  * 각 모델에 대한 설명 및 표시 이름 제공
  * UI에서 모델 선택 옵션을 위한 `get_model_display_options()` 함수 제공

### 데이터 흐름

1. **사용자 입력 처리**: 
   * `app.py`에서 사용자의 아이디어와 추가 정보(목표, 제약 조건, 가치) 입력 받음
   * Streamlit 세션 상태(`st.session_state`)에 저장

2. **ADK 세션 관리**:
   * `InMemorySessionService`를 통한 ADK 세션 생성
   * 사용자 입력을 ADK `session.state`에 저장
   * 여러 페르소나 에이전트 간 정보 공유에 활용

3. **워크플로우 실행**:
   * `AIdeaLabOrchestrator`가 `SequentialAgent` 기반 워크플로우 구성
   * 모든 페르소나 에이전트를 순차적으로 실행
   * 각 에이전트의 결과를 ADK `session.state`에 저장
   * 최종적으로 요약 에이전트가 전체 결과 종합

4. **UI 업데이트**:
   * ADK 이벤트 스트림을 통한 응답 처리
   * 각 페르소나의 결과를 순차적으로 UI에 스트리밍 표시
   * 시스템 안내 메시지를 통한 분석 흐름 안내

### 주요 상호작용

1. **에이전트-오케스트레이터 상호작용**:
   * 오케스트레이터가 페르소나 에이전트 객체 생성 및 관리
   * `SequentialAgent`를 통한 순차적 실행 조율
   * `session.state`를 통한 정보 공유

2. **오케스트레이터-UI 상호작용**:
   * UI가 오케스트레이터 메서드 호출하여 워크플로우 에이전트 획득
   * `Runner`를 통한 워크플로우 실행
   * 이벤트 스트림 기반 비동기 결과 처리

3. **설정-에이전트 상호작용**:
   * 에이전트 클래스가 설정 모듈에서 프롬프트 및 페르소나 설정 참조
   * 모델 설정을 통한 LLM 선택 적용

이러한 아키텍처는 모듈화, 확장성, 재사용성을 중심으로 설계되어 있으며, Google ADK의 에이전트 및 세션 관리 기능을 효과적으로 활용하고 있습니다. 사용자 경험 측면에서는 Streamlit의 채팅 인터페이스와 비동기 처리를 통해 자연스러운 대화형 분석 경험을 제공합니다.
