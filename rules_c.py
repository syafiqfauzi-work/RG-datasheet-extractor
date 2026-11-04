"""
C* rules: manufacturer / commodity-group detection and the CC, CE, CK, CG standardization rule.

Sources:
  * "Capacitors (CC, CE, CK, CG) - Material and supplier standardization rule"
    (released 28.11.2019, updated 25.05.2023 and 05.06.2025, CI 04.00)
  * "1 ASI categorization for material numbers in CG CC, CE, CK" (06 Jul 2023) - covers CC only.

How the rule works:
  * CC commodity parts (<= 250 V, SN termination): one ASI table per capacitance range
    (dielectric, package, value series, tolerance, voltage). The least recommended parameter wins;
  * CC special series (> 250 V, RF / high-Q series, silicon, beam lead, flexible termination):
    per-series tables, mostly ASI O; Dalicap series ASI B (manufacturer not yet approved);
  * general rows for all CC: termination, AEC-Q200, THR/THW;
  * suppliers are Preferred / Approved / Candidate / Restricted (avoid, blocked) per material group;
  * CE / CK / CG have no ASI categorization yet: the rating comes from the supplier class and the
    material group strategy (tantalum avoided, THT mica not recommended, ...), ASI T is not given.
"""
import math
import re

from asi_rules import T, O, B, U, LABEL, _val, E96 as E96_SET
from categories_c import CATEGORY_CG, C_CG_OPTIONS, MANUFACTURERS_C

SOURCE = "CC/CE/CK/CG standardization rule (CI 04.00, 05.06.2025) and CC ASI categorization (06 Jul 2023)"


# ================================================================ helpers
def _rx(word):
    return rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])"


def _hits(words, text):
    return sum(len(re.findall(_rx(w), text, flags=re.I)) for w in words)


def _score(words, names, head, text):
    return 6 * _hits(words, names) + 3 * _hits(words, head) + min(_hits(words, text), 10)


def _num(s):
    m = re.search(r"-?\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?", str(s or ""))
    return float(m.group().replace(",", ".")) if m else None


UNIT = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6, "m": 1e-3, "": 1.0}


def parse_cap(s):
    """'0.0000001', '1e-7', '100nF', '0.1 uF', '4R7' (pF), '4.7PF' -> farad (float) or None."""
    t = str(s or "").strip().replace(",", ".")
    if t.upper() in ("", "N/A"):
        return None
    m = re.fullmatch(r"(\d+)R(\d+)", t.upper())           # EIA style 4R7 = 4.7 pF
    if m:
        return float(f"{m.group(1)}.{m.group(2)}") * 1e-12
    m = re.search(r"(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([pnuµμm]?)\s*f?\b", t, flags=re.I)
    if not m:
        return None
    v = float(m.group(1))
    unit = m.group(2).lower() if m.group(2) not in ("µ", "μ") else "u"
    if unit == "m" and not re.search(r"mf", t, flags=re.I):
        unit = ""
    return v * UNIT.get(unit, 1.0)


def fmt_cap(f):
    if f is None:
        return "N/A"
    for div, u in ((1e-6, "µF"), (1e-9, "nF"), (1e-12, "pF")):
        if f >= div * 0.9999:
            return f"{f / div:.4g} {u}"
    return f"{f / 1e-12:.4g} pF"


def parse_pkg(s):
    m = re.search(r"(01005|\d{4})", str(s or ""))
    return m.group(1) if m else None


def dielectric_of(ed):
    """C0G / C0H / X7R / ... / SILICON from Description (DMS value) or the designation."""
    d = (_val(ed, "Description") + " " + _val(ed, "Designation")).upper().replace("NP0", "C0G").replace("COG", "C0G")
    if "SILICON" in d:
        return "SILICON-C0H" if "C0H" in d else "SILICON-C0G" if "C0G" in d else "SILICON"
    for code in ("C0G", "C0H", "U2J", "P90", "P100", "SL", "X7R", "X7S", "X7T", "X6S", "X6T", "X5R", "X5S",
                 "Y5V", "Y5U", "Z5U", "Y5S"):
        if re.search(rf"(?<![A-Z0-9]){code}(?![A-Z0-9])", d):
            return code
    return None


CLASS1 = {"C0G", "C0H", "U2J", "P90", "P100", "SL", "SILICON-C0G", "SILICON-C0H"}


def tol_of(ed, cap):
    """Return (value, unit 'pF' or '%'). Absolute pF tolerances matter for small values."""
    raw = _val(ed, "Tolerance_Raw")
    v = _num(raw)
    if v is not None and re.search(r"p\s*f", raw, flags=re.I):
        return abs(v), "pF"
    if v is not None and "%" in raw:
        return abs(v), "%"
    pct = _num(_val(ed, "Tolerance (%)"))
    if pct is None:
        return None, None
    if cap is not None and cap < 10e-12:                      # small values: rule is written in pF
        return round(abs(pct) / 100 * cap / 1e-12, 3), "pF"
    return abs(pct), "%"


def _yes(ed, key):
    return _val(ed, key).strip().lower() in ("yes", "y")


# value series (mantissa 1.0 .. 9.99)
E12 = (1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2)
E24 = E12 + (1.1, 1.3, 1.6, 2.0, 2.4, 3.0, 3.6, 4.3, 5.1, 6.2, 7.5, 9.1)
E96 = tuple(sorted(E96_SET))
E48 = tuple(v for i, v in enumerate(E96) if i % 2 == 0)   # E48 = every second E96 value


def mantissa(x):
    if not x or x <= 0:
        return None
    return round(x / 10 ** math.floor(math.log10(x) + 1e-9), 3)


def _in_series(m, series):
    return m is not None and any(abs(m - v) < 0.006 for v in series)


def series_name(cap):
    m = mantissa(cap)
    if _in_series(m, E12):
        return "E12"
    if _in_series(m, E24):
        return "E24"
    if _in_series(m, E48):
        return "E48"
    if _in_series(m, E96):
        return "E96"
    return "E192 / other"


