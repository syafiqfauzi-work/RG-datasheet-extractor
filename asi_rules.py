"""
ASI determination for Commodity Group RG (Resistors).

Encodes the "Resistors (RG) - Material and supplier standardization rule"
(release 18 Jul 2024) and its ASI categorization page.

Rating scale (worst parameter wins):
    ASI-T    recommended for new designs
    ASI-O    approved
    ASI-U/V  not recommended / phase-out

The rule tables live in the constants below, so a rule update only needs
edits here, not in app.py.
"""
import re

T, O, U = 0, 1, 2
LABEL = {T: "ASI-T", O: "ASI-O", U: "ASI-U/V"}

# ---------------------------------------------------------------- suppliers
PREFERRED = ("YAGEO",)
APPROVED = ("PANASONIC", "VISHAY")
APPROVED_SPECIFIC = ("SMITHS", "EMC TECHNIK", "BARRY")  # specific purpose only
SPECIFIC_EXAMPLE_MFRS = ("SUSUMU", "KYOCERA", "ROHM", "ISABELLENH")  # ASI-O examples
AVOID = ("FENGHUA",)

# ---------------------------------------------------------------- packages
STANDARD_PKGS = {"01005", "0201", "0402", "0603", "1206", "1218", "1812", "2512", "MELF"}
PKG_RATING = {
    "01005": O, "0201": T, "0402": T, "0603": O, "1206": T,
    "0805": U, "1210": U, "1218": O, "2512": O, "MELF": O,
}
# tolerance (%) per package: (set rated T, set rated O); anything else is U/V
TOL_RULES = {
    "01005": (set(), {1.0}),
    "0201": ({1.0}, {0.1}),
    "0402": ({1.0}, {0.1, 0.25, 0.5}),
    "0603": (set(), {0.1, 0.25, 0.5, 1.0}),
    "1206": ({1.0}, {0.1, 0.25, 0.5}),
    "0805": (set(), set()),
    "1210": (set(), set()),
    "1218": (set(), {1.0}),
    "2512": (set(), {1.0, 5.0}),
}
# rated power above which the HP tag is expected: (limit W, inclusive?)
HP_LIMIT = {"0402": (0.1, False), "0603": (0.1, False), "1206": (0.5, True),
            "1218": (1.0, False), "2512": (1.0, False)}

SPECIFIC_TAGS = {"HF", "HP", "HV", "AS", "FT", "SM", "AIN", "AU", "AG", "CU"}
SPECIAL_TERMINATION_TAGS = {"FT", "SM", "AU", "AG", "CU"}  # ASI-O column

# ------------------------------------------------------------ value series
E12_CLOSEST = {1.00, 1.21, 1.50, 1.82, 2.21, 2.74, 3.32, 3.92, 4.75, 5.62, 6.81, 8.25}
E24_CLOSEST_0603 = {
    1.00, 1.10, 1.21, 1.30, 1.50, 1.62, 1.82, 2.00, 2.21, 2.43, 2.74, 3.01,
    3.32, 3.57, 3.92, 4.32, 4.75, 5.11, 5.62, 6.19, 6.81, 7.50, 8.25, 9.09,
}
E24 = {1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6,
       3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1}
