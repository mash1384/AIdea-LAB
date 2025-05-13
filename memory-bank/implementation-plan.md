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

## Phase 2: 실시간 가상 회의 (챗봇 UI 내 토론 지속)

**단계 6: `DiscussionFacilitatorAgent` 정의, 2단계용 프롬프트 작성 및 라우팅 메커니즘 설계**

* **지침**:
    1.  `src/agents/facilitator_agent.py`: `DiscussionFacilitatorAgent` 클래스를 `LlmAgent`를 상속하여 정의합니다. (`name`: "facilitator\_agent")
    2.  `config/prompts.py`: **`FACILITATOR_PHASE2_PROMPT_PROVIDER`** 라는 이름의 함수를 새로 정의합니다.
        * 이 함수는 `ReadonlyContext` (또는 `CallbackContext`) 객체를 인자로 받아, 현재 `session.state` (예: `state.initial_idea`, `state.user_goal`, 1단계 페르소나별 보고서 키, `state.discussion_history_phase2` 등)를 참조하여 **동적으로 `FACILITATOR_PHASE2_PROMPT` 문자열을 생성하여 반환**합니다.
        * 프롬프트 내용에는 다음이 포함됩니다:
            * 2단계 토론 목표 및 현재까지의 주요 정보 요약 (1단계 결과 요약, 사용자 목표/제약 등).
            * 토론 진행 방식 지침: 첫 발언자 지정 (또는 LLM이 판단), 아이디어 평가 프레임워크(예: RICE) 또는 1단계에서 지적된 주요 문제점들을 기반으로 질문이나 토론 주제를 유도하는 방식.
            * **라우팅 메커니즘 명시**: LLM이 다음 행동을 결정하도록 유도합니다. 출력은 JSON 형식을 사용하도록 명확히 지시합니다. (예: `{"next_agent": "marketer_agent" | "critic_agent" | "engineer_agent" | "USER" | "FINAL_SUMMARY", "message_to_next_agent_or_topic": "구체적인 질문 또는 다음 토론 주제", "reasoning": "왜 이 에이전트/주제를 선택했는지에 대한 간략한 근거"}`). `USER`는 사용자 피드백 요청, `FINAL_SUMMARY`는 토론 종료 및 최종 요약 요청을 의미합니다.
            * **토론 종료 조건**: 명확한 종료 조건(예: "주요 쟁점이 충분히 논의되었고 더 이상 발전적인 의견이 없을 경우 FINAL\_SUMMARY를 요청하세요.", "사용자가 명시적으로 종료를 요청한 경우 (UI통해 전달받음)")과 종료 시 출력할 JSON의 `next_agent` 값을 "FINAL\_SUMMARY"로 지정하도록 안내.
    3.  `src/orchestrator/main_orchestrator.py` (`AIdeaLabOrchestrator` 클래스):
        * `DiscussionFacilitatorAgent` 인스턴스를 생성하는 메서드 `get_phase2_discussion_facilitator()`를 구현합니다. 이때, `instruction` 인자로는 위에서 정의한 `FACILITATOR_PHASE2_PROMPT_PROVIDER` 함수를 전달합니다.
* **테스트**:
    1.  `FACILITATOR_PHASE2_PROMPT_PROVIDER` 함수가 다양한 `session.state` 값에 따라 적절한 프롬프트를 생성하는지 단위 테스트합니다.
    2.  `DiscussionFacilitatorAgent`가 초기 실행 시(빈 `discussion_history_phase2` 등) 적절한 첫 발언(예: 토론 시작 안내 및 첫 발언자/주제 지정)을 JSON 형식의 라우팅 지침과 함께 생성하는지 확인합니다.

**단계 7: 페르소나 에이전트 2단계용 프롬프트 정의 및 적용 방식 구체화**