# ======================================================= CC commodity tables
# One dict per capacitance range: parameter -> (T set, O set, U set). Numbers are V / % / pF.
# "*" in a U set means "anything not listed in T or O", "le:x" means "<= x", "ge:x" means ">= x".
PKG_T3 = {"0201", "0402", "0603"}
CC_RANGES = [
    ("0.05 pF - 0.9 pF", 0.95e-12, {
        "class": ({1}, set(), {2}),
        "dielectric": ({"C0G"}, {"C0H"}, {"*"}),
        "package": (PKG_T3, {"1206", "01005"}, {"0805", "1210", "THR"}),
        "series": "step",
        "tol_unit": "pF",
        "tolerance": ({0.02, 0.03, 0.05}, {0.01, 0.1}, {0.25, 0.5, "*"}),
        "voltage": ({50, 100}, {25, 200, 250}, {"le:16"}),
        "makers": "AVX (ACCU-P); Yageo (NP0)"}),
    ("1 pF - 9.1 pF", 9.55e-12, {
        "class": ({1}, set(), {2}),
        "dielectric": ({"C0G"}, {"C0H"}, {"*"}),
        "package": (PKG_T3, {"1206", "01005"}, {"0805", "1210", "THR"}),
        "series": "step",
        "tol_unit": "pF",
        "tolerance": ({0.02, 0.03, 0.05, 0.1}, {0.01, 0.25}, {0.5, "*"}),
        "voltage": ({50, 100}, {25, 200, 250}, {"le:16"}),
        "makers": "AVX (ACCU-P); AVX (600S); Yageo (NP0)"}),
    ("10 pF - 120 pF", 125e-12, {
        "class": ({1}, set(), {2}),
        "dielectric": ({"C0G"}, {"C0H"}, {"U2J", "*"}),
        "package": (PKG_T3, {"1206", "01005"}, {"0805", "1210", "THR"}),
        "series": "E",
        "tol_unit": "%",
        "tolerance": ({5}, {1, 2}, {10, "ge:20"}),
        "voltage": ({50, 100}, {25, 200, 250}, {"le:16"}),
        "makers": "AVX (ACCU-P); AVX (600S); Yageo (NP0)"}),
    ("130 pF - 910 pF", 955e-12, {
        "class": ({1}, set(), {2}),
        "dielectric": ({"C0G"}, {"C0H"}, {"U2J", "*"}),      # X7R is T only in 0201 (handled in code)
        "package": (PKG_T3, {"1206", "01005"}, {"0805", "1210", "THR"}),
        "series": "E",
        "tol_unit": "%",
        "tolerance": ({5}, {1, 2, 10}, {"ge:20"}),
        "voltage": ({50, 100}, {25, 200, 250}, {"le:16"}),
        "makers": "Yageo (NP0)"}),
    ("1 nF - 10 nF", 10.5e-9, {
        "class": ({1, 2}, set(), set()),
        "dielectric": ({"X7R", "C0G"}, {"C0H"}, {"U2J", "*"}),
        "package": (PKG_T3, {"1206", "01005"}, {"0805", "1210", "THR"}),
        "series": "E",
        "tol_unit": "%",
        "tolerance": ({5, 10}, {1, 2}, {"ge:20"}),
        "voltage": ({50, 100, 25}, {16, 200, 250}, {"le:10"}),
        "makers": "-"}),
    ("11 nF - 100 nF", 105e-9, {
        "class": ({1, 2}, set(), set()),
        "dielectric": ({"C0G", "X7R", "X5R"}, {"C0H", "U2J"}, {"*"}),
        "package": (PKG_T3 | {"1206"}, {"0306"}, {"0805", "1210", "THR"}),
        "series": "E",
        "tol_unit": "%",
        "tolerance": ({5, 10}, {1, 2}, {"ge:20"}),
        "voltage": ({50, 100, 25}, {16, 200, 250}, {"le:10"}),
        "makers": "-"}),
    ("110 nF - 8.2 µF", 9.1e-6, {
        "class": ({2}, set(), {1}),
        "dielectric": ({"X7R", "X6S", "X5R"}, {"C0H"}, {"U2J", "*"}),
        "package": ({"0402", "0603", "1206"}, {"0201", "0805", "1812", "2220", "STACKED"}, {"1210", "THR"}),
        "series": "E",
        "tol_unit": "%",
        "tolerance": ({10, 5}, {15, 20, 1, 2}, {"gt:20"}),
        "voltage": ({50, 100, 25, 16, 10}, {6.3, 200, 250}, {"lt:4"}),
        "makers": "-"}),
    ("10 µF - 330 µF", 330e-6, {
        "class": ({2}, set(), {1}),
        "dielectric": ({"X7R", "X7S", "X6S", "X6T", "X5R"}, {"C0H"}, {"*"}),
        "package": ({"0603", "0805", "1206", "1210"}, {"0201", "0402", "1812", "2220", "STACKED"}, {"THR"}),
        "series": "E",
        "tol_unit": "%",
        "tolerance": ({10, 20}, {15}, {"gt:20"}),
        "voltage": ({50, 25, 16, 10, 6.3, 4}, {100, 200, 250, "lt:4"}, set()),
        "makers": "-"}),
]
SERIES_RATING = {"E12": T, "E24": T, "E48": O, "E96": O, "E192 / other": U}


def _match(x, items):
    pct = isinstance(x, str) and x.endswith("%")
    for it in items:
        if pct and isinstance(it, str) and it.startswith(("le:", "ge:", "lt:", "gt:")) and it.endswith("%"):
            if _match(float(x[:-1]), [it[:-1]]):
                return True
            continue
        if isinstance(it, str):
            if it == "*":
                continue
            if it.startswith(("le:", "ge:", "lt:", "gt:")) and isinstance(x, (int, float)):
                lim = float(it[3:])
                if ((it[:2] == "le" and x <= lim + 1e-9) or (it[:2] == "ge" and x >= lim - 1e-9)
                        or (it[:2] == "lt" and x < lim - 1e-9) or (it[:2] == "gt" and x > lim + 1e-9)):
                    return True
            elif it == x:
                return True
        elif isinstance(x, (int, float)) and abs(float(it) - float(x)) < 1e-6:
            return True
    return False


def tol_key(tol, unit):
    """Series tables mix absolute (pF, float) and relative ('5%', string) tolerances."""
    return f"{tol:g}%" if unit == "%" else tol


