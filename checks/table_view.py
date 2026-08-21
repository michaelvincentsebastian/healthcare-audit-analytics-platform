import pandas as pd
import os
import duckdb

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

try:
    con = duckdb.connect()

    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute("INSTALL ducklake; LOAD ducklake;")

    con.execute(f"ATTACH 'ducklake:{POSTGRES_CONNECTION}' AS lakehouse;")
    con.execute(f"USE lakehouse;")

    pd.set_option('display.max_columns', None)
    
    es = con.sql("SELECT COUNT(DISTINCT name) FROM bronze__dev.tabEncounter_SatuSehat;").df()
    print(es)
    
except Exception as e:
    print(f"Error: {e}")

finally:
    con.close()