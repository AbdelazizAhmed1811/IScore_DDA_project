import streamlit as st
import requests
import uuid
import os
import pandas as pd
from dotenv import load_dotenv
import plotly.graph_objects as go

# --- Environment and API Setup ---
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=dotenv_path)
API_URL = f"http://{os.getenv('FASTAPI_HOST', 'localhost')}:{os.getenv('FASTAPI_PORT', 8000)}"

# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="iScore Calculator",
    page_icon="🌑" # Dark mode friendly icon
)

# --- Custom CSS for Enhanced UI (Dark Mode Aware) ---
# Using Streamlit's theme variables where possible for better dark/light mode compatibility
st.markdown("""
    <style>
        /* General App Styling - Let Streamlit handle base background for dark/light mode */

        /* Sidebar Styling */
        /* Streamlit handles sidebar background in its themes */
        .st-emotion-cache-16txtl3 h1, 
        .st-emotion-cache-16txtl3 h2, 
        .st-emotion-cache-16txtl3 h3 {
             /* Use a color that works on both light and dark sidebar backgrounds */
             color: var(--primary-color, #007bff); /* Default to a blue if var not set */
        }

        /* Main Content Area Cards/Containers */
        .section-container {
            background-color: var(--background-color, #ffffff); /* Adapts to theme */
            padding: 25px; /* Increased padding */
            border-radius: 12px; /* More rounded */
            /* Use a subtle border that works in both modes */
            border: 1px solid var(--secondary-background-color, #e0e0e0); 
            box-shadow: 0 5px 15px rgba(0,0,0,0.08); /* Softer shadow */
            margin-bottom: 25px;
        }
        .section-container h2, .section-container h3, .section-container h4, .section-container h5, .section-container h6 {
            color: var(--text-color, #333); /* Adapts to theme */
            border-bottom: 2px solid var(--primary-color, #007bff);
            padding-bottom: 10px;
            margin-top: 0;
            margin-bottom: 15px; /* Added margin-bottom */
        }
         .section-container .stExpander header { /* Target expander headers within sections */
            font-weight: 600; /* Slightly bolder */
            color: var(--primary-color, #0056b3);
        }


        /* Metric Styling */
        .stMetric {
            background-color: var(--secondary-background-color, #e9ecef); /* Adapts */
            border: 1px solid var(--border-color, #ced4da); 
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }
        .stMetric > label { 
            color: var(--text-color, #495057); /* Adapts to theme's text color */
            font-weight: 500;
            font-size: 0.95em;
        }

        /* Default (Light Theme) Metric Value Color */
        .stMetric > div > div { 
            font-size: 2.2em;
            font-weight: 700;
            color: #000000; /* Black for light theme */
        }

        /* Button Styling - More subtle, relying on Streamlit's theming for primary/secondary */
        .stButton > button {
            border-radius: 8px; /* Less rounded for a more modern feel */
            font-weight: 600;
            padding: 0.6em 1.2em; /* Adjust padding */
            /* Let Streamlit handle colors based on type="primary" or "secondary" */
        }

        /* Expander Styling */
        .stExpander {
            border: 1px solid var(--border-color, #e0e0e0) !important;
            border-radius: 10px !important;
            background-color: var(--secondary-background-color, #f8f9fa) !important;
            margin-top: 10px; /* Add some space above expanders */
        }
       

        /* Dataframe Styling - Let Streamlit handle this for theme consistency */
        /* .stDataFrame { ... } */

        /* Input fields styling */
        .stTextInput input {
            border-radius: 6px;
            border: 1px solid var(--border-color, #ced4da);
        }
        .stTextInput input:focus {
            border-color: var(--primary-color, #007bff);
            box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
        }
        
        /* Custom class for centered text if needed */
        .text-center {
            text-align: center;
        }
        .subtle-caption {
            font-size: 0.85em;
            color: var(--text-color-light, #6c757d); /* Lighter text color */
        }

    </style>
""", unsafe_allow_html=True)


