"""
Washability / Varnishability codes for the Processability tab.

Source: PAD-M "Specifications for classification of washability and varnishability"
(3575.5490.00, CI 03.00, 2017-12-19), section 5.1 Table 5.1-1 (standard values per commodity group,
standard cleaning agent Vigon SC202) and section 4.1.1 (new materials default to K).

The code letters R, C, D-J, T-V, O (washability) and A, R, S (varnishability) mean R&S tested the part
in-house. Only Quality Management sets them, so the app only ever writes W, K, P, N / L, K, P, N.
"""

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


def _datasheet_says(extracted_data, key):
    item = extracted_data.get(key)
    val = item.get("value") if isinstance(item, dict) else item
    v = str(val or "").strip().lower()
    if v.startswith("yes"):
        return "Yes"
    if v.startswith("no"):
        return "No"
    return None


def apply_processability(extracted_data, cg_code):
    """Overwrite Washability / Varnishability with the PAD-M standard code for the commodity group.
    The datasheet statement is kept in the evidence; conflicts only produce warnings."""
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
    return warnings
