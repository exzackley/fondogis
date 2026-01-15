#!/bin/bash
# FondoGIS Database Setup Script
# Run this on your Linode server (172.232.163.60)
#
# Usage:
#   1. SSH to server: sshl
#   2. Copy this file: scp db/setup_database.sh zack@172.232.163.60:~/
#   3. Run: bash setup_database.sh

set -e

echo "=== FondoGIS Database Setup ==="

# Check if running on the right server
if [[ "$(hostname)" != *"linode"* ]] && [[ "$(hostname -I)" != *"172.232.163.60"* ]]; then
    echo "Warning: This script is meant to run on the Linode server"
    read -p "Continue anyway? [y/N] " confirm
    [[ "$confirm" != "y" ]] && exit 1
fi

# Create database
echo "Creating fondogis database..."
sudo -u postgres psql -c "CREATE DATABASE fondogis;" 2>/dev/null || echo "Database may already exist"

# Create user if needed (adjust password as needed)
echo "Creating/updating fondogis user..."
read -sp "Enter password for fondogis PostgreSQL user: " DB_PASSWORD
echo
sudo -u postgres psql -c "CREATE USER fondogis WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || \
sudo -u postgres psql -c "ALTER USER fondogis WITH PASSWORD '$DB_PASSWORD';"

# Grant privileges
echo "Granting privileges..."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE fondogis TO fondogis;"
sudo -u postgres psql -d fondogis -c "GRANT ALL ON SCHEMA public TO fondogis;"

# Enable PostGIS
echo "Enabling PostGIS extension..."
sudo -u postgres psql -d fondogis -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Configure pg_hba.conf for remote access (if needed)
PG_HBA="/etc/postgresql/15/main/pg_hba.conf"
if ! grep -q "fondogis" "$PG_HBA" 2>/dev/null; then
    echo "Adding remote access rule to pg_hba.conf..."
    echo "host    fondogis    fondogis    0.0.0.0/0    scram-sha-256" | sudo tee -a "$PG_HBA"
    echo "Reloading PostgreSQL..."
    sudo systemctl reload postgresql
fi

echo ""
echo "=== Setup Complete ==="
echo "Database: fondogis"
echo "User: fondogis"
echo "Host: 172.232.163.60"
echo "Port: 5432"
echo ""
echo "Test connection with:"
echo "  psql -h 172.232.163.60 -U fondogis -d fondogis"
echo ""
echo "Add to your local ~/.zshrc:"
echo "  export FONDOGIS_DB_USER=fondogis"
echo "  export FONDOGIS_DB_PASSWORD='your_password'"
