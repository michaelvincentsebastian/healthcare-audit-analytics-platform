### Streamlit Dahshboard for visualize Data in Development Phase.

import streamlit as st
import pandas as pd
import duckdb

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

def get_data(catalog, schema, table):
    try:
        con = duckdb.connect()

        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute("INSTALL postgres; LOAD postgres;")
        con.execute("INSTALL ducklake; LOAD ducklake;")

        con.execute(f"ATTACH 'ducklake:{POSTGRES_CONNECTION}' AS {catalog};")
        con.execute(f"USE {catalog};")

        view = con.sql(f"SELECT * FROM {schema}.{table};").df()
        return view

    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error

    finally:
        con.close()

def visualize_data():
    st.title("Data Visualization Dashboard")
    st.write("This dashboard visualizes data from the `bronze__dev.tabEncounter_SatuSehat` table.")

    data = get_data("lakehouse", "bronze__dev", "tabEncounter_SatuSehat")

    if not data.empty:
        st.subheader("Data Preview")
        st.dataframe(data.head(10))  # Display the first 10 rows of the DataFrame

        st.subheader("Column Statistics")
        st.write(data.describe())  # Show basic statistics for numeric columns

        st.subheader("Column Names")
        st.write(data.columns.tolist())  # List all column names

    else:
        st.warning("No data available to display.")