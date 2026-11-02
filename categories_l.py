"""
L* (inductor) DMS categories: Techn.Parameter fields, pick lists, extraction rules,
commodity groups, approved manufacturer list and detection.

Same structure as categories.py. Only the Techn.Parameter tab differs per category;
Top, Library and Processability stay the same. Numeric values are plain absolute
numbers (DMS adjusts the unit itself), e.g. 10 nH -> 0.00000001.

Pick-list rule (all categories): use the DMS list value when one fits; only when
nothing fits, write a short free-text value.
"""
import re

COIL = "Coil"

# ------------------------------------------------------------ commodity groups
# active L* groups (obsolete LC, LE, LI, LV, LW, LX, LZ are ignored)
L_CG_OPTIONS = {
    "LB": "sheet metal and cut strip-wound core with accessories",
    "LD": "choke, coil or filter without air-core coils",
    "LF": "ferrite core with accessories",
    "LK": "carbonyl iron core and electric copper core with accessories",
    "LL": "coil - air-core",
    "LM": "memory - media",
    "LP": "permanent magnet",
    "LS": "shielding can",
    "LT": "main transformer",
    "LU": "transformer",
}

# approved manufacturer list (AML) per commodity group: canonical name -> (keywords, groups)
AML = {
    "API DELEVAN": (["api delevan", "delevan"], ("LL", "LD")),
    "COILCRAFT": (["coilcraft"], ("LL", "LD")),
    "FERROXCUBE": (["ferroxcube"], ("LF",)),
    "HAUFE GmbH & Co. KG": (["haufe"], ("LU",)),
    "Inductron": (["inductron"], ("LU",)),
    "Mini-Circuits, Inc.": (["mini-circuits", "minicircuits", "mini circuits"], ("LU",)),
    "Murata Manufacturing Co., Ltd": (["murata"], ("LL", "LD")),
    "NGAI HENG BOOK-Binders PTE LTD": (["ngai heng"], ("LM",)),
    "Neosid Pemetzrieder": (["neosid"], ("LU", "LL", "LD")),
    "Piconics Inc": (["piconics"], ("LL", "LD")),
    "Pikatron GmbH": (["pikatron"], ("LU", "LT")),
    "Shenzhen Sunlord Electronics Co., L": (["sunlord"], ("LL", "LD")),
    "TDK Corporation": (["tdk", "epcos"], ("LL", "LF", "LD")),   # LI is obsolete
    "Vishay Intertechnology, Inc.": (["vishay"], ("LL", "LD")),
    "Würth Elektronik GmbH & Co. KG": (["würth", "wurth", "wuerth"], ("LL", "LK", "LF", "LD")),
}

# category -> (commodity groups allowed for it, default group)
CATEGORY_CG = {
    "Accessories R L C": (("LS", "LF", "LB", "LK", "LD", "LL"), "LF"),
    "Coil": (("LD", "LL"), "LD"),
    "Cores": (("LF", "LK", "LB"), "LF"),
    "Directional Coupler": (("LU",), "LU"),
    "EMI-Filter (Feedthrough-, Mains-)": (("LD", "LF"), "LD"),
    "Inductance": (("LD", "LL"), "LD"),
    "Permanent Magnet": (("LP",), "LP"),
    "Shielding Gasket": (("LS",), "LS"),
    "Transducer / Transformer": (("LU", "LT"), "LU"),
}

