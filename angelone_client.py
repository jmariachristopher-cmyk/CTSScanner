from SmartApi import SmartConnect
import streamlit as st
class AngelOneClient:
    @classmethod
    def from_streamlit_secrets(cls):
        if not all(k in st.secrets for k in ["ANGEL_API_KEY","ANGEL_CLIENT_ID","ANGEL_PIN","ANGEL_TOTP_SECRET"]):
            raise RuntimeError("Missing Streamlit Secrets: ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_PIN, ANGEL_TOTP_SECRET")
        raise RuntimeError("Use the angelone_client.py from your working V2 project.")
