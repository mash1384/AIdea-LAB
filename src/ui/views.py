"""
AIdea Lab UI Views Module

이 모듈은 다양한 UI 상태별 렌더링 로직을 담당합니다.
각 뷰 함수는 특정 분석 단계에 맞는 UI 요소들을 렌더링합니다.
"""

import streamlit as st
from src.ui.state_manager import AppStateManager, SYSTEM_MESSAGES


def render_idle_view():
    """
    아이디어 입력 대기 상태의 UI를 렌더링합니다.
    """
    # 추가 정보 입력 버튼
    additional_info_button_label = "아이디어 상세 정보 숨기기" if AppStateManager.get_show_additional_info() else "아이디어 상세 정보 입력 (선택)"
    st.button(
        additional_info_button_label, 
        key="toggle_additional_info_button", 
        on_click=AppStateManager.toggle_additional_info
    )

    if AppStateManager.get_show_additional_info():
        with st.expander("아이디어 상세 정보", expanded=AppStateManager.get_expander_state()):
            st.text_area("아이디어의 핵심 목표 또는 해결하고자 하는 문제:", key="user_goal_input", value=AppStateManager.get_user_goal())
            st.text_area("주요 제약 조건 (예: 예산, 시간, 기술 등):", key="user_constraints_input", value=AppStateManager.get_user_constraints())
            st.text_area("중요하게 생각하는 가치 (예: 효율성, 창의성 등):", key="user_values_input", value=AppStateManager.get_user_values())
            st.button(
                "상세 정보 저장", 
                key="save_additional_info", 
                on_click=AppStateManager.save_additional_info
            )
    
    # 아이디어 입력 필드
    st.chat_input(
        "여기에 아이디어를 입력하고 Enter를 누르세요...",
        key="idea_input",
        on_submit=lambda: AppStateManager.submit_idea(AppStateManager.get_input_value("idea_input"))
    )


def render_phase1_pending_view():
    """
    1단계 분석 시작 대기 상태의 UI를 렌더링합니다.
    """
    if AppStateManager.get_current_idea() and AppStateManager.get_current_idea() != AppStateManager.get_analyzed_idea():
        with st.spinner("AI 페르소나가 아이디어를 분석 중입니다... 이 작업은 최대 1-2분 소요될 수 있습니다."):
            # 상세 정보 저장 (만약 expanded 된 상태에서 아이디어만 바로 입력했을 경우 대비)
            if AppStateManager.get_show_additional_info():
                AppStateManager.set_user_goal(AppStateManager.get_input_value("user_goal_input", AppStateManager.get_user_goal()))
                AppStateManager.set_user_constraints(AppStateManager.get_input_value("user_constraints_input", AppStateManager.get_user_constraints()))
                AppStateManager.set_user_values(AppStateManager.get_input_value("user_values_input", AppStateManager.get_user_values()))
            
            # 분석 실행 (app.py에서 정의된 함수를 호출)
            # 이 부분은 app.py에서 호출되어야 하므로 여기서는 플래그만 설정
            return "execute_analysis"
    else:
        AppStateManager.change_analysis_phase("idle")
        st.rerun()


def render_phase1_complete_view():
    """
    1단계 분석 완료 상태의 UI를 렌더링합니다.
    """
    st.success("✔️ 1단계 아이디어 분석이 완료되었습니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.button(
            "💬 2단계 토론 시작하기", 
            key="start_phase2_button", 
            use_container_width=True,
            on_click=AppStateManager.start_phase2_discussion
        )
    
    with col2:
        st.button(
            "✨ 새 아이디어 분석", 
            key="new_idea_after_phase1_button", 
            use_container_width=True,
            on_click=lambda: AppStateManager.restart_session(keep_messages=False)
        )


def render_phase1_error_view():
    """
    1단계 분석 오류 상태의 UI를 렌더링합니다.
    """
    col_retry, col_restart_new = st.columns(2)
    with col_retry:
        st.button(
            "같은 아이디어로 재시도", 
            key="retry_button_error", 
            use_container_width=True,
            on_click=AppStateManager.retry_analysis
        )
    with col_restart_new:
        st.button(
            "새 아이디어로 시작", 
            key="restart_button_error", 
            use_container_width=True,
            on_click=lambda: AppStateManager.restart_session(keep_messages=False)
        )


def render_phase2_pending_view():
    """
    2단계 토론 시작 대기 상태의 UI를 렌더링합니다.
    """
    with st.spinner("2단계 토론을 준비 중입니다..."):
        # 토론 실행 플래그 반환
        return "execute_phase2"


