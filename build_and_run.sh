# Shell script to initialize Docker containers

# Stop and remove running Docker containers to prevent conflicts on port 5000
echo "Stopping and removing existing containers"
docker-compose down

# Build & run the PostgreSQL (eikon-db) and Flask/Gunicorn (eikon-app) Docker containers
echo "Building and starting containers"
docker-compose up -d --build

echo "Docker containers running, proceed to run_app script for API requests"