# ------------------------------------------------------------------ pick lists
# (DMS value, meaning). The DMS value (left column) is what the app writes.
ACCESSORY_FUNCTION = [
    ("ABGLEICHSCHRAUBE", "trimming screw"), ("ABGLEICHSCHRAUBENDREHER", "trimming screw driver / tuning tool"),
    ("ABSCHIRMBECHER", "shielding can"), ("ABSCHIRMTOPF", "screen can"), ("ANTRIEBSWELLE", "drive shaft"),
    ("GUMMIRING", "rubber ring"), ("HALTERUNG", "holder"), ("ISOLIERBECHER", "insulating can"),
    ("ROHR", "tube"), ("SCHLUESSEL FUER KLAPPFERRIT", "key for split ferrite"),
    ("TUELLE", "grommet / sleeve"), ("UNTERLEGER", "washer / spacer"),
]
COIL_SURFACE = [
    ("AG", "silver"), ("AG / PD", "silver palladium"), ("AG/PD/PT", "silver palladium platinum"),
    ("AG/PD/PT GLASS FRIT", "silver palladium platinum glass frit"), ("AU", "gold"),
    ("AU/NI/PD/PT GLASS FRIT", "gold nickel palladium platinum glass frit"), ("NI / SN", "nickel tin"),
    ("SN", "tin"), ("SN / AG / CU", "tin silver copper"), ("SN-AG-CU/CU", "tin-silver-copper / copper"),
    ("SN-AG-CU/SN/NI/AGPT", "tin-silver-copper / tin / nickel / silver-platinum"),
    ("SN/NI/AG GLASS FRIT", "tin nickel silver glass frit"),
    ("SN/NI/AG/PT GLASS FRIT", "tin nickel silver platinum glass frit"),
]
COIL_FUNCTION = [
    ("AIR CORE INDUCTOR", "air-core coil"), ("AIR CORE INDUCTOR TUNABLE", "tunable air-core coil"),
    ("BROADBAND CONICAL INDUCTOR", "conical broadband inductor"), ("CHOKE", "choke"),
    ("CHOKE SHIELDED", "shielded choke"), ("FIELD COIL", "field coil"), ("INDUCTOR", "inductor"),
    ("INDUCTOR SHIELDED", "shielded inductor"), ("MULTILAYER CHIP", "multilayer chip inductor"),
    ("POWER CHOKE", "power choke / power inductor"), ("POWER CHOKE SHIELDED", "shielded power choke / power inductor"),
    ("TUNABLE", "tunable inductor"), ("WIDEBAND BIAS CHOKE", "broadband bias choke"),
    ("WIRE WOUND", "wirewound inductor"),
]
COIL_PACKAGE = [(f"EIA{s}*", "SMD") for s in ("01005", "0201", "0302", "0402", "0603", "0805", "1008", "1111",
                                               "1206", "1210", "1214", "1616", "1808", "1812", "2220")] + [
    ("*AXIAL*", "axial leaded"), ("*FLYING LEADS*", "flying leads"), ("*RADIAL*", "radial leaded"),
    ("*RM*", "grid / pin-through-hole on a raster"), ("*SMD*", "other SMD"),
]
CORE_FUNCTION = [
    ("ABGLEICHKERN", "tuning slug"), ("BUEGEL", "clip"), ("DOPPELLOCHKERN", "twin aperture core"),
    ("EINSTELLKERN", "tuning core"), ("FLACHKERN", "flat core"), ("GEWINDEKERN", "thread core"),
    ("HALTERUNG", "bracket"), ("ISOLIERSCHEIBE", "insulating disc"), ("KLAMMER", "clamp"),
    ("KLAPPKERN", "book core / split clamp-on ferrite"), ("LOCHKERN", "aperture core"),
    ("RINGKERN", "toroidal core / ring core"), ("ROHRKERN", "tube core / cable ferrite"), ("SCHALENKERN", "pot core"),
    ("SPULENKOERPER", "bobbin / coil former"), ("STABKERN", "ferrite bar / rod"), ("TOPFKERN", "cup core"),
    ("WICKELKOERPER", "winding form"), ("ZYLINDERKERN", "cylindrical core"),
]
CORE_MATERIAL = [(m, "") for m in (
    "EISEN-PULVER F10B K1 K1-LACKIERT K12 K32 M33 N22 N22-LACKIERT N26 N27 N28 N30 N30-LACKIERT N4 N41 N48 N67 "
    "N87 T10 T26 T35 T38 U17 U17-LACKIERT U60 U60-LACKIERT CN20 C10J C/7D FE810 FI110 F02 F100 F100b F40 G2 J2 K2 "
    "K250 M11 T1 T46 3B1 3B8 3C8 3E25 3F3 3H2 3W800 4B1 4C65 4S2 4W1500 4W620 500F").split()]
CORE_FILTER_TYPE = [(v, "") for v in ("BEAD", "C-FILTER", "EMI", "HELIX-FILTER", "LC-FILTER", "L-FILTER",
                                      "PI-FILTER", "RC-FILTER", "T-ARRAY*", "T-FILTER")]
COLOR = [("BLAU", "blue"), ("GELB", "yellow"), ("GRAU", "grey"), ("GRUEN", "green"), ("ORANGE", "orange"),
         ("ROT", "red"), ("ROT-WEISS", "red-white"), ("SCHWARZ", "black"), ("VIOLETT", "violet"), ("WEISS", "white")]
COUPLER_FUNCTION = [("Directional Coupler", "directional coupler"), ("RF Crossover", "HF-Brücke / crossover")]
COUPLER_CONNECTOR = [("SMD", "surface-mounted device, no connector"), ("SMA", "SMA, rated to 18 GHz"),
                     ("PC2.92mm", "precision 2.92 mm connector, rated to 40 GHz"),
                     ("N-Type", "type N connector, rated to 18 GHz"), ("7/16", "7/16 DIN connector"),
                     ("FME", "for mobile equipment connector, rated to 2 GHz")]
EMI_FUNCTION = [("Feed Through Filter", "Durchführungsfilter"), ("Mains/Line/Power Filter", "mains / line / power filter"),
                ("Data Line Filter", "signal / data line filter, ferrite beads, common mode chokes for data lines")]