def render_phase2_running_view():
    """
    2단계 토론 진행 중 상태의 UI를 렌더링합니다.
    """
    st.info("AI 페르소나들이 토론 중입니다...")
    # 토론 실행 플래그 반환
    return "execute_phase2"


def render_phase2_user_input_view():
    """
    2단계 사용자 입력 대기 상태의 UI를 렌더링합니다.
    """
    if AppStateManager.is_awaiting_user_input_phase2():
        # 사용자 질문을 더 명확하게 표시
        st.info("💬 **토론에 참여해 주세요**")
        with st.container(border=True):
            st.markdown(f"**질문:** {AppStateManager.get_phase2_user_prompt()}")
        
        # 사용자 입력 필드
        st.chat_input(
            "여기에 의견을 입력하고 Enter를 누르세요...",
            key="phase2_response_input",
            on_submit=lambda: AppStateManager.submit_phase2_response(AppStateManager.get_input_value("phase2_response_input"))
        )


def render_phase2_complete_view():
    """
    2단계 토론 완료 상태의 UI를 렌더링합니다.
    """
    st.success("✔️ 2단계 토론과 최종 요약이 완료되었습니다.")
    
    st.button(
        "✨ 새 아이디어 분석", 
        key="new_idea_after_phase2_button", 
        use_container_width=True,
        on_click=lambda: AppStateManager.restart_session(keep_messages=False)
    )


def render_phase2_error_view():
    """
    2단계 토론 오류 상태의 UI를 렌더링합니다.
    """
    col_retry, col_restart_new = st.columns(2)
    with col_retry:
        st.button(
            "같은 아이디어로 재시도", 
            key="retry_phase2_button_error", 
            use_container_width=True,
            on_click=AppStateManager.retry_phase2
        )
    with col_restart_new:
        st.button(
            "새 아이디어로 시작", 
            key="restart_phase2_button_error", 
            use_container_width=True,
            on_click=lambda: AppStateManager.restart_session(keep_messages=False)
        )


def render_chat_messages():
    """
    채팅 메시지들을 렌더링합니다.
    """
    if AppStateManager.get_messages():
        for idx, message in enumerate(AppStateManager.get_messages()):
            role = message.get("role", "")
            msg_content = message.get("content", "")
            avatar = message.get("avatar", None)
            
            try:
                if role == "user":
                    st.chat_message(role, avatar="🧑‍💻").write(msg_content)
                elif role == "assistant":
                    st.chat_message(role, avatar=avatar).write(msg_content)
                elif role == "system":
                    # 시스템 메시지를 chat_message로 표시
                    st.chat_message("assistant", avatar=avatar if avatar else "ℹ️").markdown(f"_{msg_content}_")
            except Exception as e:
                print(f"Error rendering message (idx: {idx}): Role={role}, Avatar={avatar}, Exc={e}")
                st.error(f"메시지 렌더링 중 오류 발생: {str(msg_content)[:30]}...")


