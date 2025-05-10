# AIdea Lab 고도화 프로젝트: 기능 구현 상세 계획 (AI 개발자용 - 최종 상세 수정본)

## 사전 준비

**단계 1: 개발 환경, 기본 설정 및 핵심 개념 숙지**

*   **지침**:

    1.  `memory-bank/prd.md` (최종 계획서), `memory-bank/architecture.md`, [Google ADK 공식 문서](https://google.github.io/adk-docs/) (특히 Agent, Session, Runner, Workflow Agents, LLM 기반 위임 관련 내용)를 정독하고 완벽히 숙지합니다.
    2.  `config/prompts.py`: 1단계 분석용 페르소나 프롬프트들(`MARKETER_PROMPT`, `CRITIC_PROMPT`, `ENGINEER_PROMPT`)과 1단계 요약용 `FINAL_SUMMARY_PROMPT` (1단계 페르소나 결과 키들을 참조하도록 수정 필요) 정의를 확인하고 검토합니다.
*   **테스트**:
    1.  프로젝트 단계별 목표, 아키텍처, ADK 컴포넌트 역할, 데이터 흐름, 특히 세션 관리 및 에이전트 간 통신 방식을 설명할 수 있는지 자가 점검합니다.

## Phase 1: 챗봇 UI 기반 개별 심층 분석 및 2단계 진입 선택

**단계 2: 기본 챗봇 UI 레이아웃 및 사용자 아이디어 입력/표시 구현**

*   **지침**:
    1.  `src/ui/app.py`: Streamlit 페이지 설정 (`st.set_page_config`, `st.title`), 사용자 아이디어 입력을 위한 `st.chat_input` 위젯 배치, 채팅 메시지 표시용 `st.container` 생성을 완료합니다.
    2.  `src/ui/app.py`: 사용자가 아이디어를 입력하고 전송하면, 해당 아이디어를 `st.session_state.initial_idea`에 저장하고, `st.chat_message(name="user")`를 사용하여 채팅창에 즉시 표시하는 로직을 구현합니다.
*   **테스트**:
    1.  애플리케이션 실행 시 기본 UI 요소들이 정상적으로 나타나는지 확인합니다.
    2.  아이디어 입력 및 전송 시, 사용자 메시지가 채팅창에 표시되고 `st.session_state.initial_idea`에 저장되는지 확인합니다.

**단계 3: 1단계 시스템 안내 메시지 플로우 및 사용자 추가 정보 입력/상태 저장 구현**

*   **지침**:
    1.  `src/ui/app.py` 또는 별도 유틸리티 파일: 1단계 진행에 필요한 시스템 안내 메시지 템플릿(최초 안내, 분석 시작 안내, 각 페르소나 분석 시작 전 안내, 1단계 완료 및 2단계 진행 질문 안내)을 정의합니다. (LLM 불필요)
    2.  `src/ui/app.py`: `st.session_state`의 상태 변화에 따라 정의된 시스템 안내 메시지들을 `st.chat_message(name="assistant", avatar="🧠")`를 사용하여 순차적으로 채팅창에 표시하는 로직을 구현합니다.
    3.  `src/ui/app.py`: (선택 사항) 사용자가 아이디어의 "핵심 목표", "주요 제약 조건", "중요 가치"를 입력할 수 있는 `st.text_input` 필드들을 추가하고, 입력값을 `st.session_state`에 `user_goal`, `user_constraints`, `user_values` 키로 저장합니다. **이 값들은 ADK `session.state`에도 동일한 키로 저장되도록 1단계 워크플로우 시작 시 전달합니다.**
*   **테스트**:
    1.  아이디어 입력부터 1단계 분석 흐름에 따라 시스템 안내 메시지들이 정확한 순서와 내용으로 표시되는지 확인합니다.
    2.  (선택 사항) 추가 정보 입력 필드가 UI에 표시되고, 입력값이 `st.session_state` 및 ADK `session.state`에 올바르게 저장/전달되는지 확인합니다.

**단계 4: ADK 세션 관리 전략 정의 및 1단계 `SequentialAgent` 워크플로우 구현**

*   **지침**:
    1.  **세션 관리 전략**:
        *   사용자당 고유한 ADK 세션 ID를 생성하고 관리합니다.
        *   **Phase 1과 Phase 2는 동일한 ADK 세션 ID를 사용합니다.** 이를 통해 `session.state`에 저장된 1단계 결과물(`initial_idea`, `user_goal`, 각 페르소나의 1단계 보고서 키 등)이 2단계 토론에서 자연스럽게 연속적으로 참조될 수 있도록 합니다.
    2.  `src/orchestrator/main_orchestrator.py` (`AIdeaLabOrchestrator` 클래스):
        *   1단계용 페르소나 에이전트(`MarketerPersonaAgent`, `CriticPersonaAgent`, `EngineerPersonaAgent`) 인스턴스들을 생성합니다. 각 에이전트의 `instruction`은 **1단계용으로 특화된 프롬프트**를 사용하고, `output_key`는 `session.state`에 저장될 고유한 키(예: `marketer_report_phase1`)로 설정합니다.
        *   1단계 분석 결과를 종합할 `SummaryAgent_Phase1` (`Agent`) 인스턴스를 생성하고, `instruction`은 `FINAL_SUMMARY_PROMPT`(1단계 결과 키들을 참조하도록 수정된 버전), `output_key`는 `summary_report_phase1`로 설정합니다.
        *   위 에이전트들을 순서대로 `sub_agents`로 포함하는 `SequentialAgent` 인스턴스를 생성하고, 이를 반환하는 `get_phase1_workflow()` 메서드를 구현합니다.
    3.  `src/ui/app.py` (`analyze_idea_phase1` 함수 또는 유사 로직 새로 정의):
        *   ADK `InMemorySessionService` 인스턴스를 사용합니다. 사용자별 고유 세션 ID를 기반으로 ADK `Session` 객체를 생성하거나 가져옵니다.
        *   ADK `session.state`에 `initial_idea` 및 사용자 추가 정보(`user_goal` 등)를 저장합니다.
        *   `AIdeaLabOrchestrator`를 통해 `get_phase1_workflow()`를 호출하여 `SequentialAgent`를 가져옵니다.
        *   ADK `Runner`를 통해 이 `SequentialAgent`를 비동기적(`runner.run_async`)으로 실행합니다.
*   **테스트**:
    1.  `get_phase1_workflow()` 호출 시, `SequentialAgent`와 그 `sub_agents` 설정이 올바른지 단위 테스트로 검증합니다.
    2.  아이디어 분석 요청 시, ADK 세션이 생성/로드되고 초기 상태값이 저장되며, `SequentialAgent`가 `Runner`를 통해 실행되는지 확인합니다. 1단계와 2단계가 동일한 세션 ID를 공유하는 구조인지 확인합니다.

**단계 5: 1단계 페르소나 분석 결과 순차적 UI 표시 (비동기 스트리밍) 및 2단계 진입 선택 UI 구현**

*   **지침**:
    1.  `src/ui/app.py` (`analyze_idea_phase1` 함수 내): `SequentialAgent`의 실행 이벤트 스트림(`runner.run_async`의 결과)을 비동기적으로(`async for event in event_stream:`) 처리합니다.
        *   각 `sub_agent`의 실행이 완료되어 `is_final_response()`가 `True`인 이벤트를 받으면, 해당 에이전트의 `output_key`를 사용하여 `session.state`에서 결과 텍스트를 가져옵니다.
        *   가져온 결과 텍스트를 **Streamlit의 `st.write_stream` 함수와 함께 사용하여 챗봇 UI에 점진적으로(스트리밍) 표시**합니다. `st.chat_message(name="페르소나이름").write_stream(stream_function)` 형태로 구현합니다. `stream_function`은 결과 텍스트를 작은 단위로 나누어 `yield`하는 제너레이터 함수가 될 수 있습니다. (긴 내용은 "더 자세히 보기" 옵션 고려)
    2.  `src/ui/app.py`: 모든 1단계 분석 및 요약이 완료된 후, 챗봇 UI에 1단계 완료 시스템 안내 메시지와 함께 "2단계 토론 시작하기" 및 "여기서 분석 종료하기" 버튼(`st.button`)을 표시합니다. 각 버튼은 `st.session_state.proceed_to_phase2` (boolean) 상태 값을 업데이트합니다.
    3.  `src/ui/app.py`: "2단계 토론 시작하기" 버튼 위에 2단계 토론 방식 및 목표를 안내하는 간단한 시스템 메시지를 추가합니다.
*   **테스트**:
    1.  아이디어 분석 후, 각 페르소나의 결과와 1단계 요약이 순서대로, 올바른 내용으로 챗봇 UI에 **스트리밍 형태로 부드럽게 표시되는지** 확인합니다. `session.state`에 해당 결과들이 저장되었는지 확인합니다.
    2.  1단계 완료 후, 2단계 진행 선택 버튼들이 UI에 정상적으로 표시되고, 클릭 시 `st.session_state`의 관련 플래그가 올바르게 변경되는지 확인합니다.

## Phase 2: 실시간 가상 회의 (챗봇 UI 내 토론 지속)

**단계 6: `DiscussionFacilitatorAgent` 정의, 2단계용 프롬프트 작성 및 라우팅 메커니즘 설계**

*   **지침**:
    1.  `src/agents/facilitator_agent.py`: `DiscussionFacilitatorAgent` 클래스를 `LlmAgent`를 상속하여 정의합니다. (`name`: "facilitator_agent")
    2.  `config/prompts.py`: **`FACILITATOR_PHASE2_PROMPT`** 를 새로 정의합니다. 이 프롬프트에는 다음이 포함됩니다:
        *   2단계 토론 목표, 참조할 `session.state` 변수 목록(1단계 결과 전체, 사용자 목표/제약, 2단계 토론 기록).
        *   토론 진행 방식: 첫 발언자 지정, 아이디어 평가 프레임워크(예: RICE) 또는 1단계 문제점 기반 질문 유도.
        *   **라우팅 메커니즘**: "다음 발언자로 [페르소나_에이전트_이름]을 지목하고, [구체적인 질문/주제]를 제시하세요." 와 같이 LLM이 다음 행동을 결정하도록 유도합니다. LLM의 응답에서 다음 대상 에이전트 이름과 전달할 메시지를 추출할 수 있는 특정 출력 형식을 지정합니다. (예: JSON 형식으로 `{"next_agent": "marketer_agent", "message_to_next_agent": "1단계 보고서의 A 부분에 대해 더 자세히 설명해주세요."}`) **Google ADK의 `transfer_to_agent`는 LLM이 직접 함수 호출을 생성하는 방식이므로, 촉진자 LLM이 이러한 함수 호출을 생성하도록 프롬프트를 구성하거나, LLM의 텍스트 응답을 파싱하여 수동으로 다음 에이전트를 호출하는 커스텀 로직을 `DiscussionFacilitatorAgent` 또는 오케스트레이터 레벨에 구현합니다. 여기서는 후자(텍스트 응답 파싱 후 커스텀 위임 로직)를 우선 고려합니다.**
        *   **토론 종료 조건**: 명확한 종료 조건(예: "총 X라운드 발언 후 종료", "주요 쟁점 해결 시 종료", "사용자 종료 요청 시" - 단, 사용자 요청은 UI에서 별도 처리 후 촉진자에게 전달)과 종료 시 출력할 특정 메시지(예: "FINAL_SUMMARY_REQUESTED")를 정의합니다.
    3.  `src/orchestrator/main_orchestrator.py` (`AIdeaLabOrchestrator` 클래스): `DiscussionFacilitatorAgent` 인스턴스(위 프롬프트 사용)를 생성하고, 이 에이전트가 2단계 토론을 조정하도록 하는 `get_phase2_discussion_coordinator()` 메서드를 구현합니다. (페르소나 에이전트들은 촉진자의 지시에 따라 개별 호출될 것이므로, 촉진자의 `sub_agents`로 반드시 등록할 필요는 없을 수 있습니다. 대신, 촉진자 LLM의 출력을 받아 오케스트레이터가 해당 페르소나를 실행하는 구조를 고려합니다.)
*   **테스트**:
    1.  `FACILITATOR_PHASE2_PROMPT` 내용이 라우팅/위임 지침(다음 에이전트 및 메시지 명시) 및 종료 조건 포함 여부를 검토합니다.
    2.  `DiscussionFacilitatorAgent`가 초기 실행 시 적절한 첫 발언(예: 토론 시작 안내)을 생성하는지 확인합니다.

**단계 7: 페르소나 에이전트 2단계용 프롬프트 정의 및 적용 방식 구체화**

*   **지침**:
    1.  `config/prompts.py`: 각 페르소나(마케터, 비평가, 엔지니어)를 위한 **2단계 토론용 시스템 프롬프트**(`MARKETER_PHASE2_PROMPT`, `CRITIC_PHASE2_PROMPT`, `ENGINEER_PHASE2_PROMPT`)를 별도로 새로 정의합니다.
        *   **핵심 포함 내용**: 현재가 "2단계 토론" 상황임을 명시, 1단계 결과물 전체 및 현재 토론 기록(`{state.discussion_history_phase2}`)/촉진자 지시(`{state.facilitator_question_to_persona}`) 참조, 다른 페르소나 의견 구체적 지칭 및 상호작용, 아이디어 "발전" 제안 장려, 사용자 목표/제약 조건 연결 설명 권장.
    2.  **프롬프트 전환 방식**: 각 페르소나 에이전트 클래스(`MarketerPersonaAgent` 등) 내부에, `run` (또는 유사) 메서드 실행 시 `session.state.current_phase` (또는 전달받는 파라미터) 값을 확인하여, **"phase1"일 경우 1단계 프롬프트를, "phase2"일 경우 2단계 프롬프트를 `instruction`으로 사용하도록 조건부 로직을 구현합니다.** 이렇게 하면 동일한 에이전트 인스턴스를 단계에 따라 다른 행동 방식으로 사용할 수 있습니다.
*   **테스트**:
    1.  각 페르소나의 2단계용 프롬프트 내용이 상호작용과 아이디어 발전을 촉진하는 방향으로 작성되었는지 검토합니다.
    2.  2단계 토론 중 특정 페르소나가 호출될 때, 해당 페르소나가 `session.state.current_phase` (또는 유사 플래그)에 따라 올바른 2단계용 프롬프트를 사용하여 응답하는지 로그 또는 디버깅으로 확인합니다.

**단계 8: 2단계 실시간 토론 흐름 제어 및 UI 연동 구현**

*   **지침**:
    1.  `src/ui/app.py` (`analyze_idea_phase2` 함수 또는 유사 로직): 사용자가 "2단계 토론 시작하기"를 선택하면 이 함수를 호출합니다.
        *   `session.state.current_phase = "phase2"`로 설정합니다.
        *   ADK `Session` (1단계와 동일 ID) 및 `Runner`를 준비합니다.
        *   `AIdeaLabOrchestrator`를 통해 `DiscussionFacilitatorAgent` 인스턴스를 가져옵니다.
        *   `session.state.discussion_history_phase2` 리스트를 초기화합니다.
        *   **토론 루프 시작**:
            1.  `DiscussionFacilitatorAgent`를 `Runner`로 실행합니다. (입력으로 현재 `discussion_history_phase2` 전달)
            2.  촉진자의 응답을 받아 UI에 표시하고, `discussion_history_phase2`에 기록합니다.
            3.  촉진자의 응답에서 다음 행동(다음 발언할 페르소나 이름, 그 페르소나에게 전달할 메시지/질문, 또는 토론 종료 신호)을 파싱합니다.
            4.  만약 다음 발언할 페르소나가 있다면, 해당 페르소나 에이전트를 `Runner`로 실행합니다. (입력으로 촉진자가 전달한 메시지/질문과 `discussion_history_phase2` 전달)
            5.  페르소나의 응답을 받아 UI에 표시하고, `discussion_history_phase2`에 기록합니다.
            6.  다시 1번(촉진자 실행)으로 돌아가 토론을 이어갑니다.
            7.  촉진자가 토론 종료 신호("FINAL_SUMMARY_REQUESTED")를 보내면 루프를 종료합니다.
    2.  (선택 사항) 촉진자의 "ASK_USER_FEEDBACK" 요청 처리: 촉진자 응답 파싱 시 해당 신호가 있으면, UI에 사용자 입력을 받고, 그 내용을 `discussion_history_phase2`에 기록 후 다시 촉진자에게 전달하여 토론에 반영합니다.
*   **테스트**:
    1.  "2단계 토론 시작하기" 버튼 클릭 시, 촉진자의 첫 메시지가 UI에 나타나고 토론 루프가 시작되는지 확인합니다.
    2.  촉진자 → 페르소나 → 촉진자 → 다른 페르소나 순으로 발언이 오고 가며, 각 발언이 UI와 `discussion_history_phase2`에 정확히 기록되는지 여러 턴에 걸쳐 테스트합니다.
    3.  페르소나들이 서로의 의견을 참조하고, 촉진자가 적절히 토론을 이끌어가는지 확인합니다.
    4.  (선택 사항) 사용자 피드백 요청-응답-반영 흐름이 정상 작동하는지 확인합니다.

**단계 9: 2단계 토론 종료 처리 및 `FinalSummaryAgent_Phase2`를 통한 최종 결과 생성/표시**

*   **지침**:
    1.  `src/ui/app.py` (`analyze_idea_phase2` 함수 내): 토론 루프 중 `DiscussionFacilitatorAgent`로부터 "FINAL_SUMMARY_REQUESTED" 신호를 받으면, 루프를 종료하고 `FinalSummaryAgent_Phase2` (`LlmAgent`)를 호출합니다.
    2.  `config/prompts.py`: **`FINAL_SUMMARY_PHASE2_PROMPT`** 를 새로 정의합니다. 이 프롬프트는 `{state.initial_idea}`, `{state.user_goal?}`, 1단계 모든 페르소나 보고서, 그리고 2단계 전체 토론 기록(`{state.discussion_history_phase2}`)을 참조하여 "최종 발전된 아이디어 및 실행 계획 보고서"를 생성하도록 지시합니다. **이때, 보고서에는 최종 계획서 `prd.md`에 명시된 항목들(최종 아이디어 설명, 주요 변경 사항, 핵심 장점, 잠재적 리스크 및 완화 방안, 구체적인 다음 실행 단계 제안 등)이 반드시 포함되도록 상세히 작성합니다.**
    3.  `FinalSummaryAgent_Phase2`의 결과는 `session.state.final_summary_report_phase2`에 저장합니다.
    4.  `src/ui/app.py`: `session.state.final_summary_report_phase2`에 저장된 최종 보고서를 챗봇 UI 내에 가독성 있는 메시지(요약과 함께 상세 내용을 펼쳐볼 수 있는 형태)로 제시합니다.
*   **테스트**:
    1.  정의된 종료 조건에 따라 촉진자가 토론을 정상적으로 종료하고, "FINAL_SUMMARY_REQUESTED" 신호를 보내는지 확인합니다.
    2.  `FinalSummaryAgent_Phase2`가 생성하는 보고서가 1단계 및 2단계의 모든 주요 내용을 종합하고, **위에서 언급된 구체적인 보고서 항목들을 충실히 포함하는지** 검토합니다.
    3.  최종 보고서가 UI에 올바르게 표시되는지 확인합니다.

**단계 10: 전체 통합 테스트, 오류 처리 전략 구체화 및 최종 검토**

*   **지침**:
    1.  Phase 1과 Phase 2의 모든 기능이 자연스럽게 연동되어 전체 사용자 시나리오대로 작동하는지 종합적으로 테스트합니다.
    2.  다양한 아이디어 입력, 사용자 선택(1단계 종료, 2단계 진행, 사용자 피드백 제공/미제공 등)에 따른 모든 경로를 테스트합니다.
    3.  **오류 처리 전략 구체화 및 구현**:
        *   **API 통신 실패 (LLM 호출 시)**: `try-except` 블록을 사용하여 API 호출 부분을 감싸고, `requests.exceptions.RequestException` 또는 Gemini API 관련 특정 예외 발생 시, 사용자에게 "AI 모델 응답에 실패했습니다. 잠시 후 다시 시도해주세요."와 같은 친절한 오류 메시지를 챗봇 UI에 표시합니다. 내부적으로는 오류를 로깅합니다.
        *   **LLM 응답 지연**: Streamlit의 스피너(`st.spinner`) 또는 유사한 기능을 사용하여 AI가 응답을 생성 중임을 사용자에게 시각적으로 알립니다. 만약 응답이 과도하게 지연될 경우(타임아웃 설정 고려), "AI 응답이 지연되고 있습니다. 잠시만 더 기다려주시거나, 문제가 지속되면 새로고침 해주세요."와 같은 메시지를 표시할 수 있습니다.
        *   **세션 상태 관리 오류 (예상치 못한 경우)**: 주요 `session.state` 접근 시 `try-except KeyError` 등을 사용하여 방어적으로 코딩하고, 만약 필수 상태값이 없을 경우 사용자에게 "분석 진행에 필요한 정보가 부족합니다. 처음부터 다시 시도해주세요."와 같은 안내와 함께 초기화 옵션을 제공할 수 있습니다.
        *   **일반적인 예외 처리**: 각 주요 기능(함수) 실행 부분에 포괄적인 `try-except Exception as e:` 블록을 추가하여 예기치 않은 오류 발생 시 사용자에게는 일반적인 오류 메시지("오류가 발생했습니다. 관리자에게 문의해주세요.")를 보여주고, 개발자를 위해 상세 오류 정보(`str(e)`, `traceback`)를 로깅합니다.
    4.  UI 일관성, 응답 속도, 메시지 가독성 등 전반적인 사용성을 검토하고 개선합니다.
*   **테스트**:
    1.  최소 3개 이상의 다양한 아이디어를 입력하여 전체 플로우를 처음부터 끝까지 실행하고, 모든 단계에서 예상된 결과가 출력되는지 확인합니다.
    2.  오류 처리: 의도적으로 API 키 오류, 네트워크 단절, 잘못된 LLM 응답 포맷 등을 유도하여 시스템이 정의된 오류 메시지를 UI에 표시하고 안정적으로 대처하는지 확인합니다.
    3.  예외 상황(매우 짧거나 긴 아이디어, 특수문자 포함 아이디어 등)에 대한 시스템의 대응을 확인합니다.
    4.  최종 결과물이 프로젝트 비전 및 목표에 부합하는지 평가합니다.

이 상세 구현 계획은 AI가 제기한 질문들에 대한 답변을 포함하여, AIdea Lab 고도화 프로젝트를 더욱 체계적이고 견고하게 빌드하는 데 도움이 될 것입니다.