EMI_FILTER_TYPE = [("*BEAD*", "ferrite bead / bead array"), ("C-FILTER", "capacitor filter"),
                   ("CM-CHOKE", "common mode choke"), ("CM-FILTER", "common mode filter"),
                   ("LC-TP", "LC low pass"), ("LC-TP-PI", "LC low pass pi section"), ("LC-TP-T", "LC low pass T section"),
                   ("RC-FILTER", "RC filter"), ("MODUL", "filter module"), ("1PH-FILTER", "single phase mains filter"),
                   ("3PH-FILTER", "three phase mains filter")]
EMI_PACKAGE = [("*0201*", "SMD"), ("*0402*", "SMD"), ("*0603*", "SMD"), ("*0805*", "SMD"), ("*1206*", "SMD"),
               ("*1210*", "SMD"), ("*2512*", "SMD"), ("MODUL", "module"), ("FEED THROUGH", "feedthrough"),
               ("*PRESS-IN*", "press-in"), ("*SCREW-IN*", "screw-in"), ("*SMD*", "other SMD"),
               ("*SOLDER-IN*", "solder-in")]
MAGNET_FUNCTION = [("Magnet", "permanent magnet")]
GASKET_DESCRIPTION = [
    ("FORM", "form part"), ("GEWEBE", "mesh"), ("HAUBE", "board level shield / shielding cover"),
    ("LEITSCHAUM", "conductive foam"), ("PLATTE", "conductive tape / sheet"),
    ("SCHNUR", "elastomer conductive filled"), ("SCHNUR_BESCHICHTET", "elastomer coated"),
    ("SCHNUR+MONEL", "elastomer with Monel"), ("SCHNUR_UMSTRICKT", "elastomer mesh / knitted"),
    ("SPIRALE", "spiral"), ("WABENKAMM", "vent panels / honeycomb")]
GASKET_MATERIAL = [
    ("STAHL", "steel"), ("AL", "aluminium"), ("AL+KAUTSCHUK", "aluminium + rubber"),
    ("CR+CUNI", "chloroprene rubber + Monel"), ("CR-SCHAUM+CUNI", "chloroprene rubber foamed + Monel"),
    ("CU", "copper"), ("CUNI", "CuNi Monel mesh (Monel, Triconit)"), ("ECOFOAM 700", "Ecofoam 700"),
    ("KAUTSCHUK+NI+CU", "rubber + CuNi"), ("PA+CUNIPH", "polyamide + CuNi phosphor coating"),
    ("PE-SCHAUM", "polyethylene foamed"), ("POLYEST+PU-SCHAUM+CUNI", "polyester mesh + polyurethane foam, CuNi coating"),
    ("POLYEST+TPE-SCHAUM+CUNI", "polyester mesh + rubber foam, CuNi coating"), ("PUR-SCHAUM", "polyurethane foamed"),
    ("PUR-SCHAUM+CUNI", "polyurethane foam, copper and nickel plated"), ("SI", "silicone + conductive coating"),
    ("SI+AG", "silver filled silicone, e.g. CHO-SIL 1401, 1405"),
    ("SI+AL-AG", "silver-plated aluminium filled silicone, e.g. ECP876, CHO-SEAL 1285"),
    ("SI+BOR-NITRID", "boron nitride filled silicone, e.g. CHO-THERM 1671"),
    ("SI+CU-AG", "silver-plated copper filled silicone, e.g. SHIELDSEAL 103, CHO-SEAL 1215"),
    ("SI+CUNI", "CuNi filled silicone, e.g. SINCUFE"), ("SI+CUZN-AG", "silver-plated brass filled silicone"),
    ("SI+NI", "nickel filled silicone"), ("SI+NI-AG", "silver-plated nickel filled silicone"),
    ("SI+NI-C", "nickel filled silicone, carbon coating / nickel-graphite filled"),
    ("SI-SCHAUM+CUNI", "silicone foamed + Monel"), ("ST", "steel")]
GASKET_FILLER = [("AL-AG", "silver plated aluminium particle"), ("CU-AG", "silver plated copper particle"),
                 ("CUNI", "copper nickel particle"), ("NI", "nickel particle"), ("NI-AG", "silver plated nickel particle"),
                 ("NI-C", "nickel particle carbon coated / nickel-graphite")]
GASKET_SHAPE = [("D-PROF", "D profile"), ("FLACH", "plain / flat"), ("O-HOHL-PROF", "O hollow profile"),
                ("O-PROF", "O profile, solid round"), ("P-PROF", "P profile"), ("SONDER-PROF", "special profile"),
                ("4KT-PROF", "square profile")]
GASKET_SURFACE = [("AG", "silver coated"), ("CU-AG", "copper-silver coated"),
                  ("SELBSTKLEBEND", "one sided self adhesive"), ("STKLEBEND-BEID", "both sides self adhesive"),
                  ("ZN", "CRS-tin / tin plated")]
