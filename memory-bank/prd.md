# AIdea Lab 2.0: 아키텍처 디자인 문서 (Rev. 1.1)

**버전:** 1.1
**작성일:** 2025년 5월 25일 (가상)
**작성자:** AI 어시스턴트 (사용자와의 논의 및 ADK 코드 분석 기반)

**1. 개요 (Overview)**

본 문서는 AIdea Lab 2.0의 수정된 아키텍처 디자인을 설명합니다. "사용자가 아이디어를 제시하면 페르소나들이 아이디어 회의를 통해 아이디어를 깎고 다듬어서 더욱 효과적이고 최선의 아이디어가 탄생하게끔 하는 것"이라는 핵심 목표를 달성하기 위해, **"'통합 아이디어 문서(Living Document)' 중심의 반복적 개선 워크플로우"**를 Google ADK 기반으로 구현하는 방안을 구체화합니다. ADK의 동적 프롬프트 기능과 세션 상태 관리 기능을 적극 활용하여 유연성, 확장성, 그리고 협업적 아이디어 발전을 지향합니다.

**2. 목표 (Goals)**

*   **협업적 아이디어 발전 강화:** 페르소나들이 중앙의 "통합 아이디어 문서"를 중심으로 정보를 공유하고, 서로의 의견에 직간접적으로 피드백을 주고받으며 아이디어를 "깎고 다듬는" 환경 제공.
*   **효율적인 컨텍스트 관리:** 각 페르소나에게 작업에 필요한 최소한의 충분한 컨텍스트("통합 아이디어 문서"의 관련 부분)를 동적으로 제공하여 LLM의 처리 부담 감소 및 응답 품질/속도 향상.
*   **정보의 중앙 집중화 및 일관성 유지:** "통합 아이디어 문서"를 `session.state` 내 핵심 데이터로 관리하여 정보 유실 방지 및 일관된 아이디어 상태 유지.
*   **유연성 및 확장성 증대:** 새로운 페르소나 추가/제외 시 워크숍 매니저 에이전트의 로직 수정을 중심으로 대응할 수 있는 모듈식 구조.
*   **사용자 중심의 지속적 개선:** 워크숍 진행 중 또는 종료 후, 사용자가 "통합 아이디어 문서"를 기반으로 질문하거나 추가 논의를 요청하여 아이디어를 계속 발전시킬 수 있는 상호작용 지원.

**3. 아키텍처 다이어그램 (High-Level Architecture)**
+---------------------+ +---------------------------+ +-------------------------+
| 사용자 UI |<---->| UI 컨트롤러 (app.py) |<---->| 워크숍 매니저 에이전트 |
| (Streamlit) | | (ADK Runner, 상태 업데이트) | | (ADK LlmAgent, |
+---------------------+ +---------------------------+ | InstructionProvider 사용) |
^ |
| 사용자 입력 (아이디어, 질문, 결정) | ADK Runner 실행 요청
| 결과 표시 ("통합 아이디어 문서" 뷰) V (JSON 지시사항 출력)
| +-------------------------------------------------+
| | Google ADK (Agent Development Kit) |
| +-------------------------------------------------+
| ^
| | ADK Runner 실행 요청
| V (페르소나 결과 -> state_delta)
+---------------------+ +---------------------------------------------------------------------+
| 페르소나 에이전트 풀 |<---->| 세션 상태 (session.state) |
| (마케터, 분석가, | | +-------------------------------------------------------------------+ |
| 엔지니어 등 | | | "통합 아이디어 문서" (구조화된 Dict) | |
| ADK LlmAgents, | | | (예: state.idea_document.sections.problem_definition.content) | |
| InstructionProvider)| | +-------------------------------------------------------------------+ |
+---------------------+ | | 워크숍 진행 상태 (예: state.current_round_goal) | |
| +---------------------------------------------------------------------+ |
+---------------------------------------------------------------------+

**4. 주요 구성 요소 (Key Components)**

1.  **사용자 UI (User Interface - Streamlit):**
    *   (이전과 동일) 사용자의 아이디어 및 관련 정보 입력, "통합 아이디어 문서" 시각화, 사용자 피드백/질문 입력, 진행 상황 표시.

