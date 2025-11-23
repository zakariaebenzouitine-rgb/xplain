import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/predict"

# --------- PAGE CONFIG ---------
st.set_page_config(
    page_title="Xplain – X-ray Captioning",
    layout="wide",
)

# --------- CUSTOM CSS ---------
st.markdown("""
<style>
/* Smooth fade-in animation */
@keyframes fadein {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0px); }
}

.main-container {
  animation: fadein 0.7s ease-in-out;
}

/* Card container */
.card {
  background: #ffffff10;
  backdrop-filter: blur(8px);
  padding: 25px;
  border-radius: 18px;
  border: 1px solid rgba(255,255,255,0.15);
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}

/* Center button */
.generate-btn {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 90px;
}

</style>
""", unsafe_allow_html=True)

# --------- PAGE HEADER ---------
st.markdown(
    "<h1 style='text-align:center; margin-bottom:5px;'>Xplain — X-ray Captioning</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align:center; color:#888;'>Upload an X-ray and automatically generate a clinical-style caption.</p>",
    unsafe_allow_html=True
)

st.markdown("<div class='main-container'>", unsafe_allow_html=True)

# --------- 3 COLUMN LAYOUT ---------
left, center, right = st.columns([3, 1, 3])

# ---------- LEFT: UPLOAD ----------
with left:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📤 Upload X-ray Image")
    uploaded_file = st.file_uploader(" ", type=["png", "jpg", "jpeg"])

    if uploaded_file:
        st.image(uploaded_file, caption="Preview", use_column_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- CENTER: BUTTON ----------
with center:
    st.markdown("<div class='generate-btn'>", unsafe_allow_html=True)
    generate = st.button("⚡ Generate Report", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- RIGHT: OUTPUT ----------
with right:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📄 Generated Report")

    if generate:
        if not uploaded_file:
            st.error("Please upload an image first.")
        else:
            with st.spinner("Analyzing X-ray..."):
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type
                    )
                }

                response = requests.post(API_URL, files=files)

                if response.status_code == 200:
                    caption = response.json()["caption"]

                    st.success("Report Generated:")
                    st.write(caption)

                else:
                    st.error("Error generating report.")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
