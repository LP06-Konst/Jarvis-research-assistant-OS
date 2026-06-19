"""
RAG Pipeline for Jarvis Research OS
Handles PDF processing, embeddings, and semantic search
"""

import os
import hashlib
import re
from typing import List, Dict, Any, Optional

# Lazy loading to handle missing dependencies gracefully
_chroma_client = None
_embedding_model = None
_vector_collection = None

# Set to True only after successful model load; never auto-download at import time
# ML_AVAILABLE starts False; becomes True only after a successful import check.
# The embedding model itself loads lazily on first actual search/upload.
ML_AVAILABLE = False
_ml_init_attempted = False
_ml_model_loaded = False

def check_ml_available():
    """Check if ML libraries are importable (model loads lazily on first actual use)"""
    global ML_AVAILABLE, _ml_init_attempted
    if ML_AVAILABLE and _ml_model_loaded:
        return True
    if _ml_init_attempted:
        return ML_AVAILABLE
    _ml_init_attempted = True
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        ML_AVAILABLE = True
        print("[rag] ML libraries importable (model loads on first search/upload)")
    except ImportError as e:
        print(f"[rag] ML libraries not available: {e}")
        ML_AVAILABLE = False
    return ML_AVAILABLE

def is_ml_model_loaded():
    """Check if the embedding model has been loaded into memory"""
    return _ml_model_loaded

def get_chroma_client():
    """Get or initialize ChromaDB client"""
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        _chroma_client = chromadb.Client()
    return _chroma_client

def get_embedding_model():
    """Get or initialize embedding model (lazy, with timeout)"""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            import os
            os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "0")
            # Use a lightweight but effective model
            print("[rag] Loading sentence-transformer model (first use may take a moment)...")
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("[rag] Model loaded successfully")
        except Exception as e:
            print(f"[rag] Could not load embedding model: {e}")
            raise
    return _embedding_model

def get_vector_collection():
    """Get or initialize the main vector collection"""
    global _vector_collection
    if _vector_collection is None:
        if not check_ml_available():
            return None
        client = get_chroma_client()
        try:
            _vector_collection = client.get_collection("research_chunks")
        except:
            _vector_collection = client.create_collection("research_chunks")
    return _vector_collection

def extract_text_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """Extract text from PDF with page-level chunking"""
    import pdfplumber
    
    chunks = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                # Clean and chunk the text
                page_chunks = chunk_text(text, page_num)
                chunks.extend(page_chunks)
    
    return chunks

