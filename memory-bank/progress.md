# AIdea Lab 프로젝트 진행 상황

## Phase 0: 준비 및 환경 설정 (완료)

**완료일**: 2025-05-10

### 구현 내용

1. **프로젝트 기본 구조 설정**
   - src(소스 코드), tests(테스트 코드), docs(문서), config(설정 파일), scripts(유틸리티 스크립트) 등의 기본 디렉토리 구조 생성
   - src 하위에 poc(개념 증명), agents, orchestrator, ui 디렉토리 구성

2. **필수 라이브러리 설정**
   - requirements.txt에 필요한 라이브러리 명시
   - 주요 라이브러리: google-adk, google-generativeai, streamlit, python-dotenv, pytest

3. **환경 변수 설정**
   - .env 파일을 통한 API 키 및 프로젝트 설정 관리
   - API 키 보안을 위한 .gitignore 설정

4. **Google ADK 기본 테스트 코드 작성**
   - 간단한 LlmAgent 예제 구현 (src/poc/simple_adk_agent.py)
   - session.state 활용 예제 구현 (src/poc/session_state_test_agent.py)

5. **AI 페르소나 설정 및 프롬프트 정의**
   - 페르소나별 시스템 프롬프트 작성 (config/prompts.py)
     - 비판적 분석가, 창의적 마케터, 현실적 엔지니어 프롬프트 정의
     - 오케스트레이터 요약 생성 프롬프트 정의
   - 페르소나 설정 정의 (config/personas.py)
     - 페르소나별 매개변수(temperature, token limit 등) 설정
     - 오케스트레이션 순서 정의

6. **Google ADK 에이전트 실행 문제 해결**
   - **문제 상황**: ADK Agent 객체에서 `run()`, `generate()`, `invoke()` 메서드 호출 시 속성 오류 발생
     ```
     ❌ 오류 발생: 'LlmAgent' object has no attribute 'run'
     ```
   - **원인 분석**:
     - Google ADK의 API 사용법 변경: 최신 버전(0.4.0)에서는 Agent 객체의 직접 호출 방식이 아닌 Runner 클래스를 통한 실행 방식 사용
     - 입력 형식 차이: 단순 문자열이 아닌 구조화된 `types.Content` 객체를 통한 입력 전달 필요
     - 응답 처리 방식: 직접 응답 반환이 아닌 이벤트 스트림 처리 방식 채택
   - **해결 방법**:
     - `Runner` 객체 생성 및 사용
       - `InMemorySessionService`를 통한 세션 관리
       - `runner.run()` 메서드를 통한 에이전트 실행
     - 구조화된 입력 생성
       - `types.Content` 및 `types.Part` 객체 사용
     - 이벤트 기반 응답 처리
       - 이벤트 스트림 순회하며 `event.is_final_response()` 확인
       - 최종 응답 추출하여 사용
   - **참고 사항**: 세션 상태 활용 시 템플릿 태그 치환 작동 문제는 추가 검토 필요

## Phase 1: 단일 페르소나 아이디어 분석 구현 (완료)

**완료일**: 2025-05-20

### 구현 내용

1. **비판적 분석가 페르소나 Agent 클래스 구현**
   - `src/agents/critic_agent.py` 파일에 `CriticPersonaAgent` 클래스 구현
   - `CRITIC_PROMPT`를 시스템 프롬프트로 사용하고 `PersonaType.CRITIC` 설정 적용
   - 에이전트 응답을 세션 상태에 저장하기 위한 `output_key` 설정
   - 에이전트 객체 및 설정을 반환하는 메서드 구현 (`get_agent()`, `get_output_key()`)

2. **기본 UI 구축 (Streamlit)**
   - `src/ui/app.py` 파일에 Streamlit 기반 사용자 인터페이스 구현
   - 아이디어 입력을 위한 텍스트 영역 및 분석 요청 버튼 추가
   - 세션 관리 기능 구현 (`create_session()` 함수)
   - API 키 검증 및 오류 처리 로직 추가
   - 로딩 상태 표시 및 결과 표시 영역 구현

3. **사용자 아이디어 입력 및 단일 페르소나 분석 흐름 구현**
   - `analyze_idea()` 함수를 통한 아이디어 분석 로직 구현
   - 세션 상태에 사용자 아이디어 저장 (`session.state["initial_idea"]`)
   - ADK `Runner` 클래스를 사용하여 비판적 분석가 에이전트 실행
   - 이벤트 스트림을 통한 응답 처리 및 결과 표시
   - 세션 상태에서 에이전트 응답 추출 (`session.state["critic_response"]`)

