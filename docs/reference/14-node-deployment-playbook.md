# ENKI Node Deployment Playbook

**Version:** 1.0.0  
**Status:** DRAFT (Pre-Hardware)  
**Date:** 2026-01-02  
**Purpose:** Deterministic deployment checklist for ENKI Node installation

---

## Purpose

This playbook provides a **deterministic, repeatable process** for deploying ENKI Nodes on physical hardware. It is designed to be executed on any compatible machine, ensuring identical configuration across all Node deployments.

**Target Use Cases:**
- Initial Node setup (personal / development)
- Production Node deployment (single-tenant)
- Multi-Node rollout (future: multiple tenants / distributed federation)
- Golden image creation for resale / mass deployment

**Authority:**
- This playbook governs operational deployment, NOT governance or phase architecture
- Deployment must comply with Phase 0-3 locked contracts
- Hardware-specific choices (OS, partitions, services) are documented here for consistency

---

## Hardware Requirements

### Minimum Specifications

**Compute:**
- CPU: x86_64 or ARM64 (4+ cores recommended)
- RAM: 8GB minimum (16GB recommended for production)
- Storage: 128GB SSD minimum (NVMe preferred)

**Network:**
- Ethernet: 1Gbps (required for production)
- WiFi: Optional (fallback only)

**Power:**
- UPS: Recommended for production deployments
- Idle power: <15W typical

### Validated Hardware Profiles

**Development Profile (Current Target):**
- Platform: TBD (awaiting hardware arrival)
- OS: Ubuntu 24.04 LTS Server or Debian 12 (decision pending)
- Container Runtime: Docker Engine (for PostgreSQL 16)

**Production Profile (Future):**
- Platform: TBD (rack-mount or mini-PC form factor)
- OS: TBD (same as dev for consistency)
- Database: PostgreSQL 16 (system service, not Docker)
- Backup Strategy: Daily snapshots to external volume

---

## Pre-Installation Checklist

### Required Before Starting

- [ ] Hardware physically accessible (or SSH access configured)
- [ ] OS installation media prepared (USB or network boot)
- [ ] Network configuration details (static IP or DHCP)
- [ ] DNS hostname chosen (e.g., `enki-node-001.local`)
- [ ] Tenant ID defined (format TBD; see Phase 4 spec)
- [ ] Backup destination configured (if production)

### Required Credentials / Secrets

**Do NOT commit secrets to git. Use environment variables or encrypted vault.**