* **지침**:
    1.  `config/prompts.py`: 각 페르소나(마케터, 비평가, 엔지니어)를 위한 **2단계 토론용 동적 프롬프트 제공 함수**(`MARKETER_PHASE2_PROMPT_PROVIDER`, `CRITIC_PHASE2_PROMPT_PROVIDER`, `ENGINEER_PHASE2_PROMPT_PROVIDER`)를 새로 정의합니다.
        * 각 함수는 `ReadonlyContext` (또는 `CallbackContext`)를 인자로 받아, 현재 `session.state` (1단계 자신의 보고서 및 다른 페르소나 보고서 요약, `state.current_phase == "phase2"`인 상황, `state.discussion_history_phase2`의 관련 내용, 촉진자가 전달한 특정 질문/주제인 `{state.facilitator_question_to_persona}` 등)를 참조하여 **동적으로 해당 페르소나의 2단계용 프롬프트 문자열을 생성하여 반환**합니다.
        * **핵심 포함 내용**: 현재가 "2단계 토론" 상황임을 명시, 촉진자의 특정 지시사항(`{state.facilitator_question_to_persona}`)에 집중하여 답변하도록 유도, 아이디어를 "발전"시키는 구체적인 제안 장려, 다른 페르소나의 의견을 구체적으로 지칭하며 자신의 관점을 개진하도록 안내, 사용자 목표/제약조건과의 연관성 설명 권장.
    2.  **프롬프트 적용 방식**: `aidea-lab-main/src/agents/` 내의 각 페르소나 에이전트 클래스(`MarketerPersonaAgent` 등)의 `__init__`에서 `instruction`을 설정하는 대신, 또는 `AIdeaLabOrchestrator`에서 해당 페르소나 에이전트 인스턴스를 가져올 때, 위에서 정의한 각 페르소나별 `_PHASE2_PROMPT_PROVIDER` 함수를 `instruction`으로 전달하여 `LlmAgent`를 구성합니다. 이렇게 하면 에이전트가 실행될 때마다 현재 컨텍스트에 맞는 프롬프트를 사용하게 됩니다.
* **테스트**:
    1.  각 페르소나의 2단계용 프롬프트 제공 함수들이 다양한 `session.state` (특히 `facilitator_question_to_persona`)에 따라 적절하고 구체적인 프롬프트를 생성하는지 단위 테스트합니다.
    2.  2단계 토론 중 특정 페르소나가 호출될 때, 해당 페르소나가 올바른 2단계용 프롬프트를 사용하여 (촉진자의 질문을 반영하여) 응답하는지 로그 또는 디버깅으로 확인합니다.

**단계 8: 2단계 실시간 토론 흐름 제어 및 UI 연동 구현**

* **지침**:
    1.  `src/ui/app.py` (`handle_phase2_discussion` 또는 유사한 새 함수 정의): 사용자가 "2단계 토론 시작하기"를 선택하면 이 함수를 비동기로 실행합니다. (Streamlit 버튼 콜백에서 `asyncio.run()` 등으로 호출)
        * `session_manager.get_session()`을 통해 현재 ADK `Session` 객체를 가져옵니다. (1단계와 동일 ID)
        * `session.state["current_phase"] = "phase2"`로 설정하고, `session.state["discussion_history_phase2"] = []` (또는 기존 기록에 이어가는 경우 초기화 안 함)을 통해 토론 기록 리스트를 준비합니다. (이러한 상태 변경은 `session_manager.update_session_state` 와 같은 메서드를 통해 이루어지거나, 다음 에이전트 실행 시 `state_delta`로 전달되어야 합니다. 가장 간단한 방법은 `app.py`에서 `session` 객체의 `state`를 직접 수정한 후, 다음 `Runner` 실행 시 이 `session` 객체가 사용되도록 하는 것입니다. `InMemorySessionService`는 세션 객체를 참조로 다루므로 가능할 수 있으나, `state_delta`를 통해 명시적으로 전달하는 것이 ADK의 일반적인 패턴입니다. 또는 `session_manager`에 `update_current_session_state_directly(session_id, updates)` 같은 메서드 구현 고려)
            * **보완**: `session_manager`에 `set_session_state_value(session_id, key, value)` 또는 `update_session_state_values(session_id, updates: dict)`와 같은 명시적인 상태 업데이트 메서드를 구현하고, `app.py`에서 이를 호출하여 `current_phase`와 `discussion_history_phase2`를 ADK 세션 서비스에 반영합니다. 이 업데이트는 다음 에이전트가 `ReadonlyContext`를 통해 최신 상태를 읽을 수 있도록 보장합니다.
        * `AIdeaLabOrchestrator`를 통해 `DiscussionFacilitatorAgent` 인스턴스를 가져옵니다. (이때 에이전트의 `instruction`이 동적 함수이므로 현재 `session.state`를 올바르게 참조할 것입니다.)
        * **토론 루프 시작 (최대 N회 반복 또는 명시적 종료 신호까지)**:
            1.  현재 `session.state` (특히 `discussion_history_phase2`)를 포함한 `Content` 객체를 만들어 `DiscussionFacilitatorAgent`를 `Runner`로 실행합니다. (또는 촉진자 프롬프트가 `ctx.state`를 직접 참조하므로 별도 `Content`보다는 빈 `new_message`로 트리거 가능)
            2.  촉진자의 응답(`event.actions.state_delta`에 저장된 텍스트)을 받아 UI에 표시(`add_message` 사용)하고, `discussion_history_phase2`에 `{ "speaker": "facilitator", "text": "..." }` 형태로 기록 (위에서 제안한 `session_manager`의 상태 업데이트 메서드 사용).
            3.  촉진자의 응답 JSON을 파싱하여 `next_agent`, `message_to_next_agent_or_topic` (`topic_for_next`)을 추출합니다.
            4.  **라우팅 처리**:
                * `next_agent`가 "USER"이면: UI에 사용자 피드백 요청 메시지(`topic_for_next`)를 표시하고 사용자 입력을 받습니다. 입력받은 내용은 `discussion_history_phase2`에 `{ "speaker": "user", "text": "..." }` 형태로 기록 후 다시 1번(촉진자 실행)으로 갑니다.
                * `next_agent`가 "FINAL\_SUMMARY"이면: 루프를 종료하고 단계 9로 넘어갑니다.
                * `next_agent`가 특정 페르소나 이름이면: `session.state["facilitator_question_to_persona"] = topic_for_next` 와 같이 상태를 업데이트합니다. 해당 페르소나 에이전트 인스턴스를 가져와 (`AIdeaLabOrchestrator` 사용, 이때 instruction은 동적으로 `facilitator_question_to_persona` 등을 참조), `Runner`로 실행합니다.
            5.  (페르소나가 실행된 경우) 페르소나의 응답을 받아 UI에 표시하고, `discussion_history_phase2`에 기록합니다.
            6.  다시 1번(촉진자 실행)으로 돌아가 토론을 이어갑니다.
    2.  UI에는 현재 발언자와 내용을 명확히 표시하고, 사용자가 토론 중간에 "토론 종료"를 요청할 수 있는 버튼을 제공하는 것을 고려합니다. (이 버튼은 촉진자에게 "사용자 종료 요청"이라는 신호를 보내도록 할 수 있습니다.)
