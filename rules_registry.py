"""Dispatcher: picks the ASI rule set for the detected commodity group."""
from asi_rules import asi_from_extraction
from rules_rt import asi_from_extraction_rt

RULE_CGS = ("RG", "RT")   # groups that have a standardization rule loaded


def determine_asi_for_cg(cg_code, extracted_data, designation_text, manufacturer_text,
                         pdf_text="", file_names=(), category=None):
    if cg_code in ("RG", "Unknown"):       # unknown groups are treated like RG, as before
        return asi_from_extraction(extracted_data, designation_text, manufacturer_text)
    if cg_code == "RT":
        return asi_from_extraction_rt(extracted_data, manufacturer_text, pdf_text, file_names, category)
    return {"overall": None, "label": "No rule",
            "summary": f"No standardization rule is loaded for {cg_code} yet.",
            "subgroup": "-", "checks": [], "flags": []}