4. **단위 테스트 작성**
   - `tests/test_critic_agent.py` 파일에 비판적 분석가 에이전트 테스트 작성
     - 에이전트 초기화 및 속성 값 검증
     - 출력 키 반환 메서드 검증
   - `tests/test_app.py` 파일에 UI 기능 테스트 작성
     - 세션 생성 기능 테스트
     - 아이디어 분석 기능 테스트 (모킹 활용)

### 주요 문제 및 해결 방법

- **이슈**: ADK의 세션 상태를 UI 세션과 연동하는 방식에 대한 고민
- **해결**: Streamlit 세션 상태와 ADK 세션을 분리하여 관리하고, 필요 시 ADK 세션 상태의 값을 Streamlit 세션 상태로 복사하는 방식 채택

### Google ADK API 호환성 문제 해결 (2025-05-21)

- **문제 상황**: Google ADK API 호환성 문제로 테스트 실행 시 다음과 같은 검증 오류 발생
  ```
  pydantic_core._pydantic_core.ValidationError: 3 validation errors for LlmAgent
  name
    Value error, Found invalid agent name: `비판적 분석가`. Agent name must be a valid identifier.
  temperature
    Extra inputs are not permitted
  max_output_tokens
    Extra inputs are not permitted
  ```

- **원인 분석**:
  1. **Agent 이름 제약조건**: ADK API는 Agent 이름이 영문자, 숫자, 언더스코어로만 구성되어야 함
  2. **API 매개변수 변경**: `temperature`와 `max_output_tokens`가 `Agent` 클래스의 직접 매개변수가 아니라 `generate_content_config` 내부에 설정되어야 함
  3. **타입 시스템**: `generate_content_config`는 딕셔너리가 아닌 `GenerateContentConfig` 객체 타입임

- **수정 내용**:
  1. **CriticPersonaAgent 수정**:
     - `name` 매개변수를 "critic_agent"로 변경
     - LLM 파라미터를 `generate_content_config` 딕셔너리로 이동
     - 세션 상태 접근 시 안전한 처리 추가
  
  2. **테스트 코드 개선**:
     - `test_critic_agent.py`: 
       - `GenerateContentConfig` 타입을 활용한 속성 검증으로 변경
       - 딕셔너리 방식에서 객체 속성 접근 방식으로 테스트 로직 수정
     
     - `test_app.py`:
       - 모킹 방식 개선 및 명확한 픽스처 이름 사용 (mock_session_service → mock_app_session_service)
       - 테스트 세션 객체 속성 추가 (id, app_name, user_id, events, last_update_time)
       - 어설션 로직 구체화 및 개선

  3. **디렉터리 구조 보완**:
     - Python 패키지 인식을 위한 `__init__.py` 파일 추가
     - 테스트 실행을 위한 PYTHONPATH 설정 방법 확립

### 다음 단계
- Phase 2: 멀티 페르소나 순차 실행 및 오케스트레이션 구현
  - 창의적 마케터 및 현실적 엔지니어 페르소나 Agent 클래스 구현
  - 오케스트레이터 에이전트 구현
  - 순차적 페르소나 실행 로직 구현
  - UI 확장하여 멀티 페르소나 결과 표시

## Phase 2: 멀티 페르소나 및 오케스트레이션 구현 (완료)

- **마케터 에이전트 (`src/agents/marketer_agent.py`)**: 아이디어의 창의적 가치와 시장 잠재력 분석.
- **엔지니어 에이전트 (`src/agents/engineer_agent.py`)**: 아이디어의 기술적 실현 가능성 검토.
- **오케스트레이터 (`src/orchestrator/main_orchestrator.py`)**: 각 페르소나 에이전트를 순차적으로 실행하고 결과를 취합. `SequentialAgent` 대신 커스텀 로직으로 순차 실행을 구현하여 `pydantic` 유효성 검사 오류를 해결.
- **UI 업데이트 (`src/ui/app.py`)**:
    - 멀티 페르소나 분석 결과를 탭으로 구분하여 표시.
    - 오케스트레이터를 통해 페르소나 순차 실행 및 최종 요약 기능 통합.
    - `asyncio`를 사용하여 비동기적으로 에이전트 실행.
    - 모듈 경로 문제 해결 (`sys.path` 수정 및 `setup.py` 추가).
- **최종 요약 기능**: 모든 페르소나의 분석 결과를 바탕으로 최종 요약 생성.

## Phase 3: 제미니 모델 선택 기능 구현 (완료)