def chunk_text(text: str, page_num: int = 1, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
    """Split text into overlapping chunks for better retrieval"""
    # Clean the text
    text = clean_text(text)
    
    if not text.strip():
        return []
    
    chunks = []
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    
    current_chunk = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        if len(current_chunk) + len(sentence) + 1 > chunk_size:
            if current_chunk.strip():
                chunks.append({
                    "text": current_chunk.strip(),
                    "page": page_num,
                    "char_count": len(current_chunk)
                })
            # Add overlap from previous chunk
            words = current_chunk.split()
            overlap_words = words[-(overlap//5):] if len(words) > overlap//5 else words
            current_chunk = " ".join(overlap_words) + " " + sentence
        else:
            current_chunk = current_chunk + " " + sentence if current_chunk else sentence
    
    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append({
            "text": current_chunk.strip(),
            "page": page_num,
            "char_count": len(current_chunk)
        })
    
    return chunks

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep punctuation
    text = re.sub(r'[^\w\s.,!?;:\'\"-]', '', text)
    return text.strip()

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts"""
    model = get_embedding_model()
    embeddings = model.encode(texts)
    return embeddings.tolist()

def store_chunks(source_id: str, project_id: str, chunks: List[Dict[str, Any]], metadata: Dict[str, Any] = None):
    """Store chunks in vector database with metadata"""
    if not check_ml_available():
        print("ML not available - storing text chunks only")
        return []
    
    collection = get_vector_collection()
    if not collection:
        return []
    
    try:
        model = get_embedding_model()
        
        texts = [chunk["text"] for chunk in chunks]
        embeddings = model.encode(texts).tolist()
        
        ids = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{source_id}_{chunk['page']}_{i}"
            ids.append(chunk_id)
            
            meta = {
                "source_id": source_id,
                "project_id": project_id,
                "page": chunk.get("page", 1),
                "text": chunk["text"][:200],  # Store preview
                "char_count": chunk.get("char_count", 0),
            }
            if metadata:
                meta.update(metadata)
            metadatas.append(meta)
        
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        
        return ids
    except Exception as e:
        print(f"Error storing chunks: {e}")
        return []

def semantic_search(query: str, project_id: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
    """Perform semantic search against stored chunks. Falls back to text_search if ML not ready."""
    global _ml_model_loaded

    # If model not yet loaded, always use text search (non-blocking)
    if not _ml_model_loaded:
        return text_search(query, project_id, top_k)

    try:
        model = get_embedding_model()
        _ml_model_loaded = True
        collection = get_vector_collection()
        if not collection:
            return text_search(query, project_id, top_k)

        query_embedding = model.encode([query]).tolist()[0]
        where_filter = {"project_id": project_id} if project_id else None

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter
            )

            formatted_results = []
            if results and results.get('documents'):
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        "text": doc,
                        "page": results['metadatas'][0][i].get('page', 1),
                        "source_id": results['metadatas'][0][i].get('source_id'),
                        "distance": results.get('distances', [[]])[0][i] if results.get('distances') else 0
                    })

            return formatted_results
        except Exception as e:
            print(f"Search error: {e}")
            return text_search(query, project_id, top_k)
    except Exception as e:
        print(f"Semantic search error: {e}")
        return text_search(query, project_id, top_k)

def text_search(query: str, project_id: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
    """Fallback text-based search when ML is not available"""
    results = []
    query_words = query.lower().split()
    
    try:
        import json
        if os.path.exists('data/state.json'):
            with open('data/state.json', 'r') as f:
                state_data = json.load(f)
            
            for source in state_data.get('projectSources', []):
                if project_id and source.get('projectId') != project_id:
                    continue
                
                source_text = source.get('name', '').lower()
                match_count = sum(1 for word in query_words if word in source_text)
                if match_count > 0:
                    results.append({
                        "text": f"Source: {source.get('name', 'Unknown')} - Click to view in project",
                        "page": 1,
                        "source_id": source.get('id'),
                        "distance": 1.0 - (match_count / len(query_words))
                    })
    except Exception as e:
        print(f"Text search error: {e}")
    
    return results[:top_k]

def summarize_chunk(text: str, max_length: int = 200) -> str:
    """Generate a brief summary of a text chunk"""
    sentences = re.split(r'[.!?]+', text)
    
    if len(sentences) <= 1:
        return text[:max_length]
    
    summary = sentences[0]
    for sentence in sentences[1:]:
        if len(summary) + len(sentence) + 1 <= max_length:
            summary += " " + sentence
        else:
            break
    return summary.strip()

def extract_key_concepts(text: str) -> List[str]:
    """Extract key concepts/topics from text using simple NLP"""
    # Common research stopwords
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 
                 'could', 'should', 'may', 'might', 'this', 'that', 'these', 'those',
                 'it', 'its', 'they', 'their', 'we', 'our', 'you', 'your', 'i', 'my'}
    
    # Extract noun phrases (simple approach)
    words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b|\b\w{5,}\b', text)
    
    # Filter and count
    concepts = {}
    for word in words:
        word_lower = word.lower()
        if word_lower not in stopwords and len(word) > 4:
            concepts[word_lower] = concepts.get(word_lower, 0) + 1
    
    # Sort by frequency and return top concepts
    sorted_concepts = sorted(concepts.items(), key=lambda x: x[1], reverse=True)
    return [concept for concept, count in sorted_concepts[:10]]

def analyze_document_structure(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze the structure and content of a document"""
    total_chars = sum(c.get("char_count", 0) for c in chunks)
    total_pages = max(c.get("page", 1) for c in chunks) if chunks else 0
    
    # Combine all text for analysis
    all_text = " ".join(c["text"] for c in chunks)
    
    # Extract key concepts
    key_concepts = extract_key_concepts(all_text)
    
    # Detect sections (simple heuristic)
    sections = detect_sections(all_text)
    
    return {
        "total_chunks": len(chunks),
        "total_pages": total_pages,
        "total_chars": total_chars,
        "key_concepts": key_concepts,
        "sections": sections
    }

def detect_sections(text: str) -> List[Dict[str, str]]:
    """Detect document sections based on common patterns"""
    section_patterns = [
        r'(?i)(?:^|\n)\s*(abstract|introduction|background|methods?|results?|discussion|conclusion|references?|acknowledgments?)\s*(?:\n|$)',
        r'(?i)(?:^|\n)\s*(\d+\.?\s+(?:[A-Z][^.!?\n]+))\s*(?:\n|$)',
        r'(?i)(?:^|\n)\s*([A-Z][A-Z\s]{5,})\s*(?:\n|$)',
    ]
    
    sections = []
    for pattern in section_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            sections.append({
                "title": match.group(1).strip() if match.lastindex else "Section",
                "position": match.start()
            })
    
    return sections[:20]  # Limit to 20 sections

def compute_similarity(text1: str, text2: str) -> float:
    """Compute cosine similarity between two texts"""
    if not check_ml_available():
        return 0.0
    
    try:
        model = get_embedding_model()
        emb1 = model.encode([text1])[0]
        emb2 = model.encode([text2])[0]
        
        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = sum(a * a for a in emb1) ** 0.5
        norm2 = sum(a * a for a in emb2) ** 0.5
        
        return dot_product / (norm1 * norm2) if norm1 * norm2 > 0 else 0
    except:
        return 0.0

def find_related_chunks(source_id: str, chunk_text: str, threshold: float = 0.7) -> List[Dict[str, Any]]:
    """Find related chunks from other sources based on similarity"""
    if not check_ml_available():
        return []
    
    collection = get_vector_collection()
    if not collection:
        return []
    
    try:
        model = get_embedding_model()
        
        query_embedding = model.encode([chunk_text]).tolist()[0]
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            where={"source_id": {"$ne": source_id}}  # Different source
        )
        
        related = []
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents'][0]):
                distance = results.get('distances', [[]])[0][i] if results.get('distances') else 1
                similarity = 1 - distance  # Convert distance to similarity
                
                if similarity >= threshold:
                    related.append({
                        "text": doc,
                        "source_id": results['metadatas'][0][i].get('source_id'),
                        "page": results['metadatas'][0][i].get('page', 1),
                        "similarity": similarity
                    })
        
        return related
    except:
        return []