import os
from flask import Flask, render_template
import pandas as pd
from sqlalchemy import create_engine, inspect
import psycopg2

# Create Python app using Flask
app = Flask(__name__)


# Function to process input .csv files
def process_data(file_name):
    """Clean up input .csv files

    Args:
        file_name (str): Format data/{file_name}.csv;
        must be compounds, user_experiments, users csv files

    Returns:
        df (dataframe): Clean dataframe without delimiters and separators
    """
    notebook_path = os.path.abspath(file_name)
    df = pd.read_csv(notebook_path, sep="\t")

    # Remove commas and \t from dataframe
    df.columns = df.columns.str.replace(",", "")

    df = df.replace(",", "", regex=True)

    df.columns = df.columns.str.replace("\t", "")

    df = df.replace("\t", "", regex=True)

    return df


# Function to connect to PostgreSQL database
def create_connection():
    """Use login credentials to connect to PostgreSQL.

    Returns:
        conn: authenticated PostgreSQL connection
        cur: cursor object to execute PostgreSQL queries
    """

    # Connection details
    host = "db"
    port = "5432"
    database = "eikon_db"
    user = "labuser"
    password = "eikon-rules-,.bqzBwX6.}*"

    try:
        # Establish connection to PostgreSQL
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
        )
        # Create cursor object
        cur = conn.cursor()
        print("Successfully connected to PostgreSQL!")
        return conn, cur
    except psycopg2.Error as error:
        print(f"Error connecting to PostgreSQL: {error}")
        return None, None


# Function to create PostgreSQL schema
def create_postgres_schema(conn, cur):
    """Create sandbox schema in eikon_db database

    Args:
        conn: authenticated PostgreSQL connection
        cur: cursor object to execute PostgreSQL queries
    """
    try:
        cur.execute("CREATE SCHEMA IF NOT EXISTS sandbox;")

        conn.commit()

        print("Schema created successfully!")

    except psycopg2.Error as error:
        print(f"Error creating schema: {error}")


# Function to map pandas data types to PostgreSQL data types
def get_postgresql_data_type(dtype):
    """Map pandas data types to PostgreSQL data types

    Args:
        dtype (str): key in type_mappig dictionary representing pandas data type

    Returns:
        dtype (str): value in type_mappig dictionary representing PostgreSQL data type
    """
    type_mapping = {
        "int64": "INTEGER",
        "float64": "NUMERIC",
        "bool": "BOOLEAN",
        "datetime64[ns]": "TIMESTAMP",
        "object": "TEXT",
    }

    # Retrieve PostgreSQL data type from type_mapping dictionary, or else assign TEXT
    return type_mapping.get(str(dtype), "TEXT")


