"""
AIdea Lab - 아이디어 분석 워크숍 UI

이 모듈은 Streamlit을 이용한 기본 사용자 인터페이스를 제공합니다.
사용자는 아이디어를 입력하고 분석을 요청할 수 있습니다.
"""

import os
import sys
import asyncio
import streamlit as st
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.orchestrator.main_orchestrator import AIdeaLabOrchestrator
from config.personas import PERSONA_CONFIGS, PersonaType, ORCHESTRATOR_CONFIG, SELECTED_MODEL
from config.models import get_model_display_options, MODEL_CONFIGS, ModelType, DEFAULT_MODEL
import config.personas as personas

# .env 파일에서 환경 변수 로드
load_dotenv()

# Streamlit 페이지 설정
st.set_page_config(
    page_title="AIdea Lab - 아이디어 분석 워크숍",
    page_icon="🧠",
    layout="wide"
)

# 앱 정보
APP_NAME = "AIdea Lab"
USER_ID = "streamlit_user"

# 세션 서비스 초기화
session_service = InMemorySessionService()

def create_session():
    """새로운 세션 생성"""
    session_id = f"session_{st.session_state.get('session_counter', 0)}"
    session = session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id
    )
    return session, session_id

def update_selected_model():
    """
    UI에서 선택된 모델 ID로 전역 SELECTED_MODEL 변수를 업데이트
    """
    # 선택된 모델 ID를 가져옴
    model_id = st.session_state.selected_model
    
    # personas.py의 SELECTED_MODEL 전역 변수 업데이트
    personas.SELECTED_MODEL = model_id
    
    # 디버깅/확인용 메시지 (제품 환경에서는 제거)
    st.success(f"모델이 '{model_id}'(으)로 변경되었습니다.")

async def analyze_idea(idea_text, session, session_id):
    """
    사용자 아이디어를 멀티 페르소나로 분석하고 최종 요약을 생성하는 함수
    
    Args:
        idea_text (str): 사용자가 입력한 아이디어 텍스트
        session: 현재 세션 객체
        session_id (str): 세션 ID
        
    Returns:
        dict: 각 페르소나별 분석 결과와 최종 요약
    """
    # 오케스트레이터 생성
    orchestrator = AIdeaLabOrchestrator()
    
    # 세션 상태에 아이디어 저장 (run_all_personas_sequentially 내부에서도 처리하지만, 여기서도 명시적으로 수행 가능)
    current_session = session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)
    if not current_session: # 세션이 없을 경우 (create_session 직후)
         current_session = session
    current_session.state["initial_idea"] = idea_text

    # 결과 저장 딕셔너리
    results = {}
    
    # 1. 페르소나 순차 분석 실행 (수정된 부분)
    await orchestrator.run_all_personas_sequentially( # await 추가
        session_service=session_service,
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
        idea_text=idea_text
    )
            
    # 세션에서 각 페르소나의 결과 가져오기
    updated_session = session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id
    )
    
    output_keys = orchestrator.get_output_keys()
    if updated_session and hasattr(updated_session, 'state'):
        for persona_key_name, state_key in output_keys.items():
            if persona_key_name != "summary" and state_key in updated_session.state:
                results[persona_key_name] = updated_session.state[state_key]

    # 2. 최종 요약 생성
    summary_runner = Runner(
        agent=orchestrator.get_summary_agent(),
        app_name=APP_NAME,
        session_service=session_service # 동일 세션 사용
    )
    
    summary_content_parts = [types.Part(text=f"아이디어 '''{idea_text}'''와 이전 분석 내용들을 바탕으로 최종 요약을 생성해주세요.")]
    
    summary_content = types.Content(
        role="user", 
        parts=summary_content_parts
    )

    summary_events = summary_runner.run(
        user_id=USER_ID,
        session_id=session_id, # 동일 세션 ID 사용
        new_message=summary_content
    )

    for event in summary_events:
        if event.is_final_response():
            break

    # 세션에서 최종 요약 결과 가져오기
    final_session = session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id
    )

    summary_key = output_keys["summary"]
    if final_session and hasattr(final_session, 'state') and summary_key in final_session.state:
        results["summary"] = final_session.state[summary_key]
    else: # 요약 생성 실패 또는 키 부재 시 명시적 None 또는 빈 문자열 처리
        results["summary"] = None
            
    return results

