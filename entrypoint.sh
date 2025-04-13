#!/bin/bash
set -e

# Load environment variables from .env file if it exists
# This is useful for local development
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Dynamically extract database connection details from environment variables
# airflow_db
AF_USER=$(echo "$AIRFLOW__DATABASE__SQL_ALCHEMY_CONN" | sed -E 's|postgresql\+psycopg2://([^:]+):.*|\1|')
AF_PASS=$(echo "$AIRFLOW__DATABASE__SQL_ALCHEMY_CONN" | sed -E 's|postgresql\+psycopg2://[^:]+:([^@]+)@.*|\1|')
AF_HOST=$(echo "$AIRFLOW__DATABASE__SQL_ALCHEMY_CONN" | sed -E 's|.*@([^:/]+):([0-9]+)/.*|\1|')
AF_PORT=$(echo "$AIRFLOW__DATABASE__SQL_ALCHEMY_CONN" | sed -E 's|.*@[^:/]+:([0-9]+)/.*|\1|')
AF_DB=$(echo "$AIRFLOW__DATABASE__SQL_ALCHEMY_CONN" | sed -E 's|.*/([^?]+).*|\1|')

# transaction_db
TX_USER=$(echo "$DATABASE_URL" | sed -E 's|postgresql\+psycopg2://([^:]+):.*|\1|')
TX_PASS=$(echo "$DATABASE_URL" | sed -E 's|postgresql\+psycopg2://[^:]+:([^@]+)@.*|\1|')
TX_DB=$(echo "$DATABASE_URL" | sed -E 's|.*/([^?]+).*|\1|')

# Generate pgbouncer.ini
cat <<EOF > /etc/pgbouncer/pgbouncer.ini
[databases]
airflow_db = host=${AF_HOST} port=${AF_PORT} dbname=${AF_DB} user=${AF_USER} password=${AF_PASS}
transaction_db = host=${AF_HOST} port=${AF_PORT} dbname=${TX_DB} user=${TX_USER} password=${TX_PASS}

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = trust
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
server_tls_sslmode = require
ignore_startup_parameters = extra_float_digits
log_connections = 0
log_disconnections = 0
default_pool_size = 5
EOF

# Generate userlist.txt
cat <<EOF > /etc/pgbouncer/userlist.txt
"${AF_USER}" "${AF_PASS}"
"${TX_USER}" "${TX_PASS}"
EOF

# Launch PgBouncer
pgbouncer /etc/pgbouncer/pgbouncer.ini &

# Dynamically modify the URL to PgBouncer
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://${AF_USER}:${AF_PASS}@127.0.0.1:6432/airflow_db

# Init DB if needed
airflow db init

# Create a superuser if it doesn't exist
airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin || true

# Launch the scheduler
airflow scheduler &

# Launch the webserver
exec airflow webserver --port 8088
