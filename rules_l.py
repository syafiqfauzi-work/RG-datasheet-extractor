"""
L* rules: manufacturer / commodity-group detection and the LD / LL standardization rule.

Source: "Inductors: Chokes, Coils, Filter, Air Coils (LD and LL) - Material and supplier
standardization rule" (CI 03.00, released 18 Jul 2024).

How the rule works:
  * two sub-groups: GP (general purpose / catalogue: wirewound and multilayer chips, chokes)
    and SP (specific purpose: tunable, conical broadband, RFI/EMI suppression, air coils);
  * suppliers are Preferred / Approved / Candidate / Restricted (avoid, not approved);
  * ASI (VH) per package for LD:  0402 multilayer chip -> T,  0603 wirewound -> T,
    other LD packages -> O,  NRND / legacy parts -> V.  LL has no package table -> O;
  * Ag/Pd terminations are a restricted technology (not allowed);
  * advice: downsize where possible (no production restriction from 0402 up), E12 values.
"""
import math
import re

from asi_rules import T, O, U, LABEL, _val
from categories_l import AML, CATEGORY_CG, L_CG_OPTIONS

SOURCE = "LD/LL standardization rule (CI 03.00, 18 Jul 2024)"

# ---------------------------------------------------------------- manufacturer
def _rx(word):
    return rf"(?<![a-z]){re.escape(word)}(?![a-z])"


def _hits(words, text):
    return sum(len(re.findall(_rx(w), text, flags=re.I)) for w in words)


# well-known inductor makers that are NOT on the AML: detected so the AI cannot swap them for an AML name
OTHER_MANUFACTURERS = {
    "Bourns Inc.": ["bourns"],
    "Laird Technologies": ["laird"],
    "Fair-Rite Products Corp.": ["fair-rite", "fair rite"],
    "Taiyo Yuden Co., Ltd.": ["taiyo yuden"],
    "Sumida Corporation": ["sumida"],
    "Abracon LLC": ["abracon"],
    "Eaton (Coiltronics)": ["coiltronics", "eaton"],
    "Pulse Electronics": ["pulse electronics", "pulseelectronics"],
    "KEMET Corporation": ["kemet"],
    "Panasonic Corporation": ["panasonic"],
    "Bel Fuse Inc.": ["bel fuse", "belfuse"],
    "Chilisin Electronics": ["chilisin"],
    "Samsung Electro-Mechanics": ["samsung electro-mechanics", "samsung electro mechanics"],
    "Johanson Technology": ["johanson"],
    "Kyocera AVX Components Ltd.": ["kyocera avx", "avx corporation"],
    "Littelfuse, Inc.": ["littelfuse"],
    "Schaffner": ["schaffner"],
    "Schurter": ["schurter"],
    "Parker Chomerics": ["chomerics"],
    "Arnold Magnetic Technologies": ["arnold magnetic"],
}


def _mfr_score(words, names, head, text):
    return 6 * _hits(words, names) + 3 * _hits(words, head) + min(_hits(words, text), 10)


def detect_manufacturer_l(pdf_text, file_names=()):
    """Canonical manufacturer name (AML name when on the AML), or None when the evidence is weak."""
    names, head = " ".join(file_names), pdf_text[:3000]
    best, best_score = None, 0
    candidates = [(c, w) for c, (w, _cgs) in AML.items()] + list(OTHER_MANUFACTURERS.items())
    for canon, words in candidates:
        sc = _mfr_score(words, names, head, pdf_text)
        if sc > best_score:
            best, best_score = canon, sc
    return best if best_score >= 8 else None


def resolve_manufacturer_l(ai_name, pdf_text, file_names=()):
    """Strong text evidence wins. Otherwise keep the AI answer, but reject an AML name the datasheet never mentions
    (the AI tends to pick a name from the list it was given)."""
    found = detect_manufacturer_l(pdf_text, file_names)
    if found:
        return found
    canon, _cgs = aml_entry(ai_name)
    if canon:
        words = AML[canon][0]
        if _mfr_score(words, " ".join(file_names), pdf_text[:3000], pdf_text) == 0:
            return "Unknown"
    return ai_name


def aml_entry(manufacturer):
    m = str(manufacturer).lower()
    for canon, (words, cgs) in AML.items():
        if canon.lower() == m or any(re.search(_rx(w), m) for w in words):
            return canon, cgs
    return None, ()


# ------------------------------------------------------------- commodity group
IRON_POWDER = ("eisen-pulver", "iron powder", "carbonyl")
STRIP_WOUND = ("strip-wound", "strip wound", "tape-wound", "tape wound", "nanocrystalline", "amorphous", "sheet metal")


