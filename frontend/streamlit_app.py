import streamlit as st
import requests
import uuid
import os
import pandas as pd
from dotenv import load_dotenv
import plotly.graph_objects as go

# Load .env from the parent directory for API URL
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=dotenv_path)

API_URL = f"http://{os.getenv('FASTAPI_HOST', 'localhost')}:{os.getenv('FASTAPI_PORT', 8000)}"

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="iScore Calculator", page_icon="💳")


# --- Helper Function for API Calls ---
def make_api_request(method, endpoint, json_data=None, params=None):
    try:
        full_url = f"{API_URL}{endpoint}"
        if method.upper() == "GET":
            response = requests.get(full_url, params=params, timeout=10) # Added timeout
        elif method.upper() == "POST":
            response = requests.post(full_url, json=json_data, timeout=10) # Added timeout
        else:
            # This case should ideally not be reached if called correctly
            return {"success": False, "status_code": 0, "error": f"Unsupported HTTP method: {method}", "data": None}

        # Try to parse JSON, handle cases where it might not be JSON (e.g., server error pages)
        try:
            response_data = response.json()
        except requests.exceptions.JSONDecodeError:
            response_data = {"detail": response.text[:200]} # Truncate if not JSON

        if 200 <= response.status_code < 300:
            return {"success": True, "status_code": response.status_code, "data": response_data, "error": None}
        else:
            error_message = response_data.get("detail", "An unknown API error occurred.")
            return {"success": False, "status_code": response.status_code, "error": error_message, "data": response_data}

    except requests.exceptions.ConnectionError:
        return {"success": False, "status_code": 0, "error": f"Connection Error: Could not connect to API at {API_URL}. Ensure the backend server is running.", "data": None}
    except requests.exceptions.Timeout:
        return {"success": False, "status_code": 0, "error": "API request timed out. The server might be busy or unresponsive.", "data": None}
    except Exception as e:
        return {"success": False, "status_code": 0, "error": f"An unexpected error occurred during API call: {e}", "data": None}

