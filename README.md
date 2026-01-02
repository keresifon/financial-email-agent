# Financial Email Agent

An autonomous AI agent that monitors Gmail inbox, identifies financial emails, extracts structured data using open-source Llama models, and stores information in MongoDB for analysis and reporting.

## 🌟 Features

- **Automated Email Monitoring**: Continuously monitors Gmail inbox using OAuth2 authentication
- **Intelligent Classification**: Uses Llama 3.1 models to classify emails into financial categories
- **Data Extraction**: Extracts structured information from:
  - Invoices (vendor details, line items, amounts, dates)
  - Receipts (merchant info, items, payment details)
  - Bank Statements (transactions, balances, account info)
  - Expense Reports (employee expenses, categories, totals)
- **MongoDB Storage**: Stores extracted data in organized collections for easy querying
- **Scheduled Processing**: Configurable intervals for automatic email checking
- **Error Handling**: Robust retry mechanisms and error recovery
- **Logging & Monitoring**: Comprehensive logging for debugging and monitoring

## 🏗️ Architecture

**Current Implementation:** Monolithic architecture with direct service integration

The system consists of several key components:

- **Email Monitor Service**: Connects to Gmail API and fetches new emails
- **Email Classifier**: Uses Llama models to identify financial emails
- **Data Extraction Engine**: Specialized extractors for different document types
- **Attachment Processor**: Extracts text from PDFs and images (OCR)
- **MongoDB Database**: Stores emails and extracted financial data
- **Scheduler**: Automates the email checking process
- **Configuration Manager**: Centralized configuration management

**Note:** MCP (Model Context Protocol) server implementations are available in `mcp_servers/` directory for future modular architecture. See [docs/implementation-plan.md](docs/implementation-plan.md) for MCP integration roadmap.

For detailed architecture information, see [docs/architecture.md](docs/architecture.md).

## 📋 Prerequisites

- Python 3.10 or higher
- MongoDB 4.4 or higher
- Ollama (for running Llama models locally)
- Gmail account with API access enabled
- Minimum 8GB RAM (16GB recommended for Llama 3.1 8B model)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/financial-email-agent.git
cd financial-email-agent
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Install and Configure Ollama

```bash
# Install Ollama (visit https://ollama.ai for installation instructions)

# Pull Llama 3.1 model
ollama pull llama3.1:8b

# Start Ollama server (runs on http://localhost:11434 by default)
ollama serve
```

### 4. Set Up MongoDB

```bash
# Install MongoDB (visit https://www.mongodb.com/try/download/community)

# Start MongoDB service
# On Windows:
net start MongoDB
# On macOS/Linux:
sudo systemctl start mongod
```

### 5. Configure Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download credentials and save as `credentials.json` in project root

### 6. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
```

### 7. Run the Agent

```bash
# First run will prompt for Gmail authentication
python src/main.py
```

## ⚙️ Configuration

Configuration is managed through `config/config.yaml`. Key settings include:

```yaml
email:
  monitoring:
    interval_minutes: 15  # How often to check for new emails
    max_emails_per_check: 50

llama:
  model: llama3.1:8b
  temperature: 0.1
  max_tokens: 2048

mongodb:
  connection_string: mongodb://localhost:27017
  database: financial_data
```

See [config/config.example.yaml](config/config.example.yaml) for all available options.

## 📁 Project Structure

```
financial-email-agent/
├── src/
│   ├── main.py                 # Application entry point
│   ├── config/                 # Configuration management
│   ├── email/                  # Email monitoring and processing
│   ├── classifier/             # Email classification
│   ├── extractors/             # Data extraction modules
│   ├── database/               # MongoDB integration
│   ├── llm/                    # Llama model integration
│   └── utils/                  # Utility functions
├── tests/                      # Unit and integration tests
├── docs/                       # Documentation
│   ├── architecture.md         # System architecture
│   └── implementation-plan.md  # Development roadmap
├── config/                     # Configuration files
├── logs/                       # Application logs
├── credentials.json            # Gmail API credentials (not in repo)
├── .env                        # Environment variables (not in repo)
├── .gitignore
├── requirements.txt
├── LICENSE
└── README.md
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_classifier.py
```

## 📊 Data Schema

The agent stores data in MongoDB with the following collections:

- **emails**: Raw email metadata and classification results
- **invoices**: Extracted invoice data with line items
- **receipts**: Receipt information and purchased items
- **bank_statements**: Bank transactions and account balances
- **expense_reports**: Employee expense data

See [docs/architecture.md](docs/architecture.md) for detailed schema information.

## 🔒 Security Considerations

- **OAuth2 Credentials**: Store `credentials.json` and `token.json` securely
- **Environment Variables**: Never commit `.env` file to version control
- **Database Security**: Use MongoDB authentication in production
- **Data Privacy**: Sensitive information (account numbers) is masked
- **API Rate Limits**: Configured to respect Gmail API quotas

## 🛠️ Development

### Setting Up Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run linting
flake8 src/
black src/
isort src/
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📈 Roadmap

- [x] Core email monitoring and classification
- [x] Basic data extraction for invoices and receipts
- [ ] Advanced extraction for bank statements
- [ ] Web dashboard for viewing extracted data
- [ ] Email notifications for important financial events
- [ ] Multi-language support
- [ ] Cloud deployment options (Docker, Kubernetes)
- [ ] Integration with accounting software (QuickBooks, Xero)

See [docs/implementation-plan.md](docs/implementation-plan.md) for detailed development phases.

## 🐛 Troubleshooting

### Common Issues

**Gmail Authentication Fails**
- Ensure OAuth2 credentials are correctly configured
- Check that Gmail API is enabled in Google Cloud Console
- Verify redirect URIs match your configuration

**Llama Model Not Found**
- Run `ollama pull llama3.1:8b` to download the model
- Ensure Ollama server is running (`ollama serve`)
- Check Ollama API URL in configuration

**MongoDB Connection Error**
- Verify MongoDB service is running
- Check connection string in configuration
- Ensure MongoDB port (27017) is not blocked

**Low Extraction Accuracy**
- Try using a larger Llama model (13B or 70B)
- Adjust temperature and prompt settings
- Provide more training examples in prompts

## 📝 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) for easy Llama model deployment
- [Meta AI](https://ai.meta.com/) for the Llama models
- [MongoDB](https://www.mongodb.com/) for the database
- [Google](https://developers.google.com/gmail/api) for Gmail API

## 📧 Contact

For questions, issues, or suggestions, please open an issue on GitHub.

## ⚠️ Disclaimer

This software is provided as-is for educational and personal use. Always ensure compliance with data privacy regulations (GDPR, CCPA, etc.) when processing financial information. The authors are not responsible for any misuse or data breaches.

---

**Status**: 🚧 In Development - See [implementation plan](docs/implementation-plan.md) for current progress.