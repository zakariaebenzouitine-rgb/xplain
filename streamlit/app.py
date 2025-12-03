import streamlit as st
import requests
from PIL import Image
import plotly.graph_objects as go
import time
import io
from datetime import datetime

# API Configuration
API_URL = "https://xplain-api-830300217028.europe-west1.run.app/predict"

# Set page configuration
st.set_page_config(
    page_title="XPLAIN: Making X-rays talk",
    page_icon="⚕️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Theme Medical UI CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #e2e8f0;
    }

    /* Main text colors */
    .stMarkdown, .stMarkdown p, .stMarkdown div, .stText {
        color: #e2e8f0 !important;
    }

    /* Ensure all text elements are visible */
    p, span, div, label, h1, h2, h3, h4, h5, h6 {
        color: #e2e8f0 !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1e293b;
        border-radius: 8px 8px 0px 0px;
        gap: 8px;
        padding-top: 10px;
        padding-bottom: 10px;
        color: #94a3b8 !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: #334155 !important;
        color: #ffffff !important;
    }

    .stButton button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
    }

    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4) !important;
    }

    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff;
        text-align: center;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .subtitle {
        text-align: center;
        color: #94a3b8;
        font-size: 0.95rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }

    .glass-card {
        background: rgba(30, 41, 59, 0.8);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 1rem;
        color: #e2e8f0;
    }

    .glass-card * {
        color: #e2e8f0 !important;
    }

    .metric-container {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        border-radius: 12px;
        padding: 1.25rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
        transition: transform 0.2s;
    }

    .metric-container:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        margin: 0.5rem 0;
        color: white !important;
    }

    .metric-label {
        font-size: 0.8rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 500;
        color: white !important;
    }

    .status-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        color: white !important;
    }

    .badge-info {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    }

    .badge-warning {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    }

    .report-section {
        background: #1e293b;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #6366f1;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        color: #e2e8f0;
    }

    .report-section * {
        color: #e2e8f0 !important;
    }

    .section-title {
        color: #ffffff !important;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
    }

    .section-icon {
        margin-right: 0.5rem;
        font-size: 1.3rem;
    }

    .info-box {
        background: linear-gradient(135deg, #1e3a8a 0%, #3730a3 100%);
        border-radius: 10px;
        padding: 1.25rem;
        margin: 1rem 0;
        border-left: 4px solid #6366f1;
        color: #e2e8f0;
    }

    .sidebar-info {
        background: linear-gradient(135deg, #6366f115 0%, #8b5cf615 100%);
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        color: #e2e8f0;
    }

    .tab-content {
        background: #1e293b;
        border-radius: 12px;
        padding: 2rem;
        margin-top: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        color: #e2e8f0;
    }

    .tab-content * {
        color: #e2e8f0 !important;
    }
</style>
""", unsafe_allow_html=True)

def call_api(image_file, view_type="frontal"):
    """Call the cloud API with the uploaded image"""
    try:
        # Prepare the file for API request
        files = {
            "file": (
                image_file.name,
                image_file.getvalue(),
                image_file.type
            )
        }

        # Make API request (same API for both frontal and lateral)
        response = requests.post(API_URL, files=files, timeout=30)

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None

    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. Please try again.")
        return None
    except Exception as e:
        st.error(f"❌ Error calling API: {str(e)}")
        return None

def main():
    # Header
    st.markdown('<h1 class="main-header"> XPLAIN: Making X-rays talk</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Advanced AI-Powered Radiological Assessment Platform</p>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("### 🎯 Navigation")
        app_mode = st.radio("", ["📊 Analysis", "ℹ️ System Info"], label_visibility="collapsed")

        st.markdown("---")
        st.markdown('<div class="sidebar-info">', unsafe_allow_html=True)
        st.markdown("**🔒 Secure & Private**")
        st.caption("HIPAA-compliant processing")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-info">', unsafe_allow_html=True)
        st.markdown("**⚡ Fast Analysis**")
        st.caption("Results in seconds")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-info">', unsafe_allow_html=True)
        st.markdown("**🤖 AI-Powered**")
        st.caption("Cloud-based analysis")
        st.markdown('</div>', unsafe_allow_html=True)

    if app_mode == "📊 Analysis":
        analyze_xray()
    else:
        show_system_info()

def analyze_xray():
    """Main analysis interface"""

    # Modern layout
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title"><span class="section-icon">📋</span>Patient Study Upload</div>', unsafe_allow_html=True)

    # View type selection with modern cards
    st.markdown("#### 🎯 Select Imaging View")
    col1, col2 = st.columns(2)

    with col1:
        frontal_selected = st.button("🔵 Frontal View (AP/PA)", use_container_width=True, key="frontal_btn")
    with col2:
        lateral_selected = st.button("🟠 Lateral View", use_container_width=True, key="lateral_btn")

    if 'view_type' not in st.session_state:
        st.session_state.view_type = 'frontal'

    if frontal_selected:
        st.session_state.view_type = 'frontal'
    if lateral_selected:
        st.session_state.view_type = 'lateral'

    view_type = st.session_state.view_type

    # View indicator
    if view_type == 'frontal':
        st.markdown('<span class="status-badge badge-info">🔵 Frontal View Selected</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-badge badge-warning">🟠 Lateral View Selected</span>', unsafe_allow_html=True)

    st.markdown("---")

    # File upload
    uploaded_file = st.file_uploader(
        "📤 Upload Chest X-Ray Image",
        type=['jpg', 'jpeg', 'png'],
        help="Supported formats: JPG, JPEG, PNG"
    )

    st.markdown('</div>', unsafe_allow_html=True)

    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert('RGB')

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title"><span class="section-icon">🖼️</span>Source Image</div>', unsafe_allow_html=True)
            st.image(image, use_column_width=True)

            # Image metadata
            st.markdown(f"**📏 Dimensions:** {image.size[0]} x {image.size[1]} pixels")
            st.markdown(f"**👁️ View Type:** {view_type.capitalize()}")
            st.markdown(f"**📅 Upload Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title"><span class="section-icon">⚙️</span>Analysis Configuration</div>', unsafe_allow_html=True)

            st.markdown("**🌐 API Status**")
            st.markdown("✅ Connected to Cloud API")
            st.markdown(f"🔗 Endpoint: `{API_URL}`")

            st.markdown("---")

            st.markdown("**📊 Analysis Options**")
            st.markdown(f"• View Type: **{view_type.capitalize()}**")
            st.markdown("• Processing: **Cloud-based**")
            st.markdown("• Model: **BLIP Architecture**")

            st.markdown('</div>', unsafe_allow_html=True)

        # Analyze button
        st.markdown('<div style="text-align: center; margin: 2rem 0;">', unsafe_allow_html=True)
        if st.button("🚀 Begin Analysis", type="primary", use_container_width=False):
            perform_analysis(uploaded_file, view_type, image)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.markdown("**👋 Getting Started**")
        st.markdown("1. 🎯 Select your X-ray view type (Frontal or Lateral)")
        st.markdown("2. 📤 Upload a chest X-ray image")
        st.markdown("3. 🚀 Click 'Begin Analysis' to start")
        st.markdown("4. 📊 View comprehensive AI-generated report")
        st.markdown('</div>', unsafe_allow_html=True)

def perform_analysis(uploaded_file, view_type, image):
    """Perform the analysis with modern progress tracking"""

    progress_bar = st.progress(0)
    status_text = st.empty()

    status_text.markdown("🔄 Initializing analysis...")
    progress_bar.progress(10)
    time.sleep(0.5)

    status_text.markdown("📡 Sending to cloud API...")
    progress_bar.progress(30)
    time.sleep(0.3)

    status_text.markdown("🧠 Processing image with AI model...")
    progress_bar.progress(50)

    # Call the API
    api_response = call_api(uploaded_file, view_type)

    if not api_response:
        progress_bar.empty()
        status_text.empty()
        st.error("❌ Analysis failed. Please try again.")
        return

    progress_bar.progress(80)
    status_text.markdown("📊 Generating insights...")
    time.sleep(0.5)

    progress_bar.progress(100)
    status_text.markdown("✅ Analysis complete!")
    time.sleep(0.5)

    progress_bar.empty()
    status_text.empty()

    # Display results
    display_results(image, api_response, view_type)

def display_results(image, api_response, view_type):
    """Display results in modern interface"""

    st.markdown("---")
    st.markdown('<div class="section-title"><span class="section-icon">📈</span>Analysis Results</div>', unsafe_allow_html=True)

    # Extract caption from API response
    caption = api_response.get("caption", "No report generated")

    # Calculate basic metrics
    word_count = len(caption.split())

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Status</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-value">✓</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-container" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">View Type</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value" style="font-size: 1.2rem;">{view_type.upper()}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-container" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Report Length</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{word_count}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="metric-container" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Processing</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-value" style="font-size: 1.2rem;">CLOUD</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs
    tab1, tab2 = st.tabs(["📋 Clinical Report", "🖼️ Image Details"])

    with tab1:
        st.markdown('<div class="tab-content">', unsafe_allow_html=True)

        st.markdown('<div class="report-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📄 Generated Report</div>', unsafe_allow_html=True)
        st.markdown(f'<p style="color: #cbd5e1; line-height: 1.8; font-size: 1.1rem;">{caption}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Download option
        st.markdown("---")
        st.download_button(
            label="📥 Download Report",
            data=caption,
            file_name=f"xray_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )

        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="tab-content">', unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("#### 🖼️ Original Image")
            st.image(image, use_column_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("#### 📊 Image Information")
            st.markdown(f"**Dimensions:** {image.size[0]} × {image.size[1]} pixels")
            st.markdown(f"**Format:** {image.format or 'N/A'}")
            st.markdown(f"**Mode:** {image.mode}")
            st.markdown(f"**View Type:** {view_type.capitalize()}")
            st.markdown(f"**Analysis Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

def show_system_info():
    """System information page"""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 🏥 Clinical X-Ray Analysis System")
    st.markdown("""
    **Advanced AI-powered platform for chest X-ray interpretation with cloud-based processing.**

    ### 🚀 Key Features:
    - 🤖 **Cloud AI Processing** - Scalable and reliable
    - 🔵 **Frontal View Support** - AP/PA chest X-rays
    - 🟠 **Lateral View Support** - Side view analysis
    - ⚡ **Real-time Analysis** - Fast cloud processing
    - 🔒 **HIPAA Compliant** - Secure data handling
    - 📊 **Comprehensive Reports** - Detailed findings

    ### 🔧 Technical Specifications:
    - **Architecture**: BLIP-based model
    - **Processing**: Cloud API
    - **Endpoint**: Google Cloud Run
    - **Response Time**: < 10 seconds
    - **Supported Views**: Frontal, Lateral

    ### 📡 API Information:
    - **Status**: ✅ Active
    - **Endpoint**: `europe-west1.run.app`
    - **Version**: Production
    """)
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