# --- UI Styling (Optional) ---
st.markdown(
    """
    <style>
    .stMetric {
        border: 1px solid #2E3A59;
        border-radius: 7px;
        padding: 10px;
        background-color: #F0F2F6;
    }
    .stDataFrame {
        border: 1px solid #E0E0E0;
        border-radius: 5px;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# --- Main Title ---
st.title("💳 Credit Score (iScore) Calculator")
st.markdown("---")

# --- Sidebar for User Management and Actions ---
with st.sidebar:
    st.header("👤 User Management")

    with st.expander("Register New User", expanded=False):
        new_username_reg = st.text_input("New Username", key="new_username_reg") # Changed key
        new_email_reg = st.text_input("New User Email (Optional)", key="new_email_reg") # Changed key
        if st.button("Register", type="primary", key="register_button"): # Added key
            if new_username_reg:
                api_result = make_api_request(
                    "POST", "/users/", json_data={"username": new_username_reg, "email": new_email_reg}
                )
                if api_result["success"]:
                    user_data = api_result["data"]
                    st.session_state.user_id = user_data.get("user_id")
                    st.session_state.username = user_data.get("username")
                    st.success(f"User '{st.session_state.username}' registered! ID: {st.session_state.user_id}")
                    st.rerun()
                else:
                    # Specific error handling based on status code and message
                    if api_result["status_code"] == 400 and "already exists" in api_result["error"].lower():
                         st.error(f"Registration failed: {api_result['error']}") # Backend provides "Username or email already exists"
                    elif api_result["status_code"] == 422 and "email formating is wrong" in api_result["error"].lower():
                        st.error("Registration failed: The email address format is invalid.")
                    else:
                        st.error(f"Registration failed: {api_result['error']} (Status: {api_result['status_code']})")
            else:
                st.warning("Username is required for registration.")

    st.markdown("---")
    st.subheader("🎯 Active User")

    if "user_id" not in st.session_state:
        st.session_state.user_id = ""
    if "username" not in st.session_state:
        st.session_state.username = ""

    user_id_input_sidebar = st.text_input( # Changed key
        "Enter User ID to Use", value=st.session_state.user_id, key="user_id_input_sidebar"
    )

    if st.button("Set Active User ID", key="set_active_user_button"): # Added key
        if user_id_input_sidebar:
            try:
                uuid.UUID(user_id_input_sidebar)
                # Before setting, let's try to fetch user to confirm existence
                check_user_result = make_api_request("GET", f"/iscore/{user_id_input_sidebar}") # Using /iscore as a proxy for user existence check for now
                                                                                             # Ideally, you'd have a GET /users/{user_id} endpoint
                if check_user_result["success"] or (check_user_result["status_code"] == 404 and "Missing data for factors" in check_user_result["error"]):
                    # If success, or if user exists but data is missing (which is fine for setting ID)
                    st.session_state.user_id = user_id_input_sidebar
                    st.success(f"Active User ID set to: {user_id_input_sidebar}")
                    # You could fetch and set username here if you have a GET /users/{id} endpoint
                    # For now, we'll just set the ID.
                elif check_user_result["status_code"] == 404 and "User not found" in check_user_result["error"]:
                    st.error(f"User ID '{user_id_input_sidebar}' not found in the system.")
                    st.session_state.user_id = "" # Clear if not found
                else: # Other errors during check
                    st.error(f"Could not verify User ID: {check_user_result['error']}")
                    st.session_state.user_id = ""

            except ValueError:
                st.error("Invalid User ID format. Please enter a valid UUID.")
                st.session_state.user_id = ""
        else:
            st.warning("Please enter a User ID.")

    if st.session_state.user_id:
        st.success(f"Current User ID: `{st.session_state.user_id}`")
        if st.button("🔄 Generate/Refresh Credit Data", key="generate_data_button"): # Added key
            api_result = make_api_request(
                "POST", f"/users/{st.session_state.user_id}/generate-data/"
            )
            if api_result["success"]:
                st.success("Credit data generated/updated successfully!")
                st.balloons()
            else:
                if api_result["status_code"] == 404: # User not found for data generation
                     st.error(f"Error: User ID '{st.session_state.user_id}' not found. Cannot generate data.")
                else:
                    st.error(f"Error generating data: {api_result['error']}")
    else:
        st.info("Register a new user or enter an existing User ID to proceed.")

st.markdown("---")

# --- Score Calculation and Display Section ---
st.header("📊 iScore Calculation & Insights")

if not st.session_state.user_id:
    st.warning("Please set an active User ID in the sidebar to calculate iScore.")
else:
    if st.button("Calculate iScore ✨", type="primary", use_container_width=True, key="calculate_iscore_button"): # Added key
        with st.spinner("Calculating your iScore... Fetching data from multiple sources..."):
            api_result = make_api_request("GET", f"/iscore/{st.session_state.user_id}")

        if api_result["success"]:
            score_data = api_result["data"]
            st.subheader(f"iScore for User: `{score_data['user_id']}`")
            col1, col2 = st.columns([2, 3])
            with col1:
                iscore_value = score_data["iscore"]
                fig_gauge = go.Figure(
                    go.Indicator(
                        mode="gauge+number+delta",
                        value=iscore_value,
                        domain={"x": [0, 1], "y": [0, 1]},
                        title={"text": "iScore", "font": {"size": 24}},
                        delta={"reference": 650, "increasing": {"color": "MediumSeaGreen"}, "decreasing": {"color": "Tomato"}},
                        gauge={
                            "axis": {"range": [300, 850], "tickwidth": 1, "tickcolor": "darkblue"},
                            "bar": {"color": "darkblue"}, "bgcolor": "white", "borderwidth": 2, "bordercolor": "gray",
                            "steps": [
                                {"range": [300, 580], "color": "Tomato"}, {"range": [580, 670], "color": "Orange"},
                                {"range": [670, 740], "color": "YellowGreen"}, {"range": [740, 800], "color": "MediumSeaGreen"},
                                {"range": [800, 850], "color": "DarkGreen"},
                            ],
                            "threshold": {"line": {"color": "red", "width": 4}, "thickness": 0.75, "value": 500},
                        },
                    )
                )
                fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "darkblue", "family": "Arial"}, height=300, margin=dict(l=20, r=20, t=50, b=20))
                st.plotly_chart(fig_gauge, use_container_width=True)
                st.metric(label="Final Unscaled Score (0-100)", value=f"{score_data['final_unscaled_score']:.2f}")

            with col2:
                st.subheader("Factor Contributions (Weighted)")
                components = pd.DataFrame(score_data["components"])
                fig_bar = go.Figure(go.Bar(x=components["weighted_score"], y=components["name"], orientation="h", marker_color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]))
                fig_bar.update_layout(title_text="Weighted Contribution to Score", xaxis_title="Weighted Score Points", yaxis_title="Credit Factor", height=300, margin=dict(l=150, r=20, t=50, b=50))
                st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("---")
            st.subheader("Detailed Score Breakdown")
            components_df = pd.DataFrame(score_data["components"])
            components_df_display = components_df.rename(columns={"name": "Factor", "value": "Raw Input Metric Value", "raw_score": "Factor Score (0-100)", "weight": "Weight (%)", "weighted_score": "Weighted Contribution"})
            components_df_display["Weight (%)"] = (components_df_display["Weight (%)"] * 100).round(0).astype(str) + "%"
            st.dataframe(components_df_display[["Factor", "Raw Input Metric Value", "Factor Score (0-100)", "Weight (%)", "Weighted Contribution"]], use_container_width=True)

            st.markdown("---")
            st.subheader("📋 Raw Data Fetched for Calculation")
            raw = score_data["raw_data_fetched"]
            with st.expander("User Information", expanded=False):
                if raw.get("user_info"): st.json(raw["user_info"])
                else: st.caption("No user info available.")
            col_data1, col_data2 = st.columns(2)
            with col_data1:
                with st.expander("Payment History Data (Supabase 1)", expanded=False):
                    if raw.get("payment_info"): st.json(raw["payment_info"])
                    else: st.caption("No payment info.")
                with st.expander("Credit History Age Data (Supabase 2)", expanded=False):
                    if raw.get("history_info"): st.json(raw["history_info"])
                    else: st.caption("No history info.")
            with col_data2:
                with st.expander("Outstanding Debt Data (MongoDB Atlas 1)", expanded=False):
                    if raw.get("debt_info"): st.json(raw["debt_info"])
                    else: st.caption("No debt info.")
                with st.expander("Credit Mix Data (MongoDB Atlas 2)", expanded=False):
                    if raw.get("mix_info"): st.json(raw["mix_info"])
                    else: st.caption("No mix info.")
        else:
            # Specific error handling for iScore calculation
            if api_result["status_code"] == 404:
                if "User not found" in api_result["error"]:
                    st.error(f"Error: User ID '{st.session_state.user_id}' not found. Cannot calculate iScore.")
                elif "Missing data for factors" in api_result["error"]:
                    st.error(f"Error: User '{st.session_state.user_id}' found, but some credit data is missing. Please generate/refresh credit data. Details: {api_result['error']}")
                else:
                    st.error(f"Error calculating iScore (404): {api_result['error']}")
            else:
                st.error(f"Error calculating iScore: {api_result['error']} (Status: {api_result['status_code']})")

# --- Footer ---
st.markdown("---")
st.caption("iScore Calculator v1.2 - Distributed Database Demo")