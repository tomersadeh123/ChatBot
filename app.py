import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from groq import Groq
from dotenv import load_dotenv
import pdfplumber
from docx import Document
from werkzeug.utils import secure_filename
import chromadb
from sentence_transformers import SentenceTransformer
from github_sync import sync_github_repos

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize Groq client
groq_api_key = os.getenv('GROQ_API_KEY')
if not groq_api_key:
    print("WARNING: GROQ_API_KEY not found in environment variables!")
    groq_client = None
else:
    groq_client = Groq(api_key=groq_api_key)

# GitHub configuration
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME', 'tomersadeh123')

# Initialize RAG components
print("🔄 Initializing RAG system...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
chroma_client = chromadb.Client()

# Create or get collection
try:
    collection = chroma_client.get_or_create_collection(
        name="resume_collection",
        metadata={"description": "Tomer's resume information"}
    )
except Exception as e:
    print(f"⚠ Error creating collection: {e}")
    collection = None

# Store resume content
resume_content = ""
resume_loaded = False


def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into overlapping chunks"""
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)

    return chunks


def load_resume_and_create_embeddings():
    """Load resume and create vector embeddings"""
    global resume_content, resume_loaded, collection

    resume_file = 'resume_data.txt'
    if not os.path.exists(resume_file):
        print(f"⚠ {resume_file} not found")
        return

    try:
        with open(resume_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        if not content or content.startswith('# Your Professional Information'):
            print(f"⚠ Please add your information to {resume_file}")
            return

        resume_content = content
        print(f"✓ Resume loaded successfully from {resume_file}")

        # Create chunks
        chunks = chunk_text(resume_content)
        print(f"✓ Created {len(chunks)} text chunks")

        # Clear existing collection data
        if collection:
            try:
                collection.delete(where={})
            except:
                pass

            # Create embeddings and add to collection
            print("🔄 Creating embeddings...")

            ids = [f"chunk_{i}" for i in range(len(chunks))]

            # Add documents to collection
            collection.add(
                documents=chunks,
                ids=ids
            )

            print(f"✓ RAG system ready with {len(chunks)} chunks")
            resume_loaded = True
        else:
            print("⚠ Collection not available")

    except Exception as e:
        print(f"⚠ Error loading resume: {e}")
        import traceback
        traceback.print_exc()


def search_relevant_context(query, n_results=3):
    """Search for relevant context using RAG"""
    if not collection or not resume_loaded:
        return resume_content  # Fallback to full resume

    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count())
        )

        if results and results['documents']:
            # Combine top results
            relevant_chunks = results['documents'][0]
            return "\n\n".join(relevant_chunks)
        else:
            return resume_content

    except Exception as e:
        print(f"⚠ Search error: {e}")
        return resume_content  # Fallback


# Load resume and create embeddings on startup
load_resume_and_create_embeddings()

# Sync GitHub repos on startup
if GITHUB_USERNAME and collection:
    try:
        sync_github_repos(GITHUB_USERNAME, collection, chunk_text)
    except Exception as e:
        print(f"⚠ GitHub sync failed: {e}")
        print("  Continuing without GitHub data...")


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text


def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    doc = Document(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text


def extract_text_from_txt(file_path):
    """Extract text from TXT file"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/api/upload-resume', methods=['POST'])
def upload_resume():
    """Handle resume file upload"""
    global resume_content

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Please upload PDF, DOCX, or TXT'}), 400

    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Extract text based on file type
        file_ext = filename.rsplit('.', 1)[1].lower()

        if file_ext == 'pdf':
            resume_content = extract_text_from_pdf(file_path)
        elif file_ext == 'docx':
            resume_content = extract_text_from_docx(file_path)
        elif file_ext == 'txt':
            resume_content = extract_text_from_txt(file_path)

        # Clean up the uploaded file
        os.remove(file_path)

        if not resume_content.strip():
            return jsonify({'error': 'Could not extract text from file'}), 400

        return jsonify({
            'message': 'Resume uploaded successfully',
            'preview': resume_content[:200] + '...' if len(resume_content) > 200 else resume_content
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages with RAG"""
    if not groq_client:
        return jsonify({'error': 'Groq API key not configured'}), 500

    if not resume_loaded:
        return jsonify({'error': 'Resume not loaded yet'}), 400

    data = request.json
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        # Use RAG to find relevant context
        relevant_context = search_relevant_context(user_message, n_results=2)

        # Create system prompt with relevant context
        system_prompt = f"""You are Tomer Sadeh's AI assistant. Answer questions about him naturally and conversationally.

KEY RULES:
1. Keep responses SHORT and CONCISE (2-4 sentences max)
2. Speak naturally - like you're having a conversation, not reading a resume
3. Only mention the most relevant points - don't list everything
4. If asked about something specific, give a brief, focused answer
5. Don't repeat information unless asked

RELEVANT INFO:
{relevant_context}

Example good responses:
Q: "What's Tomer's experience?"
A: "Tomer is a Software Developer at Fibonatix working with .NET, React, and BigQuery. He focuses on building scalable systems and has automated workflows that reduced manual effort by 40%."

Q: "Does he know React?"
A: "Yes! Tomer builds responsive frontend applications with React, using hooks and context API. He's worked on full-stack projects combining React with .NET backends."

Now answer briefly and naturally:"""

        # Call Groq API
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=200  # Reduced from 1024 to keep responses shorter
        )

        response = chat_completion.choices[0].message.content

        return jsonify({'response': response}), 200

    except Exception as e:
        print(f"Error in chat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error generating response: {str(e)}'}), 500


@app.route('/api/resume-status', methods=['GET'])
def resume_status():
    """Check if resume is uploaded"""
    return jsonify({
        'uploaded': resume_loaded,
        'preview': resume_content[:200] + '...' if len(resume_content) > 200 else resume_content if resume_content else None
    }), 200


@app.route('/api/sync-github', methods=['POST'])
def sync_github():
    """Manually trigger GitHub sync"""
    if not GITHUB_USERNAME:
        return jsonify({'error': 'GitHub username not configured'}), 400

    if not collection:
        return jsonify({'error': 'Vector database not available'}), 500

    try:
        synced_count = sync_github_repos(GITHUB_USERNAME, collection, chunk_text)
        return jsonify({
            'message': f'Successfully synced {synced_count} repositories',
            'total_items': collection.count()
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Sync failed: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
