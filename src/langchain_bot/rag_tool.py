from pathlib import Path
from langchain_core.tools import tool
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import os

# 8.1 — Module cache singleton
_vector_store = None


# 8.2 — load_policy_documents()
def load_policy_documents() -> list[Document]:
    """Resolve policies/ directory at project root, load text files, and add metadata."""
    project_root = Path(__file__).resolve().parent.parent.parent
    policies_dir = project_root / "policies"
    
    documents = []
    
    if policies_dir.exists() and policies_dir.is_dir():
        for file_path in policies_dir.glob("*.txt"):
            loader = TextLoader(str(file_path), encoding="utf-8")
            loaded_docs = loader.load()
            
            # Set the metadata source to just the filename (e.g., "refund_policy.txt")
            for doc in loaded_docs:
                doc.metadata["source"] = file_path.name
                
            documents.extend(loaded_docs)
            
    return documents

def split_documents(documents: list[Document]) -> list[Document]:
    """Split documents into smaller, overlapping chunks for better vector retrieval."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )
    return text_splitter.split_documents(documents)

def get_vector_store() -> Chroma:
    """Initialize or load the Chroma vector store as a singleton instance."""
    global _vector_store
    
    if _vector_store is not None:
        return _vector_store
        
    project_root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(dotenv_path=project_root / ".env")
    persist_dir = project_root / "chroma_db"
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=os.environ["OPENAI_API_KEY"])
    
    if persist_dir.exists() and any(persist_dir.iterdir()):
        print("Loaded existing Chroma vector store database.")
        _vector_store = Chroma(
            persist_directory=str(persist_dir),
            embedding_function=embeddings
        )
    else:
        print("Loading documents and creating new Chroma vector store...")
        docs = load_policy_documents()
        chunks = split_documents(docs)
        _vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=str(persist_dir)
        )
        print("Vector store database created and persisted successfully.")
        
    return _vector_store

@tool
def search_policies(query: str) -> str:
    """Search company policy documentation. Use this for general policy or FAQ inquiries only, not for tracking or managing individual user orders."""
    vector_store = get_vector_store()

    docs = vector_store.similarity_search(query, k=4)
    
    formatted_results = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown source")
        formatted_results.append(f"Source [{source}]:\n{doc.page_content}")
        
    return "\n\n---\n\n".join(formatted_results)


def initialize_vector_store():
    """Public function called at application startup to populate or verify the vector store cache."""
    get_vector_store()


__all__ = ["search_policies", "initialize_vector_store"]