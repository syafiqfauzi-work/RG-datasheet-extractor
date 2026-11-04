"""
Commodity layer: one place that knows which categories, prompts and detection belong to
R* (resistors), L* (inductors) and C* (capacitors). app.py only talks to this module.

"EMI-Filter (Feedthrough-, Mains-)" exists in L* and C* (same DMS category, same fields), so
prompts and results are chosen by (commodity, category), not by the category name alone.
"""
from categories import CATEGORIES as R_CATEGORIES, RESISTOR, detect_category as detect_category_r
from categories_l import CATEGORIES_L, COIL, detect_category_l
from categories_c import CATEGORIES_C, CAP_FIXED, detect_category_c, detect_commodity
from prompts import build_prompt as build_prompt_r
from prompts_l import build_prompt_l
from prompts_c import build_prompt_c

COMMODITIES = {
    "R*": {"name": "Resistor", "categories": R_CATEGORIES, "default": RESISTOR, "detect": detect_category_r},
    "L*": {"name": "Inductor", "categories": CATEGORIES_L, "default": COIL, "detect": detect_category_l},
    "C*": {"name": "Capacitor", "categories": CATEGORIES_C, "default": CAP_FIXED, "detect": detect_category_c},
}
# Techn.Parameter lookup only (the shared EMI-Filter category has the same field list in L* and C*)
ALL_CATEGORIES = {**R_CATEGORIES, **CATEGORIES_L, **CATEGORIES_C}


def commodity_of(category, com=None):
    if com in COMMODITIES and category in COMMODITIES[com]["categories"]:
        return com
    if category in CATEGORIES_L:
        return "L*"
    if category in CATEGORIES_C:
        return "C*"
    return "R*"


def build_prompt_any(category, mpn_instruction, pdf_text, com=None):
    com = commodity_of(category, com)
    if com == "C*":
        return build_prompt_c(category, mpn_instruction, pdf_text)
    if com == "L*":
        return build_prompt_l(category, mpn_instruction, pdf_text)
    return build_prompt_r(category, mpn_instruction, pdf_text)


__all__ = ["COMMODITIES", "ALL_CATEGORIES", "commodity_of", "build_prompt_any", "detect_commodity", "RESISTOR",
           "COIL", "CAP_FIXED"]