**완료일**: 2025-05-30

### 구현 내용

1. **제미니 모델 설정 파일 생성**
   - `config/models.py` 파일에 사용 가능한 제미니 모델 정의
   - 최신 제미니 모델 지원: Gemini 2.0 Flash, Gemini 2.5 Pro Preview 03-25, Gemini 2.5 Flash Preview 04-17, Gemini 2.5 Pro Preview 05-06
   - `ModelType` 열거형과 `MODEL_CONFIGS` 사전을 통한 모델 정보 관리
   - 모델 표시 이름 및 설명 정의
   - 기본 모델 설정 (`DEFAULT_MODEL`)

2. **페르소나 에이전트 모듈 수정**
   - 모든 에이전트가 하드코딩된 모델 대신 선택 가능한 모델을 사용하도록 변경
   - `config/personas.py`에 `SELECTED_MODEL` 전역 변수 추가
   - `src/agents/critic_agent.py`, `src/agents/marketer_agent.py`, `src/agents/engineer_agent.py` 수정
   - `src/orchestrator/main_orchestrator.py` 내 에이전트 생성 코드 업데이트

3. **UI에 모델 선택 기능 추가**
   - `src/ui/app.py`에 모델 선택 드롭다운 메뉴 구현
   - "고급 설정" 섹션에 모델 선택 UI 요소 배치
   - 사용자가 선택한 모델 정보 표시
   - 모델 변경을 적용하는 `update_selected_model()` 함수 구현
   - 분석 요청 시 선택된 모델 적용

4. **테스트 코드 호환성 수정**
   - `tests/test_critic_agent.py` 수정하여 모델 선택 기능 지원
   - `src/poc/simple_adk_agent.py` 및 `src/poc/session_state_test_agent.py` 업데이트

### 문제 해결 및 개선 사항

