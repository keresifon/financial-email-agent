# Deployment Guide for Financial Email Agent

This guide covers deploying the Financial Email Agent to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Deployment](#local-deployment)
3. [Server Deployment](#server-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Cloud Deployment](#cloud-deployment)
6. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Prerequisites

### Required Services

1. **MongoDB Atlas** (or self-hosted MongoDB)
   - Already configured: `mongodb+srv://...`
   - Database: `financial_data`

2. **Ollama Server** with Llama model
   - Currently: `http://192.168.1.86:11434`
   - Model: `llama3.2:3b`

3. **Gmail API Credentials**
   - `credentials.json` already present
   - OAuth2 token will be generated on first run

### System Requirements

- Python 3.11+
- 2GB+ RAM
- 10GB+ disk space
- Network access to MongoDB and Ollama

---

## Local Deployment

### Option 1: Run Manually

**1. Ensure environment is set up:**
```bash
# Already done in your case
cd c:/Users/0B9947649/Desktop/financial-email-agent
venv\Scripts\activate
```

**2. Run the application:**
```bash
python src/main.py
```

**3. Check logs:**
```bash
# Logs are in logs/agent.log
type logs\agent.log
```

### Option 2: Run as Scheduled Task (Windows)

**Create a batch file `run_agent.bat`:**
```batch
@echo off
cd /d c:\Users\0B9947649\Desktop\financial-email-agent
call venv\Scripts\activate
python src/main.py
```

**Schedule with Task Scheduler:**
1. Open Task Scheduler
2. Create Basic Task
3. Name: "Financial Email Agent"
4. Trigger: Daily at desired time (e.g., every 4 hours)
5. Action: Start a program
6. Program: `c:\Users\0B9947649\Desktop\financial-email-agent\run_agent.bat`
7. Finish

---

## Server Deployment

### Linux Server Setup

**1. Transfer files to server:**
```bash
# On your local machine
scp -r financial-email-agent user@server:/opt/

# Or use git
ssh user@server
cd /opt
git clone <your-repo-url> financial-email-agent
```

**2. Set up on server:**
```bash
cd /opt/financial-email-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure .env
cp .env.example .env
nano .env  # Edit with your settings
```

**3. Create systemd service:**

Create `/etc/systemd/system/financial-email-agent.service`:
```ini
[Unit]
Description=Financial Email Agent
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/opt/financial-email-agent
Environment="PATH=/opt/financial-email-agent/venv/bin"
ExecStart=/opt/financial-email-agent/venv/bin/python /opt/financial-email-agent/src/main.py
Restart=always
RestartSec=300

[Install]
WantedBy=multi-user.target
```

**4. Enable and start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable financial-email-agent
sudo systemctl start financial-email-agent

# Check status
sudo systemctl status financial-email-agent

# View logs
sudo journalctl -u financial-email-agent -f
```

### Cron Job (Alternative)

```bash
# Edit crontab
crontab -e

# Run every 4 hours
0 */4 * * * cd /opt/financial-email-agent && venv/bin/python src/main.py >> /var/log/financial-agent.log 2>&1
```

---

## Docker Deployment

### Create Dockerfile

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create logs directory
RUN mkdir -p logs

# Run application
CMD ["python", "src/main.py"]
```

### Create docker-compose.yml

```yaml
version: '3.8'

services:
  financial-agent:
    build: .
    container_name: financial-email-agent
    environment:
      - MONGODB_CONNECTION_STRING=${MONGODB_CONNECTION_STRING}
      - OLLAMA_API_URL=${OLLAMA_API_URL}
      - LLAMA_MODEL=${LLAMA_MODEL}
    volumes:
      - ./logs:/app/logs
      - ./credentials.json:/app/credentials.json
      - ./token.json:/app/token.json
    restart: unless-stopped
    networks:
      - agent-network

networks:
  agent-network:
    driver: bridge
```

### Deploy with Docker

```bash
# Build image
docker build -t financial-email-agent .

# Run container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop container
docker-compose down
```

---

## Cloud Deployment

### AWS EC2

**1. Launch EC2 instance:**
- AMI: Ubuntu 22.04 LTS
- Instance type: t3.small (2GB RAM)
- Security group: Allow SSH (22)

**2. Connect and setup:**
```bash
ssh -i your-key.pem ubuntu@ec2-instance-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3.11 python3.11-venv python3-pip -y

# Clone repository
git clone <your-repo> /opt/financial-email-agent
cd /opt/financial-email-agent

# Setup (follow Linux Server Setup above)
```

**3. Configure security:**
```bash
# Set up firewall
sudo ufw allow 22/tcp
sudo ufw enable

# Secure credentials
chmod 600 credentials.json
chmod 600 .env
```

### Azure VM

Similar to AWS EC2, use Azure VM with Ubuntu.

### Google Cloud Run (Serverless)

**1. Create `cloudbuild.yaml`:**
```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/financial-agent', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/financial-agent']
```

**2. Deploy:**
```bash
gcloud run deploy financial-agent \
  --image gcr.io/$PROJECT_ID/financial-agent \
  --platform managed \
  --region us-central1 \
  --memory 2Gi
```

---

## Monitoring & Maintenance

### Log Monitoring

**View logs:**
```bash
# Local (Windows)
type logs\agent.log

# Linux
tail -f logs/agent.log

# Docker
docker-compose logs -f
```

**Log rotation is automatic:**
- Max size: 10 MB
- Retention: 7 days
- Compression: ZIP

### Health Checks

**Create health check script `health_check.py`:**
```python
import sys
from src.config.loader import load_config
from src.database.connection import MongoDBConnection
from src.llm.client import LLMClient

def check_health():
    try:
        # Load config
        config = load_config()
        
        # Check MongoDB
        db = MongoDBConnection(config.mongodb)
        db.connect()
        if not db.health_check():
            print("MongoDB: FAIL")
            return False
        print("MongoDB: OK")
        db.disconnect()
        
        # Check LLM
        llm = LLMClient(config=config.llama)
        if not llm.health_check():
            print("LLM: FAIL")
            return False
        print("LLM: OK")
        
        print("All systems: OK")
        return True
        
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)
```

**Run health check:**
```bash
python health_check.py
```

### Monitoring Dashboard

**Check MongoDB Atlas:**
- Go to MongoDB Atlas dashboard
- View metrics, queries, and performance

**Check application metrics:**
```bash
# Count processed emails
mongo "mongodb+srv://..." --eval "db.emails.count()"

# Recent activity
mongo "mongodb+srv://..." --eval "db.emails.find().sort({processed_at:-1}).limit(10)"
```

### Backup Strategy

**1. MongoDB backups:**
- MongoDB Atlas: Automatic backups enabled
- Self-hosted: Use `mongodump`

```bash
mongodump --uri="mongodb+srv://..." --out=/backup/$(date +%Y%m%d)
```

**2. Application backups:**
```bash
# Backup configuration and credentials
tar -czf backup-$(date +%Y%m%d).tar.gz .env credentials.json token.json config/
```

### Troubleshooting

**Common issues:**

1. **Gmail authentication fails:**
   ```bash
   # Delete token and re-authenticate
   rm token.json
   python src/main.py
   ```

2. **MongoDB connection timeout:**
   ```bash
   # Check connection string in .env
   # Verify network access in MongoDB Atlas
   ```

3. **Ollama not responding:**
   ```bash
   # Check Ollama server
   curl http://192.168.1.86:11434/api/tags
   
   # Restart Ollama service
   systemctl restart ollama
   ```

4. **Out of memory:**
   ```bash
   # Increase system memory or reduce batch size
   # Edit config/config.yaml:
   # email.monitoring.max_emails_per_check: 25
   ```

### Performance Optimization

**1. Adjust batch size:**
```yaml
# config/config.yaml
email:
  monitoring:
    max_emails_per_check: 25  # Reduce if memory constrained
```

**2. Increase check interval:**
```yaml
scheduler:
  check_interval_minutes: 30  # Check less frequently
```

**3. Use faster LLM model:**
```yaml
llama:
  model: "llama3.2:1b"  # Smaller, faster model
```

---

## Quick Start Commands

### Run Once
```bash
cd c:/Users/0B9947649/Desktop/financial-email-agent
venv\Scripts\activate
python src/main.py
```

### Run Tests
```bash
python run_tests.py
```

### Check Health
```bash
python health_check.py
```

### View Logs
```bash
type logs\agent.log
```

---

## Support

For issues or questions:
1. Check logs in `logs/agent.log`
2. Run health check: `python health_check.py`
3. Review `TESTING.md` for debugging
4. Check MongoDB Atlas dashboard
5. Verify Ollama server status

---

**Your application is ready to deploy!** Choose the deployment method that best fits your needs.