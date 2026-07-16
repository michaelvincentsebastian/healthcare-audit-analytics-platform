import duckdb
import os
from dotenv import load_dotenv

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
    
    table_list = con.sql("SHOW ALL TABLES;")
    print(f"Table List\n{table_list}")
    
    patient_data = con.sql("SELECT name, patient_relation FROM lakehouse.bronze__dev.patient_data;")
    print(f"Patient Data\n{patient_data}")
    
except Exception as e:
    print(f"Error: {e}")
    
finally:
    con.close()
    print("DuckDB connection closed.")    