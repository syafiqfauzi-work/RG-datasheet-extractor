"""
Extraction prompts.  Generated from the original resistor prompt: the resistor template keeps its
exact rules (plus a Category key); every other category gets the shared Top / Library / Processability
rules and its own Techn.Parameter rules from categories.py.
"""
from categories import CATEGORIES, RESISTOR

RESISTOR_TEMPLATE = """            Act as an expert electronics engineer. {mpn_instruction}
            Review the provided datasheet text and accurately extract the requested information. 
            
            Extract these exact keys:
            "Operating Temperature (Max) (°C)", "Operating Temperature (Min) (°C)", 
            "Storage Temperature (Max) (°C)", "Storage Temperature (Min) (°C)", 
            "Length (mm)", "Width (mm)", "Height_Calculation_Logic", "Height (Max)", "Height (mm)", 
            "Package Type", "Package Type (EIA)", "Pitch_Calculation_Logic", "Pitch (Footprint) (mm)", "Number of Pins", "Resistance_Calculation_Logic", 
            "Resistance (Ohm)", "Tolerance (%)", "Row_Data_Extraction", "Voltage (V)", "Function", 
            "Power_Extraction_Logic", "Power Consumption (W)", "TCR_Calculation_Logic", "Temperature Coefficient",
            "Kind of Mounting", "Washability", "Varnishability", "St. Solder (Standard Solder)", 
            "Alt. Solder (Alternate Solder)", "Rep. Solder (Repair Solder)", "ESS Suitable", 
            "Max Reflow Cycle (cycles)", "Max Reflow Time (s)", "Max Reflow Temp (°C)",
            "Manufacturer", "Designation", "Additional Information", "Quantity", "Commodity Group", "Category"

            Important Instructions:
            - Return strictly a valid JSON object with the keys above.
            - CRITICAL JSON RULE 1: Do NOT use unescaped double quotes (") inside any of your text explanations or values. Use single quotes (') instead.
            - CRITICAL JSON RULE 2: Do NOT include raw newline characters (\n), carriage returns (\r), or tabs (\t) inside any JSON string values. Replace them with standard spaces.
            - FOR ALL OTHER KEYS: Return a nested JSON object with three fields: "value" (the string value, or "N/A"), "evidence" (a short exact quote from the text), and "page" (the exact Page number where it was found, e.g., "1", or "N/A").
            
            [PROCESSABILITY RULES]
            - FOR "Kind of Mounting": Select ONLY ONE: "SMT (surface-mounting technology)", "THR, PiP (through-hole technology)", "press-fit", "THW (through-hole technology)", "ceramic substrate technology (Chip microwave)", "none", or "fine press-fit".
              * CRITICAL LOGIC: If the datasheet mentions traditional leaded components or soldering via "wave or dipping", select "THW (through-hole technology)". If it explicitly mentions "Through-Hole Reflow", "THR", or "Pin-in-Paste (PiP)", select "THR, PiP (through-hole technology)". If it is a standard surface mount chip/SMD, select "SMT (surface-mounting technology)".
            - FOR "St. Solder (Standard Solder)": Select ONLY ONE: "reflow soldering top / bottom", "reflow soldering top - only", "wave soldering bottom", "manually soldering / bonding", or "no soldering".
            - FOR "Alt. Solder (Alternate Solder)": Select ONLY ONE: "selective hot air soldering", "wave soldering bottom", "selective wave soldering", "manually soldering", or "no soldering".
            - FOR "Rep. Solder (Repair Solder)": Select ONLY ONE: "selective hot air soldering", "manually soldering", or "no soldering".
            - FOR "ESS Suitable": Evaluate the extracted Operating Temperatures. If the Operating Temperature goes OUTSIDE the standard range (e.g., Min is colder than -20°C OR Max is hotter than 75°C), select "ESS released". If the temperatures fall strictly WITHIN -20°C to 75°C (like +5 to +35 °C), select "not ESS released". If there is no information available for the Operating Temperature, strictly return "N/A".
            - FOR "Washability" and "Varnishability": Select "Yes" or "No" if explicitly stated in the datasheet. If there is no information available regarding washability or varnishability, strictly return "N/A".
            - FOR REFLOW ("Max Reflow Cycle (cycles)", "Max Reflow Time (s)", "Max Reflow Temp (°C)"): Extract ONLY the raw nominal numerical value. Discard any text, units (e.g., seconds, s, °C, cycles), and tolerances (e.g., for "10 ± 1 seconds immersion time", return "10"; for "260 °C ± 5 °C", return "260").
            
            [GENERAL RULES]
            - MASTER RULE FOR SPEC SHEETS: If the text contains a "CRITICAL PRIORITY: SPECIFIC SPEC SHEET" section, you MUST extract all available values directly from that section first. You are ALLOWED to skip complex table extraction logic. HOWEVER, for calculated fields like Height (Max), Pitch, or Voltage, you MUST still write your exact mathematical step-by-step calculation in the "evidence" field, followed by the tag "(From Spec Sheet)". Example: "Pitch = Length (5.08) - Terminal (1.47) (From Spec Sheet)" or "Height = 0.64 + 0.25 (From Spec Sheet)".
            - FOR "Resistance_Calculation_Logic": If a target MPN is provided, determine the resistance code. 1) If the code contains an 'R' (e.g., R300, R3000, 1R50), extract it. If it starts with 'R', prepend a '0' (e.g., R300 -> 0R300). Then remove trailing zeros at the end (e.g., 0R300 -> 0R3, 1R50 -> 1R5). 2) If it is a standard numeric code (e.g., 1828), let XYZ=182, M=8. If M='7' output "0RXYZ"; If M='8' output "XRYZ"; If M='9' output "XYRZ"; If M='0' output "XYZR"; If M='1' output "XKYZ"; If M='2' output "XYKZ"; If M='3' output "XYZK"; If M='4' output "XMYZ"; If M='5' output "XYMZ"; If M='6' output "XYZM".
            - FOR "Resistance (Ohm)": Extract ONLY the final string generated from the XYZ rule in "Resistance_Calculation_Logic". ABSOLUTELY NO DECIMALS.
            - FOR "Row_Data_Extraction": PDF tables are flattened. Find the target Part No. (e.g., ERJP06). The values immediately following it are typically: [Size] [Power] [Ambient Temp] [Terminal Temp] [Limiting Voltage] [Overload Voltage]. (e.g., "ERJP06 (0805) 0.50 70 115 400 600"). Isolate and write down this exact sequence for your specific MPN to prevent grabbing data from the wrong row.
            - FOR "Voltage (V)": Look STRICTLY at the isolated sequence in "Row_Data_Extraction". Extract the "Limiting element voltage" (which is typically the 4th numeric value after the package size). Example: If the sequence is "0.50 70 115 400", the voltage is 400. Do NOT grab voltages from other part numbers.
            - FOR "TCR_Calculation_Logic": Look at the isolated data for your specific Part No. 1) State the exact resistance in Ohms. 2) Find the T.C.R. sub-ranges for this part. 3) Evaluate the resistance mathematically. Example: 1000 Ohms is greater than 33 Ohms, so it matches the condition "33Ω ≤ R : ±100" (NOT R < 33Ω). 4) State the correct T.C.R.
            - FOR "Temperature Coefficient": Look STRICTLY at the mathematical range you just determined in "TCR_Calculation_Logic". Extract ONLY the specific T.C.R. value assigned to that exact range. Extract the numerical value TOGETHER WITH its exact unit (e.g., "200 ppm/°C"). Discard "±".
            - FOR DIMENSIONS (Length, Width, Height (mm)): If a value includes a tolerance (e.g., 0.60 ± 0.03), extract ONLY the nominal base value (e.g., 0.60) and discard the tolerance completely.
            - FOR THE "Function" KEY: Select ONLY ONE: "Thin Film", "Thick Film", "Metal Foil", "Wire-wound", or "Carbon Film".
            - FOR "Height_Calculation_Logic": 1) Extract the raw height dimension string. 2) If it contains dual units like "inches (mm)", you MUST isolate ONLY the millimeter portion completely inside the parentheses (e.g., from "0.025 ± 0.010 (0.635 ± 0.254)", isolate "0.635 ± 0.254"). 3) Identify the nominal mm value (X) and the positive mm tolerance (Y). 4) Output EXACTLY in this format: "X + Y" (e.g., "0.635 + 0.254"). DO NOT compute.
            - FOR "Height (Max)": Output "N/A" (This will be calculated externally).
            - FOR "Height (mm)": Extract ONLY the nominal mm value identified in "Height_Calculation_Logic", discarding any tolerance. Do NOT extract values labeled "T" (Thickness/Terminal) if "H" (Height) is available.
            - FOR "Package Type": Return the value EXACTLY in this format: EIA[Package EIA Size]*. For example, if the size is 0201, return "EIA0201*". Do NOT extract shipping or delivery packaging methods (e.g., Tape and Reel, Paper Taping Reel, Bulk, Tube).
            - FOR "Power_Extraction_Logic": 1) Identify target package size. 2) Scan ALL pages. Find EVERY wattage (W) value associated with this size (Check both "Technical Specifications" and "MAXIMUM RESISTANCE CHANGE" tables). 3) Output a list of ALL found wattages. You MUST include the 'W' unit for each. Example output: "1.0 W, 0.65 W, 1.0 W". DO NOT pick one, list ALL of them.
            - FOR "Power Consumption (W)": Output "N/A" for the "value" (This will be intercepted and calculated externally).
            - FOR VOLTAGE: If the datasheet lists multiple operation modes (e.g., "Standard" vs "Extended"), strictly extract the values for the "Standard" operation mode. Do not extract the Extended or maximum rating if a Standard mode is available.
              * Note 1: If Power is provided as a fraction (e.g., 1/20, 1/4, 1/8), you MUST calculate and return it strictly as a DECIMAL (e.g., 0.05, 0.25, 0.125) for both the "Power Consumption (W)" key and the "Designation" string.
              * Note 2: If the datasheet specifies a formula like "(P x R)1/2" instead of a direct number, calculate it mathematically using your final Power (W) and Resistance (Ohm) values. Round the final calculated value to exactly 4 decimal places (e.g., "0.5477") for the "value" field. In the "evidence" field, write your step-by-step calculation (e.g., "Formula: (P x R)^1/2 -> sqrt(1.0W x 0.3Ohm)").
           - FOR "Pitch_Calculation_Logic": YOU MUST OUTPUT A MATRIX. 1) State nominal Length (L) in mm. 2) List ALL Terminal Widths (T) and their exact Resistance Ranges line-by-line (e.g., "Range 1: 0.001 to 0.0069, T = 1.47 | Range 2: 0.007 to 0.5, T = 0.508"). 3) State the target MPN resistance. 4) State exactly which range it falls into by comparing decimals. 5) Output the final formula AT THE VERY END in exactly this format: "Formula: L - T" (e.g., "Formula: 5.08 - 0.508").
            - FOR "Pitch (Footprint) (mm)": Output "N/A" for the "value" field. For the "evidence" field, extract ONLY the exact formula string generated at the very end of "Pitch_Calculation_Logic" (e.g., "5.08 - 0.508"). Discard the matrix text.
            - FOR THE "Designation" KEY: Construct a string following EXACTLY this format: 
              [Resistance] [Tolerance] [Temperature coefficient] [Power] [RAW Package EIA] [Additional Info]
              * Note 1: For [Resistance], strictly use the R/K/M formatted value (e.g., use "5R11", do NOT use "5.11"). CRITICAL FOR JUMPERS: If the component is a Jumper (or has 0 Ohm resistance), you MUST explicitly set [Resistance] to "0R" at the very beginning of the designation. Do NOT leave it blank. For jumpers, you should replace the [Power] section with the maximal applicable current (e.g., "40A").
              * Note 2: For [RAW Package EIA], use ONLY the bare numeric code (e.g., 0201, 0402). Do NOT include the "EIA" prefix or the "*" asterisk in this designation string.
              * Note 3: For [Additional Info] in Designation, scan the datasheet and append ONLY these exact tags if found (separate with '/'): HF, PP, HP, HV, AS, FT, SM, AIN, AU, AG, CU. (CRITICAL: Do NOT include "AQ" or Automotive Grade in this designation string). If no tags apply, leave empty. Evaluate these specific mappings:
                - "HF": High Frequency (CRITICAL: Do NOT append this tag if the letters "HF" in the datasheet refer to "Halogen Free" or are associated with RoHS/environmental compliance).
                - "PP": High Pulse, Pulse Proof, or Anti Surge
                - "HP": High Power (power higher than standard)
                - "HV": High Voltage
                - "AS": Anti Sulfurated or Anti-Sulfur
                - "FT": Flexiterm, Flexible Termination, or Soft Termination
                - "SM": Special Mounting (Flange, Chassis, Stacked)
                - "AIN": Aluminium Nitride material
                - "AU": Gold (Au) contact surface
                - "AG": Silver (Ag) contact surface
                - "CU": Copper (Cu) contact surface
              * Note 4: For [Temperature coefficient], use ONLY the numeric value followed by "PPM". You MUST drop the "/K" or "/°C" completely. Example: use "50PPM", NEVER "50PPM/K" or "50PPM/°C".
              * Example output: 5R11 1% 200PPM 0.1W 0603 PP/AS
            - FOR "Manufacturer": Identify the manufacturer of the component from the datasheet. You MUST select strictly from this exact list: "Analog Devices, Inc.", "Barry Industries Inc.", "Bourns Inc.", "Caddock Electronics, Inc", "Diconex", "EMC TECHNIK & CONSULTING GmbH", "Fenghua (H.K.) Electronics Ltd.", "IMS - International Manufacturing S", "Knowles Corporation", "Kyocera AVX Components Ltd.", "Littelfuse, Inc.", "MACOM", "Marki Microwave", "Mini-Circuits, Inc.", "Panasonic Corporation", "RES-NET Microwave, Inc.", "Smiths Interconnect", "Spectrum Control (API Technologies)", "Susumu Co., LTD", "TDK Corporation", "TTM Technologies Inc.", "Vishay Intertechnology, Inc.", or "Yageo Corporation". If the exact manufacturer is not in this list, return "Unknown".
            - FOR "Additional Information": Scan the datasheet for special qualifications. If the component is AEC-Q200 qualified or explicitly stated as Automotive Grade, you MUST extract and output "AQ". You may also list other special features here if found. If nothing is found, return "N/A".
            - FOR "Quantity": Determine the number of isolated resistor elements or circuits within the component package. For a standard single chip resistor, strictly return "1" for the value, and for the "evidence" field, you MUST output this exact fixed statement: "Standard single chip resistor". For resistor arrays or networks, return the exact number of elements (e.g., "2", "4") and quote the relevant array feature as evidence.
            - FOR "Commodity Group": Select ONLY ONE code from this exact list: "RG" (resistor - fixed value: standard chip, thin film, thick film, metal film, carbon film, MELF, fixed wire-wound, jumpers / 0 Ohm, current sense), "RK" (resistor - PTC, NTC, varistor: includes PTC/NTC thermistors, polymeric PTC resettable fuses such as PolySwitch, and varistors), "RN" (resistor - network: several resistor elements in one package, i.e. Quantity greater than 1), "RR" (resistor - adjustable wire resistor), "RS" (resistor - potentiometer, trimmer), "RT" (resistor - attenuator, termination: includes RF attenuators, terminations and RF equalizers), "RX" (resistor - unencapsulated chip, bare die), or "RZ" (accessory for resistors, e.g. heat sink, clip, mounting hardware). NEVER return RJ, RL, RV or RW (obsolete). A standard single fixed resistor is "RG". If the component does not clearly fit, return "Unknown".
            - FOR "Category": Select ONLY ONE DMS category from this exact list: "Resistor constant" (fixed resistors, networks, jumpers, chips), "Potentiometer mech. adjustable", "Potentiometer electr. adjustable" (digital potentiometers), "NTC PTC Varistor Sensors" (NTC/PTC thermistors, varistors), "Resettable Fuses" (PPTC, polyfuse, polyswitch), "RF Attenuator", "RF Termination" or "RF Equalizer". A standard fixed resistor is "Resistor constant".
            
            Datasheet Text:
            -----------------
            {pdf_text}"""