def main():
    """메인 애플리케이션 함수"""
    st.title("🧠 AIdea Lab - 아이디어 분석 워크숍")
    
    if 'session_counter' not in st.session_state:
        st.session_state.session_counter = 0
    
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = {}
    
    # 선택된 모델 세션 상태 초기화
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = DEFAULT_MODEL.value
    
    # 모델 선택 드롭다운 옵션 가져오기
    model_options = get_model_display_options()
    
    st.markdown("""
    ### 💡 아이디어 분석 서비스
    자유롭게 아이디어를 입력하시면, 다양한 AI 페르소나가 여러 관점에서 분석해드리고 최종 정리까지 해드립니다.
    """)
    
    # 설정 섹션 (접을 수 있는 expander 사용)
    with st.expander("⚙️ 고급 설정"):
        # 모델 선택 드롭다운
        st.selectbox(
            "AI 모델 선택:",
            options=list(model_options.keys()),
            format_func=lambda x: x,  # 표시 이름 그대로 보여줌
            index=list(model_options.values()).index(st.session_state.selected_model),
            key="model_display_name",
            on_change=lambda: setattr(st.session_state, 'selected_model', model_options[st.session_state.model_display_name])
        )
        
        # 선택된 모델 표시
        current_model_type = next((model_type for model_type in ModelType if model_type.value == st.session_state.selected_model), None)
        if current_model_type:
            st.info(f"선택된 모델: {MODEL_CONFIGS[current_model_type]['description']}")
        
        # 모델 적용 버튼
        if st.button("모델 변경 적용"):
            update_selected_model()
    
    idea_text = st.text_area(
        "아이디어를 입력해주세요:",
        height=150,
        placeholder="예: 수면 중 꿈을 기록하고 분석해주는 웨어러블 기기"
    )
    
    if st.button("아이디어 분석 요청"):
        if not idea_text:
            st.error("아이디어를 입력해주세요!")
        else:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key or api_key == "YOUR_API_KEY":
                st.error("GOOGLE_API_KEY가 .env 파일에 설정되지 않았거나 유효하지 않습니다. 확인해주세요.")
            else:
                # 분석 요청 전 선택된 모델 적용
                update_selected_model()
                
                # create_session() 호출 시 반환되는 session 객체를 사용
                current_session, session_id = create_session() 
                st.session_state.session_counter += 1
                
                with st.spinner("AI 페르소나들이 아이디어를 분석하고 최종 요약 중입니다..."):
                    try:
                        # analyze_idea를 await으로 호출
                        analysis_results = asyncio.run(analyze_idea(idea_text, current_session, session_id))
                        st.session_state.analysis_results = analysis_results
                    except Exception as e:
                        st.error(f"분석 중 오류가 발생했습니다: {str(e)}")
                        st.exception(e) # 개발 중 상세 오류 확인용
    
    if st.session_state.analysis_results:
        st.markdown("### 🚀 AI 페르소나 분석 결과")
        
        tab_titles = [
            f"{PERSONA_CONFIGS[PersonaType.MARKETER]['icon']} {PERSONA_CONFIGS[PersonaType.MARKETER]['name']}",
            f"{PERSONA_CONFIGS[PersonaType.CRITIC]['icon']} {PERSONA_CONFIGS[PersonaType.CRITIC]['name']}",
            f"{PERSONA_CONFIGS[PersonaType.ENGINEER]['icon']} {PERSONA_CONFIGS[PersonaType.ENGINEER]['name']}",
            f"{ORCHESTRATOR_CONFIG['icon']} 최종 요약" 
        ]
        tabs = st.tabs(tab_titles)
        
        persona_keys_map = {
            PersonaType.MARKETER: "marketer",
            PersonaType.CRITIC: "critic",
            PersonaType.ENGINEER: "engineer",
        }

        for i, persona_type_enum_member in enumerate(persona_keys_map.keys()):
            with tabs[i]:
                config = PERSONA_CONFIGS[persona_type_enum_member]
                result_key = persona_keys_map[persona_type_enum_member]
                st.subheader(f"{config['icon']} {config['name']}")
                st.write(f"**역할**: {config['role']}")
                # 결과가 None일 경우도 고려
                if result_key in st.session_state.analysis_results and st.session_state.analysis_results[result_key] is not None:
                    st.markdown(st.session_state.analysis_results[result_key])
                else:
                    st.info(f"{config['name']}의 분석 결과가 아직 없거나 생성 중 오류가 발생했습니다.")
        
        # 최종 요약 탭
        with tabs[3]:
            st.subheader(f"{ORCHESTRATOR_CONFIG['icon']} 최종 아이디어 검증 보고서")
            # 결과가 None일 경우도 고려
            if "summary" in st.session_state.analysis_results and st.session_state.analysis_results["summary"] is not None:
                st.markdown(st.session_state.analysis_results["summary"])
            else:
                all_personas_analyzed = all(
                    key in st.session_state.analysis_results and st.session_state.analysis_results[key] is not None
                    for key in persona_keys_map.values()
                )
                if all_personas_analyzed: # 모든 페르소나 분석은 완료되었으나 요약만 없는 경우
                    st.warning("최종 요약 생성에 실패했거나, 요약 결과가 없습니다.")
                else: # 페르소나 분석 중 일부가 완료되지 않았거나 오류가 있는 경우
                    st.info("모든 페르소나 분석이 완료된 후 최종 요약이 제공됩니다. 일부 페르소나 분석 결과가 누락되었을 수 있습니다.")

if __name__ == "__main__":
    main() 