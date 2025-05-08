"""
AIdea Lab의 Google ADK session.state 기본 사용법 테스트
ADK의 session.state를 사용하여 데이터를 저장하고 LLM 프롬프트에서 참조하는 예제입니다.
"""

import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session
from google.adk.runners import Runner
from google.genai import types

# .env 파일에서 환경 변수 로드
load_dotenv()

# 애플리케이션 정보
APP_NAME = "AIdea Lab Session Test"
USER_ID = "test_user"
SESSION_ID = "test_session"

# 세션 서비스 초기화
session_service = InMemorySessionService()

# 세션 생성 함수
def create_session():
    session = session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    return session

# 세션 상태를 사용하는 에이전트 정의
def create_state_aware_agent():
    agent = Agent(
        name="state_aware_agent",
        model="gemini-2.0-flash",
        description="An agent that demonstrates using session state.",
        instruction="""
        당신은 사용자가 제공하는 정보를 기억하고 참조할 수 있는 도우미입니다.
        현재 세션에 저장된 값들을 다음과 같이 참조할 수 있습니다:
        - 테스트 값: {state.test_value}
        - 사용자 이름: {state.user_name}
        
        위의 정보를 활용하여 응답하세요.
        """,
        output_key="agent_response"  # 에이전트 응답을 session.state에 저장할 키
    )
    return agent

# 메인 실행 코드
def main():
    print("🤖 AIdea Lab Session State Test")
    
    # 환경 변수 확인
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY":
        print("⚠️ 에러: GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일에 API 키를 설정해주세요.")
        return
    
    try:
        # 세션 생성
        session = create_session()
        
        # 세션 상태에 값 저장
        session.state["test_value"] = "안녕하세요, 세션 상태 테스트입니다!"
        session.state["user_name"] = "홍길동"
        
        print("\n📝 세션 상태에 다음 값들을 저장했습니다:")
        print(f"- test_value: '{session.state['test_value']}'")
        print(f"- user_name: '{session.state['user_name']}'")
        
        # 에이전트 생성
        agent = create_state_aware_agent()
        
        # Runner 생성
        runner = Runner(
            agent=agent,
            app_name=APP_NAME,
            session_service=session_service
        )
        
        # 테스트 프롬프트
        test_prompt = "세션에 저장된 정보를 알려주세요."
        
        print(f"\n📝 테스트 프롬프트: '{test_prompt}'")
        print("\n⏳ LLM에 요청 중...")
        
        # Content 객체 생성
        content = types.Content(
            role="user",
            parts=[types.Part(text=test_prompt)]
        )
        
        # Runner를 통해 에이전트 실행
        events = runner.run(
            user_id=USER_ID,
            session_id=SESSION_ID, 
            new_message=content
        )
        
        # 응답 처리
        response_text = None
        for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[0].text
                break
        
        if response_text:
            print("\n✅ LLM 응답 성공:")
            print(f"🤖 응답: {response_text}")
        else:
            print("\n❌ 응답을 받지 못했습니다.")
        
        # session.state에 저장된 에이전트 응답 확인
        updated_session = session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID
        )
        
        print("\n📝 session.state에 저장된 에이전트 응답:")
        print(f"- agent_response: '{updated_session.state.get('agent_response', '저장된 응답 없음')}'")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")

if __name__ == "__main__":
    main() 