"""
Flask application for Tomer's AI Chatbot.

Enterprise-ready with modular architecture, key rotation, and MongoDB logging.
"""
import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import pdfplumber
from docx import Document
from werkzeug.utils import secure_filename

# Import our enterprise modules
from config import Config
from chatbot import get_chatbot
from rag_system import get_rag_system

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Apply configuration
app.config.from_object(Config)
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# Validate configuration
try:
    Config.validate()
    Config.print_config()
except Exception as e:
    print(f"⚠ Configuration error: {e}")
    print("  Continuing anyway...")

# Initialize enterprise components (singletons)
chatbot = None
rag_system = None


def ensure_initialized():
    """Ensure chatbot and RAG system are initialized (lazy loading)."""
    global chatbot, rag_system

    if chatbot is None:
        print("🚀 [APP] Initializing enterprise components...")
        chatbot = get_chatbot()
        rag_system = get_rag_system()
        # Initialize RAG on first call
        chatbot.ensure_initialized()
        print("✓ [APP] Enterprise components ready")


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def extract_text_from_pdf(file_path):
    """Extract text from PDF file."""
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text


def extract_text_from_docx(file_path):
    """Extract text from DOCX file."""
    doc = Document(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text


def extract_text_from_txt(file_path):
    """Extract text from TXT file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


# =============================================================================
# ROUTES
# =============================================================================

@app.route('/health')
def health():
    """Health check endpoint for deployment platforms."""
    is_initialized = rag_system.initialized if rag_system else False
    return jsonify({
        'status': 'ok',
        'rag_initialized': is_initialized,
        'version': '2.0.0-enterprise'
    }), 200


@app.route('/')
def index():
    """Serve the main page."""
    # Initialize on first request (lazy loading)
    try:
        ensure_initialized()
    except Exception as e:
        print(f"⚠ [APP] Initialization error: {e}")
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages with RAG."""
    try:
        # Ensure initialized
        ensure_initialized()

        # Get message from request
        data = request.json
        if not data:
            return jsonify({'error': 'Invalid request: no JSON data'}), 400

        user_message = data.get('message', '')
        session_id = data.get('session_id')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # Delegate to chatbot module
        result = chatbot.chat(user_message, session_id=session_id)

        if result.get('status') == 'error':
            return jsonify({'error': result.get('error')}), 500
        elif result.get('status') == 'not_ready':
            return jsonify({'error': result.get('error')}), 400

        return jsonify({
            'response': result.get('response'),
            'session_id': result.get('session_id')
        }), 200

    except Exception as e:
        print(f"⚠ [APP] Chat endpoint error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/api/upload-resume', methods=['POST'])
def upload_resume():
    """Handle resume file upload."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload PDF, DOCX, or TXT'}), 400

    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(file_path)

        # Extract text based on file type
        file_ext = filename.rsplit('.', 1)[1].lower()

        if file_ext == 'pdf':
            resume_text = extract_text_from_pdf(file_path)
        elif file_ext == 'docx':
            resume_text = extract_text_from_docx(file_path)
        elif file_ext == 'txt':
            resume_text = extract_text_from_txt(file_path)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400

        # Clean up the uploaded file
        os.remove(file_path)

        if not resume_text.strip():
            return jsonify({'error': 'Could not extract text from file'}), 400

        # TODO: Add this resume text to RAG system
        # For now, just return success
        return jsonify({
            'message': 'Resume uploaded successfully',
            'preview': resume_text[:200] + '...' if len(resume_text) > 200 else resume_text
        }), 200

    except Exception as e:
        print(f"⚠ [APP] Error processing file: {e}")
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500


@app.route('/api/resume-status', methods=['GET'])
def resume_status():
    """Check if resume is loaded."""
    ensure_initialized()

    is_loaded = rag_system.resume_loaded if rag_system else False
    preview = rag_system.resume_content if rag_system and is_loaded else None

    return jsonify({
        'uploaded': is_loaded,
        'preview': preview[:200] + '...' if preview and len(preview) > 200 else preview
    }), 200


@app.route('/api/sync-github', methods=['POST'])
def sync_github():
    """Manually trigger GitHub sync."""
    ensure_initialized()

    if not Config.GITHUB_USERNAME:
        return jsonify({'error': 'GitHub username not configured'}), 400

    if not rag_system or not rag_system.collection:
        return jsonify({'error': 'Vector database not available'}), 500

    try:
        rag_system.sync_github()
        return jsonify({
            'message': f'Successfully synced GitHub repositories',
            'total_items': rag_system.collection.count()
        }), 200

    except Exception as e:
        print(f"⚠ [APP] GitHub sync error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Sync failed: {str(e)}'}), 500


@app.route('/api/stats', methods=['GET'])
def stats():
    """Get chatbot statistics."""
    ensure_initialized()

    return jsonify(chatbot.get_stats()), 200


if __name__ == '__main__':
    # Use PORT environment variable for deployment (Render, Heroku, etc.)
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)
