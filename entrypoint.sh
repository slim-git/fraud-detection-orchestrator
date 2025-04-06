#!/bin/bash
set -e

# Charger les variables d'environnement
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Init DB si besoin
airflow db init

# Créer un user admin si aucun n'existe
airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin || true

# Lancer le scheduler en background
airflow scheduler &

# Lancer le webserver (en foreground, pour que le conteneur reste "vivant")
exec airflow webserver --port 8088