def render_sidebar():
    """
    사이드바 UI를 렌더링합니다.
    API 키 설정, 모델 선택 및 성능 정보를 표시합니다.
    """
    from config.models import get_model_display_options, MODEL_CONFIGS, ModelType
    from src.utils.model_monitor import AIModelMonitor
    
    # 모델 모니터링 인스턴스 (app.py에서 전달받을 수도 있지만, 여기서 직접 생성)
    model_monitor = AIModelMonitor(log_file_path="logs/model_performance.json")
    
    # 모델 성능 정보 가져오기
    model_recommendations = model_monitor.get_model_recommendations()
    best_model_info = model_monitor.get_best_model()
    
    with st.sidebar:
        st.title("⚙️ 설정")
        
        # === 미니멀하고 우아한 API 키 설정 섹션 ===
        st.markdown("### 🔐 API 연결")
        
        # API 키 상태에 따른 스타일링
        is_configured = AppStateManager.get_api_key_configured()
        current_key = AppStateManager.get_user_api_key()
        
        # 상태 인디케이터가 포함된 컨테이너
        status_color = "#00C851" if is_configured else "#ff4444"
        status_icon = "🟢" if is_configured else "🔴"
        status_text = "연결됨" if is_configured else "미연결"
        
        # 상태 표시 (우아한 스타일)
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, {'#e8f5e8' if is_configured else '#ffeaea'}, {'#f0f9f0' if is_configured else '#fff0f0'});
                padding: 12px 16px;
                border-radius: 12px;
                border-left: 4px solid {status_color};
                margin-bottom: 16px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            ">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <span style="font-size: 14px; font-weight: 500; color: #2c3e50;">
                        {status_icon} API 상태: <span style="color: {status_color};">{status_text}</span>
                    </span>
                    {'<span style="font-size: 12px; color: #7f8c8d; font-family: monospace;">●●●●' + current_key[-4:] + '</span>' if is_configured and current_key else ''}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # API 키 입력 영역 (접기/펼치기 가능)
        with st.expander("🔑 API 키 설정" if not is_configured else "🔑 API 키 변경", expanded=not is_configured):
            api_key_input = st.text_input(
                "",
                value="",
                type="password",
                key="api_key_input",
                placeholder="Google API 키를 입력하세요 (AIzaSy...)",
                label_visibility="collapsed"
            )
            
            # 미니멀한 적용 버튼
            col1, col2 = st.columns([4, 1])
            with col1:
                apply_key_button = st.button(
                    "✨ 적용",
                    key="apply_api_key_button",
                    use_container_width=True,
                    type="primary" if api_key_input else "secondary"
                )
            with col2:
                # 간단한 도움말 버튼
                help_button = st.button(
                    "❓", 
                    key="help_api_key_button",
                    help="Google AI Studio에서 API 키를 발급받을 수 있습니다."
                )
        
        # API 키 적용 로직
        if apply_key_button:
            if api_key_input:
                with st.spinner("🔍 API 키 확인 중..."):
                    success = AppStateManager.set_user_api_key(api_key_input)
                if success:
                    st.rerun()
            else:
                AppStateManager.set_state('api_key_status_message', "⚠️ API 키를 입력해주세요.")
        
        # 상태 메시지 표시 (더 우아한 스타일)
        status_message = AppStateManager.get_api_key_status_message()
        if status_message:
            if "✅" in status_message:
                st.success(status_message)
            elif "⚠️" in status_message:
                st.warning(status_message.replace("⚠️ ", ""))
            else:
                st.error(status_message.replace("❌ ", ""))
        
        # 섹션 구분선
        st.markdown("<br>", unsafe_allow_html=True)
        
        # === 모델 선택 섹션 ===
        st.markdown("### 🤖 AI 모델")
        
        # 모델 선택 UI
        model_options = get_model_display_options()
        selected_display_name = st.selectbox(
            "AI 모델 선택",
            options=list(model_options.keys()),
            index=list(model_options.values()).index(AppStateManager.get_selected_model()) if AppStateManager.get_selected_model() in model_options.values() else 0,
            key="model_selector",
            on_change=lambda: AppStateManager.change_model(model_options[AppStateManager.get_input_value("model_selector")]),
            label_visibility="collapsed"
        )
        
        # 선택된 모델의 내부 ID
        selected_model_id = model_options[selected_display_name]
        
        # 모델 성능 정보 표시 (미니멀한 스타일)
        if selected_model_id in model_recommendations:
            recommendation = model_recommendations[selected_model_id]
            
            # 성능 정보를 우아한 카드 스타일로 표시
            if recommendation["total_calls"] > 0:
                success_rate = recommendation["success_rate"]
                avg_time = recommendation["avg_response_time"]
                
                # 성과 지표 색상
                perf_color = "#00C851" if success_rate > 0.9 else "#ffbb33" if success_rate > 0.7 else "#ff4444"
                
                st.markdown(
                    f"""
                    <div style="
                        background: #f8f9fa;
                        padding: 10px;
                        border-radius: 8px;
                        border: 1px solid #e9ecef;
                        margin: 8px 0;
                    ">
                        <div style="font-size: 12px; color: #6c757d; margin-bottom: 4px;">모델 성능</div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 13px;">성공률</span>
                            <span style="color: {perf_color}; font-weight: 600;">{success_rate:.1%}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 2px;">
                            <span style="font-size: 13px;">응답시간</span>
                            <span style="color: #495057; font-weight: 500;">{avg_time:.1f}초</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        
        # 최고 추천 모델 표시 (더 미니멀하게)
        if best_model_info and best_model_info[0] != selected_model_id:
            best_model_name = MODEL_CONFIGS[ModelType(best_model_info[0])]["display_name"] if best_model_info[0] in [m.value for m in ModelType] else best_model_info[0]
            
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, #e3f2fd, #f8f9fa);
                    padding: 8px 12px;
                    border-radius: 8px;
                    border-left: 3px solid #2196f3;
                    margin: 8px 0;
                ">
                    <div style="font-size: 12px; color: #1976d2;">
                        💡 추천: {best_model_name}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


def render_app_header():
    """
    앱 헤더 (제목 및 소개)를 렌더링합니다.
    """
    st.title("AIdea Lab - 아이디어 분석 워크숍")
    st.markdown("당신의 아이디어를 AI가 다양한 관점에서 분석해드립니다!") 