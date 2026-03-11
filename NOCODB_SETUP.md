# NocoDB Setup on Linode Server

**Date:** 2026-03-11
**Server:** 172.232.163.60 (Linode, Debian 12 Bookworm)
**Purpose:** Give the FMCN team a web-based spreadsheet UI to explore and download data from the fondogis PostgreSQL database.

## What was installed

### 1. Docker (v29.3.0 + Compose v5.1.0)
- Installed via official script: `curl -fsSL https://get.docker.com | sudo sh`
- Was not previously on the server

### 2. NocoDB (latest, via Docker)
- Container name: `nocodb`
- Config file: `/opt/nocodb/docker-compose.yml`
- Persistent volume: `nocodb_nocodb_data` (stores NocoDB internal metadata)
- Exposed on: `0.0.0.0:8082` → container port `8080`

### 3. iptables-persistent
- Installed to persist firewall rules across reboots

## Access

- **URL:** http://172.232.163.60:8082/dashboard/
- **Login:** `admin@fondogis.org` / `fondogis2026`
- **No SSL** — served on HTTP port 8082 directly (not proxied through nginx)

## Configuration files

### /opt/nocodb/docker-compose.yml
```yaml
services:
  nocodb:
    image: nocodb/nocodb:latest
    container_name: nocodb
    ports:
      - "0.0.0.0:8082:8080"
    environment:
      NC_DB: "pg://172.17.0.1:5432?u=postgres&p=hdb2c3279R7iAWeYPTIk1bwHsB4TAbua&d=fondogis"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: always
    volumes:
      - nocodb_data:/usr/app/data
volumes:
  nocodb_data:
```

NocoDB connects to PostgreSQL via the Docker bridge gateway IP (`172.17.0.1`), not localhost.

## Changes made to existing server config

### PostgreSQL (v13)

#### /etc/postgresql/13/main/conf.d/listen.conf
Changed from:
```
listen_addresses = 'localhost'
```
To:
```
listen_addresses = '*'
```
This was needed so PostgreSQL accepts connections from the Docker bridge network. The firewall still blocks port 5432 from the internet — only local and Docker traffic can reach it.

#### /etc/postgresql/13/main/pg_hba.conf
Added one line at the end:
```
host    all             all             172.16.0.0/12           scram-sha-256
```
This allows Docker containers (which use 172.17.x.x or 172.18.x.x addresses) to authenticate to PostgreSQL.

PostgreSQL was restarted after these changes: `sudo systemctl restart postgresql@13-main`

### iptables (firewall)

Two rules were added:
```
iptables -I INPUT -s 172.16.0.0/12 -p tcp --dport 5432 -j ACCEPT   # Docker → PostgreSQL
iptables -I INPUT -p tcp --dport 8082 -j ACCEPT                      # Public → NocoDB
```
Rules were persisted with `netfilter-persistent save`.

### nginx
**No changes.** The `anps.newconsensus.ai` nginx config was left as-is. NocoDB runs on its own port (8082) independently of nginx.

We attempted to proxy NocoDB at `anps.newconsensus.ai/db/` but NocoDB's SPA uses relative asset paths that break under a subpath proxy. A subdomain (e.g., `db.newconsensus.ai`) would be the clean solution if HTTPS is needed later.

## SSH access

Graciela's machine was given SSH access as user `zack`:
```
ssh zack@172.232.163.60
```
Public key added to `/home/zack/.ssh/authorized_keys`:
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINfHiyiVmXmvnruZKCkselgEfQOr/csNpwHFqqZUJLcl graciela-macbook
```

## Common operations

```bash
# Check NocoDB status
sudo docker ps --filter name=nocodb

# View NocoDB logs
sudo docker logs nocodb --tail 50

# Restart NocoDB
sudo docker restart nocodb

# Stop NocoDB
sudo docker compose -f /opt/nocodb/docker-compose.yml down

# Start NocoDB
cd /opt/nocodb && sudo docker compose up -d

# Update NocoDB to latest version
cd /opt/nocodb && sudo docker compose pull && sudo docker compose up -d
```

## Future improvements

- **Add SSL:** Set up a subdomain (e.g., `db.newconsensus.ai`) with Certbot + nginx reverse proxy so NocoDB is served over HTTPS
- **Read-only access:** Create a read-only PostgreSQL user for NocoDB so the team can't accidentally modify data
- **Backup:** The NocoDB metadata volume (`nocodb_nocodb_data`) should be backed up if views/shared links are configured