# --- Helper Function for API Calls (no changes needed from previous) ---
def make_api_request(method, endpoint, json_data=None, params=None):
    # ... (same as your last working version) ...
    try:
        full_url = f"{API_URL}{endpoint}"
        if method.upper() == "GET": response = requests.get(full_url, params=params, timeout=10)
        elif method.upper() == "POST": response = requests.post(full_url, json=json_data, timeout=10)
        else: return {"success": False, "status_code": 0, "error": f"Unsupported HTTP method: {method}", "data": None}
        try: response_data = response.json()
        except requests.exceptions.JSONDecodeError: response_data = {"detail": response.text[:200] + "..."} # Truncate if not JSON
        if 200 <= response.status_code < 300: return {"success": True, "status_code": response.status_code, "data": response_data, "error": None}
        else: return {"success": False, "status_code": response.status_code, "error": response_data.get("detail", "Unknown API error."), "data": response_data}
    except requests.exceptions.ConnectionError: return {"success": False, "status_code": 0, "error": f"Connection Error: API at {API_URL} unreachable.", "data": None}
    except requests.exceptions.Timeout: return {"success": False, "status_code": 0, "error": "API request timed out.", "data": None}
    except Exception as e: return {"success": False, "status_code": 0, "error": f"Unexpected API call error: {e}", "data": None}


# --- Initialize Session State ---
if "user_id" not in st.session_state: st.session_state.user_id = ""
if "username" not in st.session_state: st.session_state.username = ""
if "last_iscore_data" not in st.session_state: st.session_state.last_iscore_data = None


# --- Main Title ---
col_title, col_logo_main = st.columns([0.85, 0.15])
with col_title:
    st.title("🌑 iScore: Credit Analyzer") # Dark mode icon
with col_logo_main:
    st.image("https://cdn-icons-png.flaticon.com/512/1790/1790199.png", width=70) # Example: a data/network icon
st.markdown("---")


# --- Sidebar ---
with st.sidebar:
    with st.expander("🚀 Register New User", expanded=True):
        with st.form("registration_form"):
            new_username_reg = st.text_input("Username*", key="sidebar_new_username_reg", help="Your desired username.")
            new_email_reg = st.text_input("Email (Optional)", key="sidebar_new_email_reg", help="Optional contact email.")
            submitted_reg = st.form_submit_button("➕ Register User", type="primary", use_container_width=True)
            if submitted_reg:
                # ... (registration logic - same as before) ...
                if new_username_reg:
                    api_result = make_api_request("POST", "/users/", json_data={"username": new_username_reg, "email": new_email_reg})
                    if api_result["success"]:
                        user_data = api_result["data"]
                        st.session_state.user_id = user_data.get("user_id")
                        st.session_state.username = user_data.get("username")
                        st.success(f"✅ User '{st.session_state.username}' registered! ID: `{st.session_state.user_id}`")
                        st.session_state.last_iscore_data = None 
                        st.rerun()
                    else: # Error handling (same as before)
                        error_msg = api_result['error']
                        if api_result["status_code"] == 400 and "already exists" in error_msg.lower(): st.error(f"⚠️ {error_msg}")
                        elif api_result["status_code"] == 422 and "email formating is wrong" in error_msg.lower(): st.error("⚠️ Invalid email format.")
                        else: st.error(f"❌ Registration failed: {error_msg}")
                else: st.warning("⚠️ Username is required.")


    st.markdown("---")
    st.subheader("🎯 Select Active User")
    user_id_input_sidebar = st.text_input("Enter User ID", value=st.session_state.user_id, key="sidebar_user_id_input", placeholder="Paste User ID...")

    if st.button("🔍 Set & Verify User", key="sidebar_set_active_user_button", type="secondary", use_container_width=True):
        # ... (set active user logic - same as before) ...
        if user_id_input_sidebar:
            try:
                uuid.UUID(user_id_input_sidebar)
                check_user_result = make_api_request("GET", f"/iscore/{user_id_input_sidebar}")
                if check_user_result["success"] or \
                   (check_user_result["status_code"] == 404 and "Missing data for factors" in check_user_result["error"]):
                    st.session_state.user_id = user_id_input_sidebar
                    st.success(f"✅ Active User: `{user_id_input_sidebar}`")
                    st.session_state.last_iscore_data = None 
                elif check_user_result["status_code"] == 404 and "User not found" in check_user_result["error"]:
                    st.error(f"❌ User ID '{user_id_input_sidebar}' not found.")
                    st.session_state.user_id = ""
                else:
                    st.error(f"⚠️ Could not verify User ID: {check_user_result['error']}")
                    st.session_state.user_id = ""
            except ValueError: st.error("⚠️ Invalid User ID format.")
        else: st.warning("⚠️ Please enter a User ID.")


    if st.session_state.user_id:
        st.success(f"Active: `{st.session_state.user_id[:8]}...`") # Show truncated ID
        if st.button("🔄 Generate Credit Data", key="sidebar_generate_data_button", use_container_width=True):
            # ... (generate data logic - same as before) ...
            with st.spinner("🧬 Generating diverse credit data..."):
                api_result = make_api_request("POST", f"/users/{st.session_state.user_id}/generate-data/")
            if api_result["success"]:
                st.success("✅ Credit data generated/updated!")
                st.balloons()
                st.session_state.last_iscore_data = None
            else: # Error handling (same as before)
                if api_result["status_code"] == 404: st.error(f"❌ User ID '{st.session_state.user_id}' not found.")
                else: st.error(f"⚠️ Error generating data: {api_result['error']}")
    else:
        st.info("ℹ️ Register or set User ID to begin.")


