"""
C* (capacitor) DMS categories: Techn.Parameter fields, pick lists, extraction rules,
commodity groups, manufacturer list and detection.

Same structure as categories_l.py. Only the Techn.Parameter tab differs per category;
Top, Library and Processability stay the same. The Techn.Parameter lists are the ones of
the former standalone "C* Datasheet Analyzer".

"EMI-Filter (Feedthrough-, Mains-)" is the same DMS category as in L*: its fields, lists and
rules are shared with categories_l.py, so the two commodities cannot drift apart.

Pick-list rule (all categories): use the DMS list value when one fits; only when
nothing fits, write a short free-text value.
"""
import re

from categories_l import (EMI_FUNCTION, EMI_FILTER_TYPE, EMI_PACKAGE, RULES as L_RULES, TECHN as L_TECHN,
                          R_WORDS, L_WORDS, _score)

CAP_FIXED = "Capacitors fixed"
EMI = "EMI-Filter (Feedthrough-, Mains-)"

# ------------------------------------------------------------ commodity groups
C_CG_OPTIONS = {
    "CB": "capacitor - bypass or feed through",
    "CC": "capacitor - miniature ceramic",
    "CD": "capacitor - variable",
    "CE": "capacitor - electrolytic",
    "CG": "capacitor - mica",
    "CH": "capacitor - barrier layer",
    "CK": "capacitor - film",
    "CL": "capacitor - ceramic power",
    "CM": "capacitor - MP",
    "CN": "capacitor - networks",
    "CP": "capacitor - paper",
    "CS": "capacitor - suppression",
    "CT": "capacitor - trimmer",
    "CV": "capacitor - vacuum",
    "CX": "capacitor - uncapsulated chip",
}

# category -> (commodity groups allowed for it, default group)
CATEGORY_CG = {
    "Capacitors fixed": (("CC", "CK", "CG", "CH", "CL", "CM", "CN", "CP", "CS", "CV", "CX"), "CC"),
    "Capacitor Electrolyt": (("CE",), "CE"),
    "Capacitor mech. adjustable": (("CT", "CD"), "CT"),
    "Capacitor electr. adjustable": (("CD",), "CD"),
    EMI: (("CB", "CS"), "CB"),
}

# manufacturer list of the former C* analyzer (returned exactly as written when it is the maker)
MANUFACTURERS_C = {
    "binder mpe GmbH": ["binder mpe"],
    "Dalicap Technology Co., Ltd.": ["dalicap"],
    "ebm-papst (Mulfingen) GmbH & Co. KG": ["ebm-papst", "ebmpapst"],
    "Electronicon Kiondensatoren GmbH": ["electronicon"],
    "Exxelia Group": ["exxelia", "temex"],
    "HIGH ENERGY Corp.": ["high energy corp"],
    "Holy Stone Enterprise Co., Ltd.": ["holy stone", "holystone"],
    "Richard Jahre GmbH": ["richard jahre"],
    "Johanson Precision Corporation": ["johanson", "jdi"],
    "K+B elektromechanische": ["k+b elektromechanische"],
    "Knowles Electronics, LLC": ["knowles", "novacap", "dielectric laboratories", "dli"],
    "Kyocera AVX Components Ltd.": ["kyocera avx", "avx corporation", "kyocera", "avx", "american technical ceramics"],
    "MACOM Technology Solutions Holdings": ["macom", "metelics"],
    "Murata Manufacturing Co., Ltd": ["murata"],
    "Nichicon Corporation": ["nichicon"],
    "NIPPON CHEMI-CON CORPORATION": ["chemi-con", "chemicon", "nippon chemi"],
    "OXLEY DEVELOPMENTS": ["oxley"],
    "Panasonic Corporation": ["panasonic"],
    "Presidio Components Inc.": ["presidio"],
    "PSA Passive System Alliance Group": ["passive system alliance"],
    "Rubycon Corporation": ["rubycon"],
    "Samsung Group": ["samsung"],
    "Schlund GmbH": ["schlund"],
    "Spectrum Control, Inc.": ["spectrum control"],
    "Syfer Technology Ltd.": ["syfer"],
    "Taiyo Yuden Co., Ltd.": ["taiyo yuden"],
    "TDK Corporation": ["tdk", "epcos"],
    "TE Connectivity Ltd.": ["te connectivity"],
    "Tronser GmbH": ["tronser"],
    "CTS Corporation": ["cts corporation"],
    "Vishay Intertechnology, Inc.": ["vishay", "sprague"],
    "Voltronics Corp.": ["voltronics"],
    "WIMA Spezialvertrieb elektronische": ["wima"],
    "Yageo Corporation": ["yageo"],
}

