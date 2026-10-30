"""
DMS categories: Techn.Parameter fields, commodity-group mapping, extraction rules and detection.

Only the Techn.Parameter tab differs per category. Top, Library and Processability stay the same.
All numeric values are written as plain absolute numbers (DMS adjusts the unit itself),
e.g. 18 GHz -> 18000000000.
"""
import re

RESISTOR = "Resistor constant"

# category -> commodity group written by the app (None = decided by the resistor logic: RG/RN/RX/...)
CATEGORIES = {
    "Resistor constant": {
        "cg": None,
        "techn": ["Resistance (Ohm)", "Tolerance (%)", "Voltage (V)", "Package Type", "Quantity", "Function",
                  "Power Consumption (W)", "Temperature Coefficient", "Height (mm)", "Additional Information"],
        "extra_keys": [],
        "rules": "",
    },
    "Resettable Fuses": {
        "cg": "RK",
        "techn": ["Function", "Voltage (V)", "Current (A)", "Power Consumption (W)", "Package Type",
                  "Length (mm)", "Width (mm)", "Height (mm)"],
        "extra_keys": ["Function", "Voltage (V)", "Current (A)", "Power Consumption (W)"],
        "rules": '''
            - FOR "Function": Return exactly "PPTC".
            - FOR "Voltage (V)": The maximum operating voltage (Vmax) in volts as a plain number (e.g., 16). If both DC and AC values are given, use the DC value.
            - FOR "Current (A)": The HOLD current (Ihold) in amperes as a plain number (e.g., 1.1). Do NOT use the trip current. If a target MPN is given, use the row of that MPN.
            - FOR "Power Consumption (W)": The typical power dissipation in watts as a plain number. If only a maximum is given use it. Return "N/A" if not stated.
            - FOR "Package Type": Select ONLY ONE: "RM-10.16" (radial leaded, 10.16 mm lead spacing), "RM-5.08" (radial leaded, 5.08 mm lead spacing) or "SMD*" (surface mount). Do NOT use the EIA format. Return "N/A" if none fits.
''',
    },
    "Potentiometer mech. adjustable": {
        "cg": "RS",
        "techn": ["Resistance (Ohm)", "Temperature Coefficient", "Power Consumption (W)", "Tolerance (%)",
                  "Graph", "Adjust from"],
        "extra_keys": ["Resistance (Ohm)", "Temperature Coefficient", "Power Consumption (W)", "Tolerance (%)",
                       "Graph", "Adjust from"],
        "rules": '''
            - FOR "Resistance (Ohm)": The total (end-to-end) resistance in ohms as a plain number without units or letters (e.g., 10000 for 10k).
            - FOR "Temperature Coefficient": The temperature coefficient of resistance as number with unit (e.g., "100 ppm/°C"). Discard "±".
            - FOR "Power Consumption (W)": The rated power in watts as a plain number (e.g., 0.5).
            - FOR "Tolerance (%)": The resistance tolerance in percent as a plain number without the sign (e.g., 20).
            - FOR "Graph": Select ONLY ONE: "lin" (linear, B taper), "log" (logarithmic, audio, A taper) or "exp" (exponential). Return "N/A" if not stated.
            - FOR "Adjust from": Select ONLY ONE: "OBEN" (top adjust) or "SEITE" (side adjust, beside). Return "N/A" if not clear.
''',
    },
    "Potentiometer electr. adjustable": {
        "cg": "RS",
        "techn": ["Resistance (Ohm)", "Potentiometer", "Positions", "Temperature Coefficient"],
        "extra_keys": ["Resistance (Ohm)", "Potentiometer", "Positions", "Temperature Coefficient"],
        "rules": '''
            - FOR "Resistance (Ohm)": The end-to-end resistance in ohms as a plain number without units or letters (e.g., 10000 for 10k).
            - FOR "Potentiometer": A short free-text description of the potentiometer (e.g., 'digital potentiometer, I2C, non-volatile').
            - FOR "Positions": The number of wiper positions (steps) as a plain integer (e.g., 256).
            - FOR "Temperature Coefficient": The temperature coefficient as number with unit (e.g., "35 ppm/°C"). Discard "±".
''',
    },
    "NTC PTC Varistor Sensors": {
        "cg": "RK",
        "techn": ["Function", "Resistance (Ohm)", "Voltage (V)", "Current (A)", "Power Consumption (W)",
                  "Length (mm)", "Width (mm)", "Height (mm)", "Tol. (Value)", "Package Type"],
        "extra_keys": ["Function", "Resistance (Ohm)", "Voltage (V)", "Current (A)", "Power Consumption (W)",
                       "Tol. (Value)"],
        "rules": '''
            - FOR "Function": Select ONLY ONE: "NTC-Thermistor", "PTC-Thermistor" or "Varistor".
            - FOR "Resistance (Ohm)": For thermistors the nominal resistance at 25 °C (R25) in ohms as a plain number (e.g., 10000 for 10k). For varistors return "N/A".
            - FOR "Voltage (V)": The maximum continuous operating voltage in volts as a plain number (for varistors the DC rating if given, otherwise the AC rms rating).
            - FOR "Current (A)": The maximum rated current in amperes as a plain number (for varistors the maximum surge current if no continuous rating is given).
            - FOR "Power Consumption (W)": The rated or maximum power dissipation in watts as a plain number.
            - FOR "Tol. (Value)": The tolerance as an ABSOLUTE value with its unit as free text (e.g., '±0.5 K' or '±200 Ohm'). If the datasheet gives only a percentage, calculate the absolute value when the reference value is known (e.g., R25), and write the calculation in the "evidence" field; otherwise return "N/A".
            - FOR "Package Type": Select ONLY ONE: "*1005*", "*0201*", "*0204*", "*0302*", "*0402*", "*0504*", "*0603*", "*0805*", "*1008*", "*1020*", "*1111*", "*1206*", "*1214*", "*1218*", "*2010*", "*2220*", "*2225*", "*2512*", "*4032*", "*4040*" (SMD chip sizes, pick by the EIA size code), "*RM*" (radial leaded), "*SOT*" or "*TO*". Return "N/A" if none fits.
''',
    },
    "RF Attenuator": {
        "cg": "RT",
        "techn": ["Function", "f (Min) (Hz)", "f (Max) (Hz)", "Attenuation (Min) (dB)", "Attenuation (Fix / Max) (dB)",
                  "Power Consumption (W)", "Min. case temp. (°C)", "Min. ambient temp. (°C)", "IIP3 (dBm)",
                  "IP1dB (dBm)", "td (on / off) (s)", "RFin (Max) (dBm)", "Max. case temp. (°C)",
                  "Max. ambient temp. (°C)", "Connector System"],
        "extra_keys": ["Function", "f (Min) (Hz)", "f (Max) (Hz)", "Attenuation (Min) (dB)",
                       "Attenuation (Fix / Max) (dB)", "Power Consumption (W)", "Min. case temp. (°C)",
                       "Min. ambient temp. (°C)", "IIP3 (dBm)", "IP1dB (dBm)", "td (on / off) (s)",
                       "RFin (Max) (dBm)", "Max. case temp. (°C)", "Max. ambient temp. (°C)",
                       "Connector System", "Impedance (Ohm)"],
        "rules": '''
            - FOR "Function": Select ONLY ONE: "Attenuator Fixed", "Attenuator Voltage Controlled", "Attenuator Current Controlled" or "Attenuator Digital Controlled".
            - FOR "f (Min) (Hz)" and "f (Max) (Hz)": The minimum and maximum operating frequency in Hz as a plain integer without units or exponent (e.g., 18 GHz -> 18000000000, DC -> 0).
            - FOR "Attenuation (Min) (dB)": For variable or controlled attenuators the minimum attenuation in dB as a plain number. For fixed attenuators return "N/A".
            - FOR "Attenuation (Fix / Max) (dB)": For fixed attenuators the nominal attenuation in dB (e.g., 6), for variable attenuators the maximum attenuation, as a plain number.
            - FOR "Power Consumption (W)": The maximum RF input power rating in watts as a plain number.
            - FOR "Min. ambient temp. (°C)" and "Max. ambient temp. (°C)": The operating (ambient) temperature range as plain numbers.
            - FOR "Min. case temp. (°C)" and "Max. case temp. (°C)": Only if the datasheet states a case temperature range, as plain numbers; otherwise "N/A".
            - FOR "IIP3 (dBm)" and "IP1dB (dBm)": The values in dBm as plain numbers if stated, otherwise "N/A".
            - FOR "td (on / off) (s)": The switching or settling time in seconds as a plain decimal number without exponent (e.g., 0.00000002), otherwise "N/A".
            - FOR "RFin (Max) (dBm)": The maximum RF input power in dBm as a plain number. If only watts are given convert with dBm = 10 x log10(P in mW) and write the calculation in the "evidence" field.
            - FOR "Connector System": Select ONLY ONE: "SMD" (surface-mount chip, no connector), "SMA", "PC3.5mm", "PC2.92mm", "PC2.4mm", "N-Type", "7/16", "BNC", "QMA", "PC1.85" or "N/A".
            - FOR "Impedance (Ohm)": The system impedance in ohms as a plain number (e.g., 50), otherwise "N/A".
''',
    },
    "RF Termination": {
        "cg": "RT",
        "techn": ["Function", "f (Min) (Hz)", "f (Max) (Hz)", "Power Consumption (W)", "Min. case temp. (°C)",
                  "Min. ambient temp. (°C)", "RFin (Max) (dBm)", "Impedance (Ohm)", "Max. case temp. (°C)",
                  "Max. ambient temp. (°C)", "Connector System"],
        "extra_keys": ["Function", "f (Min) (Hz)", "f (Max) (Hz)", "Power Consumption (W)", "Min. case temp. (°C)",
                       "Min. ambient temp. (°C)", "RFin (Max) (dBm)", "Impedance (Ohm)", "Max. case temp. (°C)",
                       "Max. ambient temp. (°C)", "Connector System"],
        "rules": '''
            - FOR "Function": Return exactly "RF Termination".
            - FOR "f (Min) (Hz)" and "f (Max) (Hz)": The minimum and maximum operating frequency in Hz as a plain integer without units or exponent (e.g., 18 GHz -> 18000000000, DC -> 0).
            - FOR "Power Consumption (W)": The maximum power rating in watts as a plain number.
            - FOR "Min. ambient temp. (°C)" and "Max. ambient temp. (°C)": The operating (ambient) temperature range as plain numbers.
            - FOR "Min. case temp. (°C)" and "Max. case temp. (°C)": Only if the datasheet states a case temperature range, as plain numbers; otherwise "N/A".
            - FOR "RFin (Max) (dBm)": The maximum RF input power in dBm as a plain number. If only watts are given convert with dBm = 10 x log10(P in mW) and write the calculation in the "evidence" field.
            - FOR "Impedance (Ohm)": The impedance in ohms as a plain number (e.g., 50).
            - FOR "Connector System": Select ONLY ONE: "Type-N", "SMA", "SMB", "SMC", "SMP", "BNC", "7/16", "EIA", "F", "QMA", "PC1.85", "PC2.9", "SMA REVERSE" or "N/A" (surface-mount chips and parts without a connector are "N/A").
''',
    },
    "RF Equalizer": {
        "cg": "RT",
        "techn": ["Function", "f (Min) (Hz)", "f (Max) (Hz)", "Attenuation (Typ) (dB)", "RFin (Max) (dBm)",
                  "Min. case temp. (°C)", "Min. ambient temp. (°C)", "Max. case temp. (°C)",
                  "Max. ambient temp. (°C)", "Connector System"],
        "extra_keys": ["Function", "f (Min) (Hz)", "f (Max) (Hz)", "Attenuation (Typ) (dB)", "RFin (Max) (dBm)",
                       "Min. case temp. (°C)", "Min. ambient temp. (°C)", "Max. case temp. (°C)",
                       "Max. ambient temp. (°C)", "Connector System", "Impedance (Ohm)"],
        "rules": '''
            - FOR "Function": Return exactly "Gain Equalizer".
            - FOR "f (Min) (Hz)" and "f (Max) (Hz)": The minimum and maximum operating frequency in Hz as a plain integer without units or exponent (e.g., 18 GHz -> 18000000000, DC -> 0).
            - FOR "Attenuation (Typ) (dB)": The typical attenuation (insertion loss at the reference frequency) in dB as a plain number.
            - FOR "RFin (Max) (dBm)": The maximum RF input power in dBm as a plain number. If only watts are given convert with dBm = 10 x log10(P in mW) and write the calculation in the "evidence" field.
            - FOR "Min. ambient temp. (°C)" and "Max. ambient temp. (°C)": The operating (ambient) temperature range as plain numbers.
            - FOR "Min. case temp. (°C)" and "Max. case temp. (°C)": Only if the datasheet states a case temperature range, as plain numbers; otherwise "N/A".
            - FOR "Connector System": Select ONLY ONE: "SMD" (surface-mount chip, no connector), "SMA" or "Type-N". Return "N/A" if none fits.
            - FOR "Impedance (Ohm)": The system impedance in ohms as a plain number (e.g., 50), otherwise "N/A".
''',
    },
}