# --- Main Content Area ---
if st.session_state.user_id:
    st.markdown("<div class='section-container'>", unsafe_allow_html=True)
    st.header("🧮 Calculate & View iScore")
    if st.button("✨ Calculate My iScore", type="primary", use_container_width=True, key="main_calculate_iscore_button"):
        with st.spinner("📡 Fetching data & crunching numbers..."):
            api_result = make_api_request("GET", f"/iscore/{st.session_state.user_id}")
        if api_result["success"]:
            st.session_state.last_iscore_data = api_result["data"]
        else: # Error handling (same as before)
            st.session_state.last_iscore_data = None
            if api_result["status_code"] == 404:
                if "User not found" in api_result["error"]: st.error(f"❌ User '{st.session_state.user_id}' not found.")
                elif "Missing data for factors" in api_result["error"]: st.error(f"⚠️ User found, but critical credit data missing. Please 'Generate Credit Data'. Details: {api_result['error']}")
                else: st.error(f"⚠️ Error (404): {api_result['error']}")
            else: st.error(f"❌ Error calculating iScore: {api_result['error']}")
    st.markdown("</div>", unsafe_allow_html=True)


    if st.session_state.last_iscore_data:
        score_data = st.session_state.last_iscore_data
        st.markdown("<div class='section-container'>", unsafe_allow_html=True)
        st.subheader(f"🌟 iScore Insights: `{score_data['user_id'][:8]}...`") # Truncated ID
        
        cols_score_display = st.columns([0.45, 0.55]) 

        with cols_score_display[0]:
            iscore_value = score_data['iscore']
            # Determine gauge bar color based on score
            if iscore_value < 580: bar_color = "#dc3545" # Red
            elif iscore_value < 670: bar_color = "#ffc107" # Yellow
            elif iscore_value < 740: bar_color = "#fd7e14" # Orange (using a distinct color)
            elif iscore_value < 800: bar_color = "#20c997" # Teal
            else: bar_color = "#28a745" # Green

            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta", value=iscore_value,
                title={'text': "Overall iScore", 'font': {'size': 20, 'color': "var(--text-color)"}}, # Themed color
                domain={'x': [0, 1], 'y': [0, 1]},
                delta={'reference': 650, 'increasing': {'color': "#28a745"}, 'decreasing': {'color': "#dc3545"}, 'font': {'size': 18}},
                gauge={
                    'axis': {'range': [300, 850], 'tickwidth': 1, 'tickcolor': "var(--text-color-light)"},
                    'bar': {'color': bar_color, 'thickness': 0.85}, # Dynamic bar color
                    'bgcolor': "var(--secondary-background-color)", 'borderwidth': 1, 'bordercolor': "var(--border-color)",
                    'steps': [ # Subtle steps
                        {'range': [300, 580], 'color': 'rgba(220, 53, 69, 0.2)'},
                        {'range': [580, 670], 'color': 'rgba(255, 193, 7, 0.2)'},
                        {'range': [670, 740], 'color': 'rgba(253, 126, 20, 0.2)'},
                        {'range': [740, 800], 'color': 'rgba(32, 201, 151, 0.2)'},
                        {'range': [800, 850], 'color': 'rgba(40, 167, 69, 0.2)'}
                    ],
                    'threshold': {'line': {'color': bar_color, 'width': 5}, 'thickness': 1, 'value': iscore_value} # Pointer
                }))
            fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=300, margin=dict(l=15, r=15, t=50, b=15))
            st.plotly_chart(fig_gauge, use_container_width=True)
            st.metric(label="Unscaled Score (0-100)", value=f"{score_data['final_unscaled_score']:.2f}")

        with cols_score_display[1]:
            st.markdown("<h6 style='text-align: center; color: var(--text-color);'>Factor Contributions (Weighted)</h6>", unsafe_allow_html=True)
            components_df_chart = pd.DataFrame(score_data['components'])
            factor_colors_map = { # More semantic colors
                "Payment History": "#007bff",    # Blue
                "Outstanding Debt": "#17a2b8",   # Teal
                "Credit History Age": "#28a745", # Green
                "Credit Mix": "#ffc107"          # Yellow
            }
            chart_colors = [factor_colors_map.get(name, "#6c757d") for name in components_df_chart['name']] # Use map, default grey

            fig_bar = go.Figure(go.Bar(
                x=components_df_chart['weighted_score'], y=components_df_chart['name'], orientation='h',
                marker_color=chart_colors, text=components_df_chart['weighted_score'].round(1), textposition='outside'
            ))
            fig_bar.update_layout(
                xaxis_title="Weighted Points", yaxis_title=None,
                height=280, margin=dict(l=140, r=20, t=20, b=40),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis={'categoryorder':'total ascending', 'tickfont': {'color': "var(--text-color)"}},
                xaxis={'tickfont': {'color': "var(--text-color)"}, 'gridcolor': "var(--border-color)"},
                font_color="var(--text-color)"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True) # End section-container for score display

        st.markdown("<div class='section-container'>", unsafe_allow_html=True)
        st.subheader("📄 Detailed Score Breakdown")
        # ... (Detailed breakdown table - same logic, will inherit styles) ...
        components_df_table = pd.DataFrame(score_data['components'])
        components_df_table_display = components_df_table.rename(columns={
            "name": "Factor", "value": "Raw Metric", "raw_score": "Factor Score (0-100)",
            "weight": "Weight", "weighted_score": "Contribution"
        })
        components_df_table_display["Weight"] = (components_df_table_display["Weight"] * 100).round(0).astype(int).astype(str) + '%'
        components_df_table_display["Raw Metric"] = components_df_table_display["Raw Metric"].round(2)
        components_df_table_display["Factor Score (0-100)"] = components_df_table_display["Factor Score (0-100)"].round(1)
        components_df_table_display["Contribution"] = components_df_table_display["Contribution"].round(1)
        st.dataframe(components_df_table_display[['Factor', 'Raw Metric', 'Factor Score (0-100)', 'Weight', 'Contribution']], use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True) # End section-container for breakdown


        with st.expander("💾 View Raw Data Fetched for Calculation", expanded=False):
            # This expander will now be styled by the .stExpander CSS
            if score_data and "raw_data_fetched" in score_data: # Check if raw_data_fetched exists
                raw = score_data["raw_data_fetched"]
                raw_data_cols_display = st.columns(2) # Renamed to avoid conflict
                
                data_sources_map = [
                    (raw_data_cols_display[0], "👤 User Information (Neon DB)", raw.get("user_info")),
                    (raw_data_cols_display[0], "💳 Derived Payment History (Supabase 1)", raw.get("derived_payment_history")),
                    (raw_data_cols_display[1], "💰 Outstanding Debt (MongoDB 1)", raw.get("debt_info")),
                    (raw_data_cols_display[1], "⏳ Credit History Age (Supabase 2)", raw.get("history_info")),
                    (raw_data_cols_display[1], "🧩 Credit Mix (MongoDB 2)", raw.get("mix_info")),
                ]
                for col_item, title, data_item in data_sources_map:
                    with col_item:
                        st.markdown(f"**{title}:**")
                        if data_item:
                            st.json(data_item, expanded=False)
                        else:
                            st.caption("➖ No data available for this source.")
            else:
                st.caption("ℹ️ Raw data not available or score not calculated yet.")

else: # If no user_id in session_state
    st.markdown("<div class='section-container text-center'>", unsafe_allow_html=True) # Centered text

    st.write("Your advanced credit scoring and analysis tool. Please register a new user or select an existing one from the sidebar to get started.")
    st.markdown("</div>", unsafe_allow_html=True)

# --- Footer ---
st.markdown("---")
st.markdown("<p class='subtle-caption text-center'>iScore Calculator.</p>", unsafe_allow_html=True)