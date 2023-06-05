# Shell script to make API requests

# See available API endpoints
curl http://127.0.0.1:5000/

# Send a GET request to trigger ETL
echo "Triggering ETL"
curl -X GET http://127.0.0.1:5000/trigger-etl

# Retrieve ETL results in tabular format
echo "Retrieving ETL results"
curl -s http://127.0.0.1:5000/etl-results | python -c 'import sys, json, tabulate; data = json.load(sys.stdin); headers = data[0].keys(); rows = [list(item.values()) for item in data]; print(tabulate.tabulate(rows, headers, tablefmt="grid"))'
