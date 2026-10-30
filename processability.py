"""
Washability / Varnishability codes for the Processability tab.

Source: PAD-M "Specifications for classification of washability and varnishability"
(3575.5490.00, CI 03.00, 2017-12-19), section 5.1 Table 5.1-1 (standard values per commodity group,
standard cleaning agent Vigon SC202) and section 4.1.1 (new materials default to K).

The code letters R, C, D-J, T-V, O (washability) and A, R, S (varnishability) mean R&S tested the part
in-house. Only Quality Management sets them, so the app only ever writes W, K, P, N / L, K, P, N.
"""

import re

SOURCE = "PAD-M 3575.5490.00 Tab. 5.1-1"

# commodity group -> (washability, varnishability); R* groups only
TABLE = {
    "RG": ("W", "L"),   # metal film / glaze / oxide / wire-wound / carbon, fixed
    "RN": ("W", "L"),   # resistor networks
    "RT": ("W", "K"),   # attenuators, terminating resistors
    "RK": ("K", "K"),   # PTC, NTC, varistors
    "RR": ("K", "K"),   # wire-wound resistors, variable
    "RS": ("K", "K"),   # non-wire-wound resistors
    "RX": ("N", "N"),   # unencapsulated chips
    "RZ": ("N", "N"),   # accessories for resistors
}
DEFAULT = ("K", "K")    # section 4.1.1: new material = "K - workability unknown"

WASH_MEANING = {
    "W": "Approved: no R&S test (PAD specs / manufacturer info), cleaning agent Vigon SC202, standard drying",
    "O": "Approved: no R&S test, Vigon SC202, FA+ incompatible, standard drying",
    "R": "Tested at R&S: Vigon SC202, FA+ not tested, standard drying",
    "C": "Tested at R&S: Vigon SC202, FA+ incompatible, standard drying",
    "D": "Tested at R&S: Vigon SC202 and FA+, standard drying",
    "E": "Tested at R&S: Vigon SC202, FA+ not tested, extra drying 5 h at 80 °C, no vacuum",
    "F": "Tested at R&S: Vigon SC202, FA+ incompatible, extra drying 5 h at 80 °C, no vacuum",
    "G": "Tested at R&S: Vigon SC202 and FA+, extra drying 5 h at 80 °C, no vacuum",
    "H": "Tested at R&S: Vigon SC202, FA+ not tested, extra drying 2 h at 80 °C / 200 mbar or 5 h at 80 °C",
    "I": "Tested at R&S: Vigon SC202, FA+ incompatible, extra drying 2 h at 80 °C / 200 mbar or 5 h at 80 °C",
    "J": "Tested at R&S: Vigon SC202 and FA+, extra drying 2 h at 80 °C / 200 mbar or 5 h at 80 °C",
    "T": "Tested at R&S: Vigon SC202, FA+ not tested, extra drying 5 h at 80 °C / 200 mbar",
    "U": "Tested at R&S: Vigon SC202, FA+ incompatible, extra drying 5 h at 80 °C / 200 mbar",
    "V": "Tested at R&S: Vigon SC202 and FA+, extra drying 5 h at 80 °C / 200 mbar",
    "K": "Not approved: workability unknown",
    "P": "Not approved: workability unknown but required, testing necessary",
    "N": "Not washable",
}
VARN_MEANING = {
    "L": "Approved: varnishability is given",
    "A": "Approved: varnishability with masking is given",
    "R": "Tested at R&S: varnishability given",
    "S": "Tested at R&S: varnishability with masking given",
    "K": "Not approved: workability unknown",
    "P": "Not approved: workability unknown but required, testing necessary",
    "N": "Not varnishable",
}
APPROVED_WASH = set("WORCDEFGHIJTUV")
APPROVED_VARN = set("LARS")


# ===================================================================== helpers
def _val(ed, key):
    item = ed.get(key)
    v = item.get("value", "N/A") if isinstance(item, dict) else item
    return "N/A" if v is None else str(v).strip()