2.  **UI 컨트롤러 (UI Controller - `app.py`):**
    *   (이전과 동일) Streamlit 콜백 처리, `SessionManager`를 통한 ADK 세션 관리.
    *   워크숍 매니저 에이전트 및 페르소나 에이전트를 ADK `Runner`를 통해 실행.
    *   **핵심 역할:** 워크숍 매니저가 반환한 JSON 지시사항을 파싱하여, 다음 페르소나 에이전트를 실행하거나 사용자에게 질문을 전달하는 등 워크플로우를 실제로 구동.
    *   페르소나 에이전트가 `output_key`를 통해 `state_delta`로 반환한 결과를 받아, "통합 아이디어 문서"(`session.state` 내의 특정 경로)에 병합/업데이트하는 로직 수행. (ADK의 `output_key`가 최상위 키만 지원할 경우 이 역할이 중요해짐)

3.  **워크숍 매니저 에이전트 (Workshop Manager Agent - ADK `LlmAgent`):**
    *   **역할:** 전체 아이디어 발전 워크숍을 총괄 지휘하는 핵심 LLM 에이전트.
    *   **`instruction` (동적 생성):** `InstructionProvider` (Callable)를 사용하여 `ReadonlyContext` (현재 `session.state` 접근 가능)를 인자로 받아, 다음 정보를 포함하는 동적 프롬프트 생성:
        *   "통합 아이디어 문서"(`state.idea_document`)의 현재 상태 요약 또는 주요 변경 사항.
        *   사용자의 초기 아이디어, 목표, 제약 조건, 가치 (`state.initial_idea` 등).
        *   이전 라운드의 목표 및 결과 요약 (`state.workshop_log` 등 참조).
        *   사용자의 추가 질문 또는 요청 (`state.user_follow_up_query` 등).
    *   **지능 및 작업:**
        *   입력된 컨텍스트를 바탕으로 아이디어의 완성도, 미흡점, 다음 개선 목표 등을 판단.
        *   다음 작업 라운드의 구체적인 목표, 참여할 페르소나, 각 페르소나에게 전달할 작업 지시 및 참조할 "통합 아이디어 문서"의 특정 섹션 경로 등을 결정.
        *   페르소나 간 의견 충돌 시 중재 방안이나 추가 탐색 질문 생성.
    *   **`output_key`:** `workshop_manager_decision` (예시)
    *   **출력 (LLM 생성):** `state_delta`를 통해 `session.state[self.output_key]`에 저장될 JSON 형식의 다음 행동 지침.
        ```json
        {
          "next_round_goal": "수익 모델의 시장 경쟁력 검증 및 구체화",
          "assignments": [
            {
              "persona_id": "marketer",
              "task_instruction": "현재 문서의 수익 모델 섹션과 타겟 고객 섹션을 참조하여, 제안된 수익 모델의 경쟁사 대비 강점과 약점을 분석하고, 구체적인 실행 방안을 문서의 '수익 모델 실행 전략' 코멘트 영역에 작성하시오.",
              "input_document_paths": ["idea_document.sections.revenue_model.content", "idea_document.sections.target_audience.content"]
            },
            {
              "persona_id": "critic",
              "task_instruction": "마케터가 업데이트할 '수익 모델 실행 전략' 코멘트를 포함하여, 현재 수익 모델의 잠재적 리스크와 재무적 타당성을 검토하고, 문서의 '수익 모델 리스크 평가' 코멘트 영역에 의견을 작성하시오.",
              "input_document_paths": ["idea_document.sections.revenue_model.content", "idea_document.sections.target_audience.content", "idea_document.sections.revenue_model.comments.marketer_execution_strategy"] // 예시
            }
          ],
          "request_to_user": null, // 또는 "A와 B 중 어떤 수익 모델을 우선 검토할까요?"
          "workshop_status": "in_progress" // 또는 "ready_for_final_review"
        }
        ```