def determine_cg_l(category, extracted_data, pdf_text, manufacturer):
    """Return (code, evidence). The AI answer is kept when it fits the category; strong evidence overrides it."""
    allowed, default = CATEGORY_CG[category]
    raw = extracted_data.pop("Commodity Group", "Unknown")
    if isinstance(raw, dict):
        raw = raw.get("value", "Unknown")
    ai = str(raw).strip().upper()[:2]
    func = _val(extracted_data, "Function").upper()
    cons = _val(extracted_data, "Construction").lower()
    text = pdf_text.lower()

    if category in ("Coil", "Inductance"):
        if func.startswith("AIR CORE") or cons == "air core" or re.search(r"air[\s-]?core", text[:3000]):
            return "LL", "Air-core coil -> LL"
        if ai == "LL":
            return "LD", "AI chose LL but no air core found: LD (choke, coil or filter without air-core coils)"
    if category == "Transducer / Transformer" and (func == "MAINS TRANSFORMER" or "mains transformer" in text[:3000]):
        return "LT", "Mains transformer -> LT"
    if category == "Cores":
        mat = _val(extracted_data, "Material").lower()
        if any(w in mat or w in text[:3000] for w in IRON_POWDER):
            return "LK", "Iron powder / carbonyl iron core -> LK"
        if any(w in text[:3000] for w in STRIP_WOUND):
            return "LB", "Strip-wound / sheet metal core -> LB"
    if category == "Accessories R L C" and func in ("ABSCHIRMBECHER", "ABSCHIRMTOPF", "ISOLIERBECHER"):
        return "LS", "Shielding / screening can -> LS"

    if ai in allowed:
        return ai, f"AI choice {ai} fits the category"
    # manufacturer AML as a tie-breaker inside the allowed groups
    _canon, cgs = aml_entry(manufacturer)
    fit = [c for c in cgs if c in allowed]
    if len(fit) == 1:
        return fit[0], f"Only group of {manufacturer} on the AML for this category"
    return default, f"Default group for {category}"


def cg_label(code):
    return f"{code} ({L_CG_OPTIONS[code]})" if code in L_CG_OPTIONS else str(code)


def aml_check(manufacturer, cg_code):
    """ASI-style check row for the approved manufacturer list (information only)."""
    canon, cgs = aml_entry(manufacturer)
    if canon and cg_code in cgs:
        return {"Parameter": "Approved manufacturer list", "Value": f"{canon} · {cg_code}", "Rating": None,
                "Note": f"On the AML for {cg_code}"}, None
    if canon:
        return ({"Parameter": "Approved manufacturer list", "Value": f"{canon} · {cg_code}", "Rating": None,
                 "Note": f"On the AML only for {', '.join(cgs)}"},
                f"{canon} is not on the approved manufacturer list for {cg_code} (listed for {', '.join(cgs)}).")
    return ({"Parameter": "Approved manufacturer list", "Value": f"{manufacturer} · {cg_code}", "Rating": None,
             "Note": "Not on the AML"},
            f"{manufacturer} is not on the approved manufacturer list for L* parts.")


# ------------------------------------------------------------------ suppliers
# (keyword, display name, technology, status, distributor, note)
SUPPLIERS = [
    ("murata", "Murata", ("GP", "SP"), "Preferred", "direct", ""),
    ("coilcraft", "Coilcraft", ("SP",), "Approved", "direct", "for GP, please use Murata where possible"),
    ("neosid", "Neosid", ("SP",), "Approved", "direct", ""),
    ("piconics", "Piconics", ("SP",), "Approved", "direct / Tactron", "conical inductors"),
    ("tdk", "TDK / Epcos", ("GP", "SP"), "Approved", "s.m.a.e. / direct", ""),
    ("epcos", "TDK / Epcos", ("GP", "SP"), "Approved", "s.m.a.e. / direct", ""),
    ("würth", "Würth eiSos", ("GP",), "Approved", "direct", ""),
    ("wurth", "Würth eiSos", ("GP",), "Approved", "direct", ""),
    ("vishay", "Vishay", ("GP",), "Candidate", "-",
     "LD only; joint approval of Procurement, Quality, component engineer and procurement engineer required; "
     "check the supply situation with Procurement"),
    ("sunlord", "Sunlord", ("GP", "SP"), "Avoid", "direct", "candidate status withdrawn (no business for several years)"),
    ("delevan", "API Delevan", ("GP",), "Not approved", "TTI", "several supply issues and quality problems"),
]
SUBGROUP_LABEL = {"GP": "GP - General purpose / catalogue parts", "SP": "SP - Specific purpose / others"}
SP_FUNCTIONS = ("AIR CORE INDUCTOR", "AIR CORE INDUCTOR TUNABLE", "BROADBAND CONICAL INDUCTOR", "TUNABLE")


