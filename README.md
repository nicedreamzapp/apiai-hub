# 🚀 APIAI Hub

A professional FastAPI-powered development automation server for iOS development. Built to streamline Xcode workflows, automate builds, and provide remote development control through a clean web interface.

## ✨ Features

- **🔨 Automated iOS Builds** - Build and install apps directly to connected devices
- **📱 Remote App Launch** - Launch installed apps on iPhone remotely  
- **📊 System Monitoring** - Real-time CPU, memory, and disk usage stats
- **🔐 Secure API** - API key authentication with localhost bypass
- **📋 Job Management** - Organized development tasks with detailed logging
- **🎯 Professional Dashboard** - Clean web interface for all operations

## 🏗️ Architecture

```
apiai-hub/
├── app/
│   ├── server.py          # Main FastAPI server
│   ├── config/            # Configuration management
│   ├── api/               # API endpoints (health, jobs, logs)
│   ├── jobs/              # Job definitions and executor
│   ├── utils/             # System utilities
│   └── static/            # Web dashboard
├── bin/                   # Development scripts
├── logs/                  # Execution logs
└── scripts/               # Job scripts
```

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- Xcode (for iOS development features)
- Connected iPhone (for device builds)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/nicedreamzapp/apiai-hub.git
cd apiai-hub
```

2. **Set up virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API key and settings
```

5. **Run the server**
```bash
./run.sh
```

Visit `http://127.0.0.1:8765` to access the dashboard.

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MINI_API_KEY` | API authentication key | Required |
| `HOST` | Server host address | `127.0.0.1` |
| `PORT` | Server port | `8765` |

### Development Setup

The server includes specialized jobs for iOS development:

- **Xcode Build & Install** - Automated device deployment
- **App Launch Control** - Remote app launching
- **System Monitoring** - Resource usage tracking
- **Log Management** - Centralized logging system

## 📡 API Endpoints

### Core Endpoints

```http
GET  /health              # Health check and system status
GET  /stats               # System performance metrics  
GET  /api/jobs            # Available job definitions
POST /api/jobs/{job_id}   # Execute specific job
GET  /api/logs/{log_file} # Retrieve job logs
```

### Authentication

- **API Key**: Required for remote access via `X-API-Key` header
- **Localhost**: Automatic bypass for local development
- **Security**: Environment-based key management

## 🎯 Job System

Jobs are organized into logical groups:

### Xcode • Vision Builder
- Build & Install on iPhone
- Launch on Device  
- Project Management

### System Utilities
- Performance Monitoring
- Log Analysis
- Resource Management

## 📊 Monitoring

Real-time system metrics:
- CPU usage percentage
- Memory utilization 
- Disk space tracking
- System uptime

## 🔨 Development

### Adding New Jobs

1. Define job in `app/jobs/definitions.py`:
```python
"new_job_id": {
    "name": "Job Name",
    "description": "What this job does",
    "cmd": "shell command to execute"
}
```

2. Job will automatically appear in dashboard

### Custom Scripts

Place executable scripts in `scripts/` directory for complex workflows.

## 📝 Logging

All job executions are logged to `logs/` with:
- Timestamp information
- Execution output
- Error details
- Performance metrics

## 🛠️ Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Authentication**: API key + localhost bypass
- **System**: psutil for monitoring
- **Frontend**: HTML/CSS/JavaScript dashboard
- **iOS**: Xcode command line tools

## 🔒 Security

- Environment-based API key storage
- Localhost development bypass
- Secure file path handling
- Command injection protection

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make your changes
4. Add tests if applicable
5. Submit pull request

## 📞 Support

For questions or issues:
- Open GitHub issue
- Check logs in `logs/` directory
- Verify environment configuration

---

**Built for professional iOS development workflows** 🍎
