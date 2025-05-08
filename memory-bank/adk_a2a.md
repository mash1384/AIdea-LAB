Google ADK 및 A2A 프로토콜 핵심 로직 (코드 어시스턴트 AI용 요약)
목표: 이 문서는 AI 코드 어시스턴트가 Google ADK 및 A2A 프로토콜의 작동 방식을 명확히 이해하여, 에이전트 기반 시스템 개발 지원의 정확도를 높이는 데 도움을 주기 위함입니다.
1. Google ADK (Agent Development Kit): 에이전트 구축 및 실행 프레임워크

유연성과 제어력을 바탕으로 정교한 AI 에이전트를 구축, 평가, 배포하기 위한 오픈 소스, 코드 중심 Python 툴킷입니다.
중요 링크: 문서 및 샘플 .
에이전트 개발 키트(ADK)는 AI 에이전트를 개발하고 배포하기 위한 유연하고 모듈화된 프레임워크입니다. Gemini와 Google 생태계에 최적화되어 있지만, ADK는 모델과 배포에 구애받지 않으며 다른 프레임워크와 호환되도록 설계되었습니다. ADK는 에이전트 개발을 소프트웨어 개발처럼 느껴지도록 설계되어 개발자가 간단한 작업부터 복잡한 워크플로까지 다양한 에이전트 아키텍처를 더욱 쉽게 생성, 배포 및 조정할 수 있도록 합니다.

✨ 주요 특징
풍부한 도구 생태계 : 사전 구축된 도구, 사용자 정의 기능, OpenAPI 사양을 활용하거나 기존 도구를 통합하여 에이전트에게 다양한 기능을 제공하며, 이 모든 것이 Google 생태계와 긴밀하게 통합됩니다.

코드 우선 개발 : 최고의 유연성, 테스트 가능성 및 버전 관리를 위해 에이전트 로직, 도구 및 오케스트레이션을 Python에서 직접 정의합니다.

모듈식 다중 에이전트 시스템 : 여러 개의 전문 에이전트를 유연한 계층 구조로 구성하여 확장 가능한 애플리케이션을 설계합니다.

어디서나 배포 가능 : Cloud Run에서 에이전트를 쉽게 컨테이너화하고 배포하거나 Vertex AI Agent Engine을 사용하여 원활하게 확장하세요.

🚀 설치
안정적인 릴리스(권장)
다음을 사용하여 ADK의 최신 안정 버전을 설치할 수 있습니다 pip.

pip install google-adk
출시 주기는 주 단위입니다.

이 버전은 최신 공식 릴리스 버전이므로 대부분의 사용자에게 권장됩니다.

개발 버전
버그 수정 및 새로운 기능은 GitHub의 메인 브랜치에 먼저 병합됩니다. 공식 PyPI 릴리스에 아직 포함되지 않은 변경 사항에 접근해야 하는 경우, 메인 브랜치에서 바로 설치할 수 있습니다.

pip install git+https://github.com/google/adk-python.git@main
참고: 개발 버전은 최신 코드 커밋을 기반으로 직접 빌드됩니다. 최신 수정 사항과 기능이 포함되어 있지만, 안정적인 릴리스에는 없는 실험적인 변경 사항이나 버그가 포함될 수 있습니다. 주로 예정된 변경 사항을 테스트하거나 공식 출시 전에 중요한 수정 사항을 확인하는 데 사용하세요.

📚 문서
에이전트 구축, 평가 및 배포에 대한 자세한 가이드는 전체 문서를 참조하세요.

선적 서류 비치
🏁 주요 기능
단일 에이전트 정의:
from google.adk.agents import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="search_assistant",
    model="gemini-2.0-flash", # Or your preferred Gemini model
    instruction="You are a helpful assistant. Answer user questions using Google Search when needed.",
    description="An assistant that can search the web.",
    tools=[google_search]
)
다중 에이전트 시스템을 정의하세요.
코디네이터 에이전트, 그리터 에이전트, 그리고 작업 실행 에이전트로 구성된 다중 에이전트 시스템을 정의합니다. 그러면 ADK 엔진과 모델이 에이전트들이 협력하여 작업을 완료하도록 안내합니다.

