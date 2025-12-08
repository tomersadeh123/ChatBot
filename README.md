# 🤖 AI Resume Chatbot

An intelligent, RAG-powered chatbot that answers questions about your professional background. Perfect for embedding on your portfolio website or sharing with potential employers.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

- 🧠 **RAG Architecture** - Uses Retrieval Augmented Generation for accurate, context-aware responses
- 🔄 **GitHub Auto-Sync** - Automatically pulls your latest projects from GitHub
- 💬 **Natural Conversations** - Concise, conversational responses (not resume copy-paste)
- 🎨 **Modern UI** - Clean, responsive web interface
- 📄 **Multi-Format Support** - Handles PDF, DOCX, and TXT resumes
- 🆓 **100% Free** - Uses free Groq API (no costs)
- 🔒 **Privacy-First** - All data stored locally, no external databases

## 🎯 Why This Project?

This chatbot demonstrates:
- **Full-Stack Development** - Flask backend, React-style frontend
- **AI/ML Integration** - RAG, embeddings, vector databases
- **API Integration** - Groq LLM, GitHub REST API
- **Modern Architecture** - Microservices-ready, queue-based design
- **Portfolio-Ready** - Impressive project for your resume

## 🛠️ Tech Stack

**Backend:**
- Flask 3.0 (Python web framework)
- ChromaDB (Vector database)
- Sentence Transformers (Embeddings)
- Groq API (LLM - Llama 3.3 70B)

**Frontend:**
- HTML5, CSS3, JavaScript
- Responsive design
- Clean, modern UI

**Data Processing:**
- PDFPlumber (PDF parsing)
- python-docx (Word parsing)
- GitHub REST API

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Git
- A GitHub account (for auto-sync feature)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ai-resume-chatbot.git
cd ai-resume-chatbot
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Get your free Groq API key**
   - Go to [https://console.groq.com](https://console.groq.com)
   - Sign up (free, no credit card)
   - Create an API key

5. **Configure environment**
```bash
cp .env.example .env
# Edit .env and add:
# GROQ_API_KEY=your_actual_api_key
# GITHUB_USERNAME=your_github_username
```

6. **Add your resume information**
   - Edit `resume_data.txt` with your professional background
   - Or the chatbot will auto-sync from your GitHub repos

7. **Run the application**
```bash
python app.py
```

8. **Open in browser**
   - Navigate to: `http://localhost:5000`
   - Start chatting!

## 📖 Usage

### Basic Usage
1. Server automatically loads your resume on startup
2. Auto-syncs your GitHub projects
3. Open the web interface
4. Ask questions about your background

### Updating Your Information

**Option 1: Edit resume_data.txt**
```bash
# Edit resume_data.txt with your info
# Restart server
python app.py
```

**Option 2: GitHub Auto-Sync**
- Update your GitHub repo READMEs
- Restart server or trigger manual sync:
```bash
curl -X POST http://localhost:5000/api/sync-github
```

## 🎨 Customization

### Change Response Length
In `app.py`, line 289:
```python
max_tokens=200  # Increase for longer responses
```

### Adjust Retrieval Chunks
In `app.py`, line 257:
```python
n_results=2  # Number of context chunks to retrieve
```

### Modify Prompt Style
Edit the system prompt in `app.py` (lines 260-279) to change the chatbot's personality and response style.

## 🏗️ Architecture

```
┌─────────────────┐
│   Web Browser   │
│   (Frontend)    │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  Flask Backend  │
│   (app.py)      │
└────────┬────────┘
         │
    ┌────┴────┬─────────────┬──────────────┐
    │         │             │              │
    ▼         ▼             ▼              ▼
┌─────┐  ┌────────┐  ┌──────────┐  ┌──────────┐
│Groq │  │ChromaDB│  │  GitHub  │  │  Resume  │
│ API │  │(Vector │  │   API    │  │   Data   │
│     │  │  DB)   │  │          │  │   .txt   │
└─────┘  └────────┘  └──────────┘  └──────────┘
```

### How RAG Works

1. **Startup**: Load resume + GitHub repos → Create embeddings → Store in ChromaDB
2. **User Question**: Convert to embedding → Search ChromaDB for similar chunks
3. **Generate Response**: Send relevant context + question to Groq → Get natural answer

## 📊 Project Structure

```
ai-resume-chatbot/
├── app.py                 # Main Flask application
├── github_sync.py         # GitHub API integration
├── add_data.py           # Script to add custom data
├── resume_data.txt       # Your resume content
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create from .env.example)
├── .gitignore           # Git ignore rules
├── templates/
│   └── index.html       # Frontend HTML
├── static/
│   ├── css/
│   │   └── styles.css   # Styling
│   └── js/
│       └── app.js       # Frontend JavaScript
└── uploads/             # Temporary file storage (auto-created)
```

## 🔧 Advanced Features

### Manual GitHub Sync
Trigger sync via API:
```bash
curl -X POST http://localhost:5000/api/sync-github
```

### Add Custom Content
Use `add_data.py` to add blog posts, certifications, etc:
```python
python add_data.py
```

### Check System Status
```bash
curl http://localhost:5000/api/resume-status
```

## 🚀 Deployment

### Deploy to Heroku
```bash
# Coming soon - deployment guides
```

### Deploy to Railway
```bash
# Coming soon
```

### Docker (Optional)
```bash
# Coming soon
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Groq](https://groq.com) - Free, fast LLM API
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Sentence Transformers](https://www.sbert.net/) - Embeddings