def _page(ed, key):
    item = ed.get(key)
    return str(item.get("page", "N/A")) if isinstance(item, dict) else "N/A"


def _num(v):
    m = re.search(r"-?\d+(?:\.\d+)?", str(v or "").replace(",", "."))
    return float(m.group()) if m else None


def _datasheet_says(extracted_data, key):
    v = _val(extracted_data, key).lower()
    if v.startswith("yes"):
        return "Yes"
    if v.startswith("no"):
        return "No"
    return None


# ============================================================ solder temperature
# the only options in the DMS drop-down (St. / Alt. / Rep. Solder Temp.)
SOLDER_TEMPS = {
    "leadfree": [(245, "Celsius soldering leadfree"), (260, "Celsius soldering leadfree")],
    "leaded":   [(245, "Celsius soldering leaded")],
    "manual":   [(185, "Celsius manually soldering"), (215, "Celsius manually soldering")],
}


def pick_solder_temp(temp, method, solder_type):
    """Choose the DMS option for the datasheet temperature, rounding UP to the next highest list value.
    Returns (value, evidence, warning)."""
    m = (method or "").lower()
    if not m or m == "n/a" or "no soldering" in m:
        return "N/A", "No soldering method for this field, so no temperature", None
    if temp is None:
        return "N/A", "The datasheet gives no soldering temperature for this method", None
    if "manual" in m and temp <= 215:
        group, label = SOLDER_TEMPS["manual"], "manual soldering list"
    elif solder_type == "Leaded":
        group, label = SOLDER_TEMPS["leaded"], "leaded list"
    else:
        group, label = SOLDER_TEMPS["leadfree"], "lead-free list" + (
            " (manual soldering above 215 °C: the list has no higher manual option)" if "manual" in m else "")
    chosen = next(((t, txt) for t, txt in group if t >= temp), group[-1])
    ev = f"Datasheet {temp:g} °C -> {chosen[0]} °C from the {label}"
    warn = None
    if chosen[0] > temp:
        ev += " (rounded up to the next highest value)"
        warn = f"{method}: datasheet {temp:g} °C was rounded up to {chosen[0]} °C."
    elif chosen[0] < temp:
        ev += " (datasheet value is above the highest list value)"
        warn = f"{method}: datasheet {temp:g} °C is above the highest option ({chosen[0]} °C), so {chosen[0]} °C is shown."
    return f"{chosen[0]} {chosen[1]}", ev, warn


# ============================================================ reflow profile
# Standard Reflow Profile document: peak temperature Tp and time above liquidus tL
STANDARD_PROFILE = {"leadfree": (245, 60, 217), "leaded": (235, 120, 180)}   # (min Tp, min tL, TL)