* **테스트**:
    1.  "2단계 토론 시작하기" 버튼 클릭 시, `session.state.current_phase`가 "phase2"로 설정되고, 촉진자의 첫 메시지가 UI에 나타나며 토론 루프가 정상적으로 시작되는지 확인합니다.
    2.  촉진자 -> 페르소나 -> 촉진자 -> 다른 페르소나 순으로 발언이 여러 턴에 걸쳐 오고 가는지, 각 발언이 UI와 `discussion_history_phase2`에 정확히 기록/업데이트되는지 확인합니다.
    3.  `facilitator_question_to_persona` 상태 값이 각 페르소나 호출 전에 올바르게 설정되고, 페르소나의 응답이 해당 질문에 관련된 내용인지 확인합니다.
    4.  (선택 사항) 사용자 피드백 요청-응답-반영 흐름이 정상 작동하는지 확인합니다.

**단계 9: 2단계 토론 종료 처리 및 `FinalSummaryAgent_Phase2`를 통한 최종 결과 생성/표시**

* **지침**:
    1.  `src/ui/app.py` (`handle_phase2_discussion` 또는 유사 함수 내): 토론 루프 중 `DiscussionFacilitatorAgent`로부터 파싱된 `next_agent`가 "FINAL\_SUMMARY"이면, 루프를 종료하고 `FinalSummaryAgent_Phase2` (`LlmAgent`)를 호출합니다.
    2.  `config/prompts.py`: **`FINAL_SUMMARY_PHASE2_PROMPT_PROVIDER`** 라는 이름의 함수를 새로 정의합니다.
        * 이 함수는 `ReadonlyContext`를 인자로 받아, `session.state`의 모든 관련 정보 (`initial_idea`, `user_goal` 등, 1단계 모든 페르소나 보고서, 그리고 2단계 전체 `discussion_history_phase2`)를 참조하여 "최종 발전된 아이디어 및 실행 계획 보고서" 생성을 지시하는 프롬프트 문자열을 동적으로 생성합니다.
        * **보고서 항목 명시**: 최종 계획서 `prd.md`에 명시된 항목들(최종 아이디어 설명, 주요 변경 사항, 핵심 장점, 잠재적 리스크 및 완화 방안, 구체적인 다음 실행 단계 제안 등)이 반드시 포함되도록 프롬프트에 상세히 작성합니다.
        * **컨텍스트 크기 관리**: `discussion_history_phase2`가 매우 길 경우, 전부 포함하기보다는 핵심적인 내용이나 요약본을 전달하는 방안을 고려해야 합니다 (예: 프롬프트 제공 함수 내에서 요약 로직 수행 또는 LLM에 요약 요청 후 결과 사용).
    3.  `AIdeaLabOrchestrator`를 통해 `FinalSummaryAgent_Phase2` 인스턴스를 가져오되, `instruction`에는 위에서 정의한 `FINAL_SUMMARY_PHASE2_PROMPT_PROVIDER` 함수를 사용합니다.
    4.  `FinalSummaryAgent_Phase2`의 결과는 `session.state.final_summary_report_phase2`에 저장하고 (ADK `LlmAgent`의 `output_key` 사용), `app.py`에서 해당 결과를 UI에 가독성 있게 표시합니다.