TRAFO_FUNCTION = [
    ("RF TRANSFORMER", "HF Übertrager"), ("AF TRANSFORMER", "NF Übertrager, audio"), ("TRANSFORMER", "general"),
    ("LAN TRANSFORMER", "LAN / Ethernet magnetics"), ("LAN TRANSFORMER POE", "LAN magnetics with PoE"),
    ("COUPLED INDUCTORS", "coupled inductors"), ("FLYBACK", "flyback transformer, Sperrwandler"),
    ("FLYBACK POE", "flyback transformer for PoE"), ("BALUN", "balun, Symmetrieübertrager"),
    ("MAINS TRANSFORMER", "mains transformer, Netztrafo"), ("TRANSDUCER", "current / measuring transformer, Messwandler"),
    ("ACCESSORY", "accessory, Zubehör")]
TRAFO_PACKAGE = [("*0603*", "SMD"), ("*0805*", "SMD"), ("*1206*", "SMD"), ("*1218*", "SMD"), ("*1812*", "SMD"),
                 ("*2225*", "SMD"), ("*4040*", "SMD"), ("*AT224*", "Mini-Circuits AT224 case"),
                 ("*RING CORE*", "ring core"), ("*SMD*", "other SMD"), ("*SO*", "SO package")]

# fields with a DMS pick list -> list (used for the prompt and to snap the AI answer to the list)
PICK_LISTS = {
    "Accessories R L C": {"Function": ACCESSORY_FUNCTION},
    "Coil": {"Surface": COIL_SURFACE, "Function": COIL_FUNCTION, "Package Type": COIL_PACKAGE},
    "Cores": {"Function": CORE_FUNCTION, "Material": CORE_MATERIAL, "Filter Type": CORE_FILTER_TYPE, "Color": COLOR},
    "Directional Coupler": {"Function": COUPLER_FUNCTION, "Connector System": COUPLER_CONNECTOR},
    "EMI-Filter (Feedthrough-, Mains-)": {"Function": EMI_FUNCTION, "Filter Type": EMI_FILTER_TYPE,
                                          "Package Type": EMI_PACKAGE},
    "Inductance": {},
    "Permanent Magnet": {"Function": MAGNET_FUNCTION},
    "Shielding Gasket": {"Component Description": GASKET_DESCRIPTION, "Material Short Name": GASKET_MATERIAL,
                         "Filler Material": GASKET_FILLER, "Shape": GASKET_SHAPE, "Surface": GASKET_SURFACE},
    "Transducer / Transformer": {"Function": TRAFO_FUNCTION, "Package Type": TRAFO_PACKAGE},
}


def _opts(items):
    return ", ".join(f'"{v}"' + (f" ({m})" if m else "") for v, m in items)


def _pick(key, items, extra=""):
    return (f'            - FOR "{key}": Pick from this DMS list first: {_opts(items)}. '
            f"Return the list value exactly as written. ONLY if nothing fits, return a short free-text value "
            f"in the same style.{(' ' + extra) if extra else ''}\n")


NUM = "as a plain absolute number without units or exponent"
FREQ = f"in Hz {NUM} (e.g., 100 MHz -> 100000000, 13.56 MHz -> 13560000)"
IND = f"in henry (H) {NUM} (e.g., 10 nH -> 0.00000001, 4.7 uH -> 0.0000047, 1 mH -> 0.001)"
TEMPS = '''            - FOR "Min. ambient temp. (°C)" and "Max. ambient temp. (°C)": The operating (ambient) temperature range as plain numbers.
            - FOR "Min. case temp. (°C)" and "Max. case temp. (°C)": Only if the datasheet explicitly states a CASE temperature range, as plain numbers; otherwise "N/A".
'''
DIM_RULE = ('            - FOR "Length (mm)", "Width (mm)" and "Height (mm)": Nominal body dimensions in mm as plain '
            "numbers (these are the same values as in the Library tab).\n")

