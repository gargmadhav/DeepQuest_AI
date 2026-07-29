import os
import json
import sqlite3
import re
import math
from typing import List, Dict, Any, Tuple

class VectorMemory:
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database for storing memories."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                report TEXT NOT NULL,
                embedding TEXT DEFAULT '', -- Kept for DB schema backward compatibility
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def _tokenize(self, text: str) -> List[str]:
        """Convert text into lowercase words/tokens."""
        return re.findall(r'\w+', text.lower())

    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """Compute Term Frequency (TF) weights for tokens."""
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1.0
        
        # Normalize frequencies by total tokens to prevent bias for longer text
        length = len(tokens)
        if length > 0:
            for t in tf:
                tf[t] = tf[t] / length
        return tf

    def _cosine_similarity(self, tf1: Dict[str, float], tf2: Dict[str, float]) -> float:
        """Calculate cosine similarity between two term frequency dictionaries."""
        all_words = set(tf1.keys()).union(set(tf2.keys()))
        
        dot_product = sum(tf1.get(w, 0.0) * tf2.get(w, 0.0) for w in all_words)
        
        mag1 = math.sqrt(sum(v * v for v in tf1.values()))
        mag2 = math.sqrt(sum(v * v for v in tf2.values()))
        
        if mag1 == 0.0 or mag2 == 0.0:
            return 0.0
        return dot_product / (mag1 * mag2)

    def add_memory(self, query: str, report: str):
        """Save the query and its report into memory."""
        print(f"[Memory System] Adding task to memory database: '{query[:50]}...'")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO memories (query, report, embedding) VALUES (?, ?, ?)",
            (query, report, "")
        )
        conn.commit()
        conn.close()

    def search_memory(self, query: str, limit: int = 3, threshold: float = 0.15) -> List[Dict[str, Any]]:
        """
        Search memories by computing cosine similarity of TF-IDF vectors locally.
        Works offline, fast, and does not require an API key.
        """
        print(f"[Memory System] Local similarity matching for query: '{query[:50]}...'")
        query_tokens = self._tokenize(query)
        query_tf = self._compute_tf(query_tokens)
        
        if not query_tf:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, query, report, created_at FROM memories")
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            mem_id, mem_query, mem_report, created_at = row
            try:
                mem_tokens = self._tokenize(mem_query)
                mem_tf = self._compute_tf(mem_tokens)
                
                # Calculate term-frequency text similarity
                score = self._cosine_similarity(query_tf, mem_tf)
                
                if score >= threshold:
                    results.append({
                        "id": mem_id,
                        "query": mem_query,
                        "report": mem_report,
                        "score": score,
                        "created_at": created_at
                    })
            except Exception as e:
                print(f"[Memory Warning] Failed to compute similarity for memory {mem_id}: {e}")
                
        # Sort by similarity score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
