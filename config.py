"""
Centralized configuration for the chatbot application.

All environment variables and settings are managed here.
"""
import os


class Config:
    """Application configuration from environment variables."""

    # Flask settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

    # Groq API settings
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
    GROQ_TIMEOUT = int(os.getenv('GROQ_TIMEOUT', '30'))
    GROQ_MAX_TOKENS = int(os.getenv('GROQ_MAX_TOKENS', '350'))
    GROQ_TEMPERATURE = float(os.getenv('GROQ_TEMPERATURE', '0.7'))

    # Groq key rotation settings
    GROQ_KEY_RATE_PER_MIN = int(os.getenv('GROQ_KEY_RATE_PER_MIN', '30'))
    GROQ_KEY_INTERVAL_SECONDS = float(os.getenv('GROQ_KEY_INTERVAL_SECONDS', '2'))

    # RAG settings
    RAG_CHUNK_SIZE = int(os.getenv('RAG_CHUNK_SIZE', '500'))
    RAG_CHUNK_OVERLAP = int(os.getenv('RAG_CHUNK_OVERLAP', '50'))
    RAG_TOP_K = int(os.getenv('RAG_TOP_K', '4'))
    RAG_EMBEDDING_MODEL = os.getenv('RAG_EMBEDDING_MODEL', 'paraphrase-MiniLM-L3-v2')

    # MongoDB settings (optional)
    MONGODB_URI = os.getenv('MONGODB_URI') or os.getenv('MONGODB_ATLAS_URI')
    MONGO_DB_NAME = os.getenv('CHATBOT_MONGO_DB', 'chatbot_db')
    MONGO_COLLECTION = os.getenv('CHATBOT_MONGO_COLLECTION', 'chat_logs')
    MONGO_SESS_COLLECTION = os.getenv('CHATBOT_MONGO_SESS_COLLECTION', 'chat_sessions')

    # GitHub settings
    GITHUB_USERNAME = os.getenv('GITHUB_USERNAME', 'tomersadeh123')

    # Application settings
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    PORT = int(os.getenv('PORT', '5000'))

    @classmethod
    def validate(cls):
        """Validate critical configuration settings."""
        # Check for at least one Groq API key
        groq_key = os.getenv('GROQ_API_KEY')
        groq_key_1 = os.getenv('GROQ_API_KEY_1')

        if not groq_key and not groq_key_1:
            raise ValueError(
                "No Groq API key found. Set GROQ_API_KEY (comma-separated) or GROQ_API_KEY_1, GROQ_API_KEY_2, etc."
            )

        return True

    @classmethod
    def print_config(cls):
        """Print non-sensitive configuration for debugging."""
        print("=" * 50)
        print("CONFIGURATION")
        print("=" * 50)
        print(f"Groq Model: {cls.GROQ_MODEL}")
        print(f"Groq Timeout: {cls.GROQ_TIMEOUT}s")
        print(f"Groq Max Tokens: {cls.GROQ_MAX_TOKENS}")
        print(f"Groq Temperature: {cls.GROQ_TEMPERATURE}")
        print(f"RAG Chunk Size: {cls.RAG_CHUNK_SIZE}")
        print(f"RAG Chunk Overlap: {cls.RAG_CHUNK_OVERLAP}")
        print(f"RAG Top K: {cls.RAG_TOP_K}")
        print(f"Embedding Model: {cls.RAG_EMBEDDING_MODEL}")
        print(f"MongoDB Enabled: {'Yes' if cls.MONGODB_URI else 'No'}")
        print(f"GitHub Username: {cls.GITHUB_USERNAME}")
        print(f"Debug Mode: {cls.DEBUG}")
        print("=" * 50, flush=True)