RULES = {
    "Accessories R L C": (
        _pick("Function", ACCESSORY_FUNCTION,
              "Choose by what the part is: shielding / screening cans for coils -> ABSCHIRMBECHER or ABSCHIRMTOPF, "
              "ferrite tuning screws -> ABGLEICHSCHRAUBE, tuning / trimming tools -> ABGLEICHSCHRAUBENDREHER.")
        + '            - FOR "Width (mm)" and "Height (mm)": Nominal width and height in mm as plain numbers.\n'
        + '            - FOR "Raster": The pin / lead spacing (grid, pitch) in mm as a plain number (e.g., 5.08). "N/A" if the part has no pins.\n'
        + '            - FOR "Package Type": A short free-text package description (e.g., the can size or mounting style), or "N/A".\n'),
    "Coil": (
        f'            - FOR "Inductance (H)": The nominal inductance {IND}. If a target MPN is given, use the row of that MPN.\n'
        '            - FOR "Tolerance (%)": The inductance tolerance in percent as a plain number without the sign (e.g., 5). If the tolerance is given in nH (e.g., ±0.1 nH), convert it to percent of the nominal inductance and write the calculation in the "evidence" field.\n'
        '            - FOR "Resistance (Ohm)": The DC resistance (DCR / Rdc) in ohms as a plain number. Use the MAXIMUM value if both typ and max are given.\n'
        '            - FOR "Quality Factor (Q)": The (minimum) quality factor Q as a plain number.\n'
        f'            - FOR "Frequency (Q)": The test frequency at which Q is specified, {FREQ}.\n'
        f'            - FOR "f Nom. (Typ) (Hz)": The inductance test frequency, {FREQ}.\n'
        f'            - FOR "SRF (Hz)": The (minimum) self-resonant frequency, {FREQ}.\n'
        '            - FOR "Current (A)": The rated current (Ir, Idc max) in amperes as a plain number.\n'
        '            - FOR "I sat (A)": The saturation current (Isat) in amperes as a plain number, or "N/A".\n'
        '            - FOR "I rms (A)": The RMS / temperature-rise current (Irms) in amperes as a plain number, or "N/A".\n'
        + _pick("Surface", COIL_SURFACE,
                "This is the termination / electrode finish: map the plating stack, e.g. 'Sn over Ni' -> 'NI / SN', "
                "'100% matte tin' -> 'SN', 'Ag/Pd' -> 'AG / PD'.")
        + _pick("Function", COIL_FUNCTION,
                "For SMD chip inductors (EIA case size) choose the CONSTRUCTION when the datasheet states it: "
                "'MULTILAYER CHIP' for multilayer / ceramic multilayer chips, 'WIRE WOUND' for wire-wound chips. "
                "Otherwise choose the most specific application value (e.g., shielded power inductor -> "
                "'POWER CHOKE SHIELDED', air-core spring coil -> 'AIR CORE INDUCTOR', conical inductor -> "
                "'BROADBAND CONICAL INDUCTOR').")
        + _pick("Package Type", COIL_PACKAGE,
                "SMD chips use the EIA (inch) size code: e.g., size 0402 (1005 metric) -> 'EIA0402*'. "
                "A size that is not in the list -> '*SMD*'. Leaded parts -> '*AXIAL*', '*RADIAL*' or '*RM*'.")
        + '            - FOR "Height (mm)": Nominal height in mm as a plain number (same value as in the Library tab).\n'),
    "Cores": (
        _pick("Function", CORE_FUNCTION, "For core shapes that are not in the list use the German style, e.g. 'E-KERN' (E core), 'U-KERN', 'RM-KERN', 'PQ-KERN'.")
        + '            - FOR "Tol. (Value)": The tolerance of the main parameter (AL value or permeability) as free text, e.g. "20" for ±20 %, or "N/A".\n'
        + f'            - FOR "f Nom. (Typ) (Hz)": The nominal / test frequency, {FREQ}, or "N/A".\n'
        + '            - FOR "Air Gap": The air gap in mm as a plain number; "0" for ungapped cores; "N/A" if not stated.\n'
        + _pick("Material", CORE_MATERIAL,
                "Use a list value ONLY when the grade name is identical (e.g., TDK/EPCOS N87 -> 'N87', Ferroxcube "
                "3C8 -> '3C8'). Otherwise write the grade with its ferrite type, e.g. '67 (NiZn ferrite)', "
                "'3C90 (MnZn ferrite)'. Iron powder -> 'EISEN-PULVER'.")
        + '            - FOR "AL-Value": The inductance factor AL in nH (per turn squared) as a plain number (e.g., 230).\n'
        + '            - FOR "Permeability": The initial permeability µi as a plain number.\n'
        + '            - FOR "Additional Information": Other key data as short free text (e.g., core set / pair, coating, effective dimensions), or "N/A".\n'
        + _pick("Filter Type", CORE_FILTER_TYPE, 'Only for EMI suppression cores and beads; otherwise "N/A".')
        + '            - FOR "Package Type": Free text: "MECHANIC" for cores and mechanical parts, unless the datasheet clearly gives an SMD package.\n'
        + DIM_RULE
        + '            - FOR "Outer Dimension 1 (mm)" and "Inside Dimension 1 (mm)": For round parts (toroids, tubes, beads) the outer and inner diameter in mm; otherwise "N/A".\n'
        + _pick("Color", COLOR, 'Only if the datasheet states a colour or colour coating; otherwise "N/A".')
        + '            - FOR "Impedance@MHz": For EMI suppression cores the main impedance point written as "<ohms>R@<MHz>MHZ" (e.g., "600R@100MHZ"); otherwise "N/A".\n'),
    "Directional Coupler": (
        _pick("Function", COUPLER_FUNCTION)
        + f'            - FOR "f (Min) (Hz)" and "f (Max) (Hz)": The minimum and maximum operating frequency {FREQ}.\n'
        + '            - FOR "Insertion Loss (Typ) (dB)": The typical mainline insertion loss in dB as a plain number.\n'
        + '            - FOR "Coupling (Nom) (dB)": The nominal coupling in dB as a plain number (e.g., 20).\n'
        + '            - FOR "Directivity (Typ) (dB)": The typical directivity in dB as a plain number.\n'
        + '            - FOR "RFin (Max) (dBm)": The maximum RF input power in dBm as a plain number. If only watts are given convert with dBm = 10 x log10(P in mW) and write the calculation in the "evidence" field.\n'
        + '            - FOR "Number of Pins": The number of pins / pads as a plain integer, or "N/A" for connectorized parts.\n'
        + _pick("Connector System", COUPLER_CONNECTOR, 'Surface-mount parts are "SMD".')
        + TEMPS),
    "EMI-Filter (Feedthrough-, Mains-)": (
        _pick("Function", EMI_FUNCTION,
              "Ferrite beads and common mode chokes for signal lines -> 'Data Line Filter'; mains / IEC inlet / power "
              "line filters -> 'Mains/Line/Power Filter'; feedthrough capacitors and filters -> 'Feed Through Filter'.")
        + _pick("Filter Type", EMI_FILTER_TYPE)
        + _pick("Package Type", EMI_PACKAGE,
                "SMD chips use the EIA size code (e.g., 0603 -> '*0603*'); otherwise a short free-text package / size code from the datasheet.")
        + '            - FOR "Attenuation (dB)": The attenuation / insertion loss figure in dB as a plain number, or "N/A".\n'
        + '            - FOR "Insertion Loss (Max) (dB)": The maximum insertion loss in dB as a plain number, or "N/A".\n'
        + f'            - FOR "f Nom. (Typ) (Hz)": The nominal / test frequency, {FREQ}, or "N/A".\n'
        + '            - FOR "Voltage (V)": The rated voltage in volts as a plain number.\n'
        + '            - FOR "Current (A)": The rated current in amperes as a plain number.\n'
        + f'            - FOR "Inductance (H)": The inductance {IND}, or "N/A".\n'
        + '            - FOR "Tolerance (%)": The tolerance of the impedance or inductance in percent as a plain number, or "N/A".\n'
        + '            - FOR "Capacity (F)": The capacitance in farad as a plain absolute number (e.g., 1 nF -> 0.000000001), or "N/A".\n'
        + '            - FOR "Resistance (Ohm)": The (maximum) DC resistance in ohms as a plain number.\n'
        + '            - FOR "Impedance@MHz": The main impedance point written as "<ohms>R@<MHz>MHZ" (e.g., "600R@100MHZ"). For ferrite beads use the 100 MHz value.\n'
        + '            - FOR "ImpMax (Ohm)" and "ImpMax@MHz (Hz)": The peak impedance in ohms and the frequency where it occurs (in Hz as a plain number). Free text; return "N/A" if not stated - do NOT write 0.\n'
        + '            - FOR "Additional Information": Other impedance points in the style "Z=300R@10MHZ, 625R@50MHZ", plus other key notes; "N/A" if none.\n'
        + DIM_RULE),
    "Inductance": (
        f'            - FOR "Inductance (H)": The nominal inductance {IND}.\n'
        '            - FOR "Function": Free text in capital letters: a short application description from the datasheet title / features, e.g. "RFI - EMI SUPPRESSION", "POWER CHOKE", "RF INDUCTOR".\n'),
    "Permanent Magnet": (
        '            - FOR "Function": Return exactly "Magnet".\n'
        '            - FOR "Package Type": Free text: the magnet shape in capitals, e.g. "RING", "DISC", "BLOCK", "ROD".\n'
        '            - FOR "Height (mm)": The thickness along the magnetisation axis in mm as a plain number.\n'
        '            - FOR "Length (mm)" and "Width (mm)": For blocks the length and width; for rings and discs both are the outer diameter; in mm as plain numbers.\n'
        '            - FOR "Mass": The mass as free text with its unit (e.g., "2.1g"), or "N/A".\n'
        '            - FOR "Additional Information": Material and grade (e.g., NdFeB N42, SmCo), inner diameter for rings, coating, magnetisation direction, as short free text.\n'),
    "Shielding Gasket": (
        _pick("Component Description", GASKET_DESCRIPTION, "Board level shields / shielding cans and covers -> 'HAUBE'.")
        + _pick("Material Short Name", GASKET_MATERIAL,
                "Map brand names via the examples in brackets (e.g., CHO-SEAL 1285 -> 'SI+AL-AG'). For board level "
                "shields write the cover material as free text if not in the list (e.g., 'Nickel Silver'); tin-plated steel -> 'STAHL'.")
        + _pick("Filler Material", GASKET_FILLER, 'Only for filled conductive elastomers; otherwise "N/A".')
        + _pick("Shape", GASKET_SHAPE, 'Only for profiles / strips / sheets; otherwise "N/A".')
        + _pick("Surface", GASKET_SURFACE, 'E.g. tin-plated steel cans -> "ZN"; adhesive backing -> "SELBSTKLEBEND". Otherwise "N/A".')
        + '            - FOR "Outer Dimension 1 (mm)" and "Outer Dimension 2 (mm)": Length and width (or profile outer diameter and height) in mm as plain numbers.\n'
        + '            - FOR "Inside Dimension 1 (mm)": The inner diameter of hollow profiles in mm, otherwise "N/A".\n'
        + '            - FOR "Thickness (mm)": The thickness / height in mm as a plain number (e.g., 300 µm -> 0.3).\n'
        + '            - FOR "Tol. Outer Dimension 1", "Tol. Outer Dimension 2" and "Tol. Thickness": The tolerances as free text with unit (e.g., "±0.1mm"), or "N/A".\n'
        + '            - FOR "hardness": The hardness as free text (e.g., "65 Shore A"), or "N/A".\n'
        + '            - FOR "Delivery Size": The delivery form / length as free text (e.g., "roll 10 m"), or "N/A".\n'
        + '            - FOR "Application": A short free-text application description, or "N/A".\n'),
    "Transducer / Transformer": (
        _pick("Function", TRAFO_FUNCTION)
        + _pick("Package Type", TRAFO_PACKAGE, "Otherwise a short free-text case code from the datasheet (e.g., 'SMD-SMT4').")
        + '            - FOR "Turns ratio": Free text in the style "W= 1:1", "W= 1:3+5" (several windings joined with +).\n'
        + f'            - FOR "Frequency (Hz)": The nominal operating frequency, {FREQ}.\n'
        + f'            - FOR "f (Min) (Hz)" and "f (Max) (Hz)": The operating frequency range, {FREQ}. If only one frequency is given, use it for both.\n'
        + '            - FOR "Power Consumption (W)": The rated power in watts as a plain number, or "N/A".\n'
        + '            - FOR "Input Voltage": The rated input / primary voltage in volts as a plain number, or "N/A".\n'
        + '            - FOR "Current (A)": The rated (primary / DC) current in amperes as a plain number, or "N/A".\n'
        + '            - FOR "Number OUT": The number of output (secondary) windings as a plain integer.\n'
        + '            - FOR "U OUT (V)" and "I OUT (A)": The rated output voltage and current as plain numbers, or "N/A".\n'
        + f'            - FOR "Inductance (H)": The (primary / open-circuit) inductance {IND}, or "N/A".\n'
        + DIM_RULE),
}

