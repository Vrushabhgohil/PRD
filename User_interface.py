import streamlit as st
import requests

st.set_page_config(page_title="Project Requirements Generator", layout="centered")

st.title("📄 Project Requirements Assistant")
st.write("Ask your assistant to help you gather and define your project requirements.")

# User input
user_input = st.text_area("Enter your project requirement or idea:", height=200)

if st.button("Generate Requirements"):
    if not user_input.strip():
        st.warning("Please enter some text.")
    else:
        with st.spinner("Generating response..."):
            try:
                # API endpoint
                API_URL = "http://127.0.0.1:8000/project_requirements/"
                payload = {
                    "requirements": user_input
                }

                response = requests.post(API_URL, json=payload)
                response.raise_for_status()

                data = response.json()
                st.success("Response received!")
                st.subheader("🧠 AI Response:")
                st.markdown(data["response"])
                st.caption(f"Session ID: {data['session_id']}")

            except requests.exceptions.RequestException as e:
                st.error(f"API request failed: {e}")
