import streamlit as st

def apply_seline_theme():
    st.markdown("""
    <style>
    /* Seline Analytics Theme */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    /* Variables */
    :root {
        --color-stone-canvas: #fafaf9;
        --color-pure-white: #ffffff;
        --color-stone-border: #e8e6e5;
        --color-stone-muted: #d6d3d1;
        --color-ash-gray: #a8a29e;
        --color-warm-gray: #78716c;
        --color-ink-black: #0c0a09;
        --color-soot: #1c1917;
        --color-sky-wash: #c1e1f7;
        --color-cyan-signal: #3ba6f1;
        --color-cyan-edge: #3398e1;
        
        --font-inter: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        --font-heading: 'Inter', ui-sans-serif, system-ui; 
    }

    /* Base Body & App Background */
    .stApp {
        background-color: var(--color-stone-canvas);
        font-family: var(--font-inter);
    }
    
    /* Global text colors */
    .stApp p, .stApp span, .stApp label, .stApp div {
        color: var(--color-warm-gray);
    }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        font-family: var(--font-heading) !important;
        color: var(--color-ink-black) !important;
        font-weight: 400 !important;
        letter-spacing: -0.02em !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: var(--color-stone-canvas);
        border-right: 1px solid var(--color-stone-border);
    }
    
    /* Primary Buttons */
    .stButton > button[kind="primary"] {
        background-color: var(--color-cyan-signal) !important;
        color: var(--color-pure-white) !important;
        border: 1px solid var(--color-cyan-edge) !important;
        border-radius: 9999px !important;
        padding: 8px 16px !important;
        font-weight: 500 !important;
        box-shadow: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        opacity: 0.9;
    }
    .stButton > button[kind="primary"] p {
        color: var(--color-pure-white) !important;
    }
    
    /* Secondary Buttons */
    .stButton > button[kind="secondary"] {
        background-color: transparent !important;
        color: var(--color-ink-black) !important;
        border: 1px solid var(--color-stone-border) !important;
        border-radius: 9999px !important;
        padding: 8px 16px !important;
        font-weight: 400 !important;
        box-shadow: none !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: var(--color-stone-muted) !important;
    }
    .stButton > button[kind="secondary"] p {
        color: var(--color-ink-black) !important;
    }
    
    /* Inputs */
    .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
        background-color: var(--color-pure-white) !important;
        border: 1px solid var(--color-stone-border) !important;
        border-radius: 6px !important;
        color: var(--color-ink-black) !important;
        box-shadow: none !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox > div > div:focus {
        border-color: var(--color-cyan-signal) !important;
        box-shadow: 0 0 0 1px var(--color-cyan-signal) !important;
    }
    
    /* Dataframes & Tables */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        border: 1px solid var(--color-stone-border);
        background-color: var(--color-pure-white);
        box-shadow: rgba(0, 0, 0, 0.05) 0px 4px 16px 0px;
        padding: 10px;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: var(--color-pure-white) !important;
        border: 1px solid var(--color-stone-border) !important;
        border-radius: 10px !important;
        color: var(--color-ink-black) !important;
    }
    .streamlit-expanderContent {
        border: 1px solid var(--color-stone-border) !important;
        border-top: none !important;
        background-color: var(--color-pure-white) !important;
        border-bottom-left-radius: 10px;
        border-bottom-right-radius: 10px;
    }
    
    /* Flat Content Card (Utility Class for Markdown HTML) */
    .seline-card {
        background-color: var(--color-pure-white);
        border-radius: 10px;
        border: 1px solid var(--color-stone-border);
        padding: 24px;
        box-shadow: rgba(0, 0, 0, 0.05) 0px 4px 16px 0px;
    }
    
    /* Floating Dashboard Preview (Utility Class) */
    .seline-dashboard-preview {
        background-color: var(--color-pure-white);
        border-radius: 16px;
        padding: 8px;
        box-shadow: rgba(17, 12, 46, 0.12) 0px 12px 45px 0px;
    }
    
    /* Highlighted Text Span */
    .seline-highlight {
        color: var(--color-cyan-edge) !important;
        background-color: var(--color-sky-wash) !important;
        border-radius: 4px;
        padding: 2px 8px;
        font-weight: 400;
        display: inline-block;
    }
    
    /* Override Streamlit Success/Info/Warning/Error boxes to look more minimal */
    .stAlert {
        border-radius: 6px !important;
        border: 1px solid var(--color-stone-border) !important;
        background-color: var(--color-pure-white) !important;
        box-shadow: rgba(0, 0, 0, 0.05) 0px 1px 2px 0px !important;
        color: var(--color-ink-black) !important;
    }
    </style>
    """, unsafe_allow_html=True)