E96 = {float(x) for x in (
    "1.00 1.02 1.05 1.07 1.10 1.13 1.15 1.18 1.21 1.24 1.27 1.30 1.33 1.37 1.40 1.43 "
    "1.47 1.50 1.54 1.58 1.62 1.65 1.69 1.74 1.78 1.82 1.87 1.91 1.96 2.00 2.05 2.10 "
    "2.15 2.21 2.26 2.32 2.37 2.43 2.49 2.55 2.61 2.67 2.74 2.80 2.87 2.94 3.01 3.09 "
    "3.16 3.24 3.32 3.40 3.48 3.57 3.65 3.74 3.83 3.92 4.02 4.12 4.22 4.32 4.42 4.53 "
    "4.64 4.75 4.87 4.99 5.11 5.23 5.36 5.49 5.62 5.76 5.90 6.04 6.19 6.34 6.49 6.65 "
    "6.81 6.98 7.15 7.32 7.50 7.68 7.87 8.06 8.25 8.45 8.66 8.87 9.09 9.31 9.53 9.76"
).split()}
E192 = {float(x) for x in (
    "1.00 1.01 1.02 1.04 1.05 1.06 1.07 1.09 1.10 1.11 1.13 1.14 1.15 1.17 1.18 1.20 "
    "1.21 1.23 1.24 1.26 1.27 1.29 1.30 1.32 1.33 1.35 1.37 1.38 1.40 1.42 1.43 1.45 "
    "1.47 1.49 1.50 1.52 1.54 1.56 1.58 1.60 1.62 1.64 1.65 1.67 1.69 1.72 1.74 1.76 "
    "1.78 1.80 1.82 1.84 1.87 1.89 1.91 1.93 1.96 1.98 2.00 2.03 2.05 2.08 2.10 2.13 "
    "2.15 2.18 2.21 2.23 2.26 2.29 2.32 2.35 2.37 2.40 2.43 2.46 2.49 2.52 2.55 2.58 "
    "2.61 2.64 2.67 2.71 2.74 2.77 2.80 2.84 2.87 2.91 2.94 2.98 3.01 3.05 3.09 3.12 "
    "3.16 3.20 3.24 3.28 3.32 3.36 3.40 3.44 3.48 3.52 3.57 3.61 3.65 3.70 3.74 3.79 "
    "3.83 3.88 3.92 3.97 4.02 4.07 4.12 4.17 4.22 4.27 4.32 4.37 4.42 4.48 4.53 4.59 "
    "4.64 4.70 4.75 4.81 4.87 4.93 4.99 5.05 5.11 5.17 5.23 5.30 5.36 5.42 5.49 5.56 "
    "5.62 5.69 5.76 5.83 5.90 5.97 6.04 6.12 6.19 6.26 6.34 6.42 6.49 6.57 6.65 6.73 "
    "6.81 6.90 6.98 7.06 7.15 7.23 7.32 7.41 7.50 7.59 7.68 7.77 7.87 7.96 8.06 8.16 "
    "8.25 8.35 8.45 8.56 8.66 8.76 8.87 8.98 9.09 9.20 9.31 9.42 9.53 9.65 9.76 9.88"
).split()}
E192_EXCLUSIVE = E192 - E96 - E24


# ------------------------------------------------------------------ parsing
def _num(s):
    if s is None:
        return None
    m = re.search(r"\d+(?:\.\d+)?", str(s).replace(",", "."))
    return float(m.group()) if m else None


def parse_resistance(s):
    """'0R3' -> 0.3, '1R' -> 1.0, '4K7' -> 4700.0, '10M' -> 1e7."""
    if s is None:
        return None
    s = str(s).strip().upper().replace("Ω", "").replace("OHM", "").replace(" ", "")
    if s in ("", "N/A"):
        return None
    for ch, mult in (("R", 1.0), ("K", 1e3), ("M", 1e6)):
        if ch in s:
            left, _, right = s.partition(ch)
            try:
                return float(f"{left or '0'}.{right or '0'}") * mult
            except ValueError:
                return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_package(s):
    if not s:
        return None
    t = str(s).upper()
    if "MELF" in t:
        return "MELF"
    m = re.search(r"\d{4,5}", t)
    return m.group() if m else None


def mantissa(r):
    while r >= 10:
        r /= 10
    while r < 1:
        r *= 10
    return round(r, 2)


def _in(x, values):
    return any(abs(x - v) < 1e-9 for v in values)


