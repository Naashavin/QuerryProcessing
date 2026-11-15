# CityCare Health Network — Data Wrangling Pipeline (DSA0501 Assignment 1 - CO1)

**Student:** Avinaash A (`192324260`)

## Execution Order

Run the modules in sequence from inside the `code/` folder:

1. `python setup_project.py` — Creates `raw/`, `staged/`, `curated/`, `logs/`, writes seed CSV, and checks standard-library modules.
2. `python task1_defect_check.py` — Runs the <=40-line seed CSV defect audit (Task 1).
3. `python utils.py` — Demonstrates the 5 core wrangling utility functions (Task 3).
4. `python task4_benchmark.py` — Benchmarks 200 mixed-format date parses across 5 runs (Task 4).
5. `python generate_data.py --seed 42` — Generates dirty Sources A (CSV), B (JSON), C (XML), and Day-4 Source D (JSON Lines) (Task 5 & Day-4).
6. `python profile.py` — Profiles generated raw files and checks defect injection rates (Task 5).
7. `python wellformed_demo.py` — Demonstrates parse failures on ill-formed CSV, JSON, and XML snippets (Task 6).
8. `python csv_wrangler.py` — Cleans, deduplicates, reconciles, and writes `staged/clean_visits.csv` & `staged/rejected_visits.csv` (Task 7).
9. `python json_wrangler.py` — Recursively inspects JSON schema, flattens reports to `staged/lab_results_flat.json` & `staged/lab_exceptions.json` (Task 8).
10. `python xml_wrangler.py` — Validates XML totals, handles malformed XML safely, writes `staged/dispensing_clean.xml` & `staged/dispensing_items.csv` (Task 9).
11. `python schema.py` — Demonstrates SQLite DDL constraints and `IntegrityError` handling (Task 10).
12. `python integrate.py` — Normalizes IDs, integrates Sources A/B/C by date proximity, and populates `curated/citycare.db` (Task 11).
13. `python convert.py` — Exports `patient_summary.json`, `visits_flat.csv`, `dispensing_report.xml`, runs CSV->JSON->CSV round-trip check, and benchmarks formats (Task 11).
14. `python quality_report.py` — Computes before-and-after quality metrics against Task 1 thresholds (Task 12).
15. `python day4_impact_and_benchmark.py` — Runs Day-4 D1 failure observation and D2 memory/timing comparison (Day-4 D1 & D2).
16. `python json_lines_wrangler.py` — Streams Source D JSONL, converts UTC to IST, parses European fees, and migrates `citycare.db` to `curated/citycare_v2.db` (Day-4 D3).
17. `python -m unittest test_pipeline.py -v` — Executes all 16 unit, format, integration, and negative tests (Task 12).