# ----------------------------------------------------------------- detection
# patterns are matched case-insensitively with no letter on either side
DETECT = {
    "Resettable Fuses": ["resettable", "polyswitch", "pptc", "polyfuse", "hold current", "trip current"],
    "NTC PTC Varistor Sensors": ["thermistor", "ntc", "varistor"],
    "Potentiometer electr. adjustable": ["digital potentiometer", "digipot", "i2c", "spi", "non-volatile", "wiper position"],
    "Potentiometer mech. adjustable": ["potentiometer", "trimmer", "trimpot", "rotary", "taper"],
    "RF Attenuator": ["attenuator"],
    "RF Termination": ["rf termination", "chip termination", "coaxial termination", "microwave termination"],
    "RF Equalizer": ["equalizer", "equaliser"],
}


def _rx(word):
    return rf"(?<![a-z]){word}(?![a-z])"


def _hits(words, text):
    return sum(len(re.findall(_rx(w), text, flags=re.I)) for w in words)


def detect_category(pdf_text, file_names=()):
    """Return (category, confident). Falls back to 'Resistor constant' with confident=False."""
    names, head = " ".join(file_names), pdf_text[:3000]
    scores = {c: 5 * _hits(w, names) + 3 * _hits(w, head) + min(_hits(w, pdf_text), 10)
              for c, w in DETECT.items()}
    if scores["Potentiometer electr. adjustable"] >= 8:       # digital potentiometers also say 'potentiometer'
        return "Potentiometer electr. adjustable", True
    if scores["Resettable Fuses"] >= 8:                        # fuses also mention 'ptc'
        return "Resettable Fuses", True
    best, sc = max(scores.items(), key=lambda kv: kv[1])
    if sc >= 8:
        return best, True
    return RESISTOR, False