def rate(x, triple, unlisted=O):
    """Least recommended column that contains x. Returns (rating, note)."""
    t, o, u = triple
    if _match(x, u):
        return U, "listed for phase-out / not recommended (U/V)"
    if _match(x, o):
        return O, "approved (O)"
    if _match(x, t):
        return T, "recommended for new designs (T)"
    if "*" in u:
        return U, "not listed in T / O: U/V"
    return unlisted, "not listed in the table: treated as approved (O), check with the component engineer"


def _fmt_set(s):
    return " | ".join(str(v).replace("le:", "<= ").replace("ge:", ">= ").replace("lt:", "< ").replace("gt:", "> ")
                      for v in sorted(s, key=lambda v: (isinstance(v, str), v if not isinstance(v, str) else 0, str(v)))
                      if v != "*") or "-"


def cc_range(cap):
    for name, upper, table in CC_RANGES:
        if cap <= upper:
            return name, table
    return None, None


# ===================================================== CC special series
# key -> dict(match words, display, package (T,O,U), tolerance (T,O,U), tol unit, voltage (T,O,U),
#             cap range (F), base rating cap, note). A missing table means "no restriction".
SPECIAL_SERIES = [
    ("Accu-P", {"words": ["accu-p", "accup", "accu p"], "maker": "kavx",
                "package": ({"0201", "0402"}, set(), {"0603", "0805", "1210"}),
                "tolerance": ({0.02, 0.03, 0.05, 0.1}, {0.01, "1%"}, {0.25, 0.5}),
                "voltage": ({100, 50, 25}, {16, 10}, {200}),
                "cap": (0.1e-12, 82e-12),
                "note": "Thin-film RF (functional library T_RF_THIN_CC); 50 V values preferred where available"}),
    ("Murata GJM", {"words": ["gjm"], "maker": "murata", "max": O,
                    "package": (set(), {"0201", "0402", "01005"}, {"*"}),
                    "tolerance": (set(), {0.05, 0.1, "2%"}, {0.25, 0.5, "5%"}),
                    "voltage": ({100, 50, 25}, {16, 10}, {6.3}),
                    "cap": (0.1e-12, 47e-12),
                    "note": "High Q; check for an Accu-P alternative (better tolerances, more expensive)"}),
    ("AVX 600S", {"words": ["600s"], "maker": "kavx", "max": O,
                  "package": (set(), {"0603"}, {"*"}),
                  "tolerance": (set(), {0.05, 0.1, "1%", "2%"}, {0.25, 0.5, "5%", "10%", "20%"}),
                  "voltage": (set(), {250}, set()), "cap": (0.1e-12, 100e-12), "note": "Low ESR microwave"}),
    ("AVX 180R", {"words": ["180r"], "maker": "kavx", "max": O,
                  "package": (set(), {"0709"}, {"*"}),
                  "tolerance": (set(), {0.1, 0.25, 0.5, "2%", "5%"}, {"10%", "20%"}),
                  "voltage": (set(), {500}, set()), "cap": (0.5e-12, 100e-12),
                  "note": "Old series without direct alternatives; supplier long-term support questionable; "
                          "DALICAP replacements under review"}),
    ("AVX 800R", {"words": ["800r"], "maker": "kavx", "max": O,
                  "package": (set(), {"0709"}, {"*"}),
                  "tolerance": (set(), {0.1, 0.25, 0.5, "2%", "5%"}, {"10%", "20%"}),
                  "voltage": (set(), {500}, set()), "cap": (1e-12, 100e-12),
                  "note": "180R replacement candidate; old series, long-term support questionable"}),
    ("AVX 100B", {"words": ["100b"], "maker": "kavx", "max": O,
                  "package": (set(), {"1111"}, {"*"}),
                  "tolerance": (set(), {0.1, 0.25, 0.5, "1%", "2%", "5%"}, {"10%", "20%"}),
                  "voltage": (set(), {500, 300, 200, 1500, 1000, 600}, set()), "cap": (0.1e-12, 1000e-12),
                  "note": "UNDER REVIEW; second source EXXELIA CH(B); make sure the part fits the basic agreement"}),
    ("AVX 100A", {"words": ["100a"], "maker": "kavx", "max": O,
                  "package": (set(), {"0505"}, {"*"}),
                  "tolerance": (set(), {0.1, 0.25, 0.5, "1%", "2%", "5%"}, {"10%", "20%"}),
                  "voltage": (set(), {150, 200, 250}, set()), "cap": (0.1e-12, 100e-12),
                  "note": "UNDER REVIEW; legacy series (compare AVX 600S)"}),
    ("EXXELIA CH(B)", {"words": ["chb", "ch(b)", "ch series"], "maker": "exxelia", "max": O,
                       "package": (set(), {"1111"}, {"*"}), "cap": (0.1e-12, 1000e-12),
                       "note": "UNDER REVIEW; technical twin of AVX 100B with P100"}),
    ("EXXELIA CL(X)", {"words": ["clx", "cl(x)"], "maker": "exxelia", "max": O,
                       "package": (set(), {"2225"}, {"4040", "7065"}),
                       "voltage": (set(), {300, 500, 1500, 2500, 3600}, {"*"}), "cap": (1e-12, 10000e-12),
                       "note": "UNDER REVIEW"}),
    ("AVX-U", {"words": ["u-series", "ultra low esr", "avx u"], "maker": "kavx", "max": U,
               "note": "'Ultra' low ESR: availability problems (all packages U/V)"}),
    ("Presidio BB", {"words": ["buried broadband", "presidio bb"], "maker": "presidio", "max": O,
                     "note": "Surface-mount buried broadband capacitor"}),
    ("MACOM MBC50", {"words": ["mbc50", "mbc 50"], "maker": "macom", "max": O,
                     "note": "Silicon C0H beam-lead capacitor"}),
    ("AVX GH/GB SLC", {"words": ["single layer", "gh series", "gb series", "microwave slc"], "maker": "kavx",
                       "max": O, "note": "Single layer ceramics with / without borders"}),
    ("AVX LICC", {"words": ["licc", "low inductance chip", "reverse geometry"], "maker": "kavx", "max": O,
                  "package": (set(), {"0306", "0508", "0612"}, {"*"}),
                  "voltage": (set(), {50, 25, 16, 10}, {"le:6.3"}),
                  "note": "Low inductance chip capacitor (terminations on the long sides)"}),
    ("DALICAP DLC75P", {"words": ["dlc75p"], "maker": "dalicap", "max": B,
                        "package": (set(), {"0603"}, {"*"}), "voltage": (set(), {250}, set()),
                        "note": "Low ESR microwave (compare AVX 600S); ASI-B as the manufacturer is not yet approved"}),
    ("DALICAP DLC70B", {"words": ["dlc70b"], "maker": "dalicap", "max": B,
                        "package": (set(), {"1111"}, {"*"}),
                        "note": "High Q RF/microwave (compare AVX 100B); ASI-B as the manufacturer is not yet approved"}),
    # "Others": special ASI O, provide an extensive ASI-Reason
    ("AVX 100E", {"words": ["100e"], "maker": "kavx", "max": O, "note": "Special ASI O: provide an extensive ASI-Reason"}),
    ("AVX 700C", {"words": ["700c"], "maker": "kavx", "max": O, "note": "Special ASI O: provide an extensive ASI-Reason"}),
    ("AVX 700A", {"words": ["700a"], "maker": "kavx", "max": O, "note": "Special ASI O: provide an extensive ASI-Reason"}),
    ("AVX IDC", {"words": ["interdigitated", "idc"], "maker": "kavx", "max": O,
                 "note": "Special ASI O: provide an extensive ASI-Reason"}),
    ("DALICAP DLC70R/75R", {"words": ["dlc70r", "dlc75r"], "maker": "dalicap", "max": B,
                            "note": "Special ASI O, but the manufacturer is not yet approved (ASI-B)"}),
    ("ATC 900C", {"words": ["900c"], "maker": "kavx", "max": O, "note": "Special ASI O: provide an extensive ASI-Reason"}),
    ("AVX 600F", {"words": ["600f"], "maker": "kavx", "max": U,
                  "note": "Introduction stopped: AVX 100A is used as the alternative"}),
    ("AVX SMPS", {"words": ["smps"], "maker": "kavx", "max": O, "note": "Special ASI O: provide an extensive ASI-Reason"}),
    ("ATC 560L / 550L", {"words": ["560l", "550l", "ultra-broadband", "ultra broadband"], "maker": "kavx", "max": O,
                         "note": "Special ASI O: provide an extensive ASI-Reason"}),
    ("Johanson 302/502", {"words": ["polyterm"], "maker": "johanson", "max": O,
                          "note": "Special ASI O: provide an extensive ASI-Reason"}),
]