from google.adk.agents import LlmAgent, BaseAgent

# Define individual agents
greeter = LlmAgent(name="greeter", model="gemini-2.0-flash", ...)
task_executor = LlmAgent(name="task_executor", model="gemini-2.0-flash", ...)

# Create parent agent and assign children via sub_agents
coordinator = LlmAgent(
    name="Coordinator",
    model="gemini-2.0-flash",
    description="I coordinate greetings and tasks.",
    sub_agents=[ # Assign sub_agents here
        greeter,
        task_executor
    ]
)
개발 UI
에이전트를 테스트, 평가, 디버깅하고 선보이는 데 도움이 되는 내장 개발 UI입니다.



에이전트 평가
adk eval \
    samples_for_testing/hello_world \
    samples_for_testing/hello_world/hello_world_eval_set_001.evalset.json
🤖 A2A 및 ADK 통합
원격 에이전트 간 통신을 위해 ADK는 A2A 프로토콜 과 통합됩니다 . 두 프로토콜의 연동 방식은 이 예시를 참조하세요.

🤝 기여하기
커뮤니티 여러분의 참여를 환영합니다! 버그 신고, 기능 요청, 문서 개선, 코드 기여 등 어떤 것이든 저희의

일반적인 기여 지침 및 흐름 .
코드를 기여하고 싶다면, 시작하려면 코드 기여 지침을 읽어보세요.
📄 라이센스
이 프로젝트는 Apache 2.0 라이선스에 따라 라이선스가 부여되었습니다. 자세한 내용은 LICENSE 파일을 참조하세요.

시사
이 기능은 서비스별 약관의 일반 서비스 약관 섹션에 있는 "GA 이전 기능 약관"의 적용을 받습니다 . GA 이전 기능은 "있는 그대로" 제공되며 지원이 제한될 수 있습니다. 자세한 내용은 출시 단계 설명을 참조하세요 .