def reflow_profile(ed):
    """Return (value, evidence, warning) for 'Recommended Reflow Profil'."""
    mount = _val(ed, "Kind of Mounting").upper()
    methods = " ".join(_val(ed, k).lower() for k in
                       ("St. Solder (Standard Solder)", "Alt. Solder (Alternate Solder)", "Rep. Solder (Repair Solder)"))
    if not (mount.startswith("SMT") or mount.startswith("THR") or "reflow" in methods):
        return "N/A", "Component is not reflow soldered", None

    tp = _num(_val(ed, "Reflow Peak Temp (°C)"))
    if tp is None:
        tp = _num(_val(ed, "Max Reflow Temp (°C)"))
    tl = _num(_val(ed, "Time Above Liquidus (s)"))
    stype = _val(ed, "Solder Type")
    liq = _num(_val(ed, "Liquidus Temp (°C)"))
    leaded = stype == "Leaded" or (stype != "Lead-free" and liq is not None and liq <= 200)
    basis = "leaded" if leaded else "leadfree"
    need_tp, need_tl, ref_liq = STANDARD_PROFILE[basis]
    name = "Leaded" if leaded else "Lead-free"
    pending_warn = ("Reflow profile information is missing: contact the manufacturer for the peak temperature and the "
                    "time above liquidus. The introduction can continue.")

    if tp is None:
        return "Information pending", f"{name} basis: no peak temperature (Tp) in the datasheet", pending_warn
    if tp < need_tp:
        return ("Non-Standard", f"{name} basis: Tp {tp:g} °C is below the required {need_tp} °C",
                "Non-Standard parts are reported by production planning to the technologists (e-sample order).")
    if tl is None:
        return ("Information pending",
                f"{name} basis: Tp {tp:g} °C is enough (min {need_tp} °C) but no time above liquidus is stated", pending_warn)
    if tl < need_tl:
        return ("Non-Standard", f"{name} basis: Tp {tp:g} °C ok, but time above liquidus {tl:g} s is below {need_tl} s (TL {ref_liq} °C)",
                "Non-Standard parts are reported by production planning to the technologists (e-sample order).")
    return ("Standard", f"{name} basis: Tp {tp:g} °C (min {need_tp} °C), time above liquidus {tl:g} s (min {need_tl} s at TL {ref_liq} °C)", None)


# ================================================================== ESD (HBM)
ESD_CLASSES = [("0Z", 0, 50, "< 50 V"), ("0A", 50, 125, "50 to < 125 V"), ("0B", 125, 250, "125 to < 250 V"),
               ("1A", 250, 500, "250 to < 500 V"), ("1B", 500, 1000, "500 to < 1000 V"),
               ("1C", 1000, 2000, "1000 to < 2000 V"), ("2", 2000, 4000, "2000 to < 4000 V"),
               ("3A", 4000, 8000, "4000 to < 8000 V"), ("3B", 8000, float("inf"), ">= 8000 V")]


def esd_class(raw):
    s = str(raw or "").strip()
    if s.upper() in ("", "N/A"):
        return "N/A", "The datasheet gives no HBM ESD rating", None
    for code, lo, hi, text in ESD_CLASSES:
        if s.upper() == code:
            return f"{code} – {text}", f"ESD class {code} stated in the datasheet", None
    v = _num(s)
    if v is None:
        return "N/A", f"Could not read an ESD value from '{s}'", None
    if "kv" in s.lower():
        v *= 1000
    for code, lo, hi, text in ESD_CLASSES:
        if lo <= v < hi:
            return f"{code} – {text}", f"HBM withstand voltage {v:g} V falls in class {code}", None
    return "N/A", f"HBM value {v:g} V is outside the class list", None


# ================================================= Increased Reflow Profile (Yes / No)
# packages that give "Yes" in the Standard Reflow Profile document
INCREASED_EXACT = ["XSEAM40X10P127", "BNC-BU-WIN-EB0806-01-0X", "80QSB2RGP80MTY", "XNCON-92N-50-0-6-111NY",
                   "BIG-FOOT", "TR-4P-PAYTON-55288", "PCB-PORT_RIGHT-ANGLE-99S2A8-40M", "XSMA-92-50-0-28",
                   "KLEMME-20P-WAGO-218-120", "SO8A25P375", "SO10A25P375", "LD-23.5X25.3"]


def increased_reflow(*texts):
    blob = " ".join(str(t or "") for t in texts).upper()
    m = re.search(r"BGA(\d{4})P100", blob)
    if m and int(m.group(1)) >= 1600:
        return "Y – Yes", f"Package BGA{m.group(1)}P100 (1600 pins or more) is on the PAD list"
    m = re.search(r"\bXD(\d{2})B", blob)
    if m and int(m.group(1)) >= 9:
        return "Y – Yes", f"Package XD{m.group(1)}B (Sub-D plug from 9 pins) is on the PAD list"
    for p in INCREASED_EXACT:
        if p in blob:
            return "Y – Yes", f"Package {p} is on the PAD list"
    if re.search(r"\bKUEHLPLATTE-|\bPLATE\b|\bBUSBAR\b", blob):
        return "Y – Yes", "Heat spreader / bus bar package is on the PAD list"
    return "N – No", "Package is not on the 'Yes' list of the Standard Reflow Profile document"


