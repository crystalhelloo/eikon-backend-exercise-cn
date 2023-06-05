#Shell script to fetch results from features table in PostgreSQL container

# Initialize PostgreSQL connection details
container_name="eikon-db"
database="eikon_db"
username="labuser"

# Define query to pull results from features table
query="SELECT * FROM sandbox.features;"

# Use psql to execute query inside Docker container
docker exec -it "$container_name" psql -U "$username" -d "$database" -c "$query"