# ------------------------------------------------------------------ pick lists
DESCRIPTION = [(v, "") for v in (
    "KERAMIK-P90", "KERAMIK-P100", "KERAMIK-C0G", "KERAMIK-U2J", "KERAMIK-SL", "KERAMIK-X7R", "KERAMIK-X7S",
    "KERAMIK-X7T", "KERAMIK-X6S", "KERAMIK-X5S", "KERAMIK-X5R", "KERAMIK-Y5V", "KERAMIK-Y5U", "KERAMIK-Z5U",
    "KERAMIK-Y5S", "SILICON-C0G", "SILICON-C0H", "FOLIE*", "SILICON CAPACITOR", "FOLIE-PPS", "FOLIE-PEN",
    "FOLIE-PET", "FOLIE-PP", "FOLIE-PML", "GLIMMER", "METALLPAPIER")]
SURFACE = [("SN", "tin / matte tin / Zinn"), ("AU", "gold"), ("AG-PD", "silver-palladium"),
           ("AG-SN", "silver-tin")]
ADJUST_FROM = [("OBEN", "top adjust"), ("SEITE", "side adjust / beside")]
PROCESSING = [("SMD", "surface mount (V-chip / SMD can)"), ("THT", "through-hole (radial / axial / snap-in)")]
C_PACKAGE = [(f"EIA{s}*", "SMD") for s in ("01005", "0201", "0306", "0402", "0505", "0603", "0612", "0709",
                                            "0805", "1111", "1206", "1210", "1808", "1812", "2220", "2225")] + [
    ("*AXIAL*", "axial leaded"), ("*RADIAL*", "radial leaded"), ("*SMD*", "other SMD, e.g. V-chip can")]

PICK_LISTS = {
    "Capacitors fixed": {"Description": DESCRIPTION, "Surface": SURFACE, "Package Type": C_PACKAGE},
    "Capacitor Electrolyt": {"Description": DESCRIPTION, "Package Type": C_PACKAGE,
                             "Processing Technology": PROCESSING},
    "Capacitor mech. adjustable": {"Description": DESCRIPTION, "Adjust from": ADJUST_FROM},
    "Capacitor electr. adjustable": {"Description": DESCRIPTION, "Package Type": C_PACKAGE},
    EMI: {"Function": EMI_FUNCTION, "Filter Type": EMI_FILTER_TYPE, "Package Type": EMI_PACKAGE},
}


def _opts(items):
    return ", ".join(f'"{v}"' + (f" ({m})" if m else "") for v, m in items)


def _pick(key, items, extra=""):
    return (f'            - FOR "{key}": Pick from this DMS list first: {_opts(items)}. '
            f"Return the list value exactly as written. ONLY if nothing fits, return a short free-text value "
            f"in the same style.{(' ' + extra) if extra else ''}\n")


NUM = "as a plain absolute number without units or exponent"
CAP = f"in farad (F) {NUM} (e.g., 100 pF -> 0.0000000001, 100 nF -> 0.0000001, 10 uF -> 0.00001)"
TOL = ('            - FOR "Tolerance (%)": The capacitance tolerance in percent as a plain number without the sign or letter code '
       '(e.g., ±5 % or J -> 5). If the tolerance is given in pF (e.g., ±0.1 pF), convert it to percent of the nominal capacitance and '
       'write the calculation in the "evidence" field.\n')
VOLT = '            - FOR "Voltage (V)": The rated (DC) voltage in volts as a plain number (e.g., 50). For AC-only ratings write e.g. "250VAC".\n'
DESC = _pick("Description", DESCRIPTION,
             "This is the dielectric: map 'NP0' -> 'KERAMIK-C0G', 'X7R' -> 'KERAMIK-X7R', polypropylene -> 'FOLIE-PP', "
             "polyester / PET -> 'FOLIE-PET', mica -> 'GLIMMER', silicon / MIS capacitor -> 'SILICON CAPACITOR' or "
             "'SILICON-C0G'. In the evidence field keep the raw dielectric text from the datasheet.")
PKG = _pick("Package Type", C_PACKAGE,
            "Chip capacitors use the EIA (inch) size code: e.g., size 0603 (1608 metric) -> 'EIA0603*'. A chip size "
            "that is not in the list is written the same way (e.g., 'EIA3838*'). Leaded parts -> '*RADIAL*' or "
            "'*AXIAL*'; SMD cans (V-chip) -> '*SMD*'. This rule replaces the general Package Type rule.")
HEIGHT = '            - FOR "Height (mm)": The nominal height / thickness in mm as a plain number (same value as in the Library tab).\n'

