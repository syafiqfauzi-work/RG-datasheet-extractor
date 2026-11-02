"""
Commodity layer: one place that knows which categories, prompts and detection belong to
R* (resistors) and L* (inductors). app.py only talks to this module.
"""
from categories import CATEGORIES as R_CATEGORIES, RESISTOR, detect_category as detect_category_r
from categories_l import CATEGORIES_L, COIL, detect_category_l, detect_commodity
from prompts import build_prompt as build_prompt_r
from prompts_l import build_prompt_l

COMMODITIES = {
    "R*": {"name": "Resistor", "categories": R_CATEGORIES, "default": RESISTOR, "detect": detect_category_r},
    "L*": {"name": "Inductor", "categories": CATEGORIES_L, "default": COIL, "detect": detect_category_l},
}
ALL_CATEGORIES = {**R_CATEGORIES, **CATEGORIES_L}


def commodity_of(category):
    return "L*" if category in CATEGORIES_L else "R*"


def build_prompt_any(category, mpn_instruction, pdf_text):
    if category in CATEGORIES_L:
        return build_prompt_l(category, mpn_instruction, pdf_text)
    return build_prompt_r(category, mpn_instruction, pdf_text)


__all__ = ["COMMODITIES", "ALL_CATEGORIES", "commodity_of", "build_prompt_any", "detect_commodity", "RESISTOR", "COIL"]