def supplier_of(manufacturer):
    m = str(manufacturer).lower()
    for kw, name, tech, status, dist, note in SUPPLIERS:
        if re.search(_rx(kw), m):
            return name, tech, status, dist, note
    return None


def subgroup_of(cg_code, category, func, cons):
    if (cg_code == "LL" or func in SP_FUNCTIONS or cons == "air core"
            or category == "EMI-Filter (Feedthrough-, Mains-)"):
        return "SP"
    return "GP"


# ----------------------------------------------------------------- parameters
E12 = (1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2)
E12_CLOSEST_E96 = (1.00, 1.21, 1.50, 1.82, 2.21, 2.74, 3.32, 3.92, 4.75, 5.62, 6.81, 8.25)  # as printed in the rule
AGPD = re.compile(r"ag\s*/\s*pd|agpd|silver[\s-]*palladium|\bag-pd\b", re.I)


def _float(s):
    try:
        return float(re.sub(r"[^0-9eE+.\-]", "", str(s)))
    except ValueError:
        return None


def parse_l_package(s):
    m = re.search(r"(01005|\d{4})", str(s))
    return m.group(1) if m else None


def construction_of(func, cons):
    if func == "MULTILAYER CHIP" or cons == "multilayer":
        return "Multilayer"
    if func == "WIRE WOUND" or cons == "wirewound":
        return "Wirewound"
    if cons in ("thin film", "air core", "other"):
        return cons.capitalize() if cons != "air core" else "Air core"
    return None


def mantissa(x):
    if not x or x <= 0:
        return None
    return round(x / 10 ** math.floor(math.log10(x) + 1e-12), 3)


def _in_series(m, series):
    return m is not None and any(abs(m - v) < 1e-3 for v in series)


# ------------------------------------------------------------------- the rule
def asi_from_extraction_l(extracted_data, manufacturer_text, cg_code, category):
    func = _val(extracted_data, "Function").upper()
    cons_raw = _val(extracted_data, "Construction").lower()
    sub = subgroup_of(cg_code, category, func, cons_raw)
    checks, flags = [], []

    # 1) supplier
    sup = supplier_of(manufacturer_text)
    if sup is None:
        sup_rating = U
        checks.append({"Parameter": "Supplier", "Value": str(manufacturer_text), "Rating": U,
                       "Note": "Not listed in the LD/LL rule: contact Procurement Engineering"})
        flags.append("Supplier is not listed in the LD/LL rule: contact Procurement Engineering.")
    else:
        name, tech, status, dist, note = sup
        if status in ("Preferred", "Approved"):
            if sub in tech:
                sup_rating, text = T, f"{status} supplier for {sub} (distributor: {dist})"
            else:
                sup_rating = O
                text = f"{status} for {'/'.join(tech)} only" + (f": {note}" if note else "")
                flags.append(f"{name} is {status.lower()} for {'/'.join(tech)} parts; this part is {sub}. "
                             + (note[0].upper() + note[1:] + "." if note else "Give priority to suppliers approved for this sub-group."))
        elif status == "Candidate":
            ok = sub in tech and cg_code == "LD"
            sup_rating = O if ok else U
            text = f"Candidate supplier: {note}" if ok else f"Candidate for LD / GP only: {note}"
            flags.append(f"{name} is a candidate supplier: {note}.")
        else:
            sup_rating = U
            text = f"{status}: {note}"
            flags.append(f"{name} is a restricted supplier ({status.lower()}): {note}.")
        checks.append({"Parameter": "Supplier", "Value": f"{name} · {SUBGROUP_LABEL[sub]}", "Rating": sup_rating,
                       "Note": text})

    # 2) package / construction (ASI table: LD only)
    pkg = parse_l_package(_val(extracted_data, "Package Type"))
    con = construction_of(func, cons_raw)
    if cg_code == "LL":
        pkg_rating, note = O, "No package table for LL: regular part = ASI O"
    elif pkg == "0402":
        if con == "Multilayer":
            pkg_rating, note = T, "VH T: multilayer chip inductor in 0402"
        else:
            pkg_rating, note = O, "VH T applies to multilayer chip inductors in 0402 only; this construction is O"
            if con is None:
                flags.append("Construction not identified: a 0402 multilayer chip inductor would be ASI T.")
    elif pkg == "0603":
        if con == "Wirewound":
            pkg_rating, note = T, "VH T: wirewound inductor in 0603"
        else:
            pkg_rating, note = O, "VH T applies to wirewound inductors in 0603 only; this construction is O"
            if con is None:
                flags.append("Construction not identified: a 0603 wirewound inductor would be ASI T.")
    elif pkg in ("0201", "01005"):
        pkg_rating, note = O, "VH O (smaller than 0402: design rules / production restrictions apply)"
        flags.append(f"Case size {pkg} is smaller than 0402: respect the design rules / production restrictions.")
    else:
        pkg_rating, note = O, "Other packages: VH O"
    checks.append({"Parameter": "Package / construction",
                   "Value": f"{pkg or _val(extracted_data, 'Package Type')} · {con or 'construction not stated'}",
                   "Rating": pkg_rating, "Note": note})

    # 3) lifecycle (legacy parts -> V)
    life = _val(extracted_data, "Lifecycle Status")
    if life.upper().startswith(("NRND", "DISCONTINUED", "OBSOLETE", "EOL")):
        checks.append({"Parameter": "Lifecycle", "Value": life, "Rating": U,
                       "Note": "VH V: not recommended for new design by the manufacturer / legacy part"})
    else:
        checks.append({"Parameter": "Lifecycle", "Value": life, "Rating": None,
                       "Note": "No NRND / discontinued note found in the datasheet; check the supply situation"})

    # 4) restricted technology: Ag/Pd termination
    surface = " ".join(_val(extracted_data, k) for k in ("Surface", "Terminal Plating", "Terminal Base"))
    if AGPD.search(surface) or re.search(r"\bAG\s*/\s*PD\b", surface.upper()):
        checks.append({"Parameter": "Termination surface", "Value": surface.strip(), "Rating": U,
                       "Note": "Restricted technology: Ag/Pd surface shows bad soldering results and is not allowed"})
        flags.append("Ag/Pd termination surface is a restricted technology (not allowed).")

    # 5) value series (advice only)
    ind = _float(_val(extracted_data, "Inductance (H)"))
    m = mantissa(ind) if ind else None
    if m is not None:
        on = _in_series(m, E12) or _in_series(m, E12_CLOSEST_E96)
        checks.append({"Parameter": "Value series", "Value": f"{ind:g} H", "Rating": None,
                       "Note": "E12 value" if on else "Not an E12 value: stick to the E12 series whenever possible"})

    # 6) approved manufacturer list (information)
    row, flag = aml_check(manufacturer_text, cg_code)
    checks.append(row)
    if flag:
        flags.append(flag)

    rated = [c["Rating"] for c in checks if c["Rating"] is not None]
    overall = max(rated) if rated else O
    worst = [c["Parameter"] for c in checks if c["Rating"] == overall]
    summary = ("Recommended package / construction from an approved supplier." if overall == T
               else "Regular part: ASI O." if overall == O
               else "Worst-rated parameter(s): " + ", ".join(worst))
    return {"overall": overall, "label": LABEL[overall], "summary": summary, "subgroup": SUBGROUP_LABEL[sub],
            "checks": checks, "flags": flags, "source": SOURCE,
            "l": {"sub": sub, "cg": cg_code, "pkg": pkg, "construction": con}}


