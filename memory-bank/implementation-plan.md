# AIdea Lab 고도화 프로젝트: 기능 구현 상세 계획 (AI 개발자용 - 수정본)

## 사전 준비

**단계 1: 개발 환경 및 기본 설정 검증**

*   **지침**:

    1.  `memory-bank/prd.md` (최종 계획서), `memory-bank/architecture.md`, 그리고 [Google ADK 공식 문서](https://google.github.io/adk-docs/)의 핵심 내용을 숙지합니다.
    2.  `config/prompts.py`에 1단계 분석용 페르소나 프롬프트들(`MARKETER_PROMPT`, `CRITIC_PROMPT`, `ENGINEER_PROMPT`)과 1단계 요약용 `FINAL_SUMMARY_PROMPT`가 정의되어 있는지 확인하고 내용을 검토합니다.
*   **테스트**:
    1.  프로젝트의 목표, 아키텍처, ADK 컴포넌트 역할, 데이터 흐름을 설명할 수 있는지 자가 점검합니다.

## Phase 1: 챗봇 UI 기반 개별 심층 분석 및 2단계 진입 선택

**단계 2: 기본 챗봇 UI 레이아웃 및 사용자 아이디어 입력/표시 기능 구현**

*   **지침**:
    1.  `src/ui/app.py`: Streamlit 페이지 설정 (`st.set_page_config`, `st.title`)을 완료합니다.
    2.  `src/ui/app.py`: 사용자 아이디어 입력을 위한 `st.chat_input` 위젯을 배치합니다.
    3.  `src/ui/app.py`: 채팅 메시지(시스템, 사용자, AI)가 표시될 `st.container`를 생성합니다.
    4.  `src/ui/app.py`: 사용자가 아이디어를 입력하고 전송하면, 해당 아이디어를 `st.session_state.initial_idea`에 저장하고, `st.chat_message(name="user")`를 사용하여 채팅창에 즉시 표시하는 로직을 구현합니다.
*   **테스트**:
    1.  애플리케이션 실행 시 기본 UI 요소들이 정상적으로 나타나는지 확인합니다.
    2.  아이디어 입력 및 전송 시, 사용자 메시지가 채팅창에 표시되고 `st.session_state.initial_idea`에 저장되는지 확인합니다.

**단계 3: 1단계 시스템 안내 메시지 플로우 및 사용자 추가 정보 입력 구현**

*   **지침**:
    1.  `src/ui/app.py` 또는 별도 유틸리티 파일: 1단계 진행에 필요한 시스템 안내 메시지 템플릿(최초 안내, 분석 시작 안내, 각 페르소나 분석 시작 전 안내, 1단계 완료 및 2단계 진행 질문 안내)을 정의합니다. (LLM 불필요)
    2.  `src/ui/app.py`: `st.session_state`의 상태 변화에 따라 정의된 시스템 안내 메시지들을 `st.chat_message(name="assistant", avatar="🧠")`를 사용하여 순차적으로 채팅창에 표시하는 로직을 구현합니다.
    3.  `src/ui/app.py`: (선택 사항) 아이디어 입력 부분에 사용자가 "핵심 목표", "주요 제약 조건", "중요 가치"를 입력할 수 있는 `st.text_input` 필드들을 추가하고, 입력값을 `st.session_state`에 `user_goal`, `user_constraints`, `user_values` 키로 저장하는 로직을 구현합니다.
*   **테스트**:
    1.  아이디어 입력부터 1단계 분석 흐름에 따라 시스템 안내 메시지들이 정확한 순서와 내용으로 표시되는지 확인합니다.
    2.  (선택 사항) 추가 정보 입력 필드가 UI에 표시되고, 입력값이 `st.session_state`에 저장되는지 확인합니다.

**단계 4: 1단계 `SequentialAgent` 워크플로우 정의 및 실행 로직 구현**

*   **지침**:
    1.  `src/orchestrator/main_orchestrator.py` (`AIdeaLabOrchestrator` 클래스):
        *   1단계용 페르소나 에이전트(`MarketerPersonaAgent`, `CriticPersonaAgent`, `EngineerPersonaAgent`) 인스턴스들을 생성합니다. 각 에이전트의 `instruction`은 1단계 전용 프롬프트를 사용하고, `output_key`는 `session.state`에 저장될 고유한 키(예: `marketer_report_phase1`)로 설정합니다.
        *   1단계 분석 결과를 종합할 `SummaryAgent_Phase1` (`Agent`) 인스턴스를 생성하고, `instruction`은 `FINAL_SUMMARY_PROMPT`(1단계 결과 참조하도록 수정 필요), `output_key`는 `summary_report_phase1`로 설정합니다.
        *   위 에이전트들을 순서대로 `sub_agents`로 포함하는 `SequentialAgent` 인스턴스를 생성하고, 이를 반환하는 `get_phase1_workflow()` 메서드를 구현합니다.
    2.  `src/ui/app.py` (`analyze_idea_phase1` 함수 또는 유사 로직):
        *   ADK `InMemorySessionService` 및 `Session` 객체를 생성/관리합니다.
        *   ADK `session.state`에 `initial_idea` 및 사용자 추가 정보(`user_goal` 등)를 저장합니다.
        *   `AIdeaLabOrchestrator`를 통해 `get_phase1_workflow()`를 호출하여 `SequentialAgent`를 가져옵니다.
        *   ADK `Runner`를 통해 이 `SequentialAgent`를 비동기적(`runner.run_async`)으로 실행합니다.
*   **테스트**:
    1.  `get_phase1_workflow()` 호출 시, `SequentialAgent`와 그 `sub_agents` 설정(프롬프트, output_key)이 올바른지 단위 테스트로 검증합니다.
    2.  아이디어 분석 요청 시, ADK 세션 생성, 초기 상태값 저장, `SequentialAgent` 실행이 정상적으로 이루어지는지 로그 또는 디버깅으로 확인합니다.

**단계 5: 1단계 페르소나 분석 결과 순차적 UI 표시 및 2단계 진입 선택 UI 구현**

*   **지침**:
    1.  `src/ui/app.py` (`analyze_idea_phase1` 함수 내): `SequentialAgent`의 실행 이벤트 스트림을 비동기 처리하여, 각 페르소나 및 1단계 요약 에이전트의 실행 완료 후 `session.state`에 저장된 결과를 가져와 챗봇 UI에 `st.chat_message`와 `st.write_stream`을 사용하여 순차적으로 표시합니다. 발언자(페르소나 이름 또는 "요약")와 내용을 명시합니다. (긴 내용은 "더 자세히 보기" 옵션 고려)
    2.  `src/ui/app.py`: 모든 1단계 분석 및 요약이 완료된 후, 챗봇 UI에 1단계 완료를 알리는 시스템 메시지와 함께 "2단계 토론 시작하기" 및 "여기서 분석 종료하기" 버튼(`st.button`)을 표시합니다. 각 버튼은 `st.session_state.proceed_to_phase2` (boolean) 또는 유사한 상태 값을 업데이트하도록 합니다.
    3.  `src/ui/app.py`: "2단계 토론 시작하기" 버튼 위에 2단계 토론 방식 및 목표를 안내하는 간단한 시스템 메시지를 추가합니다.
*   **테스트**:
    1.  아이디어 분석 후, 각 페르소나의 결과와 1단계 요약이 순서대로, 올바른 내용으로 챗봇 UI에 스트리밍되어 표시되는지 확인합니다. `session.state`에 해당 결과들이 저장되었는지 확인합니다.
    2.  1단계 완료 후, 2단계 진행 선택 버튼들이 UI에 정상적으로 표시되고, 클릭 시 `st.session_state`의 관련 플래그가 올바르게 변경되는지 확인합니다. 안내 메시지가 표시되는지 확인합니다.

## Phase 2: 실시간 가상 회의 (챗봇 UI 내 토론 지속)

**단계 6: `DiscussionFacilitatorAgent` (토론 촉진자) 정의 및 2단계용 프롬프트 작성**

*   **지침**:
    1.  `src/agents/facilitator_agent.py`: `DiscussionFacilitatorAgent` 클래스를 `LlmAgent`를 상속하여 정의합니다. (`name`: "facilitator_agent", `description`: "2단계 아이디어 발전 토론 진행 및 조율 에이전트")
    2.  `config/prompts.py`: **`FACILITATOR_PHASE2_PROMPT`** 를 새로 정의합니다. 이 프롬프트는 2단계 토론 목표, 참조할 `session.state` 변수 목록(1단계 결과 전체, 사용자 목표/제약, 2단계 토론 기록 등), 토론 진행 방식(첫 발언자 지정, 질문 방식, 아이디어 평가 프레임워크 활용 등), 다음 발언자 지목을 위한 `transfer_to_agent` 함수 호출 생성 유도, 토론 종료 조건 및 종료 메시지 출력 지침을 포함해야 합니다.
    3.  `src/orchestrator/main_orchestrator.py` (`AIdeaLabOrchestrator` 클래스): `DiscussionFacilitatorAgent` 인스턴스(위에서 정의한 프롬프트 사용)를 생성하고, 이 에이전트의 `sub_agents`로 1단계에서 사용된 페르소나 에이전트 인스턴스들(마케터, 비평가, 엔지니어)을 등록합니다. 이 전체 구조(촉진자와 그 하위 페르소나들)를 반환하는 `get_phase2_discussion_coordinator()` 메서드를 구현합니다.
*   **테스트**:
    1.  `FACILITATOR_PHASE2_PROMPT` 내용이 상세하고, 라우팅/위임 및 토론 진행 지침을 명확히 포함하는지 검토합니다.
    2.  `get_phase2_discussion_coordinator()` 호출 시, `DiscussionFacilitatorAgent`가 반환되고 그 `sub_agents`가 올바르게 설정되었는지 확인합니다.

**단계 7: 페르소나 에이전트 2단계용 프롬프트 정의 및 적용 로직 구현**

*   **지침**:
    1.  `config/prompts.py`: 각 페르소나(마케터, 비평가, 엔지니어)를 위한 **2단계 토론용 시스템 프롬프트**(`MARKETER_PHASE2_PROMPT`, `CRITIC_PHASE2_PROMPT`, `ENGINEER_PHASE2_PROMPT`)를 별도로 새로 정의합니다.
        *   **핵심 포함 내용**: 현재가 "2단계 토론" 상황임을 명시, 1단계 결과물 전체 및 현재 토론 기록/촉진자 지시 참조, 다른 페르소나 의견 구체적 지칭 및 상호작용(동의/반박/질문) 유도, 아이디어 "발전" 제안 장려, 사용자 목표/제약 조건 연결 설명 권장.
    2.  각 페르소나 에이전트 클래스(`MarketerPersonaAgent` 등) 또는 `AIdeaLabOrchestrator`에서, 2단계 토론 시 해당 페르소나가 호출될 때 **2단계용 프롬프트가 `instruction`으로 사용되도록** 로직을 구현합니다. (예: `DiscussionFacilitatorAgent`가 `transfer_to_agent` 시, 페르소나 에이전트가 `session.state.current_phase == "phase2"`를 확인하여 내부적으로 2단계 프롬프트를 로드하도록 수정)
*   **테스트**:
    1.  각 페르소나의 2단계용 프롬프트 내용이 상호작용과 아이디어 발전을 촉진하는 방향으로 작성되었는지 검토합니다.
    2.  2단계 토론 중 특정 페르소나가 호출될 때, 해당 페르소나가 2단계용 프롬프트를 기반으로 응답하는지 로그 또는 디버깅으로 확인합니다.

**단계 8: 2단계 실시간 토론 흐름 및 UI 연동 구현**

*   **지침**:
    1.  `src/ui/app.py` (`analyze_idea_phase2` 함수 또는 유사 로직 새로 정의): 사용자가 "2단계 토론 시작하기"를 선택하면 이 함수를 호출합니다.
        *   2단계용 ADK `Session` 및 `Runner`를 준비합니다. (1단계와 동일 세션 ID 사용, `session.state`는 이어짐)
        *   `AIdeaLabOrchestrator`를 통해 2단계 토론 조정자 에이전트(`get_phase2_discussion_coordinator()`)를 가져와 `Runner`로 실행합니다.
        *   `session.state.discussion_history_phase2` 리스트를 초기화합니다.
        *   토론 촉진자(`DiscussionFacilitatorAgent`)의 첫 발언(토론 시작 안내 및 첫 질문)을 챗봇 UI에 `st.chat_message`와 `st.write_stream`을 사용하여 표시하고, `discussion_history_phase2`에 기록합니다. (발언자: "토론 촉진자")
    2.  `analyze_idea_phase2` 함수 내에서 토론 촉진자 에이전트의 실행 이벤트 스트림을 처리합니다. 촉진자가 `transfer_to_agent`를 통해 특정 페르소나에게 발언권을 넘기면, 해당 페르소나 에이전트가 실행되고 그 응답(발언 내용)을 받습니다. 페르소나의 발언을 챗봇 UI에 표시하고 `discussion_history_phase2`에 기록합니다. 이 과정은 촉진자가 토론 종료를 결정할 때까지 반복됩니다.
    3.  (선택 사항) `DiscussionFacilitatorAgent`의 프롬프트에 특정 조건에서 사용자에게 의견을 묻는 액션("ASK_USER_FEEDBACK: [질문]")을 출력하도록 하고, UI에서 이를 감지하여 사용자 입력을 받아 `session.state`에 저장 후 촉진자에게 전달하는 로직을 구현합니다.
*   **테스트**:
    1.  "2단계 토론 시작하기" 버튼 클릭 시, 촉진자의 첫 메시지가 UI에 나타나고 `discussion_history_phase2`가 초기화되는지 확인합니다.
    2.  촉진자의 진행에 따라 각 페르소나가 순서대로 (또는 동적으로) 발언하고, 그 내용이 UI와 `discussion_history_phase2`에 정확히 기록되는지 여러 턴에 걸쳐 테스트합니다.
    3.  (선택 사항) 사용자 피드백 요청-응답-반영 흐름이 정상적으로 작동하는지 확인합니다.

**단계 9: 2단계 토론 종료 및 `FinalSummaryAgent_Phase2`를 통한 최종 결과 생성/표시**

*   **지침**:
    1.  `DiscussionFacilitatorAgent`의 2단계 프롬프트에 명확한 토론 종료 조건과 종료 시 출력할 특정 메시지(예: "FINAL_SUMMARY_REQUESTED")를 정의합니다.
    2.  `src/ui/app.py`: 촉진자의 "FINAL_SUMMARY_REQUESTED" 메시지를 감지하면, `FinalSummaryAgent_Phase2` (`LlmAgent`)를 호출합니다.
        *   `config/prompts.py`: **`FINAL_SUMMARY_PHASE2_PROMPT`** 를 새로 정의합니다. 이 프롬프트는 `{state.initial_idea}`, `{state.user_goal?}`, 1단계 모든 페르소나 보고서(`{state.marketer_report_phase1}` 등), 그리고 2단계 전체 토론 기록(`{state.discussion_history_phase2}`)을 참조하여 "최종 발전된 아이디어 및 실행 계획 보고서"를 생성하도록 지시합니다. **이때, 보고서에는 최종 계획서 `prd.md`에 명시된 항목들(최종 아이디어 설명, 주요 변경 사항, 핵심 장점, 잠재적 리스크 및 완화 방안, 구체적인 다음 실행 단계 제안 등)이 반드시 포함되도록 상세히 작성합니다.**
        *   `FinalSummaryAgent_Phase2`의 결과는 `session.state.final_summary_report_phase2`에 저장합니다.
    3.  `src/ui/app.py`: `session.state.final_summary_report_phase2`에 저장된 최종 보고서를 챗봇 UI 내에 가독성 있는 메시지(요약과 함께 상세 내용을 펼쳐볼 수 있는 형태)로 제시합니다.
*   **테스트**:
    1.  정의된 종료 조건에 따라 촉진자가 토론을 정상적으로 종료하고, "FINAL_SUMMARY_REQUESTED" 메시지를 출력하는지 확인합니다.
    2.  `FinalSummaryAgent_Phase2`가 생성하는 보고서가 1단계 및 2단계의 모든 주요 내용을 종합하고, 최종 계획서에 명시된 항목들을 포함하는지 검토합니다.
    3.  최종 보고서가 UI에 올바르게 표시되는지 확인합니다.

**단계 10: 전체 통합 테스트 및 최종 검토**

*   **지침**:
    1.  Phase 1과 Phase 2의 모든 기능이 자연스럽게 연동되어 최종 계획서에 명시된 전체 사용자 시나리오대로 작동하는지 종합적으로 테스트합니다.
    2.  다양한 아이디어 입력, 사용자 선택(1단계 종료, 2단계 진행, 사용자 피드백 제공/미제공 등)에 따른 모든 경로를 테스트합니다.
    3.  API 통신 실패, 예기치 않은 내부 오류 등 발생 가능한 오류 상황에 대해 사용자에게 친절하고 명확한 안내 메시지를 표시하는 오류 처리 로직을 `src/ui/app.py`의 주요 실행 부분에 `try-except` 블록 등을 사용하여 구현합니다.
    4.  UI 일관성, 응답 속도, 메시지 가독성 등 전반적인 사용성을 검토하고 개선합니다.
*   **테스트**:
    1.  최소 3개 이상의 다양한 아이디어를 입력하여 전체 플로우를 처음부터 끝까지 실행하고, 모든 단계에서 예상된 결과가 출력되는지 확인합니다.
    2.  오류 처리: 의도적으로 API 키를 틀리게 하거나 네트워크 연결을 끊는 등의 상황을 만들어 시스템이 적절한 오류 메시지를 UI에 표시하고 gracefully 하게 대처하는지 확인합니다.
    3.  예외 상황(예: 매우 짧거나 긴 아이디어, 특수문자 포함 아이디어 등)에 대한 시스템의 대응을 확인합니다.
    4.  최종 결과물이 프로젝트 비전 및 목표에 부합하는지 평가합니다.


이 상세 구현 계획은 AIdea Lab 고도화 프로젝트를 체계적으로 진행하고, 각 단계별 목표를 성공적으로 달성하는 데 도움이 될 것입니다.