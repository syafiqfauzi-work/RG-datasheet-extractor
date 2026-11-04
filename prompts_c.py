"""
Extraction prompts for the C* (capacitor) commodity.

Re-uses the shared template of prompts.py (Top / Library / Processability rules) and swaps in:
  * the C* manufacturer list (from the former C* analyzer),
  * the C* category rules from categories_c.py,
  * the capacitor pitch rule (L - T, terminal band) and the designation rule of the former C* analyzer,
  * the hidden helper keys used by the CC / CE / CK / CG standardization rule.
"""
import re

from prompts import OTHER_TEMPLATE, BASE_KEYS
from categories_c import CATEGORIES_C, C_CG_OPTIONS, CATEGORY_CG, MANUFACTURERS_C

_MFR_LINE = re.compile(r'^\s*- FOR "Manufacturer":.*$', re.M)

MANUFACTURER_RULE = (
    '            - FOR "Manufacturer": Identify the manufacturer of the component from the datasheet. If it is one of '
    "these, return the name exactly as written: "
    + ", ".join(f'"{n}"' for n in MANUFACTURERS_C)
    + '. Johanson / JDI / Johanson Dielectrics -> "Johanson Precision Corporation"; AVX, Kyocera AVX and ATC '
    '(American Technical Ceramics) -> "Kyocera AVX Components Ltd."; TDK and EPCOS -> "TDK Corporation". Choose a '
    "name from this list ONLY if that company name is printed in the datasheet. If the manufacturer is not in this "
    "list (e.g., KEMET, Walsin, Cornell Dubilier, Skyworks), return its company name exactly as printed in the "
    "datasheet - never substitute a listed name.")

COMMON_C_RULES = '''
            [C* COMMON RULES]
            - The [CATEGORY RULES] above and these C* rules OVERRIDE the [GENERAL RULES] where they differ (e.g., "Package Type", "Pitch").
            - PICK-LIST RULE: For every field with a DMS list, return the list value exactly as written when one fits. Only if nothing fits, return a short free-text value. Return "N/A" when the datasheet gives no information - never invent a value.
            - FOR "Pitch_Calculation_Logic" (capacitors): 1) State the nominal Length (L) in mm. 2) State the nominal terminal / termination band width (T, also called BW or E) in mm. 3) Output AT THE VERY END exactly: "Formula: L - T" (e.g., "Formula: 1.60 - 0.35"). For leaded parts with a lead spacing, write "Formula: <lead spacing> - 0".
            - FOR "Commodity Group": Select ONLY ONE code: {cg_list}. For this category the usual groups are: {cg_hint}. A standard MLCC / ceramic chip capacitor is "CC"; film -> "CK"; mica -> "CG"; aluminium / tantalum / polymer electrolytic -> "CE"; trimmer -> "CT".
            - FOR "Category": Select ONLY ONE DMS category from this exact list: {cat_list}.
            - FOR "Designation": Build ONE string in EXACTLY this format: [Capacity] [Tolerance] [Voltage] [Dielectric] [Package EIA]. Example: "0.10UF 20% 100V X7T 1210".
              * [Capacity]: the value with its unit in capitals: "PF", "NF" or "UF" (never "MF" and never "µ"), e.g. "4.7PF", "100NF", "0.10UF", "10UF".
              * [Tolerance]: the numeric percentage with "%" (e.g., "5%", "20%"), never the letter code (J, K, M) and without "±". For absolute tolerances of small values use pF, e.g. "0.1PF".
              * [Voltage]: the rated voltage with "V" (e.g., "50V").
              * [Dielectric]: the dielectric WITHOUT category prefixes such as "KERAMIK-", "SILICON-" or "FOLIE-" (e.g., "X7R", "C0G", "PP").
              * [Package EIA]: the bare EIA size code only (e.g., "0603"), without "EIA" or "*"; leave it out for leaded parts.
            - FOR "Lifecycle Status": Select ONLY ONE: "Active", "NRND" (the datasheet marks the part or series 'not recommended for new design'), "Discontinued" (obsolete, end of life, last time buy) or "N/A" if the datasheet does not say.
            - FOR "Series": The manufacturer series / product family name exactly as printed (e.g., "GRM", "GJM", "Accu-P", "600S", "100B", "CC", "X7R General Purpose", "C0G Flex"), or "N/A".
            - FOR "Tolerance_Raw": The tolerance exactly as stated for the target part, WITH its unit (e.g., "±0.05 pF", "±5 %", "±10 %"), or "N/A".
            - FOR "Electrolyte Type": Only for electrolytic capacitors select ONE: "Aluminium", "Aluminium Polymer", "Hybrid Polymer", "Tantalum Polymer", "Tantalum MnO2", "Wet Tantalum", "Niobium Oxide"; otherwise "N/A".
            - FOR "Flexible Termination": "Yes" if the part has a flexible / soft / polymer / super termination (FlexiTerm, Flex Term, soft termination, polymer termination), otherwise "No".
            - FOR "AEC-Q200": "Yes" if the part is AEC-Q200 qualified or sold as automotive grade, otherwise "No".
            - FOR "Insulating Sleeve": For electrolytic capacitors "Yes" if the can has an insulating cover / heat-shrinkable sleeve, "No" if it has none; otherwise "N/A".
            - FOR "Sealing Disk": For trimmer capacitors "Yes" if the part is sealed (sealing disk, sealed / washable construction), "No" if it is open; otherwise "N/A".
            - FOR "Coated": For film capacitors "Yes" if the part has a coating / encapsulation (e.g., epoxy coated, plastic case), "No" if uncoated; otherwise "N/A".
            - FOR "Stacked": "Yes" if the part is a stacked MLCC (several chips stacked with metal frame / leads), otherwise "No".
'''


def build_prompt_c(category, mpn_instruction, pdf_text):
    cfg = CATEGORIES_C[category]
    allowed, _default = CATEGORY_CG[category]
    common = COMMON_C_RULES.format(
        cg_list=", ".join(f'"{c}" ({d})' for c, d in C_CG_OPTIONS.items()),
        cg_hint=", ".join(f'"{c}"' for c in allowed),
        cat_list=", ".join(f'"{c}"' for c in CATEGORIES_C),
    )
    keys = BASE_KEYS + ", " + ", ".join(f'"{k}"' for k in cfg["extra_keys"])
    template = _MFR_LINE.sub(lambda _m: MANUFACTURER_RULE, OTHER_TEMPLATE, count=1)
    return (template.replace("{category_rules}", cfg["rules"].rstrip("\n") + "\n" + common.rstrip("\n"))
            .replace("{category}", category)
            .replace("{keys}", keys)
            .replace("{mpn_instruction}", mpn_instruction)
            .replace("{pdf_text}", pdf_text))