# ------------------------------------------------------------- determination
def determine_asi(manufacturer, resistance, tolerance, package, tc,
                  mounting, tags="", power=None, additional_info=""):
    checks, flags = [], []

    def add(param, value, rating, note):
        checks.append({"Parameter": param, "Value": value, "Rating": rating, "Note": note})

    mfr = (manufacturer or "").upper()
    r = parse_resistance(resistance)
    tol = _num(tolerance)
    pkg = parse_package(package)
    tc_val = _num(tc)
    pwr = _num(power)
    tag_set = {t for t in re.split(r"[/\s,]+", (tags or "").upper()) if t}
    mount = (mounting or "").upper()

    # --- supplier
    if any(k in mfr for k in AVOID):
        add("Supplier", manufacturer, U, "Restricted (avoid): needs a solution group decision")
    elif any(k in mfr for k in PREFERRED):
        add("Supplier", manufacturer, T, "Preferred supplier")
    elif any(k in mfr for k in APPROVED):
        add("Supplier", manufacturer, T, "Approved supplier (give priority to preferred)")
    elif any(k in mfr for k in APPROVED_SPECIFIC):
        add("Supplier", manufacturer, O, "Approved for specific purpose parts only")
    elif any(k in mfr for k in SPECIFIC_EXAMPLE_MFRS):
        add("Supplier", manufacturer, O, "Not in supplier table; listed in specific purpose examples (ASI-O)")
        flags.append("Supplier is not in the supplier table: contact Procurement Engineering.")
    else:
        add("Supplier", manufacturer or "N/A", U, "Not listed: contact Procurement Engineering")
        flags.append("Supplier is not listed in the rule: contact Procurement Engineering.")

    # --- resistance
    if r is None:
        add("Resistance", "N/A", None, "Could not evaluate")
    elif r < 1:
        add("Resistance", resistance, O, "< 1 Ohm is specific purpose: discuss individually")
        flags.append("Resistance < 1 Ohm: discuss with Procurement and the component engineer.")
    else:
        if pkg == "0603":
            ok = _in(mantissa(r), E24_CLOSEST_0603)
            add("Value series", resistance, O if ok else U,
                "E96 value closest to E24" if ok else "Other value: use 0402 or approved 0603 values")
            if not ok and _in(mantissa(r), E24):
                flags.append("E24 value outside the 0603 list: application high-runner values (e.g. 4K7) "
                             "can stay ASI-O per the rule. Check DMS.")
        elif _in(mantissa(r), E12_CLOSEST):
            add("Value series", resistance, T, "E96 value closest to E12")
        elif _in(mantissa(r), E192_EXCLUSIVE):
            add("Value series", resistance, U, "E192-exclusive value")
        else:
            add("Value series", resistance, O, "Other value (e.g. application high runner)")

    # --- package
    if pkg is None:
        add("Package", package or "N/A", None, "Could not evaluate")
    elif pkg in PKG_RATING:
        note = {"0805": "Use 1206 or 0402 networks instead",
                "1210": "Use 1218 or smaller networks instead",
                "0603": "Replace with 0402 network where possible",
                "01005": "Needs production feasibility discussion"}.get(pkg, "")
        add("Package", pkg, PKG_RATING[pkg], note)
    elif pkg == "1812":
        add("Package", pkg, O, "Standard package but the rule has no 1812 row: confirm with component engineer")
        flags.append("1812 has no row in the rule: rating assumed ASI-O.")
    else:
        add("Package", pkg, O, "Not in the standard package list: specific purpose")

    # --- tolerance
    if tol is None or pkg is None:
        add("Tolerance", "N/A" if tol is None else tol, None, "Could not evaluate")
    elif pkg in TOL_RULES:
        t_set, o_set = TOL_RULES[pkg]
        if _in(tol, t_set):
            add("Tolerance", f"{tol:g} %", T, f"Recommended for {pkg}")
        elif _in(tol, o_set):
            add("Tolerance", f"{tol:g} %", O, f"Approved for {pkg}")
        else:
            add("Tolerance", f"{tol:g} %", U, f"Not accepted for {pkg}")
    else:
        add("Tolerance", f"{tol:g} %", None, "No tolerance rule for this package")

    # --- temperature coefficient
    if tc_val is None:
        add("TC", "N/A", None, "Could not evaluate")
    elif pkg == "0201" and r is not None:
        if r < 10:
            rating = T if 100 <= tc_val <= 400 else (O if tc_val < 100 or tc_val >= 600 else U)
        else:
            rating = T if 100 <= tc_val <= 200 else (O if tc_val < 100 or tc_val >= 600 else U)
        add("TC", f"{tc_val:g} ppm", rating, "0201-specific TC row (verify against the rule PDF)")
    else:
        add("TC", f"{tc_val:g} ppm", T if tc_val <= 200 else U, "<= 200 ppm required")

    # --- termination / mounting
    if not mount or mount == "N/A":
        add("Mounting", "N/A", None, "Could not evaluate")
    elif "THW" in mount or "THR" in mount or "THROUGH" in mount:
        add("Mounting", mounting, U, "THT is in the not-recommended column")
    elif "SMT" in mount or "SURFACE" in mount:
        if tag_set & SPECIAL_TERMINATION_TAGS:
            add("Mounting", mounting, O,
                f"Special termination ({', '.join(sorted(tag_set & SPECIAL_TERMINATION_TAGS))})")
        else:
            add("Mounting", mounting, T, "SN termination assumed")
    else:
        add("Mounting", mounting, O, "Non-standard mounting: confirm with component engineer")
        flags.append(f"Mounting '{mounting}' is not covered by the rule tables.")

    # --- informational
    if pkg in HP_LIMIT and pwr is not None:
        lim, inclusive = HP_LIMIT[pkg]
        high = pwr >= lim if inclusive else pwr > lim
        if high and "HP" not in tag_set:
            flags.append(f"Rated power {pwr:g} W is high power for {pkg}: the HP tag is expected in the designation.")
    if "AQ" in (additional_info or "").upper():
        add("AEC-Q200", "Yes", None, "Allowed, but tends to cost more and be scarcer in shortages")

    # --- sub-group
    reasons = []
    if r is not None and r < 1:
        reasons.append("resistance < 1 Ohm")
    if pkg is not None and pkg not in STANDARD_PKGS:
        reasons.append(f"package {pkg}")
    if tag_set & SPECIFIC_TAGS:
        reasons.append("tags " + "/".join(sorted(tag_set & SPECIFIC_TAGS)))
    subgroup = "Specific purpose (" + ", ".join(reasons) + ")" if reasons else "Standard"
    if reasons:
        flags.append("Specific purpose: discuss with Procurement and the component engineer.")

    # --- overall (worst rated parameter wins)
    rated = [c["Rating"] for c in checks if c["Rating"] is not None]
    missing = [c["Parameter"] for c in checks if c["Rating"] is None and c["Value"] == "N/A"]
    if pkg is None or r is None or not rated:
        overall, summary = None, "Not enough data (package and resistance are required)."
    else:
        overall = max(rated)
        worst = [c["Parameter"] for c in checks if c["Rating"] == overall]
        summary = ("All evaluated parameters meet ASI-T." if overall == T
                   else "Worst-rated parameter(s): " + ", ".join(worst))
    if missing and overall is not None:
        flags.append("Not evaluated (missing data): " + ", ".join(missing))

    return {"overall": overall, "label": LABEL.get(overall, "Undetermined"),
            "summary": summary, "subgroup": subgroup, "checks": checks, "flags": flags}