TECHN = {
    "Accessories R L C": ["Function", "Width (mm)", "Raster", "Height (mm)"],
    "Coil": ["Inductance (H)", "Tolerance (%)", "Resistance (Ohm)", "Quality Factor (Q)", "Surface", "Function",
             "I sat (A)", "f Nom. (Typ) (Hz)", "Current (A)", "SRF (Hz)", "Frequency (Q)", "Height (mm)",
             "I rms (A)", "Package Type"],
    "Cores": ["Function", "Tol. (Value)", "f Nom. (Typ) (Hz)", "Air Gap", "Material", "AL-Value",
              "Additional Information", "Permeability", "Filter Type", "Package Type", "Height (mm)", "Width (mm)",
              "Length (mm)", "Outer Dimension 1 (mm)", "Inside Dimension 1 (mm)", "Color", "Impedance@MHz"],
    "Directional Coupler": ["Function", "f (Min) (Hz)", "f (Max) (Hz)", "Insertion Loss (Typ) (dB)",
                            "Coupling (Nom) (dB)", "Min. case temp. (°C)", "Min. ambient temp. (°C)",
                            "Connector System", "Number of Pins", "RFin (Max) (dBm)", "Directivity (Typ) (dB)",
                            "Max. case temp. (°C)", "Max. ambient temp. (°C)"],
    "EMI-Filter (Feedthrough-, Mains-)": ["Function", "Attenuation (dB)", "f Nom. (Typ) (Hz)", "Voltage (V)",
                                          "Current (A)", "Inductance (H)", "Tolerance (%)", "Additional Information",
                                          "ImpMax (Ohm)", "Insertion Loss (Max) (dB)", "Filter Type", "Package Type",
                                          "Length (mm)", "Width (mm)", "Height (mm)", "Capacity (F)",
                                          "Resistance (Ohm)", "Impedance@MHz", "ImpMax@MHz (Hz)"],
    "Inductance": ["Inductance (H)", "Function"],
    "Permanent Magnet": ["Function", "Mass", "Additional Information", "Width (mm)", "Package Type", "Height (mm)",
                         "Length (mm)"],
    "Shielding Gasket": ["Component Description", "Material Short Name", "Filler Material", "Inside Dimension 1 (mm)",
                         "Outer Dimension 1 (mm)", "Outer Dimension 2 (mm)", "Thickness (mm)", "Application", "Shape",
                         "Surface", "hardness", "Delivery Size", "Tol. Outer Dimension 1", "Tol. Outer Dimension 2",
                         "Tol. Thickness"],
    "Transducer / Transformer": ["Turns ratio", "Frequency (Hz)", "Power Consumption (W)", "Package Type",
                                 "Height (mm)", "Length (mm)", "Width (mm)", "f (Min) (Hz)", "Function",
                                 "Input Voltage", "Current (A)", "Number OUT", "U OUT (V)", "I OUT (A)",
                                 "Inductance (H)", "f (Max) (Hz)"],
}

