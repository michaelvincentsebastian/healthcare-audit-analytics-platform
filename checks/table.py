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

BRONZE_OUTPUT.mkdir(parents=True, exist_ok=True)
SILVER_SUBMISSION_OUTPUT.mkdir(parents=True, exist_ok=True)
SILVER_FHIR_OUTPUT.mkdir(parents=True, exist_ok=True)

con = None

try:
    con = duckdb.connect()

    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute("INSTALL ducklake; LOAD ducklake;")

    con.execute(f"ATTACH 'ducklake:{POSTGRES_CONNECTION}' AS lakehouse;")
    
    check_patientuid = con.sql("""
        SELECT *
        FROM lakehouse.reference__dev.icd_10
        LIMIT 5;
    """)
    
    print(check_patientuid)

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
            FROM lakehouse.bronze__dev."{table_name}"
            LIMIT 5;
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
    
    print("\nDone.")

except Exception as e:
    print(f"Error: {e}")

finally:
    if con is not None:
        con.close()
        print("DuckDB connection closed.")