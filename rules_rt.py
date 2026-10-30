"""
RT (Attenuators & Terminations) rules.

Source: "Attenuators & Terminations (RT) - Material and supplier standardization rule"
(released 08 Dec 2022, updated 05 Feb 2026).

How the rule works:
  * suppliers are Preferred / Approved / Avoid / Blocked, per technology
    (SMD, flange mount, RF equalizer);
  * ASI T is set ONLY for the 11 standard-catalog material numbers below
    (RT 0..10 DB 50R 0.1W SMD0805); every other regular part is ASI O
    (or V, A, G, N depending on its status).
"""
import re

from asi_rules import T, O, U, LABEL, _val, _num, parse_package

TECH_LABEL = {"SMD": "SMD attenuator/termination",
              "FLANGE": "Flange mount attenuator/termination",
              "EQUALIZER": "RF equalizer"}

# (keyword in manufacturer name, display name, technology, status, distributor)
SUPPLIERS = [
    ("susumu", "Susumu/YDS", "SMD", "Preferred", "Endrich"),
    ("diconex", "Diconex", "FLANGE", "Preferred", "Telemeter"),
    ("mini-circuits", "Mini-Circuits", "EQUALIZER", "Preferred", "Municom"),  # Fmax <= 10 GHz only
    ("mini-circuits", "Mini-Circuits", "SMD", "Approved", "Municom"),
    ("ttm", "TTM Technologies/Anaren", "SMD", "Approved", "RFMW (MRC Gigacomp)"),
    ("avx", "Kyocera AVX (KAVX)", "SMD", "Approved", "direct"),
    ("kyocera", "Kyocera AVX (KAVX)", "SMD", "Approved", "direct"),
    ("smiths interconnect", "Molex (Smiths Interconnect/EMC)", "SMD", "Approved", "RFMW (MRC Gigacomp)"),
    ("emc technik", "Molex (Smiths Interconnect/EMC)", "SMD", "Approved", "RFMW (MRC Gigacomp)"),
    ("international manufacturing", "IMS", "SMD", "Approved", "Tactron"),
    ("spectrum control", "Spectrum Control (API/KDI)", "FLANGE", "Approved", "Tactron"),
    ("barry", "Barry/Vishay (special applications)", "FLANGE", "Approved", "RFMW (MRC Gigacomp)"),
    ("vishay", "Barry/Vishay (special applications)", "FLANGE", "Approved", "RFMW (MRC Gigacomp)"),
    ("macom", "Macom", "EQUALIZER", "Approved", "direct"),
    ("knowles", "Knowles", "EQUALIZER", "Approved", "TTI"),
    ("marki", "Marki", "EQUALIZER", "Approved", "direct"),
]
# (keyword, status, reason)
RESTRICTED = [
    ("analog devices", "Avoid", "no further developments for RT; needs a solution group decision"),
    ("res-net", "Blocked", "has not passed the evaluation process"),
    ("resnet", "Blocked", "has not passed the evaluation process"),
]

# dB -> R&S material number of the ASI T standard-catalog chip: RT <n>DB 50R 0.1W SMD0805
T_PARTS = {0: "1135.7444.00", 1: "1135.7450.00", 2: "0048.8499.00", 3: "0048.8501.00",
           4: "1135.7467.00", 5: "1135.7473.00", 6: "1135.7480.00", 7: "1135.7496.00",
           8: "1135.7509.00", 9: "1135.7515.00", 10: "1135.7521.00"}


def t_description(db):
    return f"RT {db}DB 50R 0.1W SMD0805"


def detect_technology(pdf_text, file_names=()):
    text, names = pdf_text.lower(), " ".join(file_names).lower()
    eq = text.count("equaliz") + 5 * names.count("equaliz")
    fl = text.count("flange") + 5 * names.count("flange")
    if eq >= 3:
        return "EQUALIZER"
    if fl >= 3:
        return "FLANGE"
    return "SMD"


def supplier_status(mfr, tech, fmax=None):
    """Return (status, note, distributor); status is None when the supplier is not listed."""
    m = (mfr or "").lower()
    for kw, status, why in RESTRICTED:
        if kw in m:
            return status, why, None
    for kw, _name, t, status, dist in SUPPLIERS:
        if kw in m and t == tech:
            if kw == "mini-circuits" and tech == "EQUALIZER" and fmax is not None and fmax > 10:
                return None, "Mini-Circuits is preferred for equalizers up to 10 GHz only", None
            return status, "", dist
    return None, "", None


def rt_designation(spec):
    """DMS-style description, e.g. 'RT 6DB 50R 0.1W SMD0805'. None if data is missing."""
    if not spec or spec["tech"] != "SMD" or spec["att"] is None or spec["imp"] is None:
        return None
    pw = f" {spec['pwr']:g}W" if spec["pwr"] is not None else ""
    return f"RT {spec['att']:g}DB {spec['imp']:g}R{pw} SMD{spec['pkg'] or ''}".strip()


def _first_num(extracted_data, keys):
    for k in keys:
        v = _num(_val(extracted_data, k))
        if v is not None:
            return v
    return None


def _fmax_ghz(extracted_data):
    raw = _val(extracted_data, "f (Max) (Hz)")
    try:
        return float(re.sub(r"[^0-9eE+.\-]", "", raw)) / 1e9
    except ValueError:
        return _num(_val(extracted_data, "Frequency Max (GHz)"))


