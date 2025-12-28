import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        .stApp { background-color: #0F0F0F; color: #E0E0E0; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #222; }
        .metric-container { 
            background-color: #161616; border: 1px solid #262626; padding: 20px; 
            border-radius: 12px; text-align: center; margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2); min-height: 140px;
            display: flex; flex-direction: column; justify-content: center;
        }
        .metric-label { color: #888; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; }
        .metric-value { color: white; font-size: 24px; font-weight: 800; margin-top: 5px; }
        .metric-sub { font-size: 12px; margin-top: 4px; color: #666; }
        
        .trade-card { background-color: #161616; border-radius: 12px; padding: 15px; border: 1px solid #262626; margin-bottom: 15px; }
        .card-res-win { font-size: 18px; font-weight: 800; color: #00FF88; } 
        .card-res-loss { font-size: 18px; font-weight: 800; color: #FF4B4B; }
        </style>
    """, unsafe_allow_html=True)

def card_metric(label, value, sub_value="", color="white"):
    st.markdown(f"""
        <div class="metric-container" style="border-color: {color}40;">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color: {color};">{value}</div>
            <div class="metric-sub">{sub_value}</div>
        </div>
    """, unsafe_allow_html=True)
