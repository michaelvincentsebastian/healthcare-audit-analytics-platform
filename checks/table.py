import duckdb
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

# Credentials
PG_HOST = os.getenv("POSTGRES_HOST")
PG_PORT = os.getenv("POSTGRES_PORT")
PG_USER = os.getenv("POSTGRES_USER")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")
PG_DATABASE = os.getenv("TABULAR_METADATA_DB_NAME")

# Custom Endpoint
POSTGRES_CONNECTION=f"postgres:dbname={PG_DATABASE} host={PG_HOST} user={PG_USER} password={PG_PASSWORD} port={PG_PORT}"

try:
    con = duckdb.connect()
    
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute("INSTALL ducklake; LOAD ducklake;")
    
    con.execute(f"ATTACH 'ducklake:{POSTGRES_CONNECTION}' as lakehouse;")
    
    print(con.sql("SHOW ALL TABLES;"))
    
    encounter_raw = con.sql("SELECT * FROM lakehouse.bronze__dev.tabcondition_satusehat;").to_df()
    encounter_fhir = con.sql("SELECT * FROM lakehouse.silver__dev.condition_fhir_resource;").to_df()
    
    df1 = pd.DataFrame(encounter_raw)
    df1.to_csv('checks/output/condition_raw.csv', index=False)
    
    df2 = pd.DataFrame(encounter_fhir)
    df2.to_csv('checks/output/conditon_fhir.csv', index=False)
    
except Exception as e:
    print(f"Error: {e}")
    
finally:
    con.close()
    print("DuckDB connection closed.")    