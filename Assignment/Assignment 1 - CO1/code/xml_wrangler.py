import csv
import logging
import xml.etree.ElementTree as ET
from config import (
    CLEAN_XML_PATH,
    DISPENSING_ITEMS_CSV_PATH,
    LOGS_DIR,
    MALFORMED_XML_PATH,
    RAW_XML_PATH,
)
from utils import normalise_patient_id, parse_date, standardise_name


def setup_logger():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("xml_wrangler")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fh = logging.FileHandler(LOGS_DIR / "xml_wrangler.log", mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    return logger


def wrangle_xml(
    raw_path=RAW_XML_PATH,
    clean_xml_path=CLEAN_XML_PATH,
    items_csv_path=DISPENSING_ITEMS_CSV_PATH,
    malformed_path=MALFORMED_XML_PATH,
):
    logger = setup_logger()
    tree = ET.parse(raw_path)
    root = tree.getroot()

    # Demonstrate iter() usage to count raw <item> elements
    raw_item_count = sum(1 for _ in root.iter("item"))

    clean_root = ET.Element(
        "pharmacy_dispensing",
        branch=root.attrib.get("branch", "Hospital-B"),
        schema_version="1.0",
    )

    flat_items = []
    mismatch_count = 0
    largest_discrepancy = 0.0
    missing_total_count = 0
    non_numeric_qty_count = 0
    empty_items_count = 0
    valid_dispense_count = 0

    for disp in root.findall("dispense"):
        disp_id = disp.attrib.get("id", "").strip()
        raw_date = disp.attrib.get("date", "")
        iso_date = parse_date(raw_date)

        pat_el = disp.find("patient")
        raw_pid = pat_el.attrib.get("id", "") if pat_el is not None else ""
        raw_pname = pat_el.attrib.get("name", "") if pat_el is not None else ""
        pid_str, _ = normalise_patient_id(raw_pid)
        pname = standardise_name(raw_pname) or "Unknown"

        items_el = disp.find("items")
        raw_items = items_el.findall("item") if items_el is not None else []
        if not raw_items:
            empty_items_count += 1
            logger.warning(f"{disp_id}: Empty <items> block — record skipped from clean XML.")
            continue

        valid_items = []
        recomputed_total = 0.0
        for item in raw_items:
            dcode = item.attrib.get("drug_code", "").strip()
            raw_qty = (item.attrib.get("qty") or "").strip()
            raw_price = (item.attrib.get("unit_price") or "").strip()
            drug_name = (item.text or "").strip()

            try:
                qty_val = int(raw_qty)
                if qty_val <= 0:
                    raise ValueError("Non-positive quantity")
            except ValueError:
                non_numeric_qty_count += 1
                logger.warning(f"{disp_id} ({dcode}): Non-numeric/invalid qty '{raw_qty}' — item skipped.")
                continue

            try:
                price_val = float(raw_price)
            except ValueError:
                logger.warning(f"{disp_id} ({dcode}): Invalid unit_price '{raw_price}' — item skipped.")
                continue

            line_total = round(qty_val * price_val, 2)
            recomputed_total += line_total
            valid_items.append((dcode, drug_name, qty_val, price_val, line_total))

        if not valid_items or not pid_str or not iso_date:
            logger.warning(f"{disp_id}: No valid items or missing patient/date — record skipped.")
            continue

        recomputed_total = round(recomputed_total, 2)
        total_el = disp.find("total")
        currency = total_el.attrib.get("currency", "INR") if total_el is not None else "INR"
        total_status = "MATCHED"

        if total_el is None or not (total_el.text or "").strip():
            missing_total_count += 1
            total_status = "IMPUTED_MISSING"
            logger.info(f"{disp_id}: Missing <total> element; computed {recomputed_total:.2f}")
        else:
            try:
                stated_total = float(total_el.text.strip())
                diff = abs(stated_total - recomputed_total)
                if diff > 0.01:
                    mismatch_count += 1
                    total_status = "CORRECTED_MISMATCH"
                    if diff > largest_discrepancy:
                        largest_discrepancy = round(diff, 2)
                    logger.warning(
                        f"{disp_id}: Total mismatch (stated={stated_total:.2f}, computed={recomputed_total:.2f}, diff={diff:.2f})"
                    )
            except ValueError:
                mismatch_count += 1
                total_status = "CORRECTED_INVALID"

        # Build clean XML <dispense> element
        c_disp = ET.SubElement(clean_root, "dispense", id=disp_id, date=iso_date)
        ET.SubElement(c_disp, "patient", id=pid_str, name=pname)
        c_items = ET.SubElement(c_disp, "items")
        for dcode, drug_name, qty_val, price_val, line_total in valid_items:
            c_item = ET.SubElement(
                c_items,
                "item",
                drug_code=dcode,
                qty=str(qty_val),
                unit_price=f"{price_val:.2f}",
            )
            c_item.text = drug_name
            flat_items.append({
                "rx_id": disp_id,
                "dispensed_on": iso_date,
                "patient_id": pid_str,
                "patient_name": pname,
                "drug_code": dcode,
                "drug_name": drug_name,
                "quantity": qty_val,
                "unit_price": f"{price_val:.2f}",
                "line_total": f"{line_total:.2f}",
                "rx_total": f"{recomputed_total:.2f}",
                "total_status": total_status,
            })

        c_total = ET.SubElement(c_disp, "total", currency=currency, status=total_status)
        c_total.text = f"{recomputed_total:.2f}"
        valid_dispense_count += 1

    clean_xml_path.parent.mkdir(parents=True, exist_ok=True)
    clean_tree = ET.ElementTree(clean_root)
    ET.indent(clean_tree, space="  ")
    clean_tree.write(clean_xml_path, encoding="utf-8", xml_declaration=True)

    csv_cols = [
        "rx_id", "dispensed_on", "patient_id", "patient_name",
        "drug_code", "drug_name", "quantity", "unit_price",
        "line_total", "rx_total", "total_status",
    ]
    with open(items_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_cols)
        writer.writeheader()
        writer.writerows(flat_items)

    # Demonstrate safe failure on malformed XML
    malformed_error = None
    if malformed_path.exists():
        try:
            ET.parse(malformed_path)
        except ET.ParseError as err:
            line_no, col_no = err.position
            malformed_error = f"ET.ParseError at line {line_no}, column {col_no}: {err}"
            logger.error(f"Malformed file check ({malformed_path.name}): {malformed_error}")

    return {
        "raw_dispenses": len(root.findall("dispense")),
        "raw_items_iter": raw_item_count,
        "valid_dispenses": valid_dispense_count,
        "flat_item_rows": len(flat_items),
        "empty_items_count": empty_items_count,
        "non_numeric_qty_count": non_numeric_qty_count,
        "missing_total_count": missing_total_count,
        "mismatch_count": mismatch_count,
        "largest_discrepancy": largest_discrepancy,
        "malformed_error": malformed_error,
    }


if __name__ == "__main__":
    res = wrangle_xml()
    print("=== XML Wrangler Summary ===")
    print("Raw dispenses       :", res["raw_dispenses"])
    print("Raw items (iter)    :", res["raw_items_iter"])
    print("Valid dispenses     :", res["valid_dispenses"])
    print("Flat CSV item rows  :", res["flat_item_rows"])
    print("Empty <items> blocks:", res["empty_items_count"])
    print("Non-numeric qty     :", res["non_numeric_qty_count"])
    print("Missing <total>     :", res["missing_total_count"])
    print("Total mismatches    :", res["mismatch_count"])
    print(f"Largest discrepancy : Rs. {res['largest_discrepancy']:.2f}")
    print("Malformed XML test  :", res["malformed_error"])