4.  **페르소나 에이전트 풀 (Persona Agent Pool - ADK `LlmAgent`s):**
    *   각 전문 분야(마케터, 분석가, 엔지니어 등)의 LLM 에이전트.
    *   **`instruction` (동적 생성):** `InstructionProvider`를 사용하여 `ReadonlyContext`를 인자로 받아 다음 정보를 포함하는 동적 프롬프트 생성:
        *   워크숍 매니저가 전달한 구체적인 작업 지시 (`state.current_task_instruction_for_persona_X`).
        *   "통합 아이디어 문서"의 관련 섹션 내용 (워크숍 매니저가 `input_document_paths`로 지정한 경로의 데이터를 `state`에서 읽어와 프롬프트에 주입).
        *   자신의 이전 작업 내용이나 다른 페르소나가 최근 남긴 관련 코멘트.
    *   **작업:** 할당된 작업을 수행하여 분석 결과, 제안, 문서 수정 내용 등을 텍스트로 생성.
    *   **`output_key`:** (예시) `persona_X_output`. 이 키로 저장된 결과는 UI 컨트롤러가 후처리하여 "통합 아이디어 문서"의 적절한 위치에 반영.
    *   **출력 (LLM 생성):** 작업 결과 텍스트. (예: 특정 섹션의 수정된 내용, 새로운 코멘트 텍스트).

5.  **세션 상태 (`session.state` - ADK `Session` 객체의 `state` 필드):**
    *   **"통합 아이디어 문서 (Living Document)":**
        *   `state.idea_document`와 같이 최상위 키 밑에 구조화된 딕셔너리로 저장. (ADK `output_key`가 중첩 경로 직접 쓰기를 지원하지 않을 가능성을 고려하여, UI 컨트롤러 또는 콜백에서 결과 병합 필요)
        *   문서의 각 섹션은 `content`, `last_updated_by`, `comments` (리스트), `history` (간단한 변경 로그) 등의 하위 필드를 가질 수 있음.
    *   **워크숍 진행 상태:** `state.current_round_goal`, `state.active_personas_for_round`, `state.user_follow_up_query`, `state.workshop_log` 등.

6.  **Google ADK (Agent Development Kit):**
    *   **`LlmAgent`:** 워크숍 매니저 및 모든 페르소나 에이전트의 기반 클래스.
    *   **`InstructionProvider`:** 각 에이전트의 동적 프롬프트 생성을 위해 필수적으로 활용. `ReadonlyContext`를 통해 `session.state` 접근.
    *   **`Runner`:** UI 컨트롤러에서 각 에이전트를 실행하는 데 사용.
    *   **`SessionService` (`InMemorySessionService`):** 세션 생성 및 `session.state` 관리.
    *   **`Event` 및 `EventActions`:** `Runner` 실행 결과로 생성되며, `state_delta`를 통해 `session.state` 업데이트. (UI 컨트롤러는 이 `state_delta`를 받아 "통합 아이디어 문서"에 반영).
    *   `before_agent_callback`, `after_agent_callback`: 필요시 상태 업데이트 전후 처리, 로깅 등에 활용 가능.

**5. 워크플로우 (Workflow)**

1.  **초기화:** 사용자가 아이디어 제출 → UI 컨트롤러가 `SessionManager`를 통해 ADK 세션 생성, `session.state.idea_document` 초기 구조화.
2.  **라운드 시작 (워크숍 매니저 호출):**
    *   UI 컨트롤러가 워크숍 매니저 에이전트를 실행.
    *   워크숍 매니저는 `session.state`("통합 아이디어 문서", 기타 상태)를 읽어 다음 라운드 목표, 참여 페르소나, 작업 지시 등을 JSON으로 생성하여 자신의 `output_key` (예: `state.workshop_manager_decision`)에 저장.
3.  **페르소나 작업 루프:**
    *   UI 컨트롤러는 `state.workshop_manager_decision`을 파싱.
    *   할당된 각 페르소나에 대해:
        *   워크숍 매니저가 지정한 작업 지시와 "통합 아이디어 문서"의 참조 경로를 `session.state`의 임시 키 (예: `state.current_task_instruction_for_marketer`, `state.context_paths_for_marketer`)에 저장.
        *   해당 페르소나 에이전트를 실행. 페르소나의 `InstructionProvider`는 이 임시 키들을 사용하여 프롬프트 구성.
        *   페르소나의 결과(텍스트)는 해당 페르소나의 `output_key` (예: `state.marketer_output`)에 저장됨.
        *   UI 컨트롤러는 이 `marketer_output`을 가져와 "통합 아이디어 문서"(`state.idea_document`)의 적절한 위치(워크숍 매니저가 지정했거나, 미리 정의된 규칙에 따라)에 업데이트/병합. (코멘트 추가, 섹션 내용 수정 등)
    *   할당된 모든 페르소나의 작업이 완료되면 다음 단계로.
