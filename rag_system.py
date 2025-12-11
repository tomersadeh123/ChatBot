"""
RAG (Retrieval-Augmented Generation) system for the chatbot.

Handles document embedding, vector storage, and similarity search.
"""
import os
import hashlib
from typing import List, Optional, Dict, Any
import chromadb
from sentence_transformers import SentenceTransformer
from config import Config
from github_sync import sync_github_repos


class RAGSystem:
    """RAG system using Sentence Transformers and ChromaDB."""

    def __init__(self):
        """Initialize the RAG system with lazy loading."""
        self.embedding_model = None
        self.chroma_client = None
        self.collection = None
        self.resume_content = ""
        self.resume_loaded = False
        self.initialized = False

        # Idempotency tracking (prevent duplicate embeddings)
        self._embedded_keys = set()

    def initialize(self):
        """Initialize embeddings and vector store (lazy loading)."""
        if self.initialized:
            return

        print("🔄 [RAG] Initializing RAG system...")

        try:
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(Config.RAG_EMBEDDING_MODEL)
            print(f"✓ [RAG] Loaded embedding model: {Config.RAG_EMBEDDING_MODEL}")

            # Initialize ChromaDB
            self.chroma_client = chromadb.Client()
            self.collection = self.chroma_client.get_or_create_collection(
                name="resume_collection",
                metadata={"description": "User resume and project information"}
            )
            print("✓ [RAG] ChromaDB collection ready")

            # Load resume
            self.load_resume()

            # Sync GitHub repos
            self.sync_github()

            self.initialized = True
            print("✓ [RAG] System initialized successfully")

        except Exception as e:
            print(f"⚠ [RAG] Initialization error: {e}")
            import traceback
            traceback.print_exc()

    def chunk_text(self, text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None) -> List[str]:
        """Split text into overlapping chunks.

        Args:
            text: Text to chunk
            chunk_size: Number of words per chunk (default from config)
            overlap: Number of overlapping words (default from config)

        Returns:
            List of text chunks
        """
        chunk_size = chunk_size or Config.RAG_CHUNK_SIZE
        overlap = overlap or Config.RAG_CHUNK_OVERLAP

        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)

        return chunks

    def _generate_idempotency_key(self, source: str, content: str) -> str:
        """Generate a unique key for deduplication.

        Args:
            source: Source identifier (e.g., 'resume', 'github:repo_name')
            content: Content to hash

        Returns:
            Unique hash key
        """
        combined = f"{source}:{content[:500]}"  # Use first 500 chars for hash
        return hashlib.md5(combined.encode()).hexdigest()

    def load_resume(self):
        """Load resume and create vector embeddings."""
        resume_file = 'resume_data.txt'

        if not os.path.exists(resume_file):
            print(f"⚠ [RAG] {resume_file} not found")
            return

        try:
            with open(resume_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content or content.startswith('# Your Professional Information'):
                print(f"⚠ [RAG] Please add your information to {resume_file}")
                return

            self.resume_content = content
            print(f"✓ [RAG] Resume loaded from {resume_file}")

            # Generate idempotency key
            resume_key = self._generate_idempotency_key('resume', content)

            # Skip if already embedded
            if resume_key in self._embedded_keys:
                print("✓ [RAG] Resume already embedded (idempotency)")
                self.resume_loaded = True
                return

            # Create chunks
            chunks = self.chunk_text(content)
            print(f"✓ [RAG] Created {len(chunks)} text chunks")

            # Clear existing resume data (identified by metadata)
            if self.collection:
                try:
                    # Delete previous resume chunks
                    self.collection.delete(where={"source": "resume"})
                except:
                    pass

                # Create document IDs and metadata
                ids = [f"resume_chunk_{i}_{resume_key[:8]}" for i in range(len(chunks))]
                metadatas = [{"source": "resume", "chunk_index": i, "idempotency_key": resume_key}
                            for i in range(len(chunks))]

                # Add documents to collection
                self.collection.add(
                    documents=chunks,
                    ids=ids,
                    metadatas=metadatas
                )

                # Mark as embedded
                self._embedded_keys.add(resume_key)

                print(f"✓ [RAG] Embedded {len(chunks)} resume chunks")
                self.resume_loaded = True
            else:
                print("⚠ [RAG] Collection not available")

        except Exception as e:
            print(f"⚠ [RAG] Error loading resume: {e}")
            import traceback
            traceback.print_exc()

    def sync_github(self):
        """Sync GitHub repositories."""
        if not Config.GITHUB_USERNAME or not self.collection:
            return

        try:
            print(f"🔄 [RAG] Syncing GitHub repos for {Config.GITHUB_USERNAME}...")
            sync_github_repos(Config.GITHUB_USERNAME, self.collection, self.chunk_text)
            print("✓ [RAG] GitHub sync complete")
        except Exception as e:
            print(f"⚠ [RAG] GitHub sync failed: {e}")
            print("  Continuing without GitHub data...")

    def search_similar(self, query: str, n_results: Optional[int] = None) -> str:
        """Search for relevant context using vector similarity.

        Args:
            query: Search query
            n_results: Number of results to return (default from config)

        Returns:
            Relevant context as combined text
        """
        n_results = n_results or Config.RAG_TOP_K

        if not self.collection or not self.resume_loaded:
            print("[RAG] Search fallback: using full resume")
            return self.resume_content  # Fallback

        try:
            # Perform similarity search
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, self.collection.count())
            )

            if results and results['documents']:
                # Combine top results
                relevant_chunks = results['documents'][0]
                context = "\n\n".join(relevant_chunks)

                print(f"✓ [RAG] Retrieved {len(relevant_chunks)} relevant chunks")
                return context
            else:
                return self.resume_content  # Fallback

        except Exception as e:
            print(f"⚠ [RAG] Search error: {e}")
            return self.resume_content  # Fallback

    def add_documents(self, documents: List[str], source: str, metadata: Optional[Dict[str, Any]] = None):
        """Add documents to the vector store with deduplication.

        Args:
            documents: List of document texts
            source: Source identifier (e.g., 'github:repo_name')
            metadata: Optional metadata dict to add to all documents
        """
        if not self.collection:
            print("⚠ [RAG] Collection not initialized")
            return

        try:
            # Generate idempotency keys
            doc_keys = [self._generate_idempotency_key(source, doc) for doc in documents]

            # Filter out already embedded documents
            new_docs = []
            new_keys = []
            for doc, key in zip(documents, doc_keys):
                if key not in self._embedded_keys:
                    new_docs.append(doc)
                    new_keys.append(key)

            if not new_docs:
                print(f"✓ [RAG] All documents from {source} already embedded (idempotency)")
                return

            # Create IDs and metadata
            ids = [f"{source}_{key[:12]}" for key in new_keys]
            metadatas = []
            for i, key in enumerate(new_keys):
                meta = {"source": source, "idempotency_key": key, "index": i}
                if metadata:
                    meta.update(metadata)
                metadatas.append(meta)

            # Add to collection
            self.collection.add(
                documents=new_docs,
                ids=ids,
                metadatas=metadatas
            )

            # Mark as embedded
            self._embedded_keys.update(new_keys)

            print(f"✓ [RAG] Added {len(new_docs)} new documents from {source}")

        except Exception as e:
            print(f"⚠ [RAG] Error adding documents: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics.

        Returns:
            Dictionary with stats
        """
        stats = {
            "initialized": self.initialized,
            "resume_loaded": self.resume_loaded,
            "total_documents": self.collection.count() if self.collection else 0,
            "unique_embedded_keys": len(self._embedded_keys),
            "embedding_model": Config.RAG_EMBEDDING_MODEL
        }
        return stats


# Singleton instance
_rag_system: Optional[RAGSystem] = None


def get_rag_system() -> RAGSystem:
    """Get or create the RAG system singleton."""
    global _rag_system
    if _rag_system is None:
        _rag_system = RAGSystem()
    return _rag_system