ADK는 똑똑한 프로그램(에이전트) 여러 개를 만들고 서로 협력하게 하는 도구입니다.
LlmAgent (핵심 두뇌):
로직: LLM(예: Gemini)을 사용하여 생각하고 말하는 에이전트입니다.
입력 받기: "지시사항(instruction)"과 "공유 메모리(session.state)"에서 현재 상황 정보를 읽어 LLM에게 전달할 질문(프롬프트)을 만듭니다.
LLM으로 생각하기: LLM이 이 질문을 보고 답변을 생성하고, 필요하면 어떤 "도구(tools)"를 쓸지 결정합니다.
결과 공유: 생성된 답변은 "공유 메모리(session.state)"에 특정 이름(output_key)으로 저장되어 다른 에이전트가 볼 수 있게 합니다. 만약 도구를 쓰기로 했다면, ADK가 그 도구를 실행하고 결과를 다시 LLM에게 알려줍니다.
특징: 상황에 따라 유연하게 다르게 행동합니다. (예: AIdea Lab의 각 페르소나)
워크플로 에이전트 (예: SequentialAgent - 작업 지휘자):  
로직: 직접 LLM으로 생각하지 않고, 다른 에이전트(주로 LlmAgent)들을 정해진 순서대로 실행시키는 지휘자입니다.
SequentialAgent: 등록된 에이전트들을 하나씩 차례대로 실행합니다. (예: AIdea Lab 오케스트레이터)
특징: 항상 정해진 규칙대로 행동합니다. 여러 에이전트의 복잡한 작업을 순서대로 처리할 때 유용합니다.
session.state (공유 메모리):
로직: 같은 작업 공간에서 실행되는 여러 에이전트들이 정보를 함께 보고 쓸 수 있는 메모장 같은 것입니다.
한 에이전트가 session.state에 정보를 쓰면 (예: LlmAgent가 output_key로 답변 저장), 다른 에이전트는 그 정보를 읽어서 (예: LlmAgent의 instruction에서 {state.변수명}으로) 자기 작업에 활용합니다.
특징: 에이전트들이 서로의 작업 결과를 알고 다음 행동을 결정하는 데 필수적입니다. (예: AIdea Lab에서 마케터의 의견을 분석가가 참고)
tools (BaseTool 상속 - 에이전트의 손과 발):
로직: LlmAgent가 LLM의 언어 능력만으로는 할 수 없는 일(예: 데이터베이스 조회, 외부 웹사이트 정보 가져오기)을 할 때 사용하는 특별한 기능 모음입니다.
LlmAgent의 "지시사항(instruction)"에 언제 어떤 도구를 써야 하는지 알려줍니다.
LLM이 판단해서 특정 도구가 필요하다고 생각하면, ADK가 그 도구를 실행시키고 결과를 다시 LLM에게 전달하여 최종 답변을 만듭니다.
특징: 에이전트가 단순히 말만 하는 것을 넘어 실제적인 작업을 수행할 수 있게 합니다. (예: AIdea Lab에서 워크숍 내용을 DB에 저장)
2. A2A (Agent-to-Agent) 통신: 에이전트끼리 대화하는 방법
A2A는 크게 두 가지 상황에서 쓰입니다.
ADK 내부 A2A (한 울타리 안에서의 대화):
로직: 하나의 ADK 프로그램 안에서 만들어진 에이전트들끼리 서로 정보를 주고받는 방법입니다. (AIdea Lab MVP의 주요 방식)
session.state 활용 (가장 기본): 위에서 설명한 공유 메모리를 통해 간접적으로 정보를 주고받습니다.
transfer_to_agent (일 떠넘기기): LlmAgent가 자기 일을 마친 후, LLM의 판단에 따라 다른 특정 에이전트에게 "이제 네 차례야!" 하고 작업을 넘깁니다.
AgentTool (다른 에이전트를 도구처럼 쓰기): LlmAgent가 다른 에이전트를 마치 일반 도구처럼 호출해서 그 결과를 받아봅니다.
특징: 같은 ADK 시스템 내에서 긴밀하게 협력하는 에이전트들을 위한 것입니다.
Google의 개방형 A2A 프로토콜 (다른 동네 에이전트와의 대화):
로직: 서로 다른 회사나 다른 기술로 만들어진 외부의 에이전트들과 표준화된 약속(프로토콜)에 따라 인터넷(HTTP)으로 대화하는 방법입니다. (AIdea Lab에서는 나중에 외부 연동 시 사용)
Agent Card (명함 교환): 상대방 에이전트의 "명함(JSON 파일)"을 보고, 그 에이전트가 뭘 할 수 있는지, 어떻게 연락해야 하는지 알아냅니다.
Task 요청 (일 시키기): HTTP 요청으로 상대방 에이전트에게 "이런 일을 해줘" 하고 작업을 보냅니다. 작업 진행 상황은 실시간으로 업데이트 받을 수도 있습니다(SSE).
결과 받기: 작업이 끝나면 상대방 에이전트가 결과를 알려줍니다.
특징: 완전히 다른 환경에 있는 에이전트끼리도 서로 협력할 수 있게 해주는 "만국 공용어" 같은 것입니다.
코드 어시스턴트 AI가 기억해야 할 핵심:
ADK LlmAgent는 instruction과 session.state를 통해 LLM과 소통하고, output_key로 결과를 공유하며, 필요시 tools를 사용합니다.
ADK 내부 에이전트들은 주로 session.state를 통해 협력합니다.
개방형 A2A 프로토콜은 외부의 독립적인 에이전트와 HTTP로 통신하기 위한 표준입니다.