HV_TABLE = {   # High Voltage > 250 V (general purpose / commodity / safety)
    "package": (set(), {"1206", "1808", "1812", "2220"}, {"*"}),
    "tolerance": (set(), {0.1, 0.25, 0.5, "1%", "2%", "5%", "10%"}, {"ge:20%"}),
    "cap": (1e-12, 100e-9),
    "makers": "AVX (HV-MLCC), Yageo (HV-MLCC), Murata (HV-MLCC GRM)",
}


def find_series(ed, manufacturer, mpn, pdf_text):
    """Match a special series by the series field, the MPN prefix or (long keywords only) the datasheet head."""
    ser = _val(ed, "Series").lower()
    mpn_l = str(mpn or "").strip().lower()
    blob = " ".join([ser, _val(ed, "Additional Information"), pdf_text[:1500]]).lower()
    for name, spec in SPECIAL_SERIES:
        for w in spec["words"]:
            short = len(w) <= 5          # codes such as 600s, 100b, gjm, licc: series field / MPN prefix only
            if re.search(_rx(w), ser) or (short and mpn_l.startswith(w)) or (not short and re.search(_rx(w), blob)):
                return name, spec
    return None, None


# ================================================================ suppliers
# keyword -> (display name, {group or 'CC-special' or CE technology: status}, note)
P, A, C, R_AVOID, R_BLOCK, R_RESTR = "Preferred", "Approved", "Candidate", "Avoid", "Blocked", "Restricted"
SUPPLIERS = [
    (["murata"], "Murata", {"CC": P, "CC-special": P, "CE-polymer": A}, "MLCCs and silicon caps: preferred"),
    (["yageo"], "Yageo", {"CC": P}, "challenger for Murata, replacement for Murata legacy parts (via TTI)"),
    (["taiyo yuden"], "Taiyo Yuden", {"CC": "TY"}, "preferred for high capacitance / high voltage, otherwise approved"),
    (["kyocera avx", "kyocera", "avx", "american technical ceramics", "atc"], "Kyocera AVX (KAVX)",
     {"CC": A, "CC-special": P, "CE-polymer": A, "CE-alu": A, "CE-tantalum": A},
     "preferred for special purpose MLCCs (Accu-P), approved for general MLCCs and CE"),
    (["kemet"], "KEMET (Yageo)", {"CC": A, "CE-polymer": A, "CE-alu": A, "CE-tantalum": A, "CK": A},
     "no case sizes smaller than 0402"),
    (["macom", "metelics"], "MACOM", {"CC-special": A, "CC": A}, "special purpose CCs: MIS / beam lead"),
    (["exxelia", "temex"], "Exxelia", {"CC": A, "CC-special": A}, "high-Q MLCCs"),
    (["chemi-con", "chemicon", "nippon chemi"], "Nippon Chemi-Con", {"CE-alu": A, "CE-polymer": A}, ""),
    (["panasonic"], "Panasonic", {"CE-polymer": P, "CE-alu": A, "CK": A},
     "preferred for polymer capacitors, approved for aluminium electrolytic and film"),
    (["nichicon"], "Nichicon", {"CE-alu": P}, "aluminium electrolytic capacitors (via TTI)"),
    (["wima"], "WIMA", {"CK": P}, "film capacitors (via TTI)"),
    (["tdk", "epcos"], "TDK / Epcos", {"CK": A, "CC": R_AVOID, "CC-special": R_AVOID},
     "MLCC: avoid (might leave the MLCC market); film: approved"),
    (["rubycon"], "Rubycon", {"CK": A}, "film capacitors (via Codico)"),
    (["vishay", "sprague"], "Vishay", {"CE-tantalum": "MIL", "CE-alu": R_RESTR, "CE-polymer": R_RESTR,
                                       "CC": R_RESTR, "CC-special": C},
     "MLCC restricted (long lead time, price); high-Q MLCC candidate; CE only for MIL tantalum"),
    (["cornell dubilier", "cde", "knowles"], "CDE (Knowles)", {"CG": A}, "mica capacitors"),
    (["walsin"], "Walsin", {"CC": C}, "candidate (via Endrich)"),
    (["holy stone", "holystone"], "Holy Stone", {"CC": C}, "candidate: mid / big case sizes, HV, high capacitance"),
    (["samsung"], "Samsung", {"CC": C}, "candidate: new focus on industry / automotive"),
    (["dalicap"], "Dalicap", {"CC": C, "CC-special": C}, "candidate: high-Q MLCCs (ATC alternative)"),
    (["darfon"], "Darfon", {"CC": R_RESTR}, "candidate status to be retrieved"),
    (["charcroft"], "Charcroft", {"CG": R_AVOID}, "quality issues, no RF expertise"),
    (["richard jahre"], "Richard Jahre", {"CG": R_BLOCK}, "business relationship ended"),
    (["presidio"], "Presidio", {"CC": R_BLOCK, "CC-special": R_BLOCK}, "blocked"),
]
STATUS_RATING = {P: T, A: O, C: B, R_AVOID: U, R_BLOCK: U, R_RESTR: U}