OTHER_TEMPLATE = """
            Act as an expert electronics engineer. {mpn_instruction}
            Review the provided datasheet text and accurately extract the requested information. 
            
            Extract these exact keys:
            {keys}

                        Important Instructions:
            - Return strictly a valid JSON object with the keys above.
            - CRITICAL JSON RULE 1: Do NOT use unescaped double quotes (") inside any of your text explanations or values. Use single quotes (') instead.
            - CRITICAL JSON RULE 2: Do NOT include raw newline characters (\n), carriage returns (\r), or tabs (\t) inside any JSON string values. Replace them with standard spaces.
            - FOR ALL OTHER KEYS: Return a nested JSON object with three fields: "value" (the string value, or "N/A"), "evidence" (a short exact quote from the text), and "page" (the exact Page number where it was found, e.g., "1", or "N/A").
            
                        [PROCESSABILITY RULES]
            - FOR "Kind of Mounting": Select ONLY ONE: "SMT (surface-mounting technology)", "THR, PiP (through-hole technology)", "press-fit", "THW (through-hole technology)", "ceramic substrate technology (Chip microwave)", "none", or "fine press-fit".
              * CRITICAL LOGIC: If the datasheet mentions traditional leaded components or soldering via "wave or dipping", select "THW (through-hole technology)". If it explicitly mentions "Through-Hole Reflow", "THR", or "Pin-in-Paste (PiP)", select "THR, PiP (through-hole technology)". If it is a standard surface mount chip/SMD, select "SMT (surface-mounting technology)".
            - FOR "St. Solder (Standard Solder)": Select ONLY ONE: "reflow soldering top / bottom", "reflow soldering top - only", "wave soldering bottom", "manually soldering / bonding", or "no soldering".
            - FOR "Alt. Solder (Alternate Solder)": Select ONLY ONE: "selective hot air soldering", "wave soldering bottom", "selective wave soldering", "manually soldering", or "no soldering".
            - FOR "Rep. Solder (Repair Solder)": Select ONLY ONE: "selective hot air soldering", "manually soldering", or "no soldering".
            - FOR "ESS Suitable": Evaluate the extracted Operating Temperatures. If the Operating Temperature goes OUTSIDE the standard range (e.g., Min is colder than -20°C OR Max is hotter than 75°C), select "ESS released". If the temperatures fall strictly WITHIN -20°C to 75°C (like +5 to +35 °C), select "not ESS released". If there is no information available for the Operating Temperature, strictly return "N/A".
            - FOR "Washability" and "Varnishability": Select "Yes" or "No" if explicitly stated in the datasheet. If there is no information available regarding washability or varnishability, strictly return "N/A".
            - FOR REFLOW ("Max Reflow Cycle (cycles)", "Max Reflow Time (s)", "Max Reflow Temp (°C)"): Extract ONLY the raw nominal numerical value. Discard any text, units (e.g., seconds, s, °C, cycles), and tolerances (e.g., for "10 ± 1 seconds immersion time", return "10"; for "260 °C ± 5 °C", return "260").
            
            [GENERAL RULES]
            - MASTER RULE FOR SPEC SHEETS: If the text contains a "CRITICAL PRIORITY: SPECIFIC SPEC SHEET" section, you MUST extract all available values directly from that section first. You are ALLOWED to skip complex table extraction logic. HOWEVER, for calculated fields like Height (Max), Pitch, or Voltage, you MUST still write your exact mathematical step-by-step calculation in the "evidence" field, followed by the tag "(From Spec Sheet)". Example: "Pitch = Length (5.08) - Terminal (1.47) (From Spec Sheet)" or "Height = 0.64 + 0.25 (From Spec Sheet)".
            - FOR DIMENSIONS (Length, Width, Height (mm)): If a value includes a tolerance (e.g., 0.60 ± 0.03), extract ONLY the nominal base value (e.g., 0.60) and discard the tolerance completely.
            - FOR "Height_Calculation_Logic": 1) Extract the raw height dimension string. 2) If it contains dual units like "inches (mm)", you MUST isolate ONLY the millimeter portion completely inside the parentheses (e.g., from "0.025 ± 0.010 (0.635 ± 0.254)", isolate "0.635 ± 0.254"). 3) Identify the nominal mm value (X) and the positive mm tolerance (Y). 4) Output EXACTLY in this format: "X + Y" (e.g., "0.635 + 0.254"). DO NOT compute.
            - FOR "Height (Max)": Output "N/A" (This will be calculated externally).
            - FOR "Height (mm)": Extract ONLY the nominal mm value identified in "Height_Calculation_Logic", discarding any tolerance. Do NOT extract values labeled "T" (Thickness/Terminal) if "H" (Height) is available.
            - FOR "Package Type": Return the value EXACTLY in this format: EIA[Package EIA Size]*. For example, if the size is 0201, return "EIA0201*". Do NOT extract shipping or delivery packaging methods (e.g., Tape and Reel, Paper Taping Reel, Bulk, Tube).
           - FOR "Pitch_Calculation_Logic": YOU MUST OUTPUT A MATRIX. 1) State nominal Length (L) in mm. 2) List ALL Terminal Widths (T) and their exact Resistance Ranges line-by-line (e.g., "Range 1: 0.001 to 0.0069, T = 1.47 | Range 2: 0.007 to 0.5, T = 0.508"). 3) State the target MPN resistance. 4) State exactly which range it falls into by comparing decimals. 5) Output the final formula AT THE VERY END in exactly this format: "Formula: L - T" (e.g., "Formula: 5.08 - 0.508").
            - FOR "Pitch (Footprint) (mm)": Output "N/A" for the "value" field. For the "evidence" field, extract ONLY the exact formula string generated at the very end of "Pitch_Calculation_Logic" (e.g., "5.08 - 0.508"). Discard the matrix text.
            - FOR "Manufacturer": Identify the manufacturer of the component from the datasheet. You MUST select strictly from this exact list: "Analog Devices, Inc.", "Barry Industries Inc.", "Bourns Inc.", "Caddock Electronics, Inc", "Diconex", "EMC TECHNIK & CONSULTING GmbH", "Fenghua (H.K.) Electronics Ltd.", "IMS - International Manufacturing S", "Knowles Corporation", "Kyocera AVX Components Ltd.", "Littelfuse, Inc.", "MACOM", "Marki Microwave", "Mini-Circuits, Inc.", "Panasonic Corporation", "RES-NET Microwave, Inc.", "Smiths Interconnect", "Spectrum Control (API Technologies)", "Susumu Co., LTD", "TDK Corporation", "TTM Technologies Inc.", "Vishay Intertechnology, Inc.", or "Yageo Corporation". If the exact manufacturer is not in this list, return "Unknown".
            
            [CATEGORY RULES: {category}]
{category_rules}
            
            Datasheet Text:
            -----------------
            {pdf_text}
            """