# --------------------------------------------------------- app integration
def _val(data, key):
    item = data.get(key)
    if isinstance(item, dict):
        return str(item.get("value", "N/A"))
    return "N/A" if item is None else str(item)


def asi_from_extraction(extracted_data, designation_text, manufacturer_text):
    """Adapter: takes the analyzer's extracted_data dict and returns the ASI result."""
    parts = str(designation_text).split()
    tags = " ".join(parts[5:]) if len(parts) > 5 else ""
    return determine_asi(
        manufacturer=str(manufacturer_text),
        resistance=_val(extracted_data, "Resistance (Ohm)"),
        tolerance=_val(extracted_data, "Tolerance (%)"),
        package=_val(extracted_data, "Package Type"),
        tc=_val(extracted_data, "Temperature Coefficient"),
        mounting=_val(extracted_data, "Kind of Mounting"),
        tags=tags,
        power=_val(extracted_data, "Power Consumption (W)"),
        additional_info=_val(extracted_data, "Additional Information"),
    )


def asi_csv_rows(result):
    rows = [["ASI Overall", result["label"], "-", "-", result["summary"]],
            ["ASI Sub-group", result["subgroup"], "-", "-", "-"]]
    for c in result["checks"]:
        rows.append([f"ASI check: {c['Parameter']}", LABEL.get(c["Rating"], "info"),
                     "-", "-", f"{c['Value']} | {c['Note']}"])
    for f in result["flags"]:
        rows.append(["ASI flag", "-", "-", "-", f])
    return rows


def render_asi(result):
    import streamlit as st
    from ui_style import callout
    kind = {T: "success", O: "warning", U: "error"}.get(result["overall"], "info")
    callout(kind, result["summary"], tag=result["label"])
    st.caption(f"Sub-group: {result['subgroup']}")
    if result["checks"]:
        st.table({
            "Parameter": [c["Parameter"] for c in result["checks"]],
            "Value": [str(c["Value"]) for c in result["checks"]],
            "Rating": [LABEL.get(c["Rating"], "info") for c in result["checks"]],
            "Note": [c["Note"] for c in result["checks"]],
        })
    for f in result["flags"]:
        callout("warning", f)
    st.caption("Rule-based on the RG standardization rule (18 Jul 2024). "
               "Confirm the official status in DMS/PDM (ASI-Reason).")