def no_rule_l(manufacturer_text, cg_code):
    row, flag = aml_check(manufacturer_text, cg_code)
    return {"overall": None, "label": "No rule",
            "summary": f"No standardization rule is loaded for {cg_code} (rules exist for LD and LL only).",
            "subgroup": "-", "checks": [row], "flags": [flag] if flag else [],
            "source": "Approved manufacturer list only"}


# --------------------------------------------------------------- alternatives
def render_l_alternatives(asi_result):
    import streamlit as st
    from ui_style import callout
    spec = asi_result.get("l")
    if not spec:
        callout("info", "No LD/LL specification available.")
        return
    if asi_result["overall"] == T:
        callout("success", "Original part is ASI T: recommended package / construction from an approved supplier.")
        return
    if asi_result["overall"] == O and spec["cg"] == "LD":
        callout("info", "Original part is ASI O (approved). ASI T applies only to 0402 multilayer chip inductors "
                        "and 0603 wirewound inductors: consider them if the design allows.")
    elif asi_result["overall"] == O:
        callout("info", "Original part is ASI O (approved). LL has no ASI T package.")
    else:
        callout("warning", "Original part is ASI U/V: choose a part from a preferred / approved supplier below.")

    sub = spec["sub"]
    rows, seen = [], set()
    for _kw, name, tech, status, dist, note in SUPPLIERS:
        if status in ("Preferred", "Approved") and sub in tech and name not in seen:
            seen.add(name)
            rows.append((name, status, dist, note or "-"))
    rows.sort(key=lambda r: 0 if r[1] == "Preferred" else 1)
    st.subheader(f"Preferred / approved suppliers · {SUBGROUP_LABEL[sub]}")
    st.table({"Manufacturer": [r[0] for r in rows], "Status": [r[1] for r in rows],
              "Distributor": [r[2] for r in rows], "Note": [r[3] for r in rows]})
    st.caption("No DMS duplicate check for L*: search DMS manually for an existing material number.")
