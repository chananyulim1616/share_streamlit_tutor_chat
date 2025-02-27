import streamlit as st
import subprocess
import os
from pathlib import Path
from dotenv import load_dotenv
import requests
import time
import streamlit.components.v1 as components

# Configuration
load_dotenv()
MAX_VIDEO_SIZE_GB = 5
CACHE_DIR = Path(r"cache")
os.makedirs(CACHE_DIR, exist_ok=True)

API_ENDPOINT = os.getenv("CHAT_API_ENDPOINT", "http://localhost:8000/chat")

# Subject configuration
subjects = {
    "วิทยาศาสตร์": {
        "clips": ["อากาศ"],
        "icon": "🔬"
    },
    "สุขศึกษา": {
        "clips": ["การทํางานของระบบประสาทระบบสืบพันธุ์และระบบต่อมไร้ท่อ"],
        "icon": "🏥"
    },
    "ภาษาไทย": {
        "clips": ["ธรรมชาติของภาษา พลังของภาษา และลักษณะของภาษา"],
        "icon": "📚"
    },
    "ภาษาอังกฤษ": {
        "clips": ["หลักการออกเสียง ตอนที่ 1","หลักการออกเสียง ตอนที่ 2"],
        "icon": "🌐"
    },
    # "สังคม": {
    #     "clips": ["ความสัมพันธ์ทางเศรษฐกิจ"],
    #     "icon": "🌍"
    # }
}

lesson_topics = {
    'อากาศ': 'อากาศ',
    'การทํางานของระบบประสาทระบบสืบพันธุ์และระบบต่อมไร้ท่อ': 'การทํางานของระบบประสาทระบบสืบพันธุ์และระบบต่อมไร้ท่อ',
    'ธรรมชาติของภาษา พลังของภาษา และลักษณะของภาษา': 'ธรรมชาติของภาษา พลังของภาษา และลักษณะของภาษา',
    'หลักการออกเสียง ตอนที่ 1': 'หลักการออกเสียง',
    'หลักการออกเสียง ตอนที่ 2': 'หลักการออกเสียง',
    # 'ความสัมพันธ์ทางเศรษฐกิจ': 'ความสัมพันธ์ทางเศรษฐกิจ',
}

subject_map = {
        "วิทยาศาสตร์": "science",
        "สุขศึกษา": "health",
        "ภาษาไทย": "thai",
        "ภาษาอังกฤษ": "english",
        # "สังคม": "social"
    }
# Session state initialization
if "video_ready" not in st.session_state:
    st.session_state.video_ready = False
    st.session_state.optimized_path = ""
    st.session_state.prev_subject = None
    st.session_state.prev_lesson = None

def optimize_video_path(lesson : str) -> Path:
    """Create streaming-optimized version of video"""
    output_path = CACHE_DIR / f"opt_{lesson}.mp4"
    return output_path
# UI Layout
st.set_page_config(
    page_title="Auto-Load Video Tutor",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

if 'current_timestamp' not in st.session_state:
    st.session_state.current_timestamp = 0.0  # Initialize as float

# Sidebar Controls
with st.sidebar:
    st.header("Video Controls")
    
    # Subject selection with icons (non-editable)
    current_subject = st.selectbox(
        "Select Subject",
        options=list(subjects.keys()),
        format_func=lambda x: f"{subjects[x]['icon']} {x}",
        index=0
    )
    # Get lessons for current subject
    current_lessons = subjects[current_subject]["clips"]
    # Lesson selection (non-editable, default to first lesson)
    current_lesson = st.selectbox(
        "Select Lesson",
        options=current_lessons,
        index=0
    )

# Auto-detect selection changes
selection_changed = (
    current_subject != st.session_state.prev_subject or
    current_lesson != st.session_state.prev_lesson
)

if selection_changed:
    try:
        st.session_state.optimized_path = optimize_video_path(current_lesson)
        st.session_state.video_ready = True
        st.session_state.prev_subject = current_subject
        st.session_state.prev_lesson = current_lesson
        st.session_state.messages = []
    except Exception as e:
        st.error(f"Loading failed: {str(e)}")
        st.session_state.video_ready = False

# Main Content
col1, col2 = st.columns([3, 2])

with col1:
    st.header("Video Player")
    if st.session_state.video_ready:
        try:
            video_path = Path(st.session_state.optimized_path)
            # Display video normally
            st.video(str(video_path.resolve()), format="video/mp4")
        except Exception as e:
            st.error(f"Streaming error: {str(e)}")
    else:
        st.info("Please select a subject and lesson")
    
with col2:
    st.header("AI Tutor Chat")
    
    # Initialize chat history if not exists
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Chat container with fixed height
    chat_container = st.container(height=500)
    with chat_container:
        # Display messages in natural order (newest at bottom)
        for msg in st.session_state.messages:
            avatar = "👤" if msg["role"] == "user" else "🤖"
            if type(msg["parts"][0]) == str:
                with st.chat_message(msg["role"], avatar=avatar):
                    st.write(msg["parts"][0])

    # Chat input (outside container, fixed at bottom)
    if prompt := st.chat_input("Ask about the video..."):
        # Add user message immediately
        with chat_container:
            with st.chat_message("user", avatar="👤"):
                st.write(prompt)
        
        try:

            # API call
            with st.spinner('Analyzing...'):
                response = requests.post(
                    'http://localhost:8000/chat',
                    json={
                        'user_input': prompt,
                        'history': st.session_state.messages,
                        'subject': subject_map[current_subject],
                        'section': lesson_topics[current_lesson]
                    },
                )
                response.raise_for_status()
                response_data = response.json()
                
                # Add and display assistant response
                assistant_response = response_data.get('response', "No response received")
                with chat_container:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write(assistant_response)
                
                st.session_state.messages = response_data.get('history', [])
        
        except requests.exceptions.RequestException as e:
            st.error(f"API Error: {str(e)}")
            # Remove failed user message
            st.session_state.messages.pop()
            chat_container.empty()
            for msg in st.session_state.messages:
                with chat_container:
                    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
                        st.write(msg["parts"])
# Footer
st.markdown("---")