- [ ] OS root password or SSH key
- [ ] PostgreSQL `enki` user password
- [ ] ENKI root keypair (Phase 3.6; generation procedure TBD)
- [ ] TLS certificates (Phase 4; Let's Encrypt or manual)

---

## Installation Steps

### Step 1: OS Installation

**Option A: Bare Metal Install (Recommended for Production)**

1. Boot from installation media (USB or PXE)
2. Select minimal server install (no GUI)
3. Configure partitions:
   - `/boot`: 1GB (ext4)
   - `/`: 32GB (ext4)
   - `/var/lib/postgresql`: Remaining space (ext4 or XFS)
   - Swap: 2GB (or equal to RAM if <8GB)
4. Set hostname: `enki-node-<ID>`
5. Create admin user: `enki-admin` (sudo privileges)
6. Enable SSH server
7. Apply system updates: `sudo apt update && sudo apt upgrade -y`

**Option B: Pre-Built Image (Future Golden Image)**

1. Flash golden image to storage device (procedure TBD)
2. Boot and run first-boot configuration script
3. Set hostname, network config, tenant ID via env file

### Step 2: System Hardening

**Firewall Configuration:**
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 5432/tcp    # PostgreSQL (if remote access required)
sudo ufw allow 8000/tcp    # API server (Phase 4)
sudo ufw enable
```

**SSH Hardening:**
```bash
# Edit /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no  # Require SSH keys
PubkeyAuthentication yes
sudo systemctl restart sshd
```

**Automatic Updates:**
```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Step 3: Install Docker (Development Mode)

**For development / testing deployments using Docker Compose:**

```bash
# Install Docker Engine
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add enki-admin to docker group
sudo usermod -aG docker enki-admin
newgrp docker

# Verify installation
docker --version
docker compose version
```

### Step 4: Install PostgreSQL (Production Mode)

**For production deployments using system PostgreSQL:**

```bash
# Install PostgreSQL 16
sudo apt install -y postgresql-16 postgresql-contrib

# Configure PostgreSQL
sudo -u postgres psql
CREATE DATABASE enki;
CREATE USER enki WITH ENCRYPTED PASSWORD '<SECURE_PASSWORD>';
GRANT ALL PRIVILEGES ON DATABASE enki TO enki;
\q

# Configure authentication
# Edit /etc/postgresql/16/main/pg_hba.conf
# Add line: host enki enki 127.0.0.1/32 scram-sha-256

# Restart PostgreSQL
sudo systemctl restart postgresql
sudo systemctl enable postgresql
```

### Step 5: Deploy ENKI Node Software

**Clone Repository:**
```bash
cd /opt
sudo git clone https://github.com/BradBuilds/Enki-Node.git enki-node
cd enki-node
sudo chown -R enki-admin:enki-admin /opt/enki-node
git checkout v1.3.0-phase3-locked  # Or latest release tag
```

**Configure Environment:**
```bash
# Create .env file (DO NOT commit this file)
cat > .env << EOF
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=enki
POSTGRES_USER=enki
POSTGRES_PASSWORD=<SECURE_PASSWORD>

# Tenant Configuration
TENANT_ID=<YOUR_TENANT_ID>

# Phase 4 API Configuration (future)
# API_PORT=8000
# API_HOST=0.0.0.0
# TLS_CERT_PATH=/etc/enki/tls/cert.pem
# TLS_KEY_PATH=/etc/enki/tls/key.pem

# Phase 3.6 Device Auth Configuration (future)
# ENKI_ROOT_KEY_PATH=/etc/enki/keys/root.key
# DEVICE_AUTH_ENABLED=true
EOF
```

**Install Python Dependencies:**
```bash
# Install Python 3.13 (if not already installed)
sudo apt install -y python3.13 python3.13-venv python3-pip

# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r services/api/requirements.txt
```

### Step 6: Initialize Database Schema

**Development Mode (Docker Compose):**
```bash
# Start PostgreSQL container
docker compose up -d postgres

# Wait for PostgreSQL to be ready
sleep 5

# Apply schema
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=enki
export POSTGRES_USER=enki
export POSTGRES_PASSWORD=enki_dev_password

psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f storage/postgres/schema.sql
```

**Production Mode (System PostgreSQL):**
```bash
# Load environment variables
source .env

# Apply schema
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f storage/postgres/schema.sql
```

### Step 7: Verify Installation

**Run Phase 3 Tests:**
```bash
source .venv/bin/activate
pytest services/api/tests/test_phase3_milestone*.py -v

# Expected output: 16/16 tests passing
```

**Verify Chain Initialization:**
```bash
source .venv/bin/activate
python -c "
from storage.postgres.db import get_db_connection
from storage.postgres.queries import verify_chain

conn = get_db_connection()
result = verify_chain(conn, tenant_id='$TENANT_ID')
print('Chain verification:', result)
conn.close()
"

# Expected output: Chain verification: True (or empty chain if no events yet)
```

**Verify Database Connectivity:**
```bash
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT version();"
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT COUNT(*) FROM audit_events;"
```

---

## Operational Procedures

### Starting ENKI Node Services

**Development Mode:**
```bash
cd /opt/enki-node
docker compose up -d
source .venv/bin/activate
# Phase 4: Start API server (when implemented)
# uvicorn services.api.main:app --host 0.0.0.0 --port 8000
```

**Production Mode (Systemd Services):**
```bash
# Create systemd service file (Phase 4)
sudo nano /etc/systemd/system/enki-node.service

# [Unit]
# Description=ENKI Node API Server
# After=network.target postgresql.service
#
# [Service]
# Type=simple
# User=enki-admin
# WorkingDirectory=/opt/enki-node
# EnvironmentFile=/opt/enki-node/.env
# ExecStart=/opt/enki-node/.venv/bin/uvicorn services.api.main:app --host 0.0.0.0 --port 8000
# Restart=on-failure
# RestartSec=5s
#
# [Install]
# WantedBy=multi-user.target

# Enable and start service
# sudo systemctl daemon-reload
# sudo systemctl enable enki-node
# sudo systemctl start enki-node
# sudo systemctl status enki-node
```

### Stopping ENKI Node Services

**Development Mode:**
```bash
docker compose down
```

**Production Mode:**
```bash
sudo systemctl stop enki-node
```

### Backup Procedures

**Database Backup (Daily Recommended):**
```bash
# Create backup directory
sudo mkdir -p /var/backups/enki

# Backup script (add to cron)
#!/bin/bash
BACKUP_DIR="/var/backups/enki"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U enki enki | gzip > $BACKUP_DIR/enki_backup_$TIMESTAMP.sql.gz

# Retain last 7 days
find $BACKUP_DIR -name "enki_backup_*.sql.gz" -mtime +7 -delete
```

**Add to crontab:**
```bash
sudo crontab -e
# Add line: 0 2 * * * /usr/local/bin/enki-backup.sh
```

### Restore Procedures

**From Backup:**
```bash
# Stop services
docker compose down  # or sudo systemctl stop enki-node

# Drop and recreate database
psql -h localhost -U enki -d postgres -c "DROP DATABASE enki;"
psql -h localhost -U enki -d postgres -c "CREATE DATABASE enki;"

# Restore backup
gunzip -c /var/backups/enki/enki_backup_YYYYMMDD_HHMMSS.sql.gz | psql -h localhost -U enki -d enki

# Restart services
docker compose up -d  # or sudo systemctl start enki-node
```

### Update Procedures

**Pulling Latest Code:**
```bash
cd /opt/enki-node
git fetch --all --tags
git checkout <NEW_VERSION_TAG>  # e.g., v1.4.0-phase4-locked

# Rebuild virtual environment if requirements changed
source .venv/bin/activate
pip install --upgrade -r requirements.txt -r services/api/requirements.txt

# Apply schema migrations (if any)
# psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f storage/postgres/migrations/<MIGRATION_FILE>.sql

# Restart services
docker compose restart  # or sudo systemctl restart enki-node
```

### Factory Reset Procedure

**Complete Node Reset (DESTRUCTIVE):**
```bash
# Stop all services
docker compose down  # or sudo systemctl stop enki-node

# Delete database
psql -h localhost -U enki -d postgres -c "DROP DATABASE enki;"
psql -h localhost -U enki -d postgres -c "CREATE DATABASE enki;"

# Reinitialize schema
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f storage/postgres/schema.sql

# Restart services
docker compose up -d  # or sudo systemctl start enki-node
```

---

## Proof of Correctness

### Post-Installation Validation

**Run all tests:**
```bash
source .venv/bin/activate
pytest services/api/tests/ -v
# Expected: 16/16 Phase 3 tests passing
```

**Verify chain integrity:**
```bash
python -c "
from storage.postgres.db import get_db_connection
from storage.postgres.queries import verify_chain
conn = get_db_connection()
result = verify_chain(conn, tenant_id='$TENANT_ID')
print('Chain valid:', result)
conn.close()
"
```

**Check service status:**
```bash
docker compose ps  # Development mode
# or
sudo systemctl status enki-node postgresql  # Production mode
```

**Test ingestion pipeline (Phase 3):**
```bash
# Create test event file
echo '{"event_type": "system.test", "severity": "info", "timestamp": "2026-01-02T12:00:00Z", "tenant_id": "test-tenant", "actor_id": "system:test", "payload": {"message": "deployment test"}}' > /tmp/test_event.jsonl

# Ingest via Phase 3 pipeline
python -c "
from storage.ingest.ingestion import ingest_jsonl
with open('/tmp/test_event.jsonl', 'r') as f:
    receipt = ingest_jsonl(f.read(), tenant_id='test-tenant')
    print('Receipt:', receipt)
"
```

---

## Phase-Specific Operational Hooks

### Phase 3.6: Device Authentication (When Implemented)

**ENKI Root Key Generation:**
```bash
# Generate ENKI root keypair (Ed25519)
# python -m core.tools.generate_root_key --output /etc/enki/keys/root.key

# Secure key file
# sudo chown enki-admin:enki-admin /etc/enki/keys/root.key
# sudo chmod 600 /etc/enki/keys/root.key
```

**Device Enrollment (Operational Placeholder):**
```bash
# Enroll device via CLI (future)
# python -m core.tools.enroll_device \
#   --device-id "esp32-watch-001" \
#   --public-key "base64_encoded_key" \
#   --tier "W" \
#   --output /etc/enki/grants/esp32-watch-001.json
```

**Key Storage Locations:**
- ENKI root key: `/etc/enki/keys/root.key` (Ed25519 private key, encrypted)
- Device grants: `/etc/enki/grants/*.json` (ENKI-signed enrollment certificates)
- Physical key attestations: `/etc/enki/keys/physical/*.json` (FIDO2/WebAuthn credentials)

**Challenge Cache (Ephemeral):**
- Development: In-memory dictionary (Python runtime)
- Production: Filesystem cache at `/var/cache/enki/challenges/` or Redis (Phase 5+)

### Phase 4: API Layer (When Implemented)

**API Server Configuration:**
- Port: `8000` (default; configurable via `API_PORT`)
- Host: `0.0.0.0` (all interfaces; restrict in production)
- TLS: Required for production (Let's Encrypt or manual cert)
- Reverse Proxy: Nginx or Caddy recommended

**TLS Certificate Paths:**
- Certificate: `/etc/enki/tls/cert.pem`
- Private Key: `/etc/enki/tls/key.pem`
- CA Chain: `/etc/enki/tls/chain.pem` (if using manual cert)

**Reverse Proxy Setup (Nginx Example):**
```nginx
# /etc/nginx/sites-available/enki-node
server {
    listen 443 ssl http2;
    server_name enki-node-001.local;

    ssl_certificate /etc/enki/tls/cert.pem;
    ssl_certificate_key /etc/enki/tls/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**API Endpoints (Future):**
- `POST /ingest` → Submit JSONL events
- `GET /receipts/{rid}` → Retrieve receipt
- `GET /audit` → Query audit events (pagination)
- `GET /verify` → Verify chain integrity

### Phase 5: Federation (When Implemented)

**Node Identity:**
- Node ID: UUIDv4 or public key hash (TBD)
- Node public key: `/etc/enki/keys/node.pub` (Ed25519)
- Federation config: `/etc/enki/federation.yaml`

**Trust Relationships:**
- Trusted nodes list: `/etc/enki/federation/trusted_nodes.json`
- Trust verification: Mutual TLS or signed assertions (TBD)

---

## Golden Image Creation (Future: Mass Deployment)

### Image Preparation

**Goal:** Create a reusable disk image for rapid Node deployment.

**Steps:**
1. Complete fresh OS install following Step 1
2. Apply Steps 2-5 (system hardening, Docker/PostgreSQL, ENKI software)
3. **DO NOT configure tenant-specific secrets** (set during first boot)
4. Sysprep equivalent:
   ```bash
   # Remove unique identifiers
   sudo rm /etc/machine-id
   sudo rm /var/lib/dbus/machine-id
   sudo rm ~/.ssh/authorized_keys
   sudo rm /root/.ssh/authorized_keys
   
   # Clear logs
   sudo journalctl --rotate
   sudo journalctl --vacuum-time=1s
   
   # Clear bash history
   history -c
   ```
5. Create disk image:
   ```bash
   sudo dd if=/dev/sdX of=/path/to/enki-node-golden-v1.0.0.img bs=4M status=progress
   gzip /path/to/enki-node-golden-v1.0.0.img
   ```

### Image Deployment

**Flash to New Hardware:**
```bash
gunzip -c enki-node-golden-v1.0.0.img.gz | sudo dd of=/dev/sdX bs=4M status=progress
```

**First-Boot Configuration Script:**
```bash
#!/bin/bash
# /usr/local/bin/enki-first-boot.sh

# Prompt for configuration
read -p "Enter Node Hostname: " HOSTNAME
read -p "Enter Tenant ID: " TENANT_ID
read -s -p "Enter PostgreSQL Password: " POSTGRES_PASSWORD
echo

# Apply configuration
sudo hostnamectl set-hostname $HOSTNAME
echo "TENANT_ID=$TENANT_ID" | sudo tee -a /opt/enki-node/.env
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD" | sudo tee -a /opt/enki-node/.env

# Regenerate unique identifiers
sudo systemd-machine-id-setup
sudo reboot
```

---

## Troubleshooting

### Common Issues

**PostgreSQL Connection Failed:**
- Check `pg_hba.conf` authentication method
- Verify password in `.env` matches database user
- Ensure PostgreSQL service is running: `sudo systemctl status postgresql`

**Docker Compose Fails to Start:**
- Check Docker daemon: `sudo systemctl status docker`
- Verify `compose.yaml` syntax: `docker compose config`
- Check logs: `docker compose logs postgres`

**Tests Failing:**
- Verify database schema applied: `psql -U enki -d enki -c "\dt"`
- Check environment variables: `echo $POSTGRES_HOST $POSTGRES_USER`
- Re-run schema initialization: `psql -U enki -d enki -f storage/postgres/schema.sql`

**Chain Verification Failing:**
- Check for manual database edits (violates append-only constraint)
- Verify genesis hash initialization
- Restore from backup if chain corrupted

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-02 | Initial playbook created (pre-hardware). Development and production procedures defined. Operational hooks for Phase 3.6 and Phase 4 added. |

---

## References

- **Phase 3 Storage Implementation:** [docs/10-storage-contract-spec.md](10-storage-contract-spec.md), docs/15-ingestion-contract.md
- **Phase 3 Validation Report:** docs/implementation-reports/2026-01-01-phase3-milestone2-db-validation.md
- **Docker Compose:** compose.yaml
- **PostgreSQL Schema:** storage/postgres/schema.sql

---

**Status:** DRAFT (Pre-Hardware Arrival)  
**Next Review:** After first physical deployment  
**Authority:** Operational playbook (does NOT govern phase architecture)