def asi_from_extraction_rt(extracted_data, manufacturer_text, pdf_text="", file_names=(), category=None):
    tech = "EQUALIZER" if category == "RF Equalizer" else detect_technology(pdf_text, file_names)
    spec = {
        "tech": tech,
        "att": _first_num(extracted_data, ["Attenuation (Fix / Max) (dB)", "Attenuation (Typ) (dB)", "Attenuation (dB)"]),
        "imp": _first_num(extracted_data, ["Impedance (Ohm)"]),
        "pwr": _first_num(extracted_data, ["Power Consumption (W)"]),
        "pkg": parse_package(_val(extracted_data, "Package Type")),
        "fmax": _fmax_ghz(extracted_data),
    }
    checks, flags = [], []

    status, note, dist = supplier_status(manufacturer_text, tech, spec["fmax"])
    label = f"{manufacturer_text} · {TECH_LABEL[tech]}"
    if status in ("Preferred", "Approved"):
        sup_rating, text = O, f"{status} supplier (distributor: {dist})"
    elif status in ("Avoid", "Blocked"):
        sup_rating, text = U, f"{status}: {note}"
    else:
        sup_rating = U
        text = note or "Not listed for this technology: contact Procurement Engineering"
        flags.append("Supplier/technology combination is not listed in the RT rule: "
                     "contact Procurement Engineering.")
    checks.append({"Parameter": "Supplier / technology", "Value": label, "Rating": sup_rating, "Note": text})

    # standard-catalog (ASI T) match
    att = spec["att"]
    t_match = (tech == "SMD" and att is not None and abs(att - round(att)) < 1e-9
               and 0 <= round(att) <= 10 and spec["imp"] == 50 and spec["pwr"] == 0.1
               and spec["pkg"] == "0805")
    if t_match:
        mat = T_PARTS[int(round(att))]
        checks.append({"Parameter": "Standard catalog", "Value": t_description(int(round(att))),
                       "Rating": T if sup_rating == O else None,
                       "Note": f"Matches standard catalog material {mat}"})
        flags.append(f"ASI T applies to the listed material number only ({mat}): confirm it in DMS.")
    else:
        checks.append({"Parameter": "Standard catalog", "Value": "-", "Rating": None,
                       "Note": "Not one of the ASI T catalog parts (RT 0-10 dB, 50 R, 0.1 W, SMD0805): regular part = ASI O"})

    overall = sup_rating
    if sup_rating == O and t_match:
        overall = T
    worst = [c["Parameter"] for c in checks if c["Rating"] == overall]
    summary = ("Matches an ASI T standard catalog part." if overall == T
               else "Regular part: ASI O." if overall == O
               else "Worst-rated parameter(s): " + ", ".join(worst))
    return {"overall": overall, "label": LABEL[overall], "summary": summary,
            "subgroup": TECH_LABEL[tech], "checks": checks, "flags": flags, "rt": spec}


def render_rt_alternatives(asi_result, dms_df=None):
    import streamlit as st
    spec = asi_result.get("rt")
    if not spec:
        st.info("No RT specification available.")
        return
    if asi_result["overall"] == T:
        st.info("Original part already matches an ASI T standard catalog part.")
        return
    tech = spec["tech"]

    st.subheader("Preferred / approved suppliers")
    rows = [(n, s, d) for (_kw, n, t, s, d) in SUPPLIERS if t == tech]
    seen, uniq = set(), []
    for n, s, d in rows:
        if (n, s) not in seen:
            seen.add((n, s))
            uniq.append((n, s, d))
    uniq.sort(key=lambda r: 0 if r[1] == "Preferred" else 1)
    st.table({"Manufacturer": [r[0] for r in uniq], "Status": [r[1] for r in uniq],
              "Distributor": [r[2] for r in uniq]})

    if tech != "SMD":
        st.caption("The standard catalog (ASI T) lists SMD chip attenuators only.")
        return
    st.subheader("Standard catalog parts (ASI T)")
    att = spec["att"]
    dbs = sorted(T_PARTS, key=lambda d: abs((att if att is not None else 0) - d))[:3]
    out = {"Material Number": [], "Description": [], "ASI (rule)": [], "ASI (DMS export)": [], "Differences": []}
    for db in dbs:
        mat = T_PARTS[db]
        diffs = []
        if att is not None and abs(att - db) > 1e-9:
            diffs.append(f"attenuation {att:g} dB -> {db} dB")
        if spec["imp"] is not None and spec["imp"] != 50:
            diffs.append(f"impedance {spec['imp']:g} -> 50 Ohm")
        if spec["pwr"] is not None and spec["pwr"] != 0.1:
            diffs.append(f"power {spec['pwr']:g} -> 0.1 W")
        if spec["pkg"] and spec["pkg"] != "0805":
            diffs.append(f"package {spec['pkg']} -> 0805")
        dms_asi = "no DMS file loaded"
        if dms_df is not None:
            hit = dms_df[dms_df["Material Number"] == mat]
            dms_asi = hit.iloc[0]["_asi"] or "-" if len(hit) else "not in this export"
        out["Material Number"].append(mat)
        out["Description"].append(t_description(db))
        out["ASI (rule)"].append("T")
        out["ASI (DMS export)"].append(dms_asi)
        out["Differences"].append("; ".join(diffs) or "-")
    st.table(out)
    st.caption("The DMS export only covers the 'Resistor constant' category, so attenuator material numbers "
               "may not appear in it. Confirm the status in DMS.")
