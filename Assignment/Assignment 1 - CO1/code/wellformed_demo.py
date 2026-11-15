import csv
import io
import json
import xml.etree.ElementTree as ET


ILL_FORMED_CSV = 'P1001,"Ravi "Kumar",M,14/03/1985\n'
ILL_FORMED_JSON = '{"lab_report_id": "LR-01", "patient_ref": "1001", "status": "FINAL",}'
ILL_FORMED_XML = '<dispense id="RX-88121"><patient id="1003" name="Irfan"></dispense>'


def main():
    results = []

    # 1. CSV parse failure (strict mode catches malformed quoting)
    try:
        reader = csv.reader(io.StringIO(ILL_FORMED_CSV), strict=True)
        for _ in reader:
            pass
    except csv.Error as err:
        results.append(("CSV", type(err).__name__, str(err)))

    # 2. JSON parse failure (trailing comma violates RFC 8259)
    try:
        json.loads(ILL_FORMED_JSON)
    except json.JSONDecodeError as err:
        results.append(("JSON", type(err).__name__, str(err)))

    # 3. XML parse failure (unclosed <patient> tag)
    try:
        ET.fromstring(ILL_FORMED_XML)
    except ET.ParseError as err:
        results.append(("XML", type(err).__name__, str(err)))

    print(f"{'Format':<6} | {'Exception Type':<18} | {'Message'}")
    print("-" * 80)
    for fmt, exc_type, msg in results:
        print(f"{fmt:<6} | {exc_type:<18} | {msg}")


if __name__ == "__main__":
    main()

