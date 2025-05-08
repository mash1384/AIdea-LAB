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

### 다음 단계
- Phase 2: 멀티 페르소나 순차 실행 및 오케스트레이션 구현
  - 창의적 마케터 및 현실적 엔지니어 페르소나 Agent 클래스 구현
  - 오케스트레이터 에이전트 구현
  - 순차적 페르소나 실행 로직 구현
  - UI 확장하여 멀티 페르소나 결과 표시


