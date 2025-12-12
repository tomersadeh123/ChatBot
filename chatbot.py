"""
Chatbot orchestration with Groq API integration.

Handles chat requests, API calls with retry logic, and logging.
"""
import uuid
from typing import Dict, Any, Optional
from groq import Groq
from config import Config
from rag_system import get_rag_system
from utils.key_bank import get_keybank
from utils.mongo_logger import get_mongo_logger
from utils.error_handler import log_errors


class Chatbot:
    """Main chatbot class with enterprise features."""

    def __init__(self):
        """Initialize chatbot components."""
        self.rag_system = get_rag_system()

        try:
            self.keybank = get_keybank()
            print(f"✓ [CHATBOT] KeyBank initialized with {self.keybank.key_count()} key(s)")
        except Exception as e:
            print(f"⚠ [CHATBOT] KeyBank initialization failed: {e}")
            raise

        self.mongo_logger = get_mongo_logger()

        print("✓ [CHATBOT] Initialized with KeyBank and MongoDB logging")

    @log_errors("initialize_rag")
    def ensure_initialized(self):
        """Ensure RAG system is initialized."""
        if not self.rag_system.initialized:
            self.rag_system.initialize()

    def _build_system_prompt(self, relevant_context: str) -> str:
        """Build the system prompt with RAG context.

        Args:
            relevant_context: Relevant information from RAG

        Returns:
            Complete system prompt
        """
        return f"""You are Tomer Sadeh's AI assistant. Answer questions about him naturally and conversationally.

KEY RULES:
1. For general questions: Keep responses SHORT (2-4 sentences)
2. For specific project questions: Provide more detail (4-6 sentences covering key components)
3. Speak naturally - like you're having a conversation, not reading a resume
4. When asked about a PROJECT, mention: what it does, key technologies, and impact
5. Don't repeat information unless asked

RELEVANT INFO:
{relevant_context}

Example good responses:
Q: "What's Tomer's experience?"
A: "Tomer is a Software Developer at Fibonatix working with .NET, React, and BigQuery. He focuses on building scalable systems and has automated workflows that reduced manual effort by 40%."

Q: "Does he know React?"
A: "Yes! Tomer builds responsive frontend applications with React, using hooks and context API. He's worked on full-stack projects combining React with .NET backends."

Now answer briefly and naturally:"""

    def _call_groq_with_retry(self, messages: list, key_index: int, attempt: int = 1) -> Optional[str]:
        """Call Groq API with retry logic.

        Args:
            messages: List of message dicts
            key_index: Index of API key to use
            attempt: Current attempt number

        Returns:
            Response text or None on failure
        """
        max_attempts = 3

        try:
            # Get Groq key from keybank
            groq_key, key_idx = self.keybank.get_key_with_index("chat")

            # Create Groq client with this key
            groq_client = Groq(api_key=groq_key)

            print(f"[CHATBOT] API call attempt={attempt}/{max_attempts} key_index={key_idx}")

            # Call Groq API
            chat_completion = groq_client.chat.completions.create(
                messages=messages,
                model=Config.GROQ_MODEL,
                temperature=Config.GROQ_TEMPERATURE,
                max_tokens=Config.GROQ_MAX_TOKENS,
                timeout=Config.GROQ_TIMEOUT
            )

            response = chat_completion.choices[0].message.content
            print(f"✓ [CHATBOT] API call successful key_index={key_idx}")
            return response

        except Exception as e:
            error_msg = str(e).lower()
            is_rate_limit = 'rate' in error_msg or 'quota' in error_msg or '429' in error_msg
            is_timeout = 'timeout' in error_msg or 'timed out' in error_msg
            is_retryable = is_rate_limit or is_timeout

            print(f"⚠ [CHATBOT] API call failed: {type(e).__name__}: {e}")

            # Penalize the failed key
            self.keybank.penalize_key(key_idx, seconds=2.0)

            # Retry if possible
            if is_retryable and attempt < max_attempts:
                print(f"[CHATBOT] Retrying with different key...")
                return self._call_groq_with_retry(messages, key_idx, attempt + 1)

            # All attempts failed
            raise

    def chat(self, user_message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle a chat message with RAG and logging.

        Args:
            user_message: User's message
            session_id: Optional session ID for tracking

        Returns:
            Dictionary with response and metadata
        """
        # Ensure RAG is initialized
        self.ensure_initialized()

        if not self.rag_system.resume_loaded:
            return {
                'error': 'Resume not loaded yet. Please wait for initialization.',
                'status': 'not_ready'
            }

        if not user_message or not user_message.strip():
            return {
                'error': 'No message provided',
                'status': 'invalid_input'
            }

        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        try:
            # Use RAG to find relevant context
            relevant_context = self.rag_system.search_similar(user_message, n_results=Config.RAG_TOP_K)

            # Build system prompt
            system_prompt = self._build_system_prompt(relevant_context)

            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            # Call Groq API with retry
            response = self._call_groq_with_retry(messages, key_index=0)

            if not response:
                raise Exception("Failed to get response from Groq API")

            # Log to MongoDB
            if self.mongo_logger.enabled:
                self.mongo_logger.upsert_session_turn(
                    session_id=session_id,
                    turn={
                        "user_message": user_message,
                        "ai_response": response,
                        "used_rag": True,
                        "rag_context_preview": relevant_context[:500] if relevant_context else None,
                        "api_calls": {"groq_chat": 1},
                        "model": Config.GROQ_MODEL
                    }
                )

            return {
                'response': response,
                'status': 'success',
                'session_id': session_id
            }

        except Exception as e:
            print(f"⚠ [CHATBOT] Error in chat: {e}")
            import traceback
            traceback.print_exc()

            return {
                'error': f'Error generating response: {str(e)}',
                'status': 'error'
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get chatbot statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "rag_stats": self.rag_system.get_stats(),
            "keybank_keys": self.keybank.key_count(),
            "mongo_logging": self.mongo_logger.enabled,
            "config": {
                "model": Config.GROQ_MODEL,
                "max_tokens": Config.GROQ_MAX_TOKENS,
                "temperature": Config.GROQ_TEMPERATURE
            }
        }


# Singleton instance
_chatbot: Optional[Chatbot] = None


def get_chatbot() -> Chatbot:
    """Get or create the chatbot singleton."""
    global _chatbot
    if _chatbot is None:
        _chatbot = Chatbot()
    return _chatbot