* **테스트**:
    1.  정의된 종료 조건(예: 촉진자의 "FINAL\_SUMMARY" 라우팅)에 따라 토론이 정상적으로 종료되고 `FinalSummaryAgent_Phase2`가 호출되는지 확인합니다.
    2.  `FinalSummaryAgent_Phase2`가 생성하는 보고서가 1단계 및 2단계의 주요 내용을 종합하고, **계획서에 명시된 구체적인 보고서 항목들을 충실히 포함하는지** 검토합니다. (컨텍스트 제한으로 인해 일부 내용이 누락되지 않는지 주의)
    3.  최종 보고서가 UI에 올바르게 표시되는지 확인합니다.

**단계 10: 전체 통합 테스트, 오류 처리 전략 구체화 및 최종 검토**

* **지침**:
    1.  Phase 1과 Phase 2의 모든 기능이 자연스럽게 연동되어 전체 사용자 시나리오대로 작동하는지 종합적으로 테스트합니다. (다양한 아이디어, 사용자 선택 경로 포함)
    2.  **오류 처리 전략 구체화 및 구현**:
        * **API 통신 실패 / LLM 응답 지연**: `app.py`의 각 `Runner.run_async()` 호출 부분을 `try-except`로 감싸고, 예외 발생 시 사용자에게 "AI 모델 응답에 실패했습니다. 잠시 후 다시 시도해주세요." 또는 "응답이 지연되고 있습니다."와 같은 메시지를 `st.error` 또는 `st.warning`으로 UI에 표시합니다. `st.spinner`를 적절히 사용하여 대기 중임을 알립니다.
        * **ADK 자체 오류**: `Event` 객체의 `error_code`, `error_message` 필드를 확인하여 (만약 ADK가 채워준다면) 해당 정보를 사용자에게 좀 더 구체적으로 안내하거나 로깅합니다. ADK가 발생시킬 수 있는 특정 Exception(예: `LlmCallsLimitExceededError`)을 개별적으로 `except` 블록에서 처리하는 것을 고려합니다.
        * **세션 상태 관리 오류**: `session.state`에서 필수 키가 없을 경우(`KeyError`) 등을 방어적으로 처리하고, 사용자에게 "분석 진행에 필요한 정보가 부족합니다. 처음부터 다시 시도해주세요."와 같은 안내와 함께 `restart_session()` 옵션을 제공합니다.
        * **일반적인 예외 처리**: 각 주요 기능(함수) 실행 부분에 포괄적인 `try-except Exception as e:` 블록을 추가하여 예기치 않은 오류 발생 시 사용자에게는 일반적인 오류 메시지("오류가 발생했습니다.")를 보여주고, 개발자를 위해 상세 오류 정보(`str(e)`, `traceback`)를 로깅합니다.
    3.  UI 일관성, 응답 속도, 메시지 가독성 등 전반적인 사용성을 검토하고 개선합니다. (예: 긴 토론 내용에 대한 스크롤 처리, 가독성 높은 마크다운 포맷팅 등)
* **테스트**:
    1.  최소 3개 이상의 다양한 아이디어를 입력하여 전체 플로우를 처음부터 끝까지 실행하고, 모든 단계에서 예상된 결과가 출력되는지 확인합니다. (정상 경로, 예외 경로 모두 테스트)
    2.  오류 처리: 의도적으로 API 키 오류 유도, 네트워크 단절 상황 시뮬레이션, LLM이 잘못된 형식의 JSON을 반환하는 경우(촉진자 라우팅 파싱 시) 등을 가정하여 시스템이 정의된 오류 메시지를 UI에 표시하고 안정적으로 대처하는지 확인합니다.
    3.  매우 길거나 짧은 아이디어, 특수문자 포함 아이디어 등 예외적인 입력에 대한 시스템의 대응을 확인합니다.
    4.  최종 결과물이 프로젝트 비전 및 목표에 부합하는지 평가합니다.

---

이 상세 구현 계획은 AI가 제기한 질문들에 대한 답변을 포함하여, AIdea Lab 고도화 프로젝트를 더욱 체계적이고 견고하게 빌드하는 데 도움이 될 것입니다.