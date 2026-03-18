import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from gpt4all import GPT4All
from datetime import datetime
from pathlib import Path
import json

"""
Lightweight RAG system using FAISS for retrieval and gpt4all for local text generation.
No remote API calls, no torch - CPU-safe and stable.
"""

# Setup paths
RAG_DIR = Path(__file__).parent
EMBEDDER_PATH = RAG_DIR / "database" / "embedder"
FAISS_INDEX_PATH = RAG_DIR / "database" / "faiss_index.bin"
CHUNKS_PATH = RAG_DIR / "database" / "chunks.json"
OUTPUT_DIR = RAG_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Initialize local model (lightweight, fast)
model = GPT4All("orca-mini-3b-gguf2-q4_0")

# Functions to save/load embedder
def save_embedder(embedder):
    """Save embedder to disk."""
    embedder.save(str(EMBEDDER_PATH))
    print(f"✓ Embedder saved to {EMBEDDER_PATH}")

def load_embedder():
    """Load embedder from disk if exists, otherwise initialize and save."""
    if EMBEDDER_PATH.exists():
        print(f"✓ Loading embedder from {EMBEDDER_PATH}")
        return SentenceTransformer(str(EMBEDDER_PATH))
    else:
        print("✓ Initializing new embedder...")
        embedder = SentenceTransformer("all-MiniLM-L6-v2")
        save_embedder(embedder)
        return embedder

# Functions to save/load FAISS index and chunks
def save_faiss_index(index, chunks):
    """Save FAISS index and chunks to disk."""
    faiss.write_index(index, str(FAISS_INDEX_PATH))
    with open(CHUNKS_PATH, "w") as f:
        json.dump(chunks, f)
    print(f"✓ FAISS index saved to {FAISS_INDEX_PATH}")
    print(f"✓ Chunks saved to {CHUNKS_PATH}")

def load_faiss_index_and_chunks():
    """Load FAISS index and chunks from disk if they exist."""
    if FAISS_INDEX_PATH.exists() and CHUNKS_PATH.exists():
        print(f"✓ Loading FAISS index from {FAISS_INDEX_PATH}")
        index = faiss.read_index(str(FAISS_INDEX_PATH))
        with open(CHUNKS_PATH, "r") as f:
            chunks = json.load(f)
        return index, chunks
    return None, None

# Load or initialize embedder
embedder = load_embedder()

# Example scientific corpus
documents = [
    "CRISPR-Cas9 is a genome editing tool that allows precise DNA modification.",
    "Transformers are deep learning models based on self-attention mechanisms.",
    "Quantum entanglement describes correlated quantum states between particles.",
    "The PCR technique amplifies DNA sequences using thermal cycling."
]

# Chunking (simple version)
def chunk_docs(docs, chunk_size=100):
    chunks = []
    for doc in docs:
        chunks.append(doc)  # already small
    return chunks

chunks = chunk_docs(documents)

# Load or create embeddings and FAISS index
index, loaded_chunks = load_faiss_index_and_chunks()

if index is None:
    print("✓ Creating new embeddings and FAISS index...")
    embeddings = embedder.encode(chunks)
    embeddings = np.array(embeddings).astype("float32")
    
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    save_faiss_index(index, chunks)
else:
    chunks = loaded_chunks
    print(f"✓ Using cached embeddings ({len(chunks)} chunks)")

# Retrieval function
def retrieve(query, k=2):
    q_embedding = embedder.encode([query]).astype("float32")
    distances, indices = index.search(q_embedding, k)
    return [chunks[i] for i in indices[0]]

# RAG generation using local model
def generate_answer(query, use_retrieval=True, max_tokens=300, temp=0.7, retrieval_k=2):
    """
    Generate answer using local model.
    
    Args:
        query: The user's question
        use_retrieval: If True, retrieve context documents. If False, generate answer directly.
    
    Returns:
        Tuple of (answer, context, retrieved_docs)
    """
    retrieved_docs = []
    context = ""
    
    if use_retrieval:
        retrieved_docs = retrieve(query,k=retrieval_k)
        context = "\n".join(retrieved_docs)
        
        prompt = f"""You are a scientific assistant. Use the context below to answer the question.

Context:
{context}

Question:
{query}

Answer with citations from the context."""
    else:
        prompt = f"""You are a scientific assistant. Answer the following question directly without additional context.

Question:
{query}

Provide a clear and concise answer."""
    
    print("Generated Prompt:\n", prompt)

    response = model.generate(prompt, max_tokens=max_tokens, temp=temp)
    return response, context, retrieved_docs

# Save results to text file
def save_rag_results(query, context, retrieved_docs, answer, use_retrieval=True, max_tokens=300, temp=0.7, retrieval_k=2):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"rag_result_{timestamp}.txt"
    
    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("RAG (Retrieval-Augmented Generation) Result\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("CONFIGURATION\n")
        f.write("-" * 80 + "\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Embedding Model: all-MiniLM-L6-v2\n")
        f.write(f"Generation Model: orca-mini-3b-gguf2-q4_0\n")
        f.write(f"Vector Database: FAISS (IndexFlatL2)\n")
        f.write(f"Max Tokens: {max_tokens}\n")
        f.write(f"Temperature: {temp}\n")
        f.write(f"Use Retrieval: {'Yes' if use_retrieval else 'No'}\n")
        f.write(f"Retrieved Chunks: {len(retrieved_docs) if use_retrieval else 0}\n")
        f.write(f"Retrieval k: {retrieval_k}\n\n")
        
        f.write("QUERY\n")
        f.write("-" * 80 + "\n")
        f.write(f"{query}\n\n")
        
        if use_retrieval:
            f.write("RETRIEVED CONTEXT\n")
            f.write("-" * 80 + "\n")
            f.write(f"{context}\n\n")
        
        f.write("GENERATED ANSWER\n")
        f.write("-" * 80 + "\n")
        
        # Write each sentence on a new line for readability
        import re
        sentences = re.split(r'(?<=[.!?])\s+', answer)
        for sentence in sentences:
            if sentence.strip():
                f.write(f"{sentence.strip()}\n")
        f.write("\n")
        
        f.write("=" * 80 + "\n")
    
    print(f"\n✓ Result saved to: {output_file}")
    return output_file

# Run query
if __name__ == "__main__":
    # Configuration - toggle retrieval context on/off
    USE_RETRIEVAL = True  # Set to False to disable context retrieval
    max_tokens = 300
    temp = 0.7
    retrieval_k = 2
    
    query = "How does CRISPR work?"
    
    print(f"\n{'='*80}")
    print(f"Query Mode: {'RAG (with context retrieval)' if USE_RETRIEVAL else 'Direct Generation (no context)'}")
    print(f"{'='*80}\n")
    
    
    answer, context, retrieved_docs = generate_answer(query, use_retrieval=USE_RETRIEVAL, max_tokens=max_tokens, temp=temp, retrieval_k=retrieval_k)
    print("Answer:\n", answer)
    
    # Save results to file
    save_rag_results(query, context, retrieved_docs, answer, use_retrieval=USE_RETRIEVAL, max_tokens=max_tokens, temp=temp, retrieval_k=retrieval_k)