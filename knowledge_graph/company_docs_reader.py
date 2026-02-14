"""
Company Experience Documents Reader

Reads .txt and .docx files from the company_docs/ folder and finds
relevant excerpts for RFI response generation using keyword matching.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


# Common words to ignore when matching keywords
STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
    'could', 'should', 'may', 'might', 'shall', 'can', 'this', 'that',
    'these', 'those', 'it', 'its', 'as', 'if', 'not', 'no', 'so', 'up',
    'out', 'about', 'into', 'over', 'after', 'before', 'between', 'under',
    'above', 'below', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
    'other', 'some', 'such', 'only', 'own', 'same', 'than', 'too', 'very',
    'just', 'because', 'through', 'during', 'while', 'also', 'how', 'what',
    'which', 'who', 'whom', 'where', 'when', 'why', 'your', 'our', 'their',
    'we', 'you', 'they', 'he', 'she', 'me', 'him', 'her', 'us', 'them',
    'my', 'his', 'any', 'describe', 'provide', 'please', 'information',
    'company', 'contractor', 'offeror', 'respondent', 'government', 'federal',
    'response', 'question', 'following', 'regarding', 'related', 'including',
}


class CompanyDocsReader:
    """Reads and searches company experience documents for RFI context."""

    def __init__(self, docs_dir: str = None):
        if docs_dir is None:
            # Default: look relative to the app root
            app_root = Path(__file__).parent.parent
            self.docs_dir = app_root / 'company_docs'
        else:
            self.docs_dir = Path(docs_dir)

    def load_documents(self) -> List[Dict]:
        """Load all .txt and .docx files from the docs directory."""
        documents = []

        if not self.docs_dir.exists():
            return documents

        for filepath in sorted(self.docs_dir.iterdir()):
            if filepath.name.startswith('.') or filepath.name == 'README.txt':
                continue

            content = None
            if filepath.suffix.lower() == '.txt':
                content = self._read_txt(filepath)
            elif filepath.suffix.lower() == '.docx':
                content = self._read_docx(filepath)

            if content and content.strip():
                documents.append({
                    'filename': filepath.name,
                    'content': content,
                    'chunks': self._chunk_text(content, filepath.name),
                })

        return documents

    def _read_txt(self, path: Path) -> str:
        """Read a plain text file."""
        try:
            return path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Warning: Could not read {path.name}: {e}")
            return ''

    def _read_docx(self, path: Path) -> str:
        """Read a Word document."""
        if not DOCX_AVAILABLE:
            print(f"Warning: python-docx not installed, skipping {path.name}")
            return ''
        try:
            doc = DocxDocument(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return '\n'.join(paragraphs)
        except Exception as e:
            print(f"Warning: Could not read {path.name}: {e}")
            return ''

    def _chunk_text(self, text: str, filename: str, chunk_size: int = 500) -> List[Dict]:
        """Split text into chunks of approximately chunk_size words."""
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)
            if chunk_text.strip():
                chunks.append({
                    'text': chunk_text,
                    'source': filename,
                    'word_count': len(chunk_words),
                })

        return chunks

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        # Lowercase and extract words
        words = re.findall(r'[a-z]+', text.lower())
        # Filter stop words and short words
        keywords = [w for w in words if w not in STOP_WORDS and len(w) > 2]
        return keywords

    def find_relevant_chunks(self, question: str, top_k: int = 3) -> List[Dict]:
        """Find the most relevant document chunks for a given RFI question.

        Returns a list of dicts with keys: text, source, score
        """
        documents = self.load_documents()
        if not documents:
            return []

        # Extract keywords from the question
        q_keywords = self._extract_keywords(question)
        if not q_keywords:
            return []

        q_keyword_set = set(q_keywords)
        q_keyword_counts = Counter(q_keywords)

        # Score each chunk
        scored_chunks = []
        for doc in documents:
            for chunk in doc['chunks']:
                chunk_keywords = self._extract_keywords(chunk['text'])
                chunk_keyword_set = set(chunk_keywords)

                # Count keyword overlaps (weighted by question keyword frequency)
                overlap = q_keyword_set & chunk_keyword_set
                if not overlap:
                    continue

                # Score: sum of question-keyword frequencies that appear in chunk
                score = sum(q_keyword_counts[kw] for kw in overlap)

                # Bonus for multi-word phrase matches (bigrams)
                q_lower = question.lower()
                chunk_lower = chunk['text'].lower()
                for kw in overlap:
                    # Check if keyword appears in a multi-word context match
                    if kw in q_lower and kw in chunk_lower:
                        score += 0.5

                scored_chunks.append({
                    'text': chunk['text'],
                    'source': chunk['source'],
                    'score': score,
                    'matching_keywords': list(overlap),
                })

        # Sort by score descending, return top_k
        scored_chunks.sort(key=lambda x: x['score'], reverse=True)
        return scored_chunks[:top_k]
