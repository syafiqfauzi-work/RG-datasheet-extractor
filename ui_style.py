"""Minimal-but-practical styling for the RG Datasheet Analyzer."""
import html
import re

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


/* --- Reset button in red (the Extract button keeps the primary colour) --- */
.st-key-reset_btn button {background-color: #dc2626; border-color: #dc2626; color: #ffffff;}
.st-key-reset_btn button p {color: #ffffff;}
.st-key-reset_btn button:hover {background-color: #b91c1c; border-color: #b91c1c; color: #ffffff;}
.st-key-reset_btn button:focus, .st-key-reset_btn button:active {background-color: #991b1b; border-color: #991b1b; color: #ffffff; box-shadow: none;}

/* --- label above the designation box: same look and spacing as a Streamlit widget label --- */
div[data-testid="stMarkdownContainer"] p.field-label {font-size: 0.875rem; line-height: 1.6; font-weight: 400; margin: 0 0 0.25rem 0 !important;}

/* --- status text beside the Category box: as tall as the box, text centred --- */
div[data-testid="stMarkdownContainer"] p.status-line {display: flex; align-items: center; height: 2.5rem; font-size: 0.875rem; opacity: 0.7;}

/* --- last-update pill, top right --- */
div[data-testid="stMarkdownContainer"] p.update-wrap {text-align: right;}
.update-pill {display: inline-block; padding: 0.25rem 0.75rem; border: 1px solid rgba(128,128,128,0.3);
    border-radius: 999px; font-size: 0.75rem; opacity: 0.75; white-space: nowrap;}


/* --- compact callouts (replace the big coloured Streamlit boxes) --- */
div[data-testid="stMarkdownContainer"] p.callout {display: flex; align-items: baseline; gap: 0.6rem;
    margin: 0 0 0.75rem 0 !important; padding: 0.4rem 0.75rem; border-radius: 6px; font-size: 0.85rem;
    line-height: 1.45; border: 1px solid rgba(128,128,128,0.25); border-left-width: 4px;}
div[data-testid="stMarkdownContainer"] p.callout-error {border-left-color: #dc2626; background: rgba(220,38,38,0.08);}
div[data-testid="stMarkdownContainer"] p.callout-warning {border-left-color: #d97706; background: rgba(217,119,6,0.09);}
div[data-testid="stMarkdownContainer"] p.callout-info {border-left-color: #2563eb; background: rgba(37,99,235,0.08);}
div[data-testid="stMarkdownContainer"] p.callout-success {border-left-color: #16a34a; background: rgba(22,163,74,0.09);}
.callout-tag {flex: none; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.03em; text-transform: uppercase;
    padding: 0.05rem 0.5rem; border-radius: 999px; color: #ffffff; white-space: nowrap;}
.callout-error .callout-tag {background: #dc2626;}
.callout-warning .callout-tag {background: #d97706;}
.callout-info .callout-tag {background: #2563eb;}
.callout-success .callout-tag {background: #16a34a;}

/* --- result summary --- */
.kv span {display: block; font-size: 0.7rem; opacity: 0.65; text-transform: uppercase; letter-spacing: 0.05em;}
.kv b {font-size: 1.05rem; font-weight: 600; display: block; overflow-wrap: anywhere;}
.kv-grid {display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 0.1rem;}
.kv-grid .kv {padding: 0 1rem; border-left: 1px solid rgba(128,128,128,0.25);}
.kv-grid .kv:first-child {padding-left: 0; border-left: none;}
@media (max-width: 640px) {
    .kv-grid {grid-template-columns: repeat(2, minmax(0, 1fr)); row-gap: 0.8rem;}
    .kv-grid .kv:nth-child(3) {padding-left: 0; border-left: none;}
}
</style>
"""

ASI_TEXT = {0: ("T", "Recommended", "#16a34a"), 1: ("O", "Approved", "#d97706"),
            2: ("U/V", "Avoid for new designs", "#dc2626")}


def _inline(text):
    """Escape HTML and turn **bold** into <b>."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(str(text)))


def callout(kind, text, tag=None):
    """Compact, theme-friendly replacement for st.success / st.warning / st.error / st.info.
    kind: 'error' | 'warning' | 'info' | 'success'; tag: optional small pill in front of the text."""
    import streamlit as st
    pill = f'<span class="callout-tag">{html.escape(str(tag))}</span>' if tag else ""
    st.markdown(f'<p class="callout callout-{kind}">{pill}<span>{_inline(text)}</span></p>', unsafe_allow_html=True)


def apply_style():
    import streamlit as st
    st.markdown(CSS, unsafe_allow_html=True)


def _kv(label, value, color=None):
    style = f' style="color:{color}"' if color else ""
    return f'<div class="kv"><span>{html.escape(label)}</span><b{style}>{html.escape(str(value))}</b></div>'


def render_summary(designation_text, manufacturer_text, cg_text, asi_result, mpn="", rule_applies=True, na_text="No rule loaded"):
    """Compact result header: copyable designation + four evenly spaced fields."""
    import streamlit as st
    st.markdown('<p class="field-label">Designation</p>', unsafe_allow_html=True)
    st.code(str(designation_text), language=None)  # has a copy button
    if rule_applies:
        letter, meaning, color = ASI_TEXT.get(asi_result["overall"], ("-", "Undetermined", None))
    else:
        letter, meaning, color = "N/A", na_text, None
    cells = [
        _kv("ASI (rule)", f"{letter} · {meaning}", color),
        _kv("Commodity group", cg_text),
        _kv("Manufacturer", manufacturer_text),
        _kv("MPN", str(mpn).strip().upper() or "-"),
    ]
    st.markdown('<div class="kv-grid">' + "".join(cells) + "</div>", unsafe_allow_html=True)
