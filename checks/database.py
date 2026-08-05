import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

HOST=os.getenv("SATUSEHAT_HOST")
PORT=os.getenv("SATUSEHAT_PORT")
USER=os.getenv("SATUSEHAT_USER")
PASSWORD=os.getenv("SATUSEHAT_PASSWORD")
DB=os.getenv("SATUSEHAT_DB")

try:
    con = duckdb.connect()
    print("Connected to DuckDB")
    con.execute("INSTALL mysql; LOAD mysql;")
    print("Install Suceed")
    
    con.execute(f"ATTACH 'host={HOST} user={USER} password={PASSWORD} port={PORT} database={DB}' AS frappe_mariadb (TYPE mysql);")
    print("MariaDB Connection Succeed")
    
    con.execute("USE frappe_mariadb;")
    print(con.sql("SELECT * FROM 'tabPatient Encounter';"))
    
except Exception as error:
    print(f"❌ Error Mesage: {error}")
    
finally:
    con.close()