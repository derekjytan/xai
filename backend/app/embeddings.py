"""Local embedding service using hash-based embeddings for semantic search.

This provides a fallback when external embedding APIs are not available.
Uses deterministic hashing to create fixed-dimension vector representations.
"""

import hashlib
import numpy as np
from typing import List, Optional


class LocalEmbedder:
    """Hash-based embedding generator for semantic search.
    
    Uses deterministic hashing to create consistent fixed-dimension vectors
    for any text input, regardless of vocabulary.
    """
    
    def __init__(self, embedding_dim: int = 128):
        self.embedding_dim = embedding_dim
    
    def get_embedding(self, text: str) -> List[float]:
        """Generate a deterministic hash-based embedding for text."""
        if not text or not text.strip():
            return [0.0] * self.embedding_dim
        
        # Normalize text
        text = text.lower().strip()
        
        # Generate embedding using multiple hash functions
        embedding = []
        
        # Use word-level features
        words = text.split()
        word_hashes = [self._hash_string(w) for w in words]
        
        # Use character n-gram features
        ngrams = self._get_ngrams(text, 3)
        ngram_hashes = [self._hash_string(ng) for ng in ngrams]
        
        # Combine features into fixed-dimension vector
        for i in range(self.embedding_dim):
            # Mix word and ngram features
            word_val = sum(self._hash_combo(w, i) for w in words) if words else 0
            ngram_val = sum(self._hash_combo(ng, i) for ng in ngrams) if ngrams else 0
            
            # Normalize and combine
            combined = (word_val + ngram_val * 0.5) / (len(words) + len(ngrams) * 0.5 + 1)
            embedding.append(combined)
        
        # L2 normalize
        norm = np.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    def _hash_string(self, s: str) -> int:
        """Hash a string to an integer."""
        return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)
    
    def _hash_combo(self, s: str, index: int) -> float:
        """Create a position-dependent hash value."""
        h = hashlib.md5(f"{s}_{index}".encode()).hexdigest()
        return (int(h[:8], 16) / (2**32)) - 0.5  # Normalize to [-0.5, 0.5]
    
    def _get_ngrams(self, text: str, n: int = 3) -> List[str]:
        """Extract character n-grams from text."""
        return [text[i:i+n] for i in range(max(0, len(text) - n + 1))]
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        return [self.get_embedding(text) for text in texts]
    
    def similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts."""
        emb1 = np.array(self.get_embedding(text1))
        emb2 = np.array(self.get_embedding(text2))
        
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


# Singleton instance
_embedder: Optional[LocalEmbedder] = None


def get_local_embedder() -> LocalEmbedder:
    """Get or create local embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = LocalEmbedder()
    return _embedder