def supplier_of(manufacturer):
    m = str(manufacturer).lower()
    for words, name, groups, note in SUPPLIERS:
        if any(re.search(_rx(w), m) for w in words):
            return name, groups, note
    return None


# ============================================================ manufacturer
OTHER_MANUFACTURERS = {
    "KEMET Corporation": ["kemet"], "Walsin Technology Corp.": ["walsin"], "Darfon Electronics": ["darfon"],
    "Cornell Dubilier Electronics": ["cornell dubilier"], "Charcroft Electronics": ["charcroft"],
    "Skyworks Solutions": ["skyworks"], "Würth Elektronik GmbH & Co. KG": ["würth", "wurth", "wuerth"],
    "Elna Co., Ltd.": ["elna"], "Lelon Electronics": ["lelon"], "Fenghua (H.K.) Electronics Ltd.": ["fenghua"],
    "Viking Tech": ["viking tech"], "Eyang": ["eyang"],
}


def resolve_manufacturer_c(ai_name, pdf_text, file_names=()):
    """Strong text evidence wins; an AI answer from the list that the datasheet never mentions is rejected."""
    names, head = " ".join(file_names), pdf_text[:3000]
    best, best_sc = None, 0
    for canon, words in list(MANUFACTURERS_C.items()) + list(OTHER_MANUFACTURERS.items()):
        sc = _score(words, names, head, pdf_text)
        if sc > best_sc:
            best, best_sc = canon, sc
    if best and best_sc >= 8:
        return best
    if ai_name in MANUFACTURERS_C and _score(MANUFACTURERS_C[ai_name], names, head, pdf_text) == 0:
        return "Unknown"
    return ai_name


# ========================================================= commodity group
def determine_cg_c(category, extracted_data, pdf_text):
    allowed, default = CATEGORY_CG[category]
    raw = extracted_data.pop("Commodity Group", "Unknown")
    if isinstance(raw, dict):
        raw = raw.get("value", "Unknown")
    ai = str(raw).strip().upper()[:2]
    desc = _val(extracted_data, "Description").upper()
    head = pdf_text[:3000].lower()
    if category == "Capacitors fixed":
        if desc.startswith("FOLIE") or "film capacitor" in head:
            return "CK", "Film dielectric -> CK"
        if desc == "GLIMMER" or re.search(r"\bmica\b", head):
            return "CG", "Mica dielectric -> CG"
        if desc.startswith(("KERAMIK", "SILICON")) and ai not in ("CX", "CN", "CL", "CH"):
            return "CC", "Ceramic / silicon chip capacitor -> CC"
    if ai in allowed:
        return ai, f"AI choice {ai} fits the category"
    return default, f"Default group for {category}"


def cg_label_c(code):
    return f"{code} ({C_CG_OPTIONS[code]})" if code in C_CG_OPTIONS else str(code)


# ============================================================== the rules
def _supplier_check(manufacturer, key, sub_label, checks, flags, cap=None, volt=None):
    sup = supplier_of(manufacturer)
    if sup is None:
        checks.append({"Parameter": "Supplier", "Value": str(manufacturer), "Rating": U,
                       "Note": "Not listed in the CC/CE/CK/CG rule: contact Procurement Engineering"})
        flags.append("Supplier is not listed in the capacitor standardization rule: contact Procurement Engineering.")
        return
    name, groups, note = sup
    status = groups.get(key)
    if status is None and key == "CC-special":
        status = groups.get("CC")
    if status == "TY":   # Taiyo Yuden: preferred for high capacitance / high voltage only
        high = (cap is not None and cap >= 10e-6) or (volt is not None and volt > 250)
        status = P if high else A
        note = ("preferred for high capacitance (>= 10 µF) / high voltage (> 250 V)" if high
                else "approved (preferred only for high capacitance / high voltage)")
    if status == "MIL":
        checks.append({"Parameter": "Supplier", "Value": f"{name} · {sub_label}", "Rating": B,
                       "Note": "Only for MIL tantalum (wet tantalum: Vishay/Sprague only), otherwise restricted"})
        flags.append("Vishay tantalum is allowed for MIL applications only; otherwise it is restricted.")
        return
    if status is None:
        listed = ", ".join(f"{k}: {v}" for k, v in groups.items())
        checks.append({"Parameter": "Supplier", "Value": f"{name} · {sub_label}", "Rating": U,
                       "Note": f"Not listed for this group / technology (listed: {listed})"})
        flags.append(f"{name} is not listed for {sub_label} in the rule (listed for {listed}).")
        return
    rating = STATUS_RATING[status]
    checks.append({"Parameter": "Supplier", "Value": f"{name} · {sub_label}", "Rating": rating,
                   "Note": f"{status} supplier" + (f": {note}" if note else "")})
    if status == C:
        flags.append(f"{name} is a candidate supplier: joint approval of Procurement, Quality, the component "
                     f"engineer and the procurement engineer is required.")
    elif rating == U:
        flags.append(f"{name} is a restricted supplier for {sub_label} ({status.lower()}): {note}.")


