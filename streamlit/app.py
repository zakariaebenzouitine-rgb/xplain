import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/predict"

st.title("🩻 Xplain — X-ray Captioning")
st.write("Upload an X-ray image to generate a clinical-style caption.")

uploaded_file = st.file_uploader("Upload X-ray", type=["png", "jpg", "jpeg"])

if uploaded_file:
    st.image(uploaded_file, caption="Uploaded image", use_column_width=True)

if st.button("Generate Caption"):
    if not uploaded_file:
        st.error("Please upload an image first.")
    else:
        with st.spinner("Generating caption..."):
            files = {
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),   # <-- IMPORTANT
                    uploaded_file.type
                )
            }

            response = requests.post(API_URL, files=files)

            if response.status_code == 200:
                st.success("Caption generated:")
                st.write(response.json()["caption"])
            else:
                st.error(f"Error: {response.text}")