4.  **라운드 종료 및 다음 라운드 준비 (워크숍 매니저 재호출):**
    *   UI 컨트롤러는 다시 워크숍 매니저를 호출 (2단계로 돌아감). 워크숍 매니저는 업데이트된 `state.idea_document`를 보고 다음 행동을 결정.
5.  **반복:** 2~4단계가 아이디어가 충분히 발전하거나 사용자가 만족할 때까지 반복.
6.  **사용자 개입:** 워크숍 매니저의 JSON 지시에 `request_to_user` 필드가 있거나, UI에서 사용자가 직접 개입을 원할 경우, 사용자에게 질문/옵션을 제시하고 입력을 받아 `session.state`에 반영 후 워크숍 매니저에게 전달.
7.  **종료 및 후속 작업:** 워크숍 매니저가 `workshop_status: "completed"`를 반환하거나 사용자가 종료 요청 시, 최종 `state.idea_document`를 결과물로 제시. 이후 사용자의 추가 질문은 `state.user_follow_up_query`로 입력받아 2단계부터 다시 시작 가능.

**6. 컨텍스트 관리 전략**

*   **워크숍 매니저의 지능적 필터링:** 페르소나에게 작업 할당 시, "통합 아이디어 문서"에서 현재 작업과 직접 관련된 섹션 경로(`input_document_paths`)를 명시적으로 지정하여 전달. 페르소나의 `InstructionProvider`는 이 경로의 데이터만 `state`에서 읽어 프롬프트에 포함.
*   **변경 이력 및 코멘트 활용:** "통합 아이디어 문서" 내에 변경 이력이나 코멘트 섹션을 두어, 페르소나가 다른 이의 최근 작업이나 피드백을 쉽게 파악하도록 함.
*   **RAG (선택적 확장):** 문서가 매우 커지거나 특정 과거 정보 검색이 중요해지면, 문서 내용을 Vector DB에 인덱싱하고, 워크숍 매니저나 페르소나가 자연어 질의를 통해 필요한 정보를 검색하여 컨텍스트에 동적으로 포함시키는 RAG 방식 도입 고려.
*   **문서 섹션별 요약 (선택적 확장):** 특정 섹션이 지나치게 방대해지면, 해당 섹션에 대한 온디맨드 요약 기능을 워크숍 매니저나 페르소나가 요청할 수 있도록 구현.

**7. 확장성**

*   **페르소나 추가/제외:**
    *   새로운 페르소나 `LlmAgent` 정의 및 `InstructionProvider` 구현.
    *   워크숍 매니저 에이전트의 프롬프트(LLM의 지식)에 새로운 페르소나의 역할, 전문성, 호출 조건 등을 업데이트.
    *   워크숍 매니저의 JSON 출력 로직(페르소나 선택 부분)에 새 페르소나 ID 반영.
*   **새로운 분석/작업 단계 추가:** "통합 아이디어 문서" 스키마에 새로운 섹션 정의, 해당 섹션을 다루는 작업 목표 및 페르소나 할당 로직을 워크숍 매니저에 추가.

**8. 안정성**

*   **상태 업데이트의 명확성:** 페르소나의 출력을 "통합 아이디어 문서"에 병합하는 로직(UI 컨트롤러 또는 콜백)의 견고성 확보. (예: 동시에 여러 페르소나가 같은 섹션을 수정하려 할 때의 처리 방안 - 순차 실행 또는 코멘트 후 매니저 병합).
*   **JSON 출력 검증:** 워크숍 매니저 및 (필요시) 페르소나 에이전트의 JSON 출력에 대한 스키마 유효성 검사 및 오류 발생 시 폴백 로직 구현.
*   ADK 자체의 오류 처리 메커니즘 활용 및 애플리케이션 레벨에서의 추가적인 예외 처리.