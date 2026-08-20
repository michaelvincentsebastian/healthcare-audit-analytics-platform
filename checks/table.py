import os
from pathlib import Path

import duckdb
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Credentials
PG_HOST = os.getenv("POSTGRES_HOST")
PG_PORT = os.getenv("POSTGRES_PORT")
PG_USER = os.getenv("POSTGRES_USER")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")
PG_DATABASE = os.getenv("TABULAR_METADATA_DB_NAME")

POSTGRES_CONNECTION = (
    f"postgres:dbname={PG_DATABASE} "
    f"host={PG_HOST} "
    f"user={PG_USER} "
    f"password={PG_PASSWORD} "
    f"port={PG_PORT}"
)

BRONZE_OUTPUT = Path("checks/output/bronze")
SILVER_SUBMISSION_OUTPUT = Path("checks/output/silver/submission")
SILVER_FHIR_OUTPUT = Path("checks/output/silver/fhir")
GOLD_OUTPUT = Path("checks/output/gold")

BRONZE_OUTPUT.mkdir(parents=True, exist_ok=True)
SILVER_SUBMISSION_OUTPUT.mkdir(parents=True, exist_ok=True)
SILVER_FHIR_OUTPUT.mkdir(parents=True, exist_ok=True)
GOLD_OUTPUT.mkdir(parents=True, exist_ok=True)

con = None

try:
    con = duckdb.connect()

    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute("INSTALL ducklake; LOAD ducklake;")

    con.execute(f"ATTACH 'ducklake:{POSTGRES_CONNECTION}' AS lakehouse;")
    
    # ==========================================================
    # Export Bronze
    # ==========================================================
    bronze_tables = con.sql("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'bronze__dev'
        ORDER BY table_name;
    """).fetchall()

    print(f"Found {len(bronze_tables)} bronze tables.\n")

    for (table_name,) in bronze_tables:
        print(f"[Bronze] Exporting {table_name}...")

        df = con.sql(f"""
            SELECT *
            FROM lakehouse.bronze__dev."{table_name}";
        """).to_df()

        output_file = BRONZE_OUTPUT / f"{table_name}.csv"
        df.to_csv(output_file, index=False)

        print(f"  -> {output_file}")

    # ==========================================================
    # Export Silver Submission Audit
    # ==========================================================
    silver_tables = con.sql("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'silver__dev'
          AND table_name LIKE '%_data_submission_audit'
        ORDER BY table_name;
    """).fetchall()

    print(f"\nFound {len(silver_tables)} silver submission audit tables.\n")

    for (table_name,) in silver_tables:
        print(f"[Silver] Exporting {table_name}...")

        df = con.sql(f"""
            SELECT *
            FROM lakehouse.silver__dev."{table_name}"
        """).to_df()

        output_file = SILVER_SUBMISSION_OUTPUT / f"{table_name}.csv"
        df.to_csv(output_file, index=False)

        print(f"  -> {output_file}")
    # ==========================================================
    # Export Silver FHIR Resource
    # ==========================================================
    silver_fhir_tables = con.sql("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'silver__dev'
        AND table_name LIKE '%_fhir_resource'
        ORDER BY table_name;
    """).fetchall()

    print(f"\nFound {len(silver_fhir_tables)} silver FHIR resource tables.\n")

    for (table_name,) in silver_fhir_tables:
        print(f"[Silver FHIR] Exporting {table_name}...")

        df = con.sql(f"""
            SELECT *
            FROM lakehouse.silver__dev."{table_name}"
        """).to_df()

        output_file = SILVER_FHIR_OUTPUT / f"{table_name}.csv"
        df.to_csv(output_file, index=False)

        print(f"  -> {output_file}")

    # ==========================================================
    # Export Gold + cek kosong/tidaknya tiap tabel
    # ==========================================================
    # Ambil SEMUA tabel/view di schema gold__dev -- ini termasuk
    # audit_rule / audit_run / audit_finding DAN 8 tabel
    # audit_check_* (check model per rule) yang jadi sumber audit_finding.
    # Row count per tabel dicek TERPISAH dari export CSV-nya supaya tetap
    # dapat angkanya walau tabel kosong (count(*) atas 0 baris tetap valid,
    # to_df() atas 0 baris tetap valid juga -- tapi count(*) dipisah biar
    # jelas dibaca sebagai "hasil pengecekan", bukan sekedar len(df)).
    gold_tables = con.sql("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'gold__dev'
        ORDER BY table_name;
    """).fetchall()

    print(f"\nFound {len(gold_tables)} gold tables.\n")

    row_counts = []

    for (table_name,) in gold_tables:
        count = con.sql(f"""
            SELECT count(*) FROM lakehouse.gold__dev."{table_name}"
        """).fetchone()[0]

        is_empty = count == 0
        flag = "KOSONG (0 baris)" if is_empty else f"{count} baris"
        print(f"[Gold] {table_name}: {flag}")

        row_counts.append({
            "table_name": table_name,
            "row_count": count,
            "is_empty": is_empty,
        })

        # Tetap export isinya ke CSV (walau kosong -- df 0 baris tetap valid,
        # kolomnya tetap kebaca) supaya bisa diperiksa manual kalau perlu.
        df = con.sql(f"""
            SELECT *
            FROM lakehouse.gold__dev."{table_name}"
        """).to_df()

        output_file = GOLD_OUTPUT / f"{table_name}.csv"
        df.to_csv(output_file, index=False)
        print(f"  -> {output_file}")

    summary_df = pd.DataFrame(row_counts)
    summary_file = GOLD_OUTPUT / "_row_counts_summary.csv"
    summary_df.to_csv(summary_file, index=False)

    empty_tables = [r["table_name"] for r in row_counts if r["is_empty"]]
    print(f"\nRingkasan gold__dev: {len(row_counts)} tabel dicek, "
          f"{len(empty_tables)} kosong.")
    if empty_tables:
        print(f"  Tabel kosong: {', '.join(empty_tables)}")
    print(f"  -> {summary_file}")

    print("\nDone.")

except Exception as e:
    print(f"Error: {e}")

finally:
    if con is not None:
        con.close()
        print("DuckDB connection closed.")