# keys already asked by the shared (Top / Library / Processability) part of the prompt
_BASE = {"Length (mm)", "Width (mm)", "Height (mm)", "Package Type", "Number of Pins"}
# hidden helper keys for the L* rules (not shown in the tabs)
L_HELPER_KEYS = ["Commodity Group", "Construction", "Lifecycle Status", "Category"]

CATEGORIES_L = {
    cat: {"cg": None, "techn": techn,
          "extra_keys": [k for k in techn if k not in _BASE] + L_HELPER_KEYS,
          "rules": RULES[cat]}
    for cat, techn in TECHN.items()
}


# ----------------------------------------------------------------- pick-list snap
def _norm(s):
    return re.sub(r"[\s*_\-/]+", "", str(s)).upper()


def snap_pick_lists(category, extracted_data):
    """Snap AI answers to the exact DMS list value (case / spacing); mark free-text values."""
    for key, items in PICK_LISTS.get(category, {}).items():
        item = extracted_data.get(key)
        if not isinstance(item, dict):
            continue
        val = str(item.get("value", "N/A")).strip()
        if val in ("", "N/A"):
            continue
        exact = {v: v for v, _ in items}
        loose = {_norm(v): v for v, _ in items}
        if val in exact:
            continue
        if _norm(val) in loose:
            item["value"] = loose[_norm(val)]
        else:
            item["evidence"] = f"{item.get('evidence', 'N/A')} [free text: not in DMS list]"