def _lifecycle_check(ed, checks):
    life = _val(ed, "Lifecycle Status")
    if life.upper().startswith(("NRND", "DISCONTINUED", "OBSOLETE", "EOL")):
        checks.append({"Parameter": "Lifecycle", "Value": life, "Rating": U,
                       "Note": "Legacy: manufacturer status 'not recommended for new design' / discontinued -> V"})
    else:
        checks.append({"Parameter": "Lifecycle", "Value": life, "Rating": None,
                       "Note": "No NRND / discontinued note found in the datasheet; check the manufacturer status"})


def _row(checks, param, value, rating_note):
    rating, note = rating_note
    checks.append({"Parameter": param, "Value": value, "Rating": rating, "Note": note})


def _thr(ed):
    mount = _val(ed, "Kind of Mounting").upper()
    return mount.startswith(("THR", "THW"))


def asi_cc(ed, manufacturer, mpn="", pdf_text=""):
    checks, flags = [], []
    cap = parse_cap(_val(ed, "Capacity (F)"))
    volt = _num(_val(ed, "Voltage (V)"))
    pkg = "THR" if _thr(ed) else parse_pkg(_val(ed, "Package Type"))
    if _yes(ed, "Stacked"):
        pkg = "STACKED"
    diel = dielectric_of(ed)
    tol, tol_unit = tol_of(ed, cap)
    surface = _val(ed, "Surface").upper()
    flex = _yes(ed, "Flexible Termination")
    sname, spec = find_series(ed, manufacturer, mpn, pdf_text)
    special_term = surface in ("AU", "AG-PD") or "BEAM" in _val(ed, "Additional Information").upper()
    silicon = bool(diel and diel.startswith("SILICON"))

    if spec:
        sub = f"Special series: {sname}"
    elif volt is not None and volt > 250:
        sub = "Special series: High Voltage > 250 V (general purpose / safety)"
    elif silicon or special_term:
        sub = "Special: silicon / AU / AG-PD / beam-lead parts (special series)"
    elif flex:
        sub = "Special series: Flexible termination"
    else:
        rname, _t = cc_range(cap) if cap else (None, None)
        sub = f"Commodity / general purpose · {rname}" if rname else "Commodity / general purpose"

    # 1) supplier
    _supplier_check(manufacturer, "CC" if sub.startswith("Commodity") else "CC-special", sub.split(" · ")[0],
                    checks, flags, cap, volt)

    # 2) parameters
    if cap is None:
        checks.append({"Parameter": "Capacitance", "Value": _val(ed, "Capacity (F)"), "Rating": None,
                       "Note": "Capacitance could not be read: parameter checks skipped"})
        flags.append("Capacitance not identified: the range-dependent ASI checks were skipped.")
    elif spec:
        _special_checks(spec, sname, ed, cap, volt, pkg, tol, tol_unit, checks, flags)
    elif volt is not None and volt > 250:
        _hv_checks(cap, volt, pkg, tol, tol_unit, diel, checks, flags)
    elif silicon or special_term:
        checks.append({"Parameter": "Termination / technology", "Value": f"{surface} · {diel or '-'}", "Rating": O,
                       "Note": "Special series (AU, AG-PD, pellet, microstrip, beam lead, silicon): approved (O)"})
        flags.append("No series table matched: check the CC special-series list and give an ASI-Reason.")
    else:
        _commodity_checks(cap, volt, pkg, diel, tol, tol_unit, checks, flags)
        if flex:
            checks.append({"Parameter": "Termination", "Value": "Flexible termination", "Rating": O,
                           "Note": "Special series flexible / soft / polymer termination: approved (O)"})

    # 3) general rows for all CC
    if not (silicon or special_term or flex):
        if pkg == "THR":
            _row(checks, "Termination", "THR / THW", (U, "THR / THW termination: U/V"))
        elif surface == "SN":
            _row(checks, "Termination", "SN", (T, "SN termination: recommended (T)"))
        elif surface not in ("", "N/A"):
            _row(checks, "Termination", surface, (O, "Other / special termination: approved (O)"))
    if _yes(ed, "AEC-Q200"):
        _row(checks, "Automotive AEC-Q200", "yes",
             (O, "AEC-Q200 parts: approved (O) - more expensive and less available at part shortages"))
    if pkg == "01005":
        flags.append("01005: attention regarding E-CAD design rules; feasibility discussion with production necessary.")
    _lifecycle_check(ed, checks)
    return _result(checks, flags, sub, {"cg": "CC", "cap": cap, "volt": volt, "pkg": pkg, "diel": diel,
                                        "tol": tol, "tol_unit": tol_unit, "series": sname, "sub": sub})


