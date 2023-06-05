# Backend Engineering Take-Home Challenge

Submitted by: Crystal Nguyen

This API allows you to trigger an **ETL (Extract, Transform, Load)** process and retrieve the results from a **PostgreSQL** database. Uses **Flask** as the web framework for building the API and **Gunicorn** to deploy the Flask app.

## System Requirements

The app and its dependencies have been containerized via Docker, so make sure you have Docker Desktop installed! 

- Docker Desktop v4.19.0
  - Docker will manage dependencies related to:
    - Python: `python:3.10-slim`
    - PostgreSQL `(PostgreSQL) 15.3 (Debian 15.3-1.pgdg110+1)`
    - `requirements.txt`

## Input Requirements

See below for how the Github repo is structured and the files that are needed to run the app:

```symbol
  eikon-backend-exercise-cn
  ├─ data
  │   ├─ compounds.csv
  │   ├─ user_experiments.csv
      └─ users.csv
  ├─ templates
  │   ├─ error.html
  │   └─ success.html
  ├─ .dockerignore
  ├─ app.py
  ├─ build_and_run.sh
  ├─ docker-compose.yml
  ├─ Dockerfile-app
  ├─ Dockerfile-postgres
  ├─ fetch_results.sh
  ├─ init.sql
  ├─ README.md
  ├─ requirements.txt
  └─ run_app.sh
```

**Notable files:**
- **`README.md`** intro to the app and general usage!
- `data` directory contains provided raw input files
- `templates` directory contains HTML templates that the Flask app uses to render API request status
- **`requirements.txt`** used to install dependences for Docker containers
- **`app.py`** file is the entry point for the Flask app
- **`docker-compose.yml`** used to handle both PostgreSQL and Flask/Gunicorn containers in single app
- **`Dockerfile-app`** for building the Flask/Gunicorn app container, referred to as `eikon-app`
- **`Dockerfile-postgres`** for building the PostgreSQL container, referred to as `eikon-db`
- `init.sql` used for initializing the PostgreSQL database container
- **`build_and_run.sh`** shell script used to build and run Docker containers
- **`run_app.sh`** shell script used to make curl requests to API endpoints
- **`fetch_results.sh`** shell script used to fetch PostgreSQL table with feature derivation data from the Docker container

## Build and run the application

1. Make sure you have Docker installed https://www.docker.com/products/docker-desktop/
3. Open terminal or command prompt and use `cd` to navigate to where you want the git repo cloned.
2. Clone the git repo: `git clone https://github.com/crystalhelloo/eikon-backend-exercise-cn.git`
4. Navigate into the project folder: `cd eikon-backend-exercise-cn`
5. Build and run the Docker container via one of the options below:
 - **Shell:** Run the `build_and_run.sh` shell script: `./build_and_run.sh`
 - **Manually:** `docker-compose up -d --build`
 - **Note:** The shell script first runs `docker-compose down` to resolve conflicts with ports and container names upon rebuilding containers. You can run the `docker-compose down` line manually/separately in the terminal as well. This command will stop and remove existing containers. 
6. Access the application via one of the options below:
 - **Shell:** Run the `run_app.sh` shell script to make curl requests to the API endpoint: `./run_app.sh`. The shell script `run_app.sh` returns the JSON response for the `/etl-results` endpoint in tabular format.
 - **Manually:** Use the terminal to run command `curl -s http://127.0.0.1:5000/api-endpoint`. Replace **api-endpoint** with the endpoint you want to access. Note that `curl -s http://127.0.0.1:5000/etl-results` will return the data as a JSON object.
7. Query the PostgreSQL database container via one of the options below:
 - **Shell:** Run the `fetch_results.sh` shell script to return the feature table from the PostgreSQL database container: `./run_app.sh`
 - **Manually:** Use the terminal to run the below command:
 ```docker exec -it "eikon-db" psql -U "labuser" -d "eikon_db" -c "SELECT * from eikon_db.sandbox.features";```


## API Endpoints

You can also access the app by going to http://127.0.0.1:5000/ in the web browser

### Index
**Endpoint** `/`

HTML response that provides links to available API endpoints: `/trigger-etl` and `/etl-results`

### Trigger ETL

**Endpoint** `/trigger-etl`

**Method** GET

Triggers the ETL process by calling the `etl()` function. Returns HTML response with the status of the ETL process.

```
ETL Process Successful
Status Code: 200

Message: ETL process completed for 20 rows
```

### ETL Results

**Endpoint** `/etl-results`

**Method** GET

Retrieves the results of the ETL process. Returns JSON response containing the ETL results, e.g. features table from PostgreSQL container.

```
[{"user_id":1,"name":"Alice","email":"alice@example.com","signup_date":1672531200000,"experiment_count":2,"avg_experiment_run_time":12.5,"compound_id":1,"compound_name":"Compound A","compound_structure":"C20H25N3O"},. . . ]
```

### Database Structure for PostgreSQL Container

**database** `eikon_db`

**schema** `sandbox`

**table** `features`

-  `user_id (bigint)`: ID specifying user, e.g. *1-10*
-  `name (text)`: name of the user, e.g. *Alice*
-  `email (text)`: user's email address, e.g. *alice@example.com*
-  `signup_date (timestamp without time zone)`: user's signup date, e.g. *2023-01-01*
-  **`experiment_count (bigint)`**: Total experiments a user ran
-  **`avg_experiment_run_time (double precision)`**: Average experiments amount per user, assumed to be average run time per user
-  `compound_id (bigint)`: User's most commonly experimented compound by compound ID, e.g. *1-3*
-  `compound_name (text)`: User's most commonly experimented compound by compound name, e.g. *A-C*
-  **`compound_structure (text)`**: User's most commonly experimented compound by compound structure, e.g. *C20H25N3O*

**Note:** For the provided datasets, only Alice ran a compound that had multiple occurrences, whereas everyone else only ran a given compound once. To derive the features, it was assumed that all compounds with only one occurrence per user would be returned -- therefore, the features table in PostgreSQL container has 20 rows.

## Potential Improvements

- Store sensitive database information more securely, e.g. host, username, password, etc.
- Gather information from stakeholders on typical raw data files, such as potential areas of standardization and current issues.
  - Ask if there's units associated with the numeric measurement columns.
  - Incorporate timezone (e.g. UTC) into PostgreSQL table columns with timestamp data type
- Assumed how the database, schema, and table are implemented -- see `Database Structure` section. Design PostgreSQL table based on stakeholder use cases.
- Application is only validated with the provided input files in the `data` folder. Include testing with more input files to expose edge cases to improve error handling and logging for easier troubleshooting. Set up text fixtures and unit testing.
- Potentially add other API requests such as `PUT`,`PATCH`,`DELETE` to add more flexibility to the ETL process and if the scope of the API is expanded.
- This API is user-triggered which might be preferred, but assess whether the ETL process should be triggered automatically, such as by using airflow to manage and schedule ETL workflows.