# ------------------------------------------------------------------- detection
DETECT_L = {
    "Shielding Gasket": ["gasket", "board level shield", "board-level shield", "conductive foam", "conductive elastomer",
                         "shielding tape", "fabric over foam", "emi shielding", "shielding cover"],
    "Permanent Magnet": ["permanent magnet", "neodymium", "ndfeb", "smco", "samarium", "remanence", "coercivity"],
    "Directional Coupler": ["directional coupler", "directivity", "coupled port"],
    "Transducer / Transformer": ["transformer", "balun", "flyback", "turns ratio", "transducer", "lan magnetics"],
    "EMI-Filter (Feedthrough-, Mains-)": ["ferrite bead", "chip bead", "emi filter", "emi suppression filter",
                                          "common mode choke", "common mode filter", "feedthrough", "feed-through",
                                          "mains filter", "power line filter", "line filter"],
    "Cores": ["ferrite core", "toroid", "ring core", "pot core", "e core", "bobbin", "al value", "core material",
              "cable ferrite", "snap ferrite", "ferrite sleeve", "rod core"],
    "Accessories R L C": ["shielding can", "screening can", "trimming tool", "tuning tool", "adjustment tool",
                          "trimming screw", "coil former accessory"],
    "Coil": ["inductor", "choke", "coil", "inductance", "multilayer", "wirewound", "wire wound", "air core",
             "self-resonant", "srf", "q factor"],
}

R_WORDS = ["resistor", "resistors", "thermistor", "varistor", "potentiometer", "trimmer", "attenuator",
           "rf termination", "resettable fuse", "polyfuse", "pptc", "equalizer", "ohm resistor"]
L_WORDS = ["inductor", "inductors", "inductance", "choke", "chokes", "ferrite", "coil", "coils", "transformer",
           "balun", "magnet", "gasket", "directional coupler", "bead", "beads", "shielding can"]


def _rx(word):
    return rf"(?<![a-z]){re.escape(word)}(?![a-z])"


def _hits(words, text):
    return sum(len(re.findall(_rx(w), text, flags=re.I)) for w in words)


def _score(words, names, head, text):
    return 5 * _hits(words, names) + 3 * _hits(words, head) + min(_hits(words, text), 10)


def detect_category_l(pdf_text, file_names=()):
    """Return (category, confident). Falls back to 'Coil' with confident=False."""
    names, head = " ".join(file_names), pdf_text[:3000]
    scores = {c: _score(w, names, head, pdf_text) for c, w in DETECT_L.items()}
    # specific categories win over the generic 'Coil' words (bead / transformer datasheets also say 'inductance')
    specific = {c: s for c, s in scores.items() if c != COIL}
    best, sc = max(specific.items(), key=lambda kv: kv[1])
    if sc >= 8 and sc >= 0.5 * scores[COIL]:
        return best, True
    if scores[COIL] >= 8:
        return COIL, True
    return COIL, False


def detect_commodity(pdf_text, file_names=()):
    """Return ('R*' or 'L*', confident)."""
    names, head = " ".join(file_names), pdf_text[:3000]
    r, l = _score(R_WORDS, names, head, pdf_text), _score(L_WORDS, names, head, pdf_text)
    if l > r:
        return "L*", l >= 8
    return "R*", r >= 8 and r > l
