"""
Alternative part suggestions for RG resistors rated ASI-U/V.

Builds the replacement spec that the standardization rule would rate better
(package, value series, tolerance, SMT) and turns it into candidate MPNs
for the preferred/approved suppliers (Yageo RC_L, Vishay CRCW).

IMPORTANT: MPNs are generated from the manufacturers' part-number patterns.
They are NOT looked up in a live catalog, so every row carries distributor
search links for verification.
"""
import math
from urllib.parse import quote

import dms_lookup as dms
from asi_rules import (T, O, U, LABEL, E12_CLOSEST, E192_EXCLUSIVE, TOL_RULES,
                       _val, _num, _in, mantissa, parse_resistance,
                       parse_package, determine_asi)

SMT = "SMT (surface-mounting technology)"
SUPPLIERS = [("Yageo Corporation", "Yageo", "RC_L"),
             ("Vishay Intertechnology, Inc.", "Vishay", "CRCW")]
YAGEO_TOL = {0.1: "B", 0.25: "C", 0.5: "D", 1.0: "F", 5.0: "J"}
VISHAY_TOL = {0.1: "B", 0.5: "D", 1.0: "F", 5.0: "J"}
PKG_ORDER = ["0402", "1206", "1218", "2512"]
# standard (non high-power) rated power limit per package, in W
POWER_FIT = {"0402": 0.1, "1206": 0.25, "1218": 1.0, "2512": 2.0}
MAX_ROWS = 4


# ------------------------------------------------------------- formatting
def fmt_r(r):
    """4700.0 -> '4K7', 1.0 -> '1R', 4.75 -> '4R75'."""
    for div, ch in ((1e6, "M"), (1e3, "K"), (1.0, "R")):
        if r >= div * 0.999999:
            s = f"{r / div:.3f}".rstrip("0").rstrip(".")
            if "." in s:
                a, b = s.split(".")
                return f"{a}{ch}{b}"
            return f"{s}{ch}"
    return None


def vishay_code(r):
    """4-character value code: 1R00, 10R0, 100R, 1K00, 4K75."""
    s = fmt_r(r)
    ch = next(c for c in "RKM" if c in s)
    a, _, b = s.partition(ch)
    code = a + ch + b
    return code + "0" * (4 - len(code)) if len(code) < 4 else code


def mpn_yageo(pkg, r, tol):
    reel = "K" if pkg in ("1218", "2512") else "R"
    return f"RC{pkg}{YAGEO_TOL[tol]}{reel}-07{fmt_r(r)}L"


def mpn_vishay(pkg, r, tol):
    pack = {"0402": "ED", "1218": "EK", "2512": "EG"}.get(pkg, "EA")
    return f"CRCW{pkg}{vishay_code(r)}{VISHAY_TOL[tol]}K{pack}"


def search_links(mpn):
    q = quote(mpn)
    return (f"[DigiKey](https://www.digikey.com/en/products/result?keywords={q}) · "
            f"[Mouser](https://www.mouser.com/c/?q={q}) · "
            f"[Octopart](https://octopart.com/search?q={q})")


# ------------------------------------------------------------ spec logic
def snap_value(r):
    """Snap an E192-exclusive value to the nearest E96-closest-to-E12 value."""
    m = mantissa(r)
    if not _in(m, E192_EXCLUSIVE):
        return r, False
    best = min(E12_CLOSEST, key=lambda v: abs(math.log(v / m)))
    return round(best * (r / m), 6), True


def candidate_packages(pwr, orig_pkg):
    if pwr is None:
        return [orig_pkg] if orig_pkg in PKG_ORDER else ["0402", "1206"]
    fits = [p for p in PKG_ORDER if pwr <= POWER_FIT[p]]
    if orig_pkg in fits:
        fits.remove(orig_pkg)
        fits.insert(0, orig_pkg)
    return fits[:2]


