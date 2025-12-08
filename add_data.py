"""
Script to add more data to your RAG chatbot
Run this anytime you want to add new information
"""

import chromadb
from sentence_transformers import SentenceTransformer

# Initialize
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="resume_collection")

def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into overlapping chunks"""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def add_document(title, content):
    """Add a new document to the knowledge base"""
    print(f"Adding: {title}")

    # Add title as context
    full_content = f"# {title}\n\n{content}"

    # Create chunks
    chunks = chunk_text(full_content)

    # Get current count for unique IDs
    current_count = collection.count()

    # Generate IDs
    ids = [f"{title.lower().replace(' ', '_')}_{i}" for i in range(len(chunks))]

    # Add to collection
    collection.add(
        documents=chunks,
        ids=ids
    )

    print(f"✓ Added {len(chunks)} chunks from '{title}'")

# Example: Add more data
if __name__ == "__main__":
    # Example 1: Add a project description
    add_document(
        title="E-Commerce Project",
        content="""
        Detailed description of your e-commerce project...
        Technologies used, challenges solved, features implemented, etc.
        """
    )

    # Example 2: Add certification
    add_document(
        title="AWS Certification",
        content="""
        AWS Certified Solutions Architect - Associate
        Completed: December 2024
        Key skills: EC2, S3, Lambda, API Gateway, CloudFormation...
        """
    )

    # Example 3: Add blog post
    add_document(
        title="How I Built a Scalable API",
        content="""
        Your blog post content here...
        """
    )

    print(f"\n✓ Total documents in knowledge base: {collection.count()}")