# Function to generate SQL statement to create PostgreSQL table
def generate_create_table_statement(df, table_name):
    """Create PostgreSQL table if it doesn't exist, using data type mapping

    Args:
        df (dataframe): dataframe to be written to PostgreSQL table
        table_name (str): PostgreSQL table name

    Returns:
        create_table_sql (str): SQL statement to create table in database
    """
    create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ("

    for column_name, dtype in df.dtypes.items():
        column_type = get_postgresql_data_type(dtype)
        create_table_sql += f"{column_name} {column_type}, "

    create_table_sql = create_table_sql.rstrip(", ") + ")"

    return create_table_sql


# Function to execute SQL statement to create PostgreSQL table
def create_postgres_table(conn, cur, create_table_statement):
    """Execute SQL statement to create PostgreSQL table

    Args:
        conn: authenticated PostgreSQL connection
        cur: cursor object to execute PostgreSQL queries
        create_table_statement (str): SQL statement to create table in database
        from generate_create_table_statement()
    """
    try:
        cur.execute(create_table_statement)

        conn.commit()
        print("Table created or already exists.")

    except psycopg2.Error as error:
        conn.rollback()  # Cancel previous action
        print(f"Error creating table: {error}")


# Function to write dataframe to PostgreSQL table
def write_data_to_postgres(feature_df):
    """Write dataframe to PostgreSQL table

    Args:
        feature_df (dataframe): final dataframe after feature derivation from
        compounds, user_experiments, users csv files
    """

    engine = create_engine("postgresql://labuser:eikon-rules-,.bqzBwX6.}*@db:5432/eikon_db")

    inspector = inspect(engine)

    # Check if features table exists in the sandbox schema
    if inspector.has_table("features", schema="sandbox"):
        # Retrieve feature derivation table from the database
        query = "SELECT * FROM sandbox.features"
        existing_data = pd.read_sql(query, engine)

        # Check if existing data is the same as the dataframe to prevent duplication
        if existing_data.equals(feature_df):
            print("Data is already up to date. No changes made.")
        if not existing_data.equals(feature_df):
            # Write dataframe to the PostgreSQL table
            feature_df.to_sql("features", engine, schema="sandbox", if_exists="replace", index=False)

            print("Data inserted successfully.")

    engine.dispose()


# ETL function to load, process, and write data to PostgreSQL database
def etl():
    """Load, process, and write data to PostgreSQL database

    Returns:
        (dict): status, message
        (int): status
    """
    # Begin ETL process
    try:
        # Load, read, and clean compounds, user_experiments, users csv files
        user_file = "data/users.csv"

        user_df = process_data(user_file)

        compounds_file = "data/compounds.csv"
        compounds_df = process_data(compounds_file)

        experiments_file = "data/user_experiments.csv"
        experiments_df = process_data(experiments_file)

        user_compounds_df = experiments_df.copy()
        # Split the semicolon-separated compound id's into a list
        user_compounds_df["experiment_compound_ids"] = user_compounds_df["experiment_compound_ids"].str.split(";")

        # Explode the list of compound id's into individual rows
        user_compounds_df = user_compounds_df.explode("experiment_compound_ids")

        user_compounds_df = user_compounds_df.reset_index(drop=True)

        # Derive Feature 1: "Total experiments a user ran"
        user_counts_df = experiments_df.groupby(["user_id"]).size().reset_index(name="experiment_count")

        # Derive Feature 2: "Average experiments amount per user",
        # assuming this is referring to average experiment run time per user
        avg_runtime_per_user = (
            experiments_df.groupby("user_id")["experiment_run_time"]
            .mean()
            .reset_index()
            .rename(columns={"experiment_run_time": "avg_experiment_run_time"})
        )

        # Merge original users table with user_counts_df
        user_count_final = pd.merge(user_df, user_counts_df, how="outer", on="user_id")

        # Merge user_count_final with avg_runtime_per_user
        avg_runtime_final = pd.merge(user_count_final, avg_runtime_per_user, how="outer", on="user_id")

        # Derive Feature 3: "User's most commonly experimented compound"
        # Get count of compound id's per user
        compound_counts = (
            user_compounds_df.groupby(["user_id", "experiment_compound_ids"]).size().reset_index(name="count")
        )
        compound_counts.sort_values("count", ascending=False, inplace=True)

        # Derive most common compound per user based on compound counts
        most_common_compound_per_user = (
            compound_counts.groupby("user_id")
            .apply(
                lambda x: x["experiment_compound_ids"].tolist()
                if x["count"].max() == 1
                else x["experiment_compound_ids"].mode()[0]
            )
            .reset_index(name="compound_id")
        )

        # Explode the list of compound id's into individual rows
        most_common_compound_per_user = (
            most_common_compound_per_user.explode("compound_id").drop_duplicates().reset_index(drop=True)
        )

        # Merge most_common_compound_per_user with original compounds table
        most_common_compound_per_user_final = pd.merge(
            most_common_compound_per_user, compounds_df, how="outer", on="compound_id"
        )
        # Generate final dataframe
        feature_df = pd.merge(
            avg_runtime_final,
            most_common_compound_per_user_final,
            how="outer",
            on="user_id",
        )

        # Set data types for final dataframe to be mapped to PostgreSQL
        feature_df[["user_id", "compound_id"]] = feature_df[["user_id", "compound_id"]].astype("int64")
        feature_df["signup_date"] = pd.to_datetime(feature_df["signup_date"])

        # Get number of rows of final dataframe
        num_rows = len(feature_df)

        # Begin PostgreSQL transaction
        # Create connection to PostgreSQL database
        conn, cur = create_connection()
        if conn is not None:
            try:
                # Create sandbox schema
                create_postgres_schema(conn, cur)

                # SQL statement to create features table
                table_name = "sandbox.features"
                create_table_statement = generate_create_table_statement(feature_df, table_name)

                # Create features table in sandbox schema
                create_postgres_table(conn, cur, create_table_statement)

                # Write final dataframe to sandbox.features table
                write_data_to_postgres(feature_df)
            finally:
                cur.close()
                conn.close()
        return {
            "status": "success",
            "message": "ETL process completed" + " for " + str(num_rows) + " rows",
        }, 200  # Successful status code

    except Exception as error:
        return {"status": "error", "message": str(error)}, 500  # Error status code


# Function to fetch data from features table in PostgreSQL
def fetch_postgre_data():
    """Fetch data from features table in PostgreSQL

    Returns:
        df (dataframe): features table in PostgreSQL as dataframe
    """
    conn, cur = create_connection()

    # Run query to pull data from PostgreSQL
    cur.execute("SELECT * FROM eikon_db.sandbox.features")

    col_names = [desc[0] for desc in cur.description]

    rows = cur.fetchall()

    cur.close()
    conn.close()

    # Convert the fetched column names and rows into a dataframe
    df = pd.DataFrame(rows, columns=col_names)

    return df


# API endpoint for the index page
@app.route("/", methods=["GET"])
def index():
    """Endpoint for available API resources

    Returns:
        (html): Links to available API endpoints, /trigger-etl and /etl-results
    """

    return """
    <html>
      <head>
        <title>Eikon Backend ETL API</title>
      </head>
      <body>
        <h1>Eikon Backend ETL API</h1>
        <p>Available endpoints:</p>
        <ul>
          <li><a href="/trigger-etl">Trigger ETL</a></li>
          <li><a href="/etl-results">ETL Results</a></li>
        </ul>
      </body>
    </html>
    """


# API endpoint to trigger ETL process
@app.route("/trigger-etl", methods=["GET", "POST"])
def trigger_etl():
    """Endpoint to trigger etl() function

    Returns:
        (html): _description_
    """
    with app.app_context():
        # Call the etl() function to trigger the ETL process
        result, status_code = etl()

        # Render html files from templates folder based on ETL status
        # Success
        if status_code == 200:
            return render_template("success.html", status_code=status_code, message=result["message"])
        # Error
        else:
            return render_template("error.html", status_code=status_code, message=result["message"])


# API endpoint to retrieve ETL results
@app.route("/etl-results", methods=["GET"])
def etl_results():
    """Endpoint to retrieve ETL results -- features table in PostgreSQL

    Returns:
        json_response (json): Converted features table/dataframe in JSON format
    """
    # Fetch the features table from PostgreSQL
    df = fetch_postgre_data()

    # Convert dataframe to JSON format for HTML rendering
    json_response = df.to_json(orient="records")

    # Set response headers
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
    }

    # Return dataframe as JSON response
    return json_response, 200, headers


# Start Flask server
if __name__ == "__main__":
    app.run()
