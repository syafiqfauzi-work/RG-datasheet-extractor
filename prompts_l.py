"""
Extraction prompts for the L* (inductor) commodity.

Re-uses the shared template of prompts.py (Top / Library / Processability rules) and swaps in:
  * the L* approved manufacturer list,
  * the L* category rules from categories_l.py,
  * the hidden helper keys used by the L* rules (commodity group, construction, lifecycle, category).
"""
import re

from prompts import OTHER_TEMPLATE, BASE_KEYS
from categories_l import CATEGORIES_L, L_CG_OPTIONS, CATEGORY_CG, AML

_MFR_LINE = re.compile(r'^\s*- FOR "Manufacturer":.*$', re.M)

MANUFACTURER_RULE = (
    '            - FOR "Manufacturer": Identify the manufacturer of the component from the datasheet. If it is one of '
    "these, return the name exactly as written: "
    + ", ".join(f'"{n}"' for n in AML)
    + ". TDK and EPCOS are both \"TDK Corporation\". Choose a name from this list ONLY if that company name is "
    "printed in the datasheet. If the manufacturer is not in this list (e.g., Bourns, Laird, Sumida), return its "
    "company name exactly as printed in the datasheet - never substitute a listed name.")

COMMON_L_RULES = '''
            [L* COMMON RULES]
            - The [CATEGORY RULES] above OVERRIDE the [GENERAL RULES] where they differ (e.g., "Package Type").
            - PICK-LIST RULE: For every field with a DMS list, return the list value exactly as written when one fits. Only if nothing fits, return a short free-text value. Return "N/A" when the datasheet gives no information - never invent a value.
            - FOR "Commodity Group": Select ONLY ONE code: {cg_list}. For this category the usual groups are: {cg_hint}. A coil or choke WITHOUT an air core is "LD"; an air-core coil is "LL".
            - FOR "Construction": Select ONLY ONE: "Multilayer" (multilayer / ceramic multilayer chip), "Wirewound" (wire-wound, incl. wire-wound chips), "Thin film", "Air core", "Other" or "N/A".
            - FOR "Lifecycle Status": Select ONLY ONE: "Active", "NRND" (the datasheet marks the part 'not recommended for new design'), "Discontinued" (obsolete, end of life, last time buy) or "N/A" if the datasheet does not say.
            - FOR "Category": Select ONLY ONE DMS category from this exact list: {cat_list}.
'''


def build_prompt_l(category, mpn_instruction, pdf_text):
    cfg = CATEGORIES_L[category]
    allowed, _default = CATEGORY_CG[category]
    common = COMMON_L_RULES.format(
        cg_list=", ".join(f'"{c}" ({d})' for c, d in L_CG_OPTIONS.items()),
        cg_hint=", ".join(f'"{c}"' for c in allowed),
        cat_list=", ".join(f'"{c}"' for c in CATEGORIES_L),
    )
    keys = BASE_KEYS + ", " + ", ".join(f'"{k}"' for k in cfg["extra_keys"])
    template = _MFR_LINE.sub(lambda _m: MANUFACTURER_RULE, OTHER_TEMPLATE, count=1)
    return (template.replace("{category_rules}", cfg["rules"].rstrip("\n") + "\n" + common.rstrip("\n"))
            .replace("{category}", category)
            .replace("{keys}", keys)
            .replace("{mpn_instruction}", mpn_instruction)
            .replace("{pdf_text}", pdf_text))