BASE_KEYS = '''"Operating Temperature (Max) (°C)", "Operating Temperature (Min) (°C)", "Storage Temperature (Max) (°C)", "Storage Temperature (Min) (°C)",
            "Length (mm)", "Width (mm)", "Height_Calculation_Logic", "Height (Max)", "Height (mm)",
            "Package Type", "Package Type (EIA)", "Pitch_Calculation_Logic", "Pitch (Footprint) (mm)", "Number of Pins",
            "Kind of Mounting", "Washability", "Varnishability", "St. Solder (Standard Solder)", "Alt. Solder (Alternate Solder)", "Rep. Solder (Repair Solder)", "ESS Suitable",
            "Max Reflow Cycle (cycles)", "Max Reflow Time (s)", "Max Reflow Temp (°C)", "Manufacturer"'''


def build_prompt(category, mpn_instruction, pdf_text):
    if category == RESISTOR or category not in CATEGORIES:
        return (RESISTOR_TEMPLATE.replace("{mpn_instruction}", mpn_instruction)
                .replace("{pdf_text}", pdf_text))
    cfg = CATEGORIES[category]
    extra = ", ".join(f'"{k}"' for k in cfg["extra_keys"])
    keys = BASE_KEYS + ", " + extra
    return (OTHER_TEMPLATE.replace("{category_rules}", cfg["rules"].strip("\n"))
            .replace("{category}", category)
            .replace("{keys}", keys)
            .replace("{mpn_instruction}", mpn_instruction)
            .replace("{pdf_text}", pdf_text))
