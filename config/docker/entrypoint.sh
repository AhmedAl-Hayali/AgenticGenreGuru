#!/bin/sh
set -e

mkdir -p /certs

if [ ! -f /certs/server.crt ]; then
    openssl req -x509 -nodes \
        -newkey rsa:2048 \
        -keyout /certs/server.key \
        -out /certs/server.crt \
        -days 365 \
        -subj "/CN=localhost"
fi

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done

exec "$@"
