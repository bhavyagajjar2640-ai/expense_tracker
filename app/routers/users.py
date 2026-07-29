import streamlit as st

from app.services.user_service import authenticate_user, register_user
from streamlit_cookies_controller import CookieController

controller = CookieController()

def render_login_signup():
    st.title("🔐 Login / Signup")
    option = st.selectbox("Select action", ["Login", "Signup"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if option == "Signup" and st.button("Create Account"):
        if not username or not password:
            st.error("Please enter a username and password.")
            return
        try:
            register_user(username, password)
            st.success("Account created. Please log in.")
        except ValueError as exc:
            st.error(str(exc))

    if option == "Login" and st.button("Login"):
        user = authenticate_user(username, password)
        if user:
            st.session_state.user = user["username"]
            st.session_state.user_id = user["id"]
            controller.set("user", user["username"])
            controller.set("user_id", user["id"])
            st.success("Login successful.")
            st.rerun()
        else:
            st.error("Invalid credentials.")


def render_account_sidebar(username):
    with st.sidebar:
        st.header("Account")
        st.write(f"User: {username}")
        if st.button("Logout"):
            controller.remove("user")
            controller.remove("user_id")
            if "user" in st.session_state:
                del st.session_state.user
            if "user_id" in st.session_state:
                del st.session_state.user_id
            st.rerun()