- **문제 상황**: 초기 구현에서 모델 ID가 구글 Gemini API 문서와 불일치
- **해결 방법**: [구글 Gemini API 문서](https://ai.google.dev/gemini-api/docs/models)를 참조하여 정확한 모델 ID로 수정
  - "exo"를 "preview"로 변경
  - 날짜 형식 수정 (03-25, 04-17, 05-06)
  - 모델 ID 형식 표준화
  
- **UI 개선**: 모델 선택 기능을 expander 안에 배치하여 UI 복잡성을 줄이고 고급 사용자를 위한 옵션으로 제공

### 향후 개선 방향

- **모델 메타데이터 자동 업데이트**: Gemini API에서 사용 가능한 모델 목록을 자동으로 가져오는 기능
- **모델별 성능 메트릭 수집**: 각 모델의 응답 속도 및 품질 비교를 위한 메트릭 수집
- **사용자별 모델 선호도 저장**: 개별 사용자의 모델 선호도를 기억하고 자동으로 적용하는 기능

## Phase 4: 모델 선택 처리 방식 개선 (완료)

**완료일**: 2025-06-05

### 구현 내용

1. **전역 변수 의존성 문제 해결**
   - `config/personas.py`에서 `SELECTED_MODEL` 전역 변수 제거
   - 전역 변수 대신 의존성 주입 방식으로 변경하여 코드 안정성 향상

2. **에이전트 클래스 모델 주입 기능 추가**
   - 모든 페르소나 에이전트(`CriticPersonaAgent`, `MarketerPersonaAgent`, `EngineerPersonaAgent`)의 `__init__` 메서드에 `model_name` 파라미터 추가
   - 파라미터 기본값으로 `DEFAULT_MODEL.value` 사용하여 이전 코드와의 호환성 유지
   - 내부에서 전달받은 `model_name`을 사용하여 ADK 에이전트 객체 생성

3. **오케스트레이터 클래스 개선**
   - `AIdeaLabOrchestrator` 클래스의 `__init__` 메서드에 `model_name` 파라미터 추가
   - 하위 에이전트 생성 시 동일한 모델 이름 전달하여 일관성 유지
   - 요약 에이전트와 오케스트레이터 에이전트도 동일한 모델 사용

4. **UI 코드 개선**
   - 불필요한 `update_selected_model()` 함수 제거
   - `analyze_idea()` 함수에서 `AIdeaLabOrchestrator` 객체 생성 시 `model_name` 파라미터 명시적 전달
   - 사용자가 UI에서 선택한 모델이 바로 전체 시스템에 적용되도록 개선

5. **테스트 코드 업데이트**
   - `tests/test_app.py` 파일을 수정하여 새로운 API와 호환되도록 변경
   - 비동기 방식으로 `analyze_idea` 함수를 테스트하도록 수정
   - `AIdeaLabOrchestrator`가 올바른 모델 이름으로 생성되는지 검증하는 로직 추가

### 개선 효과

- **향상된 모듈성**: 전역 변수 의존성을 제거하여 코드 모듈성 향상
- **향상된 테스트 용이성**: 명시적 의존성 주입으로 테스트 용이성 증가
- **웹 앱 안정성 향상**: 웹 환경(Streamlit)에서 전역 변수 수정으로 인한 예기치 않은 동작 방지
- **확장성 개선**: 다양한 모델 구성을 각 에이전트마다 독립적으로 지정할 수 있는 가능성 열림

### 주요 변경점 요약

1. 전역 변수 `SELECTED_MODEL` 제거 → 의존성 주입 패턴으로 대체
2. 에이전트 및 오케스트레이터 생성자에 `model_name` 파라미터 추가
3. UI에서 모델 선택 처리 방식을 명시적 파라미터 전달 방식으로 변경
4. 관련 테스트 코드 업데이트

### 다음 단계

- Phase 5: 오케스트레이터 실행 로직 개선 (ADK 워크플로우 활용)
  - `src/orchestrator/main_orchestrator.py`의 실행 로직 개선
  - ADK의 `SequentialAgent`를 활용하여 페르소나 에이전트 실행
  - `session.state`가 페르소나 에이전트 실행 간에 올바르게 공유되도록 개선

## Phase 5: 오케스트레이터 실행 로직 개선 (ADK 워크플로우 활용) (완료)

**완료일**: 2025-06-10

### 구현 내용

1. **SequentialAgent 도입**
   - `google.adk.agents.SequentialAgent`를 활용하여 모든 페르소나 에이전트를 단일 워크플로우로 통합
   - 기존의 수동 `for` 루프 기반 실행 방식을 ADK 표준 워크플로우 에이전트로 대체
   - 요약 에이전트도 동일한 워크플로우에 포함시켜 통합 실행 가능하도록 개선

2. **src/orchestrator/main_orchestrator.py 리팩토링**
   - `run_all_personas_sequentially()` 메서드 제거 및 표준 ADK 워크플로우 사용 방식으로 전환
   - 불필요한 `orchestrator_agent` 변수 제거
   - `get_sequential_agent()` 메서드를 `get_workflow_agent()`로 이름 변경 및 기능 수정
   - 불필요한 `Session` 임포트 제거

3. **src/ui/app.py의 analyze_idea() 함수 수정**
   - 단일 `Runner` 인스턴스를 통해 전체 워크플로우를 실행하도록 로직 변경
   - 개별적인 요약 에이전트 실행 로직 제거 (워크플로우에 통합)
   - 세션 상태가 전체 실행 과정에서 일관되게 관리되도록 개선

4. **tests/test_app.py 업데이트**
   - 새로운 워크플로우 기반 아키텍처를 반영한 테스트 로직 구현
   - `get_workflow_agent()` 메서드와 SequentialAgent 사용 검증 추가
   - 테스트 픽스처 수정으로 현재 구현과 일치하도록 업데이트

### 개선 효과

- **상태 일관성 강화**: 페르소나 에이전트 간 `session.state` 공유가 ADK 프레임워크에 의해 자동으로 관리되어 더 안정적인 상태 공유 가능
- **표준 패턴 준수**: Google ADK의 표준 워크플로우 패턴을 따름으로써 프레임워크의 장점을 최대한 활용
- **코드 간소화**: 불필요한 반복 코드 제거 및 전체 워크플로우 실행 로직 단순화
- **확장성 향상**: 새로운 페르소나 에이전트 추가 시 `sub_agents` 리스트에만 추가하면 되어 확장이 용이
- **메모리 효율성**: 여러 Runner 인스턴스 대신 단일 Runner를 사용하여 메모리 사용량 개선

### 주요 변경점 요약

1. `run_all_personas_sequentially()` 메서드 제거 → `SequentialAgent` 활용
2. 각 페르소나마다 별도의 Runner 인스턴스 생성 → 단일 Runner로 통합
3. 최종 요약 생성 별도 실행 → 워크플로우의 마지막 단계로 통합
4. 테스트 코드 업데이트로 변경된 아키텍처 반영

### 다음 단계

- Phase 6: 사용자 경험 향상 (UI/UX 개선)
  - 분석 진행 상태 표시 기능 추가
  - 인터랙티브 피드백 메커니즘 구현
  - 모바일 친화적 레이아웃 최적화