def _commodity_checks(cap, volt, pkg, diel, tol, tol_unit, checks, flags):
    rname, tb = cc_range(cap)
    if tb is None:
        checks.append({"Parameter": "Capacitance", "Value": fmt_cap(cap), "Rating": U,
                       "Note": "Above 330 µF: outside the CC commodity table"})
        return
    checks.append({"Parameter": "Capacitance range", "Value": f"{fmt_cap(cap)} -> {rname}", "Rating": None,
                   "Note": f"Main manufacturers (series): {tb['makers']}"})
    # dielectric / class
    if diel is None:
        checks.append({"Parameter": "Dielectric", "Value": "not stated", "Rating": None, "Note": "Check the dielectric"})
    else:
        if rname == "130 pF - 910 pF" and diel == "X7R":
            r = (T, "X7R is recommended (T) in this range only for 0201") if pkg == "0201" else \
                (U, "X7R in this range is T only for 0201; otherwise class 2 is U/V")
        else:
            r = rate(diel, tb["dielectric"])
            klass = 1 if diel in CLASS1 else 2
            rc = rate(klass, tb["class"])
            if rc[0] > r[0]:
                r = (rc[0], f"class {klass} dielectric: {rc[1]}")
        _row(checks, "Dielectric", diel, r)
    # package
    if pkg is None:
        checks.append({"Parameter": "Package", "Value": "not stated", "Rating": None, "Note": "Check the package"})
    else:
        _row(checks, "Package", pkg, rate(pkg, tb["package"]))
    # value series
    if tb["series"] == "step":
        pf = cap / 1e-12
        steps01 = abs(pf * 10 - round(pf * 10)) < 1e-6
        r = (T, "0.1 pF step size (n.a. / 0.1 pF)") if steps01 else \
            (U, "0.05 pF step size or finer: U/V (0.05 pF steps are monitored as an ASI-O candidate)")
        _row(checks, "Value step", f"{pf:g} pF", r)
    else:
        s = series_name(cap)
        r = SERIES_RATING[s]
        _row(checks, "Value series", f"{fmt_cap(cap)} ({s})",
             (r, {T: "E12 / E24: recommended (T); stick to E12 whenever possible",
                  O: "E48 / E96: approved (O)", U: "E192 / other: U/V"}[r]))
        if s == "E24":
            flags.append("E24 value: the strategy prefers E12; a new value beyond E12 needs an SG decision.")
    # tolerance
    if tol is None:
        checks.append({"Parameter": "Tolerance", "Value": "not stated", "Rating": None, "Note": "Check the tolerance"})
    else:
        if tb["tol_unit"] == "pF" and tol_unit == "%":
            tol, tol_unit = round(tol / 100 * cap / 1e-12, 3), "pF"
        elif tb["tol_unit"] == "%" and tol_unit == "pF":
            tol, tol_unit = round(tol * 1e-12 / cap * 100, 2), "%"
        _row(checks, "Tolerance", f"±{tol:g} {tol_unit}", rate(tol, tb["tolerance"]))
    # voltage
    if volt is None:
        checks.append({"Parameter": "Voltage", "Value": "not stated", "Rating": None, "Note": "Check the voltage"})
    else:
        _row(checks, "Voltage", f"{volt:g} V", rate(volt, tb["voltage"]))
    if rname in ("1 nF - 10 nF", "11 nF - 100 nF", "0.05 pF - 0.9 pF", "1 pF - 9.1 pF"):
        flags.append("XOR rule: only one introduced part is allowed per capacitance for the marked parameters "
                     "(tolerance / voltage) - check DMS for an existing part with the same capacitance.")


def _special_checks(spec, sname, ed, cap, volt, pkg, tol, tol_unit, checks, flags):
    lo, hi = spec.get("cap", (None, None))
    if lo is not None and not (lo * 0.999 <= cap <= hi * 1.001):
        _row(checks, "Capacitance", fmt_cap(cap), (U, f"Outside the series range {fmt_cap(lo)} - {fmt_cap(hi)}"))
    elif lo is not None:
        _row(checks, "Capacitance", fmt_cap(cap), (None, f"Series range {fmt_cap(lo)} - {fmt_cap(hi)}"))
    if "package" in spec and pkg:
        _row(checks, "Package", pkg, rate(pkg, spec["package"]))
    if "tolerance" in spec and tol is not None:
        _row(checks, "Tolerance", f"±{tol:g} {tol_unit}", rate(tol_key(tol, tol_unit), spec["tolerance"]))
    if "voltage" in spec and volt is not None:
        _row(checks, "Voltage", f"{volt:g} V", rate(volt, spec["voltage"]))
    cap_rating = spec.get("max", T)
    checks.append({"Parameter": "Series", "Value": sname, "Rating": cap_rating if cap_rating != T else None,
                   "Note": spec["note"]})
    if cap_rating == O:
        flags.append(f"{sname}: special series, ASI O at best - document the reason in ASI-Reason.")


def _hv_checks(cap, volt, pkg, tol, tol_unit, diel, checks, flags):
    lo, hi = HV_TABLE["cap"]
    _row(checks, "Capacitance", fmt_cap(cap),
         (O, "1 pF - 100 nF: approved (O)") if lo * 0.999 <= cap <= hi * 1.001 else (U, "Outside 1 pF - 100 nF: U/V"))
    if diel:
        good = diel in ("C0G", "C0H", "X7R", "X7S", "X7T", "U2J", "P90", "P100")
        _row(checks, "Dielectric", diel, (O, "NP0 (C0G) / X7R or better") if good else (U, "Worse than X7R: U/V"))
    if pkg:
        _row(checks, "Package", pkg, rate(pkg, HV_TABLE["package"]))
    s = series_name(cap)
    _row(checks, "Value series", f"{fmt_cap(cap)} ({s})", (O, "E12") if s == "E12" else (U, "Not E12: U/V"))
    if tol is not None:
        _row(checks, "Tolerance", f"±{tol:g} {tol_unit}", rate(tol_key(tol, tol_unit), HV_TABLE["tolerance"]))
    _row(checks, "Voltage", f"{volt:g} V", (O, ">= 300 V: approved (O)") if volt >= 300 else
         (O, "251 - 299 V: not listed, treated as approved (O)"))
    flags.append(f"High-voltage MLCC: main manufacturers {HV_TABLE['makers']}. Safety-class parts: see the S2 series (Walsin).")


# ------------------------------------------------------------- CE / CK / CG
POLYMER = ("Aluminium Polymer", "Hybrid Polymer", "Tantalum Polymer")
TANTAL = ("Tantalum MnO2", "Wet Tantalum")


def ce_tech(ed):
    t = _val(ed, "Electrolyte Type")
    d = (_val(ed, "Description") + " " + t).upper()
    if t in POLYMER or "POLYMER" in d:
        return "CE-polymer", "Polymer"
    if t in TANTAL or "TANTAL" in d:
        return "CE-tantalum", "Tantalum"
    if t == "Aluminium" or "ALU" in d:
        return "CE-alu", "Aluminium"
    return "CE-alu", "Aluminium (assumed: electrolyte type not stated)"