# =================================================================== main entry
def apply_processability(extracted_data, cg_code, mpn="", designation=""):
    """Fill Washability / Varnishability (PAD-M), solder temperatures, reflow profile, ESD,
    increased reflow profile and terminal data. Returns warnings to show under the tab."""
    listed = cg_code in TABLE
    wash, varn = TABLE.get(cg_code, DEFAULT)
    src = (f"{SOURCE}: {cg_code} = {wash} / {varn}" if listed
           else f"PAD-M 3575.5490.00 4.1.1: group {cg_code} not in the table, default K / K")
    warnings = []

    for key, letter, meaning, approved, bad_word in (
            ("Washability", wash, WASH_MEANING, APPROVED_WASH, "washable"),
            ("Varnishability", varn, VARN_MEANING, APPROVED_VARN, "varnishable")):
        says = _datasheet_says(extracted_data, key)
        evidence = src + (f"; datasheet says: {says}" if says else "")
        extracted_data[key] = {"value": f"{letter} – {meaning[letter]}", "evidence": evidence, "page": "N/A"}
        if says == "No" and letter in approved:
            warnings.append(f"The datasheet says the part is not {bad_word}, but the PAD-M standard value for "
                            f"{cg_code} is {letter}. The standard value is kept: ask Quality Management to review "
                            f"(N is set only after a test).")
        elif says == "Yes" and letter == "N":
            warnings.append(f"The datasheet says the part is {bad_word}, but the PAD-M standard value for "
                            f"{cg_code} is N. The standard value is kept: ask Quality Management to review.")

    # solder temperatures: DMS list only, rounded up
    solder_type = _val(extracted_data, "Solder Type")
    for disp, mkey, tkey in (("St. Solder Temp.", "St. Solder (Standard Solder)", "St. Solder Temp (°C)"),
                             ("Alt. Solder Temp.", "Alt. Solder (Alternate Solder)", "Alt. Solder Temp (°C)"),
                             ("Rep. Solder Temp.", "Rep. Solder (Repair Solder)", "Rep. Solder Temp (°C)")):
        method = _val(extracted_data, mkey)
        temp = _num(_val(extracted_data, tkey))
        if temp is None and disp.startswith("St.") and "reflow" in method.lower():
            temp = _num(_val(extracted_data, "Max Reflow Temp (°C)"))
        value, ev, warn = pick_solder_temp(temp, method, solder_type)
        extracted_data[disp] = {"value": value, "evidence": ev, "page": _page(extracted_data, tkey)}
        if warn:
            warnings.append(warn)

    # recommended reflow profile
    value, ev, warn = reflow_profile(extracted_data)
    extracted_data["Recommended Reflow Profil"] = {"value": value, "evidence": ev, "page": "N/A"}
    if warn:
        warnings.append(warn)

    # increased reflow profile (Yes / No)
    pkg_text = _val(extracted_data, "Package Type")
    value, ev = increased_reflow(mpn, pkg_text, designation)
    extracted_data["Increased Reflow Profile"] = {
        "value": value, "evidence": ev + ". Normally maintained only after introduction.", "page": "N/A"}

    # ESD (HBM class)
    value, ev, _ = esd_class(_val(extracted_data, "ESD HBM (V)"))
    extracted_data["ESD"] = {"value": value, "evidence": ev, "page": _page(extracted_data, "ESD HBM (V)")}

    # terminal data: free text from the datasheet
    for key in ("Terminal Base", "Terminal Plating"):
        if key not in extracted_data:
            extracted_data[key] = {"value": "N/A", "evidence": "N/A", "page": "N/A"}
    return warnings
