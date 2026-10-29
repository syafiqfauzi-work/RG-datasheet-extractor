"""
Deterministic checks that back up the AI extraction for fields that must not
change between runs (manufacturer, commodity group).

The AI answer is only replaced when the evidence is strong:
  * file name hit  -> weight 6 (manufacturer) / 5 (group)
  * first 3000 characters of the text -> weight 3 per hit
  * whole text -> 1 per hit, capped at 10
A score of 8 or more is treated as confident.
"""
import re

# canonical name (exactly as in the AI prompt list) -> keywords
MANUFACTURERS = {
    "Analog Devices, Inc.": ["analog devices"],
    "Barry Industries Inc.": ["barry industries"],
    "Bourns Inc.": ["bourns"],
    "Caddock Electronics, Inc": ["caddock"],
    "Diconex": ["diconex"],
    "EMC TECHNIK & CONSULTING GmbH": ["emc technik"],
    "Fenghua (H.K.) Electronics Ltd.": ["fenghua"],
    "IMS - International Manufacturing S": ["international manufacturing services"],
    "Kyocera AVX Components Ltd.": ["kyocera avx", "avx corporation", "kyocera"],
    "Littelfuse, Inc.": ["littelfuse"],
    "Mini-Circuits, Inc.": ["mini-circuits", "minicircuits"],
    "Panasonic Corporation": ["panasonic"],
    "RES-NET Microwave, Inc.": ["res-net", "resnet microwave"],
    "Smiths Interconnect": ["smiths interconnect"],
    "Susumu Co., LTD": ["susumu"],
    "TDK Corporation": ["tdk"],
    "TTM Technologies Inc.": ["ttm technologies"],
    "Vishay Intertechnology, Inc.": ["vishay"],
    "Yageo Corporation": ["yageo"],
}

# commodity group -> keywords (RG is the default, so it has no patterns)
CG_PATTERNS = {
    "RK": ["thermistor", "ptc", "ntc", "pptc", "varistor", "polyswitch", "resettable",
           "hold current", "trip current", "positive temperature coefficient",
           "negative temperature coefficient"],
    "RS": ["potentiometer", "trimmer", "wiper"],
    "RT": ["attenuator"],
}


def _rx(word):
    # letters on both sides are not allowed, but '_' and '-' are (file names use them)
    return rf"(?<![a-z]){word}(?![a-z])"


def _hits(words, text):
    return sum(len(re.findall(_rx(w), text, flags=re.I)) for w in words)


def _score(words, names, head, text, w_name):
    return w_name * _hits(words, names) + 3 * _hits(words, head) + min(_hits(words, text), 10)


def detect_manufacturer(pdf_text, file_names=()):
    """Canonical manufacturer name, or None when the evidence is weak."""
    names, head = " ".join(file_names), pdf_text[:3000]
    best, best_score = None, 0
    for canon, words in MANUFACTURERS.items():
        sc = _score(words, names, head, pdf_text, 6)
        if sc > best_score:
            best, best_score = canon, sc
    return best if best_score >= 8 else None


def quantity_from(extracted_data):
    item = extracted_data.get("Quantity")
    val = item.get("value") if isinstance(item, dict) else item
    m = re.search(r"\d+", str(val or ""))
    return int(m.group()) if m else None


def detect_commodity_group(pdf_text, file_names, ai_code, quantity=None):
    """Return the commodity group code; overrides the AI answer only on strong evidence."""
    names, head = " ".join(file_names), pdf_text[:3000]
    scores = {cg: _score(words, names, head, pdf_text, 5) for cg, words in CG_PATTERNS.items()}
    cg, sc = max(scores.items(), key=lambda kv: kv[1])
    if sc >= 8 or (ai_code == "Unknown" and sc >= 4):
        return cg
    if quantity is not None and quantity >= 2 and ai_code in ("RG", "Unknown"):
        return "RN"
    return ai_code