def find_alternatives(resistance, tolerance, package, tc, mounting, tags, power, asi_result, dms_df=None):
    r = parse_resistance(resistance)
    tol = _num(tolerance)
    pkg0 = parse_package(package)
    tc0 = _num(tc)
    pwr = _num(power)
    tag_set = {t for t in str(tags or "").upper().replace("/", " ").split() if t}
    out = {"rows": [], "notes": [], "warnings": [], "spec": None}

    failing = [f"{c['Parameter']} ({c['Value']}): {c['Note']}"
               for c in asi_result["checks"] if c["Rating"] == U]
    if failing:
        out["notes"].append("Why ASI-U/V: " + "; ".join(failing))

    if r is None or pkg0 is None:
        out["warnings"].append("Resistance or package was not extracted, so no alternative can be built.")
        return out
    if r < 1:
        out["warnings"].append("Resistance < 1 Ohm is specific purpose (e.g. Vishay WSL, Isabellenhuette "
                               "ISA-PLAN): discuss with Procurement and the component engineer.")
        return out
    if tag_set & {"HF", "HV", "AS", "AIN", "AU", "AG", "CU", "SM", "FT", "PP"}:
        out["warnings"].append("The original carries special tags (" + "/".join(sorted(tag_set)) +
                               "). General-purpose RC_L/CRCW chips do not provide them, so the candidates "
                               "below must be checked against that requirement.")
    if pwr is not None and pwr > POWER_FIT["2512"]:
        out["warnings"].append(f"{pwr:g} W is above the standard chip range: consider a high power / "
                               "wirewound series and ask the component engineer.")
        return out

    r_new, snapped = snap_value(r)
    pkgs = candidate_packages(pwr, pkg0)
    tc_chk = 200 if r_new < 10 else 100  # typical general-purpose chip TC (confirm on datasheet)
    was_tht = any(k in (mounting or "").upper() for k in ("THW", "THR", "THROUGH"))

    out["spec"] = {"r": r_new, "tol": tol, "pkgs": pkgs, "pkg0": pkg0,
                   "pwr": pwr, "tc0": tc0, "was_tht": was_tht}

    rows = []
    for pkg in pkgs:
        t_set, o_set = TOL_RULES.get(pkg, (set(), set()))
        for mfr, short, series in SUPPLIERS:
            codes = YAGEO_TOL if short == "Yageo" else VISHAY_TOL
            tol_ok = tol is not None and _in(tol, t_set | o_set) and _in(tol, codes)
            tol_new = tol if tol_ok else 1.0
            mpn = mpn_yageo(pkg, r_new, tol_new) if short == "Yageo" else mpn_vishay(pkg, r_new, tol_new)
            res = determine_asi(manufacturer=mfr, resistance=fmt_r(r_new), tolerance=str(tol_new),
                                package=pkg, tc=str(tc_chk), mounting=SMT, tags="",
                                power=str(pwr) if pwr is not None else None)
            if res["overall"] is None or res["overall"] >= U:
                continue
            diffs = []
            if snapped:
                diffs.append(f"value {fmt_r(r)} -> {fmt_r(r_new)}")
            if tol is not None and abs(tol - tol_new) > 1e-9:
                diffs.append(f"tolerance {tol:g}% -> {tol_new:g}%")
            if pkg != pkg0:
                diffs.append(f"package {pkg0} -> {pkg} (new footprint)")
            if was_tht:
                diffs.append("THT -> SMT")
            if tc0 is not None and tc0 < tc_chk:
                diffs.append(f"TC {tc0:g} ppm vs typical {tc_chk} ppm: check datasheet")
            rows.append({
                "sort": (res["overall"], PKG_ORDER.index(pkg), 0 if short == "Yageo" else 1),
                "Match": "Exact spec" if not diffs else "Similar spec",
                "Manufacturer": short, "Series": series, "MPN": mpn, "Package": pkg,
                "Value/Tol": f"{fmt_r(r_new)} / {tol_new:g}%", "ASI": res["label"],
                "Differences": "; ".join(diffs) or "-", "Verify": search_links(mpn),
                "InDMS": dms.mpn_status(dms_df, mpn),
            })

    rows.sort(key=lambda x: x["sort"])
    out["rows"] = rows[:MAX_ROWS]
    if not out["rows"]:
        out["warnings"].append("No general-purpose chip option reaches ASI-T/O for this spec. "
                               "Ask the component engineer about a specific purpose series.")
    elif all(x["ASI"] == "ASI-O" for x in out["rows"]):
        out["notes"].append("No ASI-T option exists at this power/package: the best available is ASI-O.")
    return out


