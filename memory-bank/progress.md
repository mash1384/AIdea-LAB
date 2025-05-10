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

- Phase 5: 챗봇 UI 기반 개별 심층 분석 (완료)
  - `src/ui/app.py`: 시스템 안내 메시지 템플릿 정의를 위한 `SYSTEM_MESSAGES` 딕셔너리 추가
    - 초기 환영 메시지, 분석 시작 안내, 각 페르소나 소개, 1단계 완료 안내 등 메시지 포함
  - `show_system_message()` 함수 구현하여 채팅창에 시스템 메시지를 일관되게 표시하는 기능 추가
  - 페르소나 실행 시퀀스에 맞춰 적절한 순서로 안내 메시지가 표시되도록 로직 개선

## Phase 5: 챗봇 UI 기반 개별 심층 분석 (완료)

**완료일**: 2025-06-15

### 구현 내용

1. **1단계 시스템 안내 메시지 플로우 구현**
   - `src/ui/app.py`: 시스템 안내 메시지 템플릿 정의를 위한 `SYSTEM_MESSAGES` 딕셔너리 추가
     - 초기 환영 메시지, 분석 시작 안내, 각 페르소나 소개, 1단계 완료 안내 등 메시지 포함
   - `show_system_message()` 함수 구현하여 채팅창에 시스템 메시지를 일관되게 표시하는 기능 추가
   - 페르소나 실행 시퀀스에 맞춰 적절한 순서로 안내 메시지가 표시되도록 로직 개선

2. **사용자 추가 정보 입력 및 상태 저장 구현**
   - `src/ui/app.py`: 고급 설정 영역 내에 추가 정보 입력 필드 추가
     - "아이디어의 핵심 목표", "주요 제약 조건", "중요 가치" 필드 제공
     - 토글 방식으로 추가 정보 입력 UI를 표시/숨김 가능하도록 구현
   - 입력된 추가 정보를 `st.session_state`에 저장
     - `user_goal`, `user_constraints`, `user_values` 키 사용
   - 분석 실행 시 ADK 세션 상태에도 동일한 키로 값 저장
     - Google ADK `session.state` 객체에 정보 전달하여 페르소나가 활용 가능하도록 구현

3. **Phase 1 워크플로우 정의 및 실행 구현**
   - `src/orchestrator/main_orchestrator.py`: `get_phase1_workflow()` 메서드 추가
     - 기존에 정의된 `SequentialAgent`를 1단계 워크플로우로 활용하여 반환
     - 향후 Phase별로 다른 에이전트 구성이 필요한 경우를 위한 확장성 확보
   - `src/ui/app.py`: `run_phase1_analysis_and_update_ui()` 함수에서 새 워크플로우 메서드 활용
     - `orchestrator.get_phase1_workflow()`를 호출하여 1단계 워크플로우 에이전트 생성
     - 사용자 입력 아이디어 및 추가 정보를 ADK 세션에 저장
     - 순차적인 페르소나 실행과 안내 메시지 표시 로직 통합

### 개선 효과

- **향상된 사용자 경험**: 시스템 안내 메시지를 통해 현재 분석 단계와 흐름을 사용자가 명확히 이해할 수 있음
- **풍부한 컨텍스트 제공**: 사용자가 입력한 추가 정보가 LLM 페르소나에게 전달되어 더 맥락에 맞는 분석 가능
- **모듈화된 워크플로우**: 1단계 워크플로우가 명확히 정의되어 향후 2단계와의 구분 및 확장이 용이함
- **UI 일관성**: `show_system_message()` 함수를 통해 모든 시스템 메시지가 일관된 스타일로 표시됨

### 다음 단계
- Phase 1 단계 4: ADK 세션 관리 전략 정의 및 Phase 2 토론을 위한 준비
- 유닛 테스트 작성 및 엣지 케이스 처리 강화
- 다양한 사용자 입력에 대한 안정성 테스트

## Phase 6: 시스템 메시지 흐름 및 상태 관리 개선 (완료)

**완료일**: 2025-06-20

### 구현 내용

1. **시스템 메시지 표시 로직 개선**
   - `show_system_message()` 함수의 `rerun` 파라미터 기본값을 `False`로 변경하여 불필요한 화면 갱신 방지
   - 메시지 표시 후 UI 즉시 업데이트가 필요한 경우에만 명시적으로 `rerun=True` 전달하도록 수정
   - 상위 로직에서 여러 상태 변경 후 한 번만 `st.rerun()`을 호출하도록 최적화

2. **상태 관리 체계화**
   - `phase1_step` 상태 변수 추가로 1단계 분석의 세부 진행 상태 명확하게 관리
     - `awaiting_idea`: 아이디어 입력 대기 중
     - `idea_submitted`: 아이디어 입력됨
     - `analysis_ready`: 분석 준비 완료
     - `analysis_started`: 분석 시작됨
     - `marketer_analyzing`, `비판적_분석가_analyzing`, `현실적_엔지니어_analyzing`: 각 페르소나 분석 중
     - `complete`: 분석 완료됨
     - `error`: 오류 발생
   - 세션 상태 기반의 조건부 처리 강화로 메시지 흐름 안정화
   - 메인 함수에 상태에 따른 조건부 처리 로직 추가

3. **아이디어 입력과 메시지 흐름 연동 개선**
   - 아이디어 입력 직후 `phase1_step`을 "idea_submitted"로 설정하고 UI 상태 업데이트
   - 메인 루프에서 `phase1_step == "idea_submitted"` 조건 확인 시 자동으로 분석 시작 안내 메시지 표시
   - 페르소나 분석 중 적절한 소개 메시지가 표시되도록 워크플로우 개선

4. **페르소나 분석 시퀀스 자연스러운 흐름 구현**
   - 페르소나 간 전환 시 약간의 지연(0.5초) 추가로 사용자가 결과를 읽을 시간 확보
   - 각 페르소나 결과 표시 전 해당 페르소나 소개 메시지 표시
   - 페르소나 응답 결과의 단어 단위 스트리밍으로 자연스러운 응답 효과 구현

### 개선 효과

- **향상된 UI 응답성**: 불필요한 화면 리로드 감소로 UI 반응성 향상
- **일관된 메시지 흐름**: 사용자에게 분석 과정의 각 단계를 명확하게 안내하는 메시지 표시
- **상태 추적 강화**: 세부 상태 변수를 통한 정확한 애플리케이션 상태 추적으로 디버깅 용이성 증가
- **사용자 경험 개선**: 명확한 안내 메시지와 자연스러운 응답 스트리밍으로 직관적인 사용자 경험 제공

### 주요 변경점 요약

1. `show_system_message()` 함수 `rerun` 파라미터 기본값 변경 및 사용 최적화
2. `phase1_step` 상태 변수 추가로 세부 진행 상태 관리 체계화
3. 아이디어 입력 후 메시지 표시 로직 강화로 사용자 안내 개선
4. 페르소나 간 전환 시 자연스러운 흐름을 위한 지연 및 안내 메시지 추가

### 향후 개선 방향

- 2단계(Phase 2) 토론 진행을 위한 유사한 상태 관리 체계 구축
- 다국어 지원을 위한 시스템 메시지 템플릿 분리
- 사용자 설정에 따른 메시지 스타일 및 세부 정보 레벨 조정 기능 추가
- 시스템 메시지 및 사용자 인터랙션 로그 기능 구현



