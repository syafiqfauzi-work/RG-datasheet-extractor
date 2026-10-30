"""
DMS database lookup for the RG Datasheet Analyzer.

  * dms_sidebar()            sidebar uploader that loads the DMS export once
  * render_duplicate_check() "DMS Check" tab: is this part already in DMS?
  * find_better()            existing DMS parts rated ASI T/O that could replace a U/V part
  * mpn_status()             one-line DMS status for any MPN

ASI letters follow the PAD-M "Application-Specific Information (ASI)" document
(v07.00, 2025-07-09). The DMS ASI of an existing material number always governs.
"""
import io
import os
import re

import pandas as pd

from ui_style import callout
from asi_rules import _val, _num, _in, TOL_RULES, parse_resistance, parse_package

LOCAL_PATH = "dms_database.xlsx"   # optional: only for a PRIVATE repo
USABLE_ASI = {"T", "O"}
AVOID_ASI = {"U", "V", "B", "A", "N", "G"}

ASI_MEANING = {
    "T": "Recommended: best option, should be preferred",
    "O": "Approved: usable without restrictions",
    "U": "Not recommended for new designs (standardization): an alternative must be named in the ASI Reason",
    "V": "Not recommended for new designs (risks: NRND, purchasing, quality or manufacturing)",
    "B": "Blocked for new designs: must not be used in new designs",
    "M": "Pre-introduced: prototype production only",
    "A": "Discontinued (all time): last-time-buy possible, not for new designs",
    "N": "Discontinued (end of life): no longer available, not for new designs",
    "G": "Blocked by quality management: service needs only",
    "": "No ASI: introduction not completed, rejected, or not maintained in DMS",
}
ASI_SHORT = {
    "T": "T Recommended", "O": "O Approved", "U": "U Not rec. (standardization)",
    "V": "V Not rec. (risks)", "B": "B Blocked for new designs", "M": "M Pre-introduced",
    "A": "A Discontinued (LTB)", "N": "N Discontinued (EOL)", "G": "G Blocked", "": "- No ASI",
}
ASI_RANK = {"T": 0, "O": 1, "M": 2, "U": 3, "V": 4, "": 5, "A": 6, "N": 7, "G": 8, "B": 9}
MFR_PREF = {"Yageo": 0, "Vishay": 1, "Panasonic": 2}

REQUIRED_COLS = ["ASI", "Material Number", "Manufacturer Part Number", "Commodity Group",
                 "Manufacturer", "Introduction Status", "Tolerance (%)", "TC [ppm/K]",
                 "Package Type", "Resistance [Ohm]", "Power Consumption [W]", "Quantity"]


# ------------------------------------------------------------ normalisers
def norm_mpn(s):
    return re.sub(r"[^A-Z0-9]", "", str(s).upper()) if isinstance(s, str) else ""


def norm_mfr(s):
    if not isinstance(s, str) or not s.strip():
        return "-"
    t = s.lower()
    for key, name in (("vishay", "Vishay"), ("yageo", "Yageo"), ("panasonic", "Panasonic")):
        if key in t:
            return name
    return s.strip()


def pkg_code(s):
    if not isinstance(s, str):
        return None
    t = s.upper()
    if "MELF" in t:
        return "MELF"
    m = re.search(r"EIA(\d{4,5})", t)
    if m:
        return m.group(1)
    if "THRU" in t or "THT" in t or "THROUGH" in t:
        return "THT"
    m = re.search(r"\b(\d{4})\b", t)
    return m.group(1) if m else None


def _f(x, unit=""):
    return "-" if pd.isna(x) else f"{x:g}{unit}"