def asi_other(ed, manufacturer, cg):
    checks, flags = [], []
    if cg == "CE":
        key, tech = ce_tech(ed)
        sub = f"CE · {tech}"
        _supplier_check(manufacturer, key, sub, checks, flags)
        if key == "CE-tantalum":
            _row(checks, "Technology", tech, (U, "Tantalum: avoid in new designs (passive phase-out); replace with "
                                                 "polymer capacitors or MLCCs"))
            if _val(ed, "Electrolyte Type") == "Wet Tantalum":
                flags.append("Wet tantalum only in MIL applications (Vishay/Sprague).")
        elif key == "CE-polymer":
            _row(checks, "Technology", tech, (None, "Polymer: Panasonic preferred; check whether a polymer cap can "
                                                    "replace large MLCCs"))
        if "assumed" in tech:
            flags.append("Electrolyte type not stated: aluminium assumed for the supplier check.")
    elif cg == "CK":
        sub = "CK · Film capacitors"
        _supplier_check(manufacturer, "CK", sub, checks, flags)
    else:   # CG
        sub = "CG · Mica capacitors"
        _supplier_check(manufacturer, "CG", sub, checks, flags)
        pkg = parse_pkg(_val(ed, "Package Type"))
        if _thr(ed) or _val(ed, "Package Type").upper() in ("*RADIAL*", "*AXIAL*"):
            _row(checks, "Mounting", "THT", (U, "THT mica: not recommended for new design (V)"))
        elif pkg in ("1210", "1812"):
            _row(checks, "Package", pkg, (U, "SMT mica: avoid 1210 / 1812 case sizes"))
        elif pkg in ("3838", "4640"):
            _row(checks, "Package", pkg, (B, "SMT mica 3838 / 4640: restricted for specific use (conditional, B)"))
        elif pkg:
            _row(checks, "Package", pkg, (None, "SMT mica"))
        flags.append("Mica strategy: use high-Q ceramic capacitors where possible.")
    # no ASI catalogue for CE / CK / CG: a preferred supplier is still 'approved' (O)
    for c in checks:
        if c["Parameter"] == "Supplier" and c["Rating"] == T:
            c["Rating"] = O
            c["Note"] += " (no ASI-T catalogue for CE/CK/CG yet: approved O)"
    _lifecycle_check(ed, checks)
    return _result(checks, flags, sub, {"cg": cg, "sub": sub})


def _result(checks, flags, sub, spec):
    rated = [c["Rating"] for c in checks if c["Rating"] is not None]
    overall = max(rated) if rated else O
    worst = [c["Parameter"] for c in checks if c["Rating"] == overall]
    summary = ("All rated parameters are recommended for new designs." if overall == T
               else "Approved part: ASI O." if overall == O and len(worst) == len(rated)
               else f"Worst-rated parameter(s): {', '.join(worst)}")
    return {"overall": overall, "label": LABEL[overall], "summary": summary, "subgroup": sub,
            "checks": checks, "flags": flags, "source": SOURCE, "c": spec}


def asi_from_extraction_c(extracted_data, manufacturer_text, cg_code, mpn="", pdf_text=""):
    if cg_code == "CC":
        return asi_cc(extracted_data, manufacturer_text, mpn, pdf_text)
    return asi_other(extracted_data, manufacturer_text, cg_code)


def no_rule_c(manufacturer_text, cg_code):
    return {"overall": None, "label": "No rule",
            "summary": f"No standardization rule is loaded for {cg_code} (rules exist for CC, CE, CK and CG).",
            "subgroup": "-", "checks": [], "flags": [], "source": "-"}


# ============================================================== alternatives
def render_c_alternatives(asi_result):
    import streamlit as st
    from ui_style import callout
    spec = asi_result.get("c")
    if not spec:
        callout("info", "No capacitor specification available.")
        return
    if asi_result["overall"] == T:
        callout("success", "Original part is ASI T: recommended for new designs.")
        return
    cg = spec["cg"]
    if cg == "CC" and spec.get("cap") and spec["sub"].startswith("Commodity"):
        rname, tb = cc_range(spec["cap"])
        if tb:
            callout("info" if asi_result["overall"] == O else "warning",
                    f"Original part is {asi_result['label']}. An ASI-T part in the {rname} range looks like this:")
            rows = [("Dielectric", _fmt_set(tb["dielectric"][0])), ("Package", _fmt_set(tb["package"][0])),
                    ("Value series", "0.1 pF step size" if tb["series"] == "step" else "E12 (E24)"),
                    ("Tolerance", _fmt_set(tb["tolerance"][0]) + f" {tb['tol_unit']}"),
                    ("Voltage", _fmt_set(tb["voltage"][0]) + " V"), ("Termination", "SN, no AEC-Q200 (unless needed)")]
            st.subheader("Target specification (ASI T)")
            st.table({"Parameter": [r[0] for r in rows], "Recommended (T)": [r[1] for r in rows]})
    else:
        callout("info" if asi_result["overall"] in (O, B) else "warning",
                f"Original part is {asi_result['label']} ({spec['sub']}). Choose a preferred / approved supplier below.")
    key = "CC" if cg == "CC" else "CK" if cg == "CK" else "CG" if cg == "CG" else ce_key_from_sub(spec["sub"])
    rows = []
    for _w, name, groups, note in SUPPLIERS:
        st_ = groups.get(key) or (groups.get("CC-special") if key == "CC" else None)
        if st_ == "TY":
            st_ = "Preferred (high cap / HV) / Approved"
        if st_ in (P, A) or (isinstance(st_, str) and st_.startswith("Preferred")):
            rows.append((name, st_, note or "-"))
    rows.sort(key=lambda r: 0 if str(r[1]).startswith("Preferred") else 1)
    if rows:
        st.subheader(f"Preferred / approved suppliers · {key}")
        st.table({"Manufacturer": [r[0] for r in rows], "Status": [r[1] for r in rows], "Note": [r[2] for r in rows]})
    st.caption("No DMS duplicate check for C*: search DMS manually for an existing material number "
               "(XOR rule: one part per capacitance for the marked parameters).")


def ce_key_from_sub(sub):
    return "CE-polymer" if "Polymer" in sub else "CE-tantalum" if "Tantalum" in sub else "CE-alu"


# =============================================================== designation
def clean_designation_c(text):
    """Enforce the former C* analyzer's designation rules: '0.10UF 20% 100V X7T 1210'."""
    s = str(text or "N/A").upper().replace("µ", "U").replace("Μ", "U").replace("±", "")
    s = re.sub(r"\b(KERAMIK|SILICON|FOLIE)-", "", s)
    s = re.sub(r"\bEIA(\d{4,5})\*?", r"\1", s).replace("*", "")
    s = re.sub(r"(\d)\s*MF\b", r"\1UF", s)                 # never 'MF' for microfarad
    return re.sub(r"\s+", " ", s).strip() or "N/A"
