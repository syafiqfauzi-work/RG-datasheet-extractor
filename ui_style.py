"""Minimal-but-practical styling for the RG Datasheet Analyzer."""
import html

CSS = """
<style>
/* --- chrome: hide footer and Deploy button only (keeps the sidebar toggle and the
       three-dot menu, which holds Settings > Theme for dark mode) --- */
footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}
[data-testid="stAppDeployButton"], .stDeployButton {display: none;}

/* --- page width and spacing (works in landscape and portrait) --- */
.block-container {padding: 2rem 2rem 3rem 2rem; max-width: 1400px;}
@media (max-width: 640px) {.block-container {padding: 1.2rem 0.75rem 2rem 0.75rem;}}

/* --- typography --- */
h1 {font-size: 1.6rem !important; font-weight: 600 !important; letter-spacing: -0.01em; padding: 0 0 0.2rem 0 !important;}
h2, h3 {font-size: 1.0rem !important; font-weight: 600 !important; margin: 0.6rem 0 0.2rem 0 !important; padding: 0 !important;}
div[data-testid="stCaptionContainer"] {opacity: 0.7;}

/* --- controls --- */
.stButton > button, .stDownloadButton > button {border-radius: 8px; font-weight: 500; padding: 0.3rem 1rem;}
/* file uploader: centre the button / file chip vertically inside the box */
[data-testid="stFileUploaderDropzone"] {display: flex; align-items: center !important;
    padding: 0.9rem 1rem !important; min-height: 4.2rem;}
[data-testid="stFileUploaderDropzone"] > * {margin-top: 0 !important; margin-bottom: 0 !important; align-self: center;}
button[data-baseweb="tab"] {font-size: 0.9rem;}
div[data-testid="stTabs"] {margin-top: 0.8rem;}
div[data-testid="stAlert"] {border-radius: 8px; padding: 0.55rem 0.9rem; font-size: 0.9rem;}
hr {margin: 0.8rem 0 !important;}

/* --- tables: light, compact, scroll sideways when too wide --- */
div[data-testid="stTable"] {overflow-x: auto;}
div[data-testid="stTable"] table {font-size: 0.82rem; border-collapse: collapse; width: 100%;}
div[data-testid="stTable"] th {font-weight: 600; opacity: 0.7; background: transparent;
    border: none; border-bottom: 1px solid rgba(128,128,128,0.35); padding: 0.4rem 0.6rem;}
div[data-testid="stTable"] td {border: none; border-bottom: 1px solid rgba(128,128,128,0.15);
    padding: 0.35rem 0.6rem; white-space: normal; word-break: break-word;}

/* --- result summary --- */
.kv span {display: block; font-size: 0.7rem; opacity: 0.65; text-transform: uppercase; letter-spacing: 0.05em;}
.kv b {font-size: 1.05rem; font-weight: 600;}
</style>
"""

ASI_TEXT = {0: ("T", "Recommended", "#16a34a"), 1: ("O", "Approved", "#d97706"),
            2: ("U/V", "Avoid for new designs", "#dc2626")}


def apply_style():
    import streamlit as st
    st.markdown(CSS, unsafe_allow_html=True)


def _kv(label, value, color=None):
    style = f' style="color:{color}"' if color else ""
    return f'<div class="kv"><span>{html.escape(label)}</span><b{style}>{html.escape(str(value))}</b></div>'


def render_summary(designation_text, manufacturer_text, cg_text, asi_result, mpn=""):
    """Compact result header: copyable designation + ASI / group / manufacturer."""
    import streamlit as st
    st.markdown('<div class="kv" style="margin-bottom:-0.6rem"><span>Designation</span></div>', unsafe_allow_html=True)
    st.code(str(designation_text), language=None)  # has a copy button
    letter, meaning, color = ASI_TEXT.get(asi_result["overall"], ("-", "Undetermined", None))
    c1, c2, c3, c4 = st.columns([2, 3, 3, 3])
    with c1:
        st.markdown(_kv("ASI (rule)", f"{letter} · {meaning}", color), unsafe_allow_html=True)
    with c2:
        st.markdown(_kv("Commodity group", cg_text), unsafe_allow_html=True)
    with c3:
        st.markdown(_kv("Manufacturer", manufacturer_text), unsafe_allow_html=True)
    with c4:
        st.markdown(_kv("MPN", str(mpn).strip().upper() or "-"), unsafe_allow_html=True)
