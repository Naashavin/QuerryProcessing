import re
from datetime import datetime, timezone, timedelta
from config import EXPECTED_DATE_FORMATS

IST_TZ = timezone(timedelta(hours=5, minutes=30))


def normalise_gender(value):
    """Normalise gender encodings ('M', 'm', 'Male', 'Female', etc.) to 'M', 'F', 'O', or None."""
    if value is None:
        return None
    cleaned = str(value).strip().lower()
    if cleaned in ("m", "male", "man"):
        return "M"
    if cleaned in ("f", "female", "woman"):
        return "F"
    if cleaned in ("o", "other", "non-binary", "nb"):
        return "O"
    return None


def parse_date(value):
    """Parse mixed date strings (day-first for ambiguous numeric formats) to ISO 'YYYY-MM-DD', or None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in ("NA", "N/A", "NULL", "NONE"):
        return None

    # Handle full ISO timestamps (e.g., 2026-10-03T09:42:00+05:30 or ...Z)
    if "T" in text:
        try:
            iso_text = text.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso_text)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    for fmt in EXPECTED_DATE_FORMATS:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def clean_phone(value):
    """Strip formatting, validate 10-digit Indian mobile numbers starting [6-9], or return None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in ("NA", "N/A", "NULL"):
        return None
    digits = re.sub(r"\D", "", text)
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return digits
    return None


def parse_amount(value):
    """Parse currency strings like '1,200.50' or '₹ 1500' to non-negative float, or None if invalid/NA."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2) if value >= 0 else None
    text = str(value).strip()
    if not text or text.upper() in ("NA", "N/A", "NULL", "PENDING", "NONE"):
        return None
    cleaned = re.sub(r"[₹$,\s]|INR", "", text, flags=re.IGNORECASE)
    try:
        num = float(cleaned)
        if num < 0:
            return None
        return round(num, 2)
    except ValueError:
        return None


def standardise_name(value):
    """Normalise spacing, remove comma artifacts ('Mohammed, Irfan'), and apply title case."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in ("NA", "N/A", "NULL"):
        return None
    # Replace comma inside name like 'Mohammed, Irfan' with space
    text = text.replace(",", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text.title() if text else None


def normalise_patient_id(value):
    """Convert '1001', 'P1001', 'PT-1001' into canonical ('P1001', 1001) or (None, None)."""
    if value is None:
        return None, None
    text = str(value).strip().upper()
    if not text:
        return None, None
    m = re.fullmatch(r"(?:PT-|PT|P-|P)?0*(\d+)", text)
    if not m:
        return None, None
    num = int(m.group(1))
    return f"P{num}", num


def parse_eu_amount(value):
    """Parse European-style currency strings like '1.250,00 INR' to float 1250.00, or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2) if value >= 0 else None
    text = str(value).strip()
    if not text or text.upper() in ("NA", "NULL", "NONE"):
        return None
    cleaned = re.sub(r"(?:INR|EUR|₹|\s)", "", text, flags=re.IGNORECASE)
    # European format: dots are thousands separators, comma is decimal separator
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        num = float(cleaned)
        return round(num, 2) if num >= 0 else None
    except ValueError:
        return None


def utc_to_ist(timestamp_str):
    """Convert UTC ISO timestamp ('2026-11-09T14:30:00Z') to IST (UTC+05:30) ISO string & date."""
    if not timestamp_str:
        return None, None
    try:
        iso = str(timestamp_str).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_ist = dt.astimezone(IST_TZ)
        return dt_ist.isoformat(), dt_ist.strftime("%Y-%m-%d")
    except ValueError:
        return None, None


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    demos = [
        ("normalise_gender", normalise_gender, [
            ("M", "Exact uppercase code"),
            ("Female", "Full word title case"),
            ("m", "Lowercase single letter"),
            ("Male", "Full word title case"),
            ("", "Blank treated as None"),
        ]),
        ("parse_date", parse_date, [
            ("2026-10-03", "Already ISO 8601"),
            ("03-10-2026", "Day-first DD-MM-YYYY -> 2026-10-03"),
            ("14/03/1985", "Day-first DD/MM/YYYY"),
            ("05-Oct-2026", "Abbreviated month DD-Mon-YYYY"),
            ("04.10.2026", "Dot-separated DD.MM.YYYY"),
        ]),
        ("clean_phone", clean_phone, [
            ("9840012345", "Valid 10-digit mobile"),
            ("98400 56789", "Strip internal space"),
            ("+91-9444098765", "Strip country code & hyphen"),
            ("", "Missing -> None"),
            ("12345", "Too short -> None"),
        ]),
        ("parse_amount", parse_amount, [
            ("1,200.50", "Strip thousands comma -> float"),
            ("850", "Numeric string -> float"),
            ("₹ 1500", "Strip currency symbol & space"),
            ("NA", "Sentinel 'NA' -> None"),
            ("-250", "Negative fee rejected -> None"),
        ]),
        ("standardise_name", standardise_name, [
            ("Ravi Kumar", "Valid name retained"),
            ("Anitha S", "Valid initials retained"),
            ("Mohammed, Irfan", "Remove comma noise"),
            ("  karthik   r ", "Collapse spaces & title-case"),
            ("", "Blank -> None"),
        ]),
    ]
    print(f"{'Function':<18} | {'Input':<18} | {'Output':<14} | {'Rule Applied'}")
    print("-" * 86)
    for fname, fn, cases in demos:
        for raw_in, rule in cases:
            out = repr(fn(raw_in))
            print(f"{fname:<18} | {repr(raw_in):<18} | {out:<14} | {rule}")