RULES = {
    "Capacitors fixed": (
        f'            - FOR "Capacity (F)": The nominal capacitance {CAP}. If a target MPN is given, use the row of that MPN.\n'
        + TOL + VOLT + PKG + HEIGHT + DESC
        + _pick("Surface", SURFACE,
                "This is the termination / contact surface: tin, matte tin, Sn, Zinn (also Sn over Ni barrier) -> 'SN'; "
                "gold -> 'AU'; silver-palladium -> 'AG-PD'; silver-tin -> 'AG-SN'. 'N/A' if not stated.")
        + '            - FOR "Additional Information": Special features as short free text, e.g. "AEC-Q200", "FLEX TERMINATION", '
          '"SAFETY X1/Y2", "STACKED", "HIGH Q"; "N/A" if none.\n'),
    "Capacitor Electrolyt": (
        f'            - FOR "Capacity (F)": The nominal capacitance {CAP}.\n'
        + TOL + VOLT
        + '            - FOR "Ripple Current": The rated ripple current in amperes as a plain number, and the condition in the '
          'evidence field (e.g., value "0.85", evidence "850 mA rms at 100 kHz, 105 °C").\n'
        + PKG
        + _pick("Processing Technology", PROCESSING)
        + DESC.replace("'SILICON-C0G'.", "'SILICON-C0G'. For electrolytic capacitors nothing in the list fits: write the "
                                         "electrolyte in capitals as free text, e.g. 'ALUMINIUM', 'ALU-POLYMER', "
                                         "'TANTAL', 'TANTAL-POLYMER', 'HYBRID-POLYMER'.")
        + '            - FOR "ESR (Ohm)": The (maximum) equivalent series resistance in ohms as a plain number (e.g., 15 mOhm -> 0.015), '
          'with the test frequency in the evidence field.\n'
        + '            - FOR "Endurance (h/°C)": The load life / endurance written as "<hours>h/<temperature>°C" (e.g., "2000h/105°C").\n'
        + HEIGHT),
    "Capacitor mech. adjustable": (
        f'            - FOR "C-Start (F)" and "C-End (F)": The minimum and maximum capacitance of the adjustment range {CAP}.\n'
        + VOLT
        + _pick("Adjust from", ADJUST_FROM)
        + DESC),
    "Capacitor electr. adjustable": (
        f'            - FOR "C-Start (F)" and "C-End (F)": The minimum and maximum capacitance of the tuning range {CAP}.\n'
        + f'            - FOR "Step size (F)": The capacitance step (LSB) {CAP}, or "N/A".\n'
        + TOL + VOLT + PKG + DESC),
    EMI: L_RULES[EMI],
}

TECHN = {
    "Capacitors fixed": ["Capacity (F)", "Tolerance (%)", "Package Type", "Height (mm)", "Voltage (V)", "Description",
                         "Surface", "Additional Information"],
    "Capacitor Electrolyt": ["Capacity (F)", "Tolerance (%)", "Ripple Current", "Package Type",
                             "Processing Technology", "Description", "Voltage (V)", "ESR (Ohm)", "Endurance (h/°C)",
                             "Height (mm)"],
    "Capacitor mech. adjustable": ["C-Start (F)", "C-End (F)", "Voltage (V)", "Adjust from", "Description"],
    "Capacitor electr. adjustable": ["C-Start (F)", "C-End (F)", "Step size (F)", "Tolerance (%)", "Voltage (V)",
                                     "Package Type", "Description"],
    EMI: L_TECHN[EMI],
}

_BASE = {"Length (mm)", "Width (mm)", "Height (mm)", "Package Type", "Number of Pins"}
# hidden helper keys for the C* rules (not shown in the tabs)
C_HELPER_KEYS = ["Commodity Group", "Category", "Designation", "Lifecycle Status", "Series", "Tolerance_Raw",
                 "Electrolyte Type", "Flexible Termination", "AEC-Q200", "Insulating Sleeve", "Sealing Disk",
                 "Coated", "Stacked"]

CATEGORIES_C = {
    cat: {"cg": None, "techn": techn,
          "extra_keys": [k for k in techn if k not in _BASE] + C_HELPER_KEYS,
          "rules": RULES[cat]}
    for cat, techn in TECHN.items()
}


# ----------------------------------------------------------------- pick-list snap
def _norm(s):
    return re.sub(r"[\s*_\-/]+", "", str(s)).upper()


ALIASES = {"NP0": "KERAMIK-C0G", "COG": "KERAMIK-C0G", "C0G": "KERAMIK-C0G", "X7R": "KERAMIK-X7R",
           "X5R": "KERAMIK-X5R", "X7S": "KERAMIK-X7S", "X6S": "KERAMIK-X6S", "X7T": "KERAMIK-X7T",
           "U2J": "KERAMIK-U2J", "Y5V": "KERAMIK-Y5V", "Z5U": "KERAMIK-Z5U", "P90": "KERAMIK-P90",
           "P100": "KERAMIK-P100", "MICA": "GLIMMER"}