# ---------------------------------------------------------------- loading
def _parse(data: bytes) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(data), sheet_name=0)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))
    for c in ["Tolerance (%)", "TC [ppm/K]", "Resistance [Ohm]", "Power Consumption [W]", "Quantity"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["_asi"] = df["ASI"].fillna("").astype(str).str.strip().str.upper()
    df["_rank"] = df["_asi"].map(ASI_RANK).fillna(9)
    df["_mpn"] = df["Manufacturer Part Number"].map(norm_mpn)
    df["_pkg"] = df["Package Type"].map(pkg_code)
    df["_mfr"] = df["Manufacturer"].map(norm_mfr)
    df["_released"] = df["Introduction Status"].fillna("").astype(str).str.lower().str.startswith("released")
    return df


try:
    import streamlit as _st
    _parse_cached = _st.cache_data(show_spinner="Loading DMS database...")(_parse)
except Exception:  # streamlit missing or too old: run uncached
    _parse_cached = _parse


def dms_sidebar():
    """Sidebar uploader. Returns the DMS dataframe, or None when nothing is loaded."""
    import streamlit as st
    with st.sidebar:
        st.divider()
        st.header("🗄️ DMS Database")
        up = st.file_uploader("Upload DMS export (xlsx)", type=["xlsx"], key="dms_upload")
        data, src = None, None
        if up is not None:
            data, src = up.getvalue(), up.name
        elif os.path.exists(LOCAL_PATH):
            with open(LOCAL_PATH, "rb") as fh:
                data, src = fh.read(), LOCAL_PATH
        if data is None:
            st.caption("Upload the DMS export to enable the duplicate check and existing-part alternatives.")
            return None
        try:
            df = _parse_cached(data)
        except Exception as e:
            st.error(f"Could not read the DMS file: {e}")
            return None
        st.caption(f"✅ {len(df):,} material numbers loaded ({src})")
        return df


# ---------------------------------------------------------------- lookups
def find_mpn(df, mpn):
    """Return (exact, related) matches. Related = one normalised MPN starts with the other."""
    key = norm_mpn(mpn)
    empty = df.iloc[0:0]
    if len(key) < 6:
        return empty, empty
    exact = df[df["_mpn"] == key].sort_values("_rank")
    mask = df["_mpn"].str.len() >= 10
    related = df[mask & (df["_mpn"] != key) &
                 (df["_mpn"].str.startswith(key) | df["_mpn"].map(lambda m: key.startswith(m) if m else False))]
    return exact, related.sort_values("_rank")


def mpn_status(df, mpn):
    if df is None:
        return "-"
    exact, related = find_mpn(df, mpn)
    if len(exact):
        b = exact.iloc[0]
        return f"In DMS: {b['Material Number']} (ASI {b['_asi'] or '-'})"
    if len(related):
        b = related.iloc[0]
        return f"Similar in DMS: {b['Material Number']} (ASI {b['_asi'] or '-'})"
    return "Not in DMS"


def find_spec_matches(df, r, tol, pkg, was_tht=False, cg=None):
    """Existing parts with the same value, tolerance and package."""
    if r is None:
        return df.iloc[0:0]
    m = df[df["Resistance [Ohm]"].notna()]
    m = m[(m["Resistance [Ohm]"] - r).abs() <= 1e-6 * abs(r)]
    if tol is not None:
        m = m[(m["Tolerance (%)"] - tol).abs() < 1e-9]
    if was_tht:
        m = m[m["_pkg"] == "THT"]
    elif pkg:
        m = m[m["_pkg"] == pkg]
    if cg and cg in set(df["Commodity Group"]):
        m = m[m["Commodity Group"] == cg]
    return m.sort_values(["_rank", "Material Number"])


def find_better(df, r, tol, pkgs, pkg0=None, pwr=None, tc0=None, was_tht=False, limit=8):
    """Existing RG parts with ASI T/O, same value, in an acceptable package."""
    if df is None or r is None:
        return []
    m = df[(df["Commodity Group"] == "RG") & df["_asi"].isin(USABLE_ASI) & df["_released"]
           & df["_pkg"].isin(pkgs) & df["Resistance [Ohm]"].notna()]
    m = m[(m["Resistance [Ohm]"] - r).abs() <= 1e-6 * abs(r)]
    m = m[m["Quantity"].isna() | (m["Quantity"] == 1)]
    rows = []
    for _, x in m.iterrows():
        diffs = []
        t_set, o_set = TOL_RULES.get(x["_pkg"], (set(), set()))
        if pd.notna(x["Tolerance (%)"]):
            if not _in(x["Tolerance (%)"], t_set | o_set):
                continue
            if tol is not None and abs(x["Tolerance (%)"] - tol) > 1e-9:
                diffs.append(f"tolerance {x['Tolerance (%)']:g}% vs {tol:g}%")
        else:
            diffs.append("tolerance n/a: verify")
        if pd.notna(x["Power Consumption [W]"]):
            if pwr is not None and x["Power Consumption [W]"] < pwr * 0.999:
                continue
        else:
            diffs.append("power n/a: verify")
        if pd.notna(x["TC [ppm/K]"]):
            if x["TC [ppm/K]"] > 200:
                continue
            if tc0 is not None and x["TC [ppm/K]"] > tc0:
                diffs.append(f"TC {x['TC [ppm/K]']:g} ppm vs {tc0:g} ppm")
        else:
            diffs.append("TC n/a: verify")
        if pkg0 and x["_pkg"] != pkg0:
            diffs.append(f"package {pkg0} -> {x['_pkg']} (new footprint)")
        if was_tht:
            diffs.append("THT -> SMT")
        rows.append({
            "sort": (ASI_RANK[x["_asi"]], 0 if not diffs else 1,
                     0 if x["_pkg"] == pkg0 else 1, MFR_PREF.get(x["_mfr"], 3), x["Material Number"]),
            "Material Number": x["Material Number"],
            "MPN": x["Manufacturer Part Number"] if isinstance(x["Manufacturer Part Number"], str) else "-",
            "Manufacturer": x["_mfr"], "ASI": ASI_SHORT[x["_asi"]], "Package": x["_pkg"],
            "Value/Tol": f"{x['Resistance [Ohm]']:g} Ohm / {_f(x['Tolerance (%)'], '%')}",
            "Power": _f(x["Power Consumption [W]"]), "TC": _f(x["TC [ppm/K]"]),
            "Match": "Exact spec" if not diffs else "Similar spec",
            "Differences": "; ".join(diffs) or "-",
        })
    rows.sort(key=lambda d: d["sort"])
    return rows[:limit]


# -------------------------------------------------------------- rendering
def _table_from_df(m, limit=15):
    m = m.head(limit)
    return {
        "Material Number": [str(v) for v in m["Material Number"]],
        "MPN": [v if isinstance(v, str) else "-" for v in m["Manufacturer Part Number"]],
        "Manufacturer": list(m["_mfr"]),
        "ASI": [ASI_SHORT[a] for a in m["_asi"]],
        "Package": [str(v) if isinstance(v, str) else "-" for v in m["Package Type"]],
        "Value / Tol": [f"{_f(r)} Ohm / {_f(t, '%')}" for r, t in
                        zip(m["Resistance [Ohm]"], m["Tolerance (%)"])],
        "TC (ppm)": [_f(v) for v in m["TC [ppm/K]"]],
        "Power (W)": [_f(v) for v in m["Power Consumption [W]"]],
        "Intro status": [str(v) for v in m["Introduction Status"]],
    }


def render_duplicate_check(df, target_mpn, extracted_data, designation_text, cg_code):
    import streamlit as st
    if df is None:
        callout("info", "Upload the DMS export in the sidebar (🗄️ DMS Database) to check whether this part already exists.")
        return

    r = parse_resistance(_val(extracted_data, "Resistance (Ohm)"))
    tol = _num(_val(extracted_data, "Tolerance (%)"))
    pkg = parse_package(_val(extracted_data, "Package Type"))
    mount = _val(extracted_data, "Kind of Mounting").upper()
    was_tht = any(k in mount for k in ("THW", "THR", "THROUGH"))

    # 1) MPN lookup
    st.subheader("1. MPN lookup")
    exact, related = find_mpn(df, target_mpn)
    if not str(target_mpn).strip():
        st.caption("No MPN entered above, so only the specification check below was done.")
    elif len(exact):
        b = exact.iloc[0]
        asi, mat = b["_asi"], b["Material Number"]
        msg = f"**{mat}** · ASI {asi or '-'} · {ASI_MEANING[asi]}."
        if len(exact) > 1:
            msg += f" ({len(exact)} material numbers share this MPN; the best ASI is shown first.)"
        if asi in USABLE_ASI:
            callout("success", msg + " Reuse it instead of introducing a new material number.", tag="In DMS")
        elif asi == "M":
            callout("warning", msg, tag="In DMS")
        else:
            callout("error", msg + " Check the Alternative tab for a replacement.", tag="In DMS")
        st.table(_table_from_df(exact))
    elif len(related):
        callout("warning", "No exact match, but similar MPN(s) exist (same start of part number).", tag="Similar MPN")
        st.table(_table_from_df(related, 8))
    else:
        callout("info", f"{target_mpn.strip().upper()} is not in the DMS database.", tag="Not in DMS")

    if cg_code not in ("RG", "Unknown"):
        st.caption(f"Specification matching is available for RG only; the MPN lookup above covers {cg_code} parts too.")
        with st.expander("ASI legend (PAD-M)"):
            st.table({"ASI": [k or "(empty)" for k in ASI_MEANING], "Meaning": list(ASI_MEANING.values())})
        return

    # 2) specification lookup
    st.subheader("2. Same value, tolerance and package")
    if r is None:
        callout("warning", "Resistance was not extracted, so the specification check cannot run.")
    else:
        cg = cg_code if cg_code in ("RG", "RN", "RK", "RR", "RS", "RT", "RX", "RZ") else None
        spec = find_spec_matches(df, r, tol, pkg, was_tht, cg)
        label = f"{r:g} Ohm, {_f(tol if tol is not None else float('nan'), '%')}, " + \
                ("through-hole" if was_tht else (pkg or "package n/a"))
        if len(spec):
            good = spec[spec["_asi"].isin(USABLE_ASI)]
            if len(good):
                callout("warning", f"{len(spec)} existing part(s) match {label}; {len(good)} of them ASI T/O. "
                                   f"Consider reusing one before a new introduction.", tag="Possible duplicate")
            else:
                callout("info", f"{len(spec)} existing part(s) match {label}, but none is ASI T/O.", tag="Same spec")
            st.table(_table_from_df(spec))
            if len(spec) > 15:
                st.caption(f"Showing the best 15 of {len(spec)}.")
            if was_tht:
                st.caption("Through-hole parts are matched on value and tolerance only; body size can't be compared.")
        else:
            callout("success", f"No existing DMS part matches {label}: a new introduction would be needed.", tag="New part")
        n_missing = int(df["Resistance [Ohm]"].isna().sum())
        st.caption(f"{n_missing:,} DMS rows have no resistance value and cannot be matched by specification.")

    with st.expander("ASI legend (PAD-M)"):
        st.table({"ASI": [k or "(empty)" for k in ASI_MEANING], "Meaning": list(ASI_MEANING.values())})
