"""
GitHub Auto-Sync Module
Automatically fetches your GitHub repos and adds them to the RAG system
"""

import requests
from datetime import datetime


def fetch_github_repos(username):
    """Fetch all public repos for a GitHub user"""
    try:
        # Fetch repos
        url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=50"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"⚠ GitHub API error: {response.status_code}")
            return []

        repos = response.json()
        print(f"✓ Found {len(repos)} GitHub repositories")
        return repos

    except Exception as e:
        print(f"⚠ Error fetching GitHub repos: {e}")
        return []


def fetch_repo_readme(owner, repo_name):
    """Fetch README content for a specific repo"""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo_name}/readme"
        headers = {'Accept': 'application/vnd.github.v3.raw'}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.text
        return None

    except Exception as e:
        print(f"  ⚠ Could not fetch README for {repo_name}: {e}")
        return None


def format_repo_info(repo, readme_content=None):
    """Format repo information for the knowledge base"""
    info = []

    # Basic info
    info.append(f"# GitHub Project: {repo['name']}")
    info.append(f"\n**Repository**: {repo['html_url']}")

    # Description
    if repo.get('description'):
        info.append(f"\n**Description**: {repo['description']}")

    # Tech stack
    if repo.get('language'):
        info.append(f"\n**Primary Language**: {repo['language']}")

    # Topics/Tags
    if repo.get('topics'):
        topics = ', '.join(repo['topics'])
        info.append(f"\n**Technologies/Topics**: {topics}")

    # Stats
    info.append(f"\n**Stars**: {repo.get('stargazers_count', 0)}")
    info.append(f"**Forks**: {repo.get('forks_count', 0)}")

    # Dates
    created = datetime.strptime(repo['created_at'], '%Y-%m-%dT%H:%M:%SZ')
    updated = datetime.strptime(repo['updated_at'], '%Y-%m-%dT%H:%M:%SZ')
    info.append(f"\n**Created**: {created.strftime('%B %Y')}")
    info.append(f"**Last Updated**: {updated.strftime('%B %Y')}")

    # README content
    if readme_content:
        info.append("\n## Project Details\n")
        # Limit README to reasonable length
        if len(readme_content) > 3000:
            readme_content = readme_content[:3000] + "\n\n[README truncated for length]"
        info.append(readme_content)

    return '\n'.join(info)


def sync_github_repos(username, collection, chunk_function):
    """
    Main function to sync GitHub repos to the vector database

    Args:
        username: GitHub username
        collection: ChromaDB collection
        chunk_function: Function to chunk text

    Returns:
        Number of repos synced
    """
    print(f"\n🔄 Syncing GitHub repos for @{username}...")

    repos = fetch_github_repos(username)

    if not repos:
        print("⚠ No repos found or error occurred")
        return 0

    synced_count = 0

    # Process each repo
    for repo in repos:
        repo_name = repo['name']

        # Skip forks unless they have significant changes
        if repo.get('fork') and repo.get('stargazers_count', 0) == 0:
            print(f"  ⏭ Skipping fork: {repo_name}")
            continue

        print(f"  📦 Processing: {repo_name}")

        # Fetch README
        readme = fetch_repo_readme(username, repo_name)

        # Format repo information
        repo_info = format_repo_info(repo, readme)

        # Create chunks
        chunks = chunk_function(repo_info)

        # Generate unique IDs
        ids = [f"github_{repo_name.lower()}_{i}" for i in range(len(chunks))]

        try:
            # Remove existing chunks for this repo (if any)
            existing_ids = []
            try:
                results = collection.get()
                if results and results['ids']:
                    existing_ids = [id for id in results['ids'] if id.startswith(f"github_{repo_name.lower()}_")]
                    if existing_ids:
                        collection.delete(ids=existing_ids)
            except:
                pass

            # Add new chunks
            collection.add(
                documents=chunks,
                ids=ids
            )

            print(f"    ✓ Added {len(chunks)} chunks")
            synced_count += 1

        except Exception as e:
            print(f"    ⚠ Error adding {repo_name}: {e}")

    print(f"\n✓ Successfully synced {synced_count} GitHub repositories")
    print(f"✓ Total items in knowledge base: {collection.count()}")

    return synced_count


if __name__ == "__main__":
    # Test the sync
    import chromadb
    from sentence_transformers import SentenceTransformer

    def chunk_text(text, chunk_size=500, overlap=50):
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks

    # Initialize
    chroma_client = chromadb.Client()
    collection = chroma_client.get_or_create_collection(name="resume_collection")

    # Sync repos
    sync_github_repos("tomersadeh123", collection, chunk_text)