# --------------------------------------------------------- app integration
def render_alternatives(extracted_data, designation_text, manufacturer_text, asi_result,
                        dms_df=None, target_mpn="", cg_code="RG"):
    import streamlit as st
    if cg_code == "RT":
        from rules_rt import render_rt_alternatives
        render_rt_alternatives(asi_result, dms_df)
        return
    if cg_code not in ("RG", "Unknown"):
        st.info(f"Alternative suggestions are not available for {cg_code} yet (no standardization rule loaded).")
        return

    # the DMS ASI of an existing material number governs over the rule-based result
    dms_bad = False
    if dms_df is not None and str(target_mpn).strip():
        exact, _ = dms.find_mpn(dms_df, target_mpn)
        if len(exact):
            b = exact.iloc[0]
            if b["_asi"] in dms.AVOID_ASI:
                dms_bad = True
                st.warning(f"DMS lists {b['Material Number']} as ASI {b['_asi']}: {dms.ASI_MEANING[b['_asi']]}.")

    if asi_result["overall"] != U and not dms_bad:
        st.info(f"Original part is {asi_result['label']}: alternatives are only suggested for ASI-U/V.")
        return

    parts = str(designation_text).split()
    tags = " ".join(parts[5:]) if len(parts) > 5 else ""
    res = find_alternatives(
        resistance=_val(extracted_data, "Resistance (Ohm)"),
        tolerance=_val(extracted_data, "Tolerance (%)"),
        package=_val(extracted_data, "Package Type"),
        tc=_val(extracted_data, "Temperature Coefficient"),
        mounting=_val(extracted_data, "Kind of Mounting"),
        tags=tags,
        power=_val(extracted_data, "Power Consumption (W)"),
        asi_result=asi_result,
        dms_df=dms_df,
    )
    for n in res["notes"]:
        st.info(n)

    # --- 1) parts that already exist in DMS (ASI T/O)
    st.subheader("Already in DMS (ASI T/O)")
    if dms_df is None:
        st.caption("Upload the DMS export in the sidebar (🗄️ DMS Database) to see existing material numbers.")
    elif res["spec"] is None:
        st.caption("No replacement spec could be built, so DMS was not searched.")
    else:
        found = dms.find_better(dms_df, **res["spec"])
        if found:
            st.table({
                "#": [str(i) for i in range(1, len(found) + 1)],
                "Material Number": [x["Material Number"] for x in found],
                "MPN": [x["MPN"] for x in found],
                "Manufacturer": [x["Manufacturer"] for x in found],
                "ASI": [x["ASI"] for x in found],
                "Package": [x["Package"] for x in found],
                "Value / Tol": [x["Value/Tol"] for x in found],
                "Power (W)": [x["Power"] for x in found],
                "TC (ppm)": [x["TC"] for x in found],
                "Match": [x["Match"] for x in found],
                "Differences": [x["Differences"] for x in found],
            })
        else:
            st.info("No released ASI T/O part in DMS matches this value and an acceptable package.")

    # --- 2) new part suggestions
    if res["rows"]:
        st.subheader("New part suggestions")
        st.table({
            "#": [str(i) for i in range(1, len(res["rows"]) + 1)],
            "Match": [x["Match"] for x in res["rows"]],
            "Manufacturer": [f"{x['Manufacturer']} ({x['Series']})" for x in res["rows"]],
            "Suggested MPN": [x["MPN"] for x in res["rows"]],
            "Package": [x["Package"] for x in res["rows"]],
            "Value / Tol": [x["Value/Tol"] for x in res["rows"]],
            "Expected ASI": [x["ASI"] for x in res["rows"]],
            "In DMS?": [x["InDMS"] for x in res["rows"]],
            "Differences": [x["Differences"] for x in res["rows"]],
        })
        st.write("**Verify availability:**")
        for i, x in enumerate(res["rows"], 1):
            st.markdown(f"{i}. {x['MPN']}: {x['Verify']}")
    for w in res["warnings"]:
        st.warning(w)
    st.caption("New-part MPNs are generated from the manufacturers' part-number patterns, not looked up in a "
               "live catalog. Open the DigiKey/Mouser/Octopart links to confirm the part exists, then confirm "
               "the ASI in DMS and with the component engineer.")