def _surface_code(val):
    v = str(val).lower()
    if re.search(r"silver[\s-]*pallad|ag\s*/?\s*pd", v):
        return "AG-PD"
    if re.search(r"silver[\s-]*tin|ag\s*/?\s*sn", v):
        return "AG-SN"
    if re.search(r"\bgold\b|\bau\b", v):
        return "AU"
    if re.search(r"\btin\b|\bsn\b|zinn", v):
        return "SN"
    return None


def snap_pick_lists_c(category, extracted_data):
    """Snap AI answers to the exact DMS list value (case / spacing / bare dielectric code); mark free-text values."""
    for key, items in PICK_LISTS.get(category, {}).items():
        item = extracted_data.get(key)
        if not isinstance(item, dict):
            continue
        val = str(item.get("value", "N/A")).strip()
        if val in ("", "N/A"):
            continue
        exact = {v for v, _ in items}
        loose = {_norm(v): v for v, _ in items}
        if val in exact:
            continue
        if _norm(val) in loose:
            item["value"] = loose[_norm(val)]
        elif key == "Surface" and _surface_code(val):
            item["value"] = _surface_code(val)
        elif key == "Description" and _norm(val).replace("KERAMIK", "") in ALIASES:
            item["value"] = ALIASES[_norm(val).replace("KERAMIK", "")]
        elif key == "Package Type" and re.fullmatch(r"(EIA)?\d{4,5}", _norm(val)):
            size = re.search(r"\d{4,5}", val).group()
            item["value"] = f"EIA{size}*"
        else:
            item["evidence"] = f"{item.get('evidence', 'N/A')} [free text: not in DMS list]"


# ------------------------------------------------------------------- detection
DETECT_C = {
    EMI: ["feedthrough capacitor", "feed-through capacitor", "feedthrough filter", "feed-through filter",
          "emi filter", "emi suppression filter", "pi filter", "pi-filter", "mains filter", "line filter",
          "power line filter", "x2y"],
    "Capacitor Electrolyt": ["electrolytic", "aluminum electrolytic", "aluminium electrolytic", "tantalum",
                             "polymer capacitor", "conductive polymer", "ripple current", "endurance", "load life",
                             "snap-in", "v-chip", "e-cap", "elko"],
    "Capacitor mech. adjustable": ["trimmer capacitor", "trimmer capacitors", "variable capacitor", "air trimmer",
                                   "ceramic trimmer", "adjustable capacitor", "piston trimmer"],
    "Capacitor electr. adjustable": ["digitally tunable capacitor", "tunable capacitor", "dtc", "varactor",
                                     "programmable capacitor", "capacitor array tunable"],
    CAP_FIXED: ["mlcc", "multilayer ceramic", "ceramic capacitor", "chip capacitor", "film capacitor",
                "mica capacitor", "silicon capacitor", "capacitor", "capacitors", "c0g", "np0", "x7r", "x5r",
                "dielectric"],
}

C_WORDS = ["capacitor", "capacitors", "mlcc", "capacitance", "dielectric", "electrolytic", "tantalum", "c0g", "np0",
           "x7r", "x5r", "x7s", "u2j", "farad", "esr", "ripple current", "trimmer capacitor", "feedthrough capacitor"]


def detect_category_c(pdf_text, file_names=()):
    """Return (category, confident). Falls back to 'Capacitors fixed' with confident=False."""
    names, head = " ".join(file_names), pdf_text[:3000]
    scores = {c: _score(w, names, head, pdf_text) for c, w in DETECT_C.items()}
    specific = {c: s for c, s in scores.items() if c != CAP_FIXED}
    best, sc = max(specific.items(), key=lambda kv: kv[1])
    if sc >= 8 and sc >= 0.4 * scores[CAP_FIXED]:
        return best, True
    if scores[CAP_FIXED] >= 8:
        return CAP_FIXED, True
    return CAP_FIXED, False


def detect_commodity(pdf_text, file_names=()):
    """Return ('R*', 'L*' or 'C*', confident). Replaces the R*/L*-only version of categories_l.py."""
    names, head = " ".join(file_names), pdf_text[:3000]
    scores = {"R*": _score(R_WORDS, names, head, pdf_text),
              "L*": _score(L_WORDS, names, head, pdf_text),
              # 'capacitance' also shows up in inductor / resistor datasheets (parasitics): weight C* a little lower
              "C*": int(0.8 * _score(C_WORDS, names, head, pdf_text))}
    best = max(scores, key=lambda k: (scores[k], k == "R*"))   # tie -> R* (as before)
    others = max(v for k, v in scores.items() if k != best)
    return best, scores[best] >= 8 and scores[best] > others
