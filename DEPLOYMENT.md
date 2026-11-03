# Ubuntu VPS Production Deployment Guide

This guide details the deployment of the Compliance Risk Analytics System (CRAS) on an Ubuntu 22.04 / 24.04 LTS VPS using Docker, Gunicorn, PostgreSQL 16, and Nginx reverse proxy with SSL termination.

---

## 1. Prerequisites on Ubuntu VPS

Ensure Docker and Docker Compose v2 are installed on the VPS:

```bash
sudo apt update && sudo apt upgrade -y && \
sudo apt install -y curl git ufw fail2ban && \
curl -fsSL https://get.docker.com -o get-docker.sh && \
sudo sh get-docker.sh && \
sudo usermod -aG docker $USER && \
sudo systemctl enable docker && sudo systemctl start docker
```

Configure the UFW firewall:

```bash
sudo ufw allow OpenSSH && \
sudo ufw allow 80/tcp && \
sudo ufw allow 443/tcp && \
sudo ufw --force enable
```

---

## 2. Production Deployment Command Sequence

Run this complete copy-paste ready deployment sequence on your VPS:

```bash
git clone https://github.com/your-org/CRAS.git /opt/cras && \
cd /opt/cras && \
cp .env.example .env && \
sed -i "s/change-this-to-a-very-secure-random-secret-key-in-production/$(openssl rand -hex 32)/g" .env && \
sed -i "s/cras_password/$(openssl rand -hex 16)/g" .env && \
docker compose build --no-cache && \
docker compose up -d && \
docker compose ps
```

---

## 3. Verification & Health Check Commands

Verify that all three production containers (`cras_web`, `cras_postgres`, `cras_nginx`) are running and healthy:

```bash
docker compose ps && \
curl -i http://localhost/health && \
docker compose logs --tail=50 web
```

Expected health check response:
```json
HTTP/1.1 200 OK
Content-Type: application/json

{"database":"connected","service":"CRAS","status":"healthy"}
```

---

## 4. Initial Super Administrator Setup

Upon initial container launch, the system automatically runs schema migrations, seeds Kenyan statutory regulatory requirements, and creates the default Super Administrator account defined in your `.env`:

- **Email:** `admin@cras.ke` (or custom `INITIAL_ADMIN_EMAIL`)
- **Password:** `Admin@CRAS2026!` (or custom `INITIAL_ADMIN_PASSWORD`)

> **Security Action:** Immediately log in at `http://your-server-ip/auth/login`, navigate to **Account Profile > Change Password**, and update the administrator credentials.

To create an additional Super Administrator via CLI:

```bash
docker compose exec web flask create-admin
```

To seed the 4 synthetic demonstration SME profiles:

```bash
docker compose exec web flask seed-samples
```

---

## 5. Automated Daily Database Backups

Add an automated compressed daily database backup to the server's crontab:

```bash
sudo chmod +x /opt/cras/scripts/backup.sh && \
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/cras/scripts/backup.sh >> /var/log/cras_backup.log 2>&1") | crontab -
```

To test backup creation immediately:

```bash
/opt/cras/scripts/backup.sh
```

---

## 6. Zero-Downtime Application Update Sequence

When updating to a newer release:

```bash
cd /opt/cras && \
git pull origin main && \
docker compose build --no-cache web && \
docker compose up -d --no-deps web && \
docker image prune -f && \
curl -i http://localhost/health
```

---

## 7. Rollback Procedure

If a failure occurs during an update:

```bash
cd /opt/cras && \
git reset --hard HEAD~1 && \
docker compose up -d --build && \
./scripts/restore.sh backups/latest_backup.sql.gz
```
