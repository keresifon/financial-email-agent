# Setup Instructions - Financial Email Agent

Complete guide to set up and run the Financial Email Agent with MCP architecture.

## Quick Start Guide

### For Windows Users:
```bash
setup.bat
```

### For Linux/Mac Users:
```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:
1. ✅ Check Python version (3.8+ required)
2. ✅ Create virtual environment
3. ✅ Install all dependencies
4. ✅ Create necessary directories
5. ✅ Set up configuration files

---

## What the Setup Script Does

### 1. Virtual Environment
Creates an isolated Python environment in the `venv/` directory to avoid conflicts with system packages.

### 2. Dependencies Installation
Installs all required packages from `requirements.txt`:
- **MCP SDK** - Model Context Protocol for modular architecture
- **Pydantic** - Data validation and settings management
- **Google APIs** - Gmail integration
- **PyMongo/Motor** - MongoDB database drivers
- **Loguru** - Advanced logging
- **httpx** - HTTP client for Ollama
- **Document processing** - PyPDF2, python-docx, openpyxl, pytesseract
- **APScheduler** - Task scheduling

### 3. Directory Structure
Creates:
```
logs/                    # Application logs
credentials/             # OAuth credentials (gitignored)
data/
  ├── attachments/      # Downloaded email attachments
  └── processed/        # Processed documents
```

### 4. Configuration Files
Copies templates:
- `.env` from `.env.example` - Environment variables
- `config/config.yaml` from `config/config.example.yaml` - Application settings

---

## After Running Setup Script

### Step 1: Configure Gmail API

1. **Create Google Cloud Project:**
   - Visit: https://console.cloud.google.com/
   - Click "Create Project" → Name it "Financial Email Agent"

2. **Enable Gmail API:**
   - Navigate to: APIs & Services → Library
   - Search "Gmail API" → Click Enable

3. **Create OAuth Credentials:**
   - Go to: APIs & Services → Credentials
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: "Desktop app"
   - Download JSON file
   - **Rename to `credentials.json`**
   - **Place in project root**

4. **Configure OAuth Consent:**
   - Go to: APIs & Services → OAuth consent screen
   - User Type: "External" (for testing)
   - Add your email as test user
   - Scopes needed:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.modify`

### Step 2: Set Up MongoDB

**Option A: Local MongoDB**
```bash
# Install MongoDB Community Edition
# Visit: https://www.mongodb.com/try/download/community

# Start MongoDB
mongod --dbpath C:\data\db  # Windows
mongod --dbpath /usr/local/var/mongodb  # Mac
```

**Option B: MongoDB Atlas (Cloud - Recommended)**
1. Create free account: https://www.mongodb.com/cloud/atlas
2. Create cluster (free tier available)
3. Create database user
4. Whitelist your IP (0.0.0.0/0 for testing)
5. Get connection string
6. Update in `.env`:
   ```
   MONGODB_CONNECTION_STRING=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/
   ```

### Step 3: Install Ollama

1. **Download Ollama:**
   - Visit: https://ollama.ai/
   - Download for your OS

2. **Install and Start:**
   ```bash
   # After installation, pull the model
   ollama pull llama3.1:8b
   
   # Start Ollama server (runs on http://localhost:11434)
   ollama serve
   ```

3. **Verify:**
   ```bash
   ollama list  # Should show llama3.1:8b
   ```

### Step 4: Update Configuration

1. **Edit `.env` file:**
   ```env
   # Gmail API
   GMAIL_CREDENTIALS_FILE=credentials.json
   GMAIL_TOKEN_FILE=token.json

   # MongoDB (update with your connection string)
   MONGODB_CONNECTION_STRING=mongodb://localhost:27017
   MONGODB_DATABASE=financial_data

   # Ollama
   OLLAMA_API_URL=http://localhost:11434
   LLAMA_MODEL=llama3.1:8b

   # Email Settings
   EMAIL_CHECK_INTERVAL_MINUTES=15
   EMAIL_MAX_PER_CHECK=50
   EMAIL_UNREAD_ONLY=true

   # Logging
   LOG_LEVEL=INFO
   LOG_FILE=logs/agent.log

   # Environment
   ENVIRONMENT=development
   DEBUG=false
   ```

2. **Review `config/config.yaml`** (optional - defaults are good)

---

## Testing Your Setup

### Test 1: Configuration Loading
```bash
# Activate virtual environment first
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Test config
python -c "from src.config.loader import get_config; print('Config loaded:', get_config().environment)"
```

### Test 2: MongoDB Connection
```bash
python -c "from src.database.connection import MongoDBConnection; from src.config.loader import get_config; conn = MongoDBConnection(get_config().mongodb); conn.connect(); print('MongoDB: Connected!')"
```

### Test 3: Ollama Connection
```bash
python -c "from src.llm.client import LLMClient; from src.config.loader import get_config; client = LLMClient(get_config().llm); print('Ollama:', 'Connected!' if client.health_check() else 'Failed')"
```

### Test 4: Run Main Application
```bash
python src/main.py
```

---

## Running the Agent

### Start Services (in separate terminals)

**Terminal 1 - MongoDB** (if local):
```bash
mongod --dbpath /path/to/data
```

**Terminal 2 - Ollama**:
```bash
ollama serve
```

**Terminal 3 - Financial Agent**:
```bash
# Activate venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Run agent
python src/main.py
```

### Running MCP Servers

The agent uses MCP servers for modular functionality:

```bash
# Gmail MCP Server
python -m mcp_servers.gmail

# Database MCP Server (when implemented)
python -m mcp_servers.database

# Document MCP Server (when implemented)
python -m mcp_servers.document
```

---

## Troubleshooting

### "Python not found"
- Install Python 3.8+ from python.org
- Add Python to PATH during installation

### "credentials.json not found"
- Download from Google Cloud Console
- Place in project root directory
- Ensure filename is exactly `credentials.json`

### "MongoDB connection refused"
- Ensure MongoDB is running
- Check connection string in `.env`
- For Atlas: whitelist your IP

### "Ollama connection failed"
- Start Ollama: `ollama serve`
- Verify model: `ollama list`
- Check URL in `.env`: `http://localhost:11434`

### "Module not found" errors
- Activate virtual environment
- Reinstall dependencies: `pip install -r requirements.txt`

### Gmail authentication issues
- Delete `token.json` and re-authenticate
- Add your email as test user in OAuth consent screen
- Check scopes are correct

---

## Next Steps After Setup

1. **Send test email** to your Gmail account
2. **Monitor logs**: `tail -f logs/agent.log`
3. **Check MongoDB** for processed data
4. **Review MCP architecture**: `docs/mcp-architecture.md`
5. **Read implementation plan**: `docs/implementation-plan.md`

---

## Development Commands

```bash
# Run tests
pytest

# Format code
black src/ tests/

# Lint code
flake8 src/

# Type checking
mypy src/
```

---

## Security Reminders

⚠️ **Never commit:**
- `credentials.json`
- `token.json`
- `.env`

✅ **Always:**
- Use strong MongoDB passwords
- Enable `MASK_SENSITIVE_DATA=true` in production
- Regularly rotate API credentials
- Review OAuth consent screen permissions

---

## Support & Resources

- **MCP Architecture**: `docs/mcp-architecture.md`
- **Implementation Plan**: `docs/implementation-plan.md`
- **Gmail API Docs**: https://developers.google.com/gmail/api
- **MongoDB Docs**: https://docs.mongodb.com/
- **Ollama Docs**: https://github.com/ollama/ollama

---

**Setup complete! Ready to process financial emails! 🚀**