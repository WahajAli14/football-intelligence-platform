"""Document Chunking Service - Split documents into smaller, meaningful chunks for processing and analysis."""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

__all__ = ["ChunkingService", "Chunk"]


@dataclass
class Chunk:
    """Represents a single chunk of text."""
    text: str
    metadata: Dict[str, Any]
    chunk_index: int
    char_start: int
    char_end: int


class DocumentChunker:
    """
    Split documents into smaller chunks for better retreival.

    Strategies:
    - fixed: Simplet character-based with overlap.
    - paragraph: Preserves natural document structure
    - semantic: Splits by topic shifts (sentence-based)
    """

    VALID_STRATEGIES = {"fixed", "paragraph", "semantic"}

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50,
        strategy: str = "paragraph", 
    ):
        """
        Initialize chunker

        Args:
            chunk_size: Target characters per chunk
            overlap: Characters to overlap between chunks
            strategy: "fixed", "paragraph", or "semantic"
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")
        if strategy not in self.VALID_STRATEGIES:
            raise ValueError(f"strategy must be one of {self.VALID_STRATEGIES}")
        
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.strategy = strategy

    def chunk_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Split a document into chunks based on the selected strategy.

        Args:
            text: The document text to chunk.
            metadata: Optional list of metadata dictionaries for each chunk.

        Returns:
            List of Chunk objects.
        """
        if not text or not text.strip():
            return []
        
        if metadata is None:
            metadata =  {}

        if self.strategy == "fixed":
            chunks = self._chunk_fixed(text, metadata)
        elif self.strategy == "paragraph":
            chunks = self._chunk_paragraph(text, metadata)
        elif self.strategy == "semantic":
            chunks = self._chunk_semantic(text, metadata)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")
        
        return chunks
    
    def _chunk_fixed(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """Chunk text into fixed-size segments with overlap."""
        chunks = []
        start = 0
        chunk_index = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            if end < text_length:
                search_end = min(end + 50, text_length)
                end_offset = self._find_sentence_boundary(text[end: search_end])

            if end_offset != -1:
                end += end_offset + 1

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(Chunk(
                    text=chunk_text,
                    metadata={**metadata, "chunk_index": chunk_index},
                    chunk_index=chunk_index,
                    char_start=start,
                    char_end=end
                ))
                chunk_index += 1
            
            if end >= text_length:
                break
            
            start = max(end-self.overlap, start+1)

        return chunks

    def _chunk_paragraph(self, text:str, metadata: Dict[str, Any]) -> List[Chunk]:
        """Split by pargraphs first, then chunk if too long."""
        paragraphs = text.split('\n\n')
        chunks = []
        chunk_index = 0
        char_position = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(para) <= self.chunk_size:
                chunks.append(Chunk(
                    text=para,
                    metadata={**metadata, "chunk_index": chunk_index},
                    chunk_index=chunk_index,
                    char_start=char_position,
                    char_end=char_position + len(para)
                ))
                char_position += len(para) + 2
                chunk_index += 1
            
            else:
                para_chunks = self._chunk_fixed(para, {**metadata, "chunk_index": chunk_index})
                for pc in para_chunks:
                    chunks.append(Chunk(
                        text=pc.text,
                        metadata={**metadata, "chunk_index": chunk_index},
                        chunk_index=chunk_index,
                        char_start=char_position + pc.char_start,
                        char_end=char_position + pc.char_end
                    ))
                    chunk_index += 1
                char_position += len(para) + 2

        return chunks
    
    def _chunk_semantic(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """Semantic chunking - split by sentences, group similar ones."""
        sentences = re.split(r'(?<=[.!?]) +', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return []
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        char_position = 0

        for sentence in sentences:
            sentence_len = len(sentence)
            if  current_length + sentence_len > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk).strip()
                chunks.append(Chunk(
                    text = chunk_text,
                    metadata = {**metadata, "chunk_index": chunk_index},
                    chunk_index = chunk_index,
                    char_start = char_position,
                    char_end = char_position + len(chunk_text)
                ))
                chunk_index += 1
                char_position += len(chunk_text) + 2
                current_chunk = [current_chunk[-1]] if current_chunk else []
                current_length = len(current_chunk[-1]) if current_chunk else 0
            current_chunk.append(sentence)
            current_length += sentence_len

        if current_chunk:
            chunk_text = ' '.join(current_chunk).strip()
            chunks.append(Chunk(
                text = chunk_text,
                metadata = {**metadata, "chunk_index": chunk_index},
                chunk_index = chunk_index,
                char_start = char_position,
                char_end = char_position + len(chunk_text)
            ))

        return chunks
    
    def _find_sentence_boundary(self, text: str) -> int:
        """Find the nearest sentence boundary before the given index."""
        for i, char in enumerate(text):
            if char in '.!?':
                return i
        return -1
    
    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk multiple documents and return as list of dicts.
        
        Input: [{"id": "doc1", "title": "Title", "text": "Content...", "source": "..."}]
        Output: [{"id": "doc1_chunk0", "title": "Title", "text": "Chunk...", "chunk_index": 0, "source": "..."}]
        """

        all_chunks = []
        for doc in documents:
            doc_id = doc.get('id', 'unkown')
            text = doc.get('text', '')
            if not text:
                continue

            metadata = {k: v for k, v in doc.items() if k not in ["id", "text"]}
            chunks = self.chunk_document(text, metadata)
            for chunk in chunks:
                all_chunks.append(
                    {
                        "id": f"{doc_id}_chunk{chunk.chunk_index}",
                        "title": doc.get('title', 'No Title'),
                        "text": chunk.text,
                        "chunk_index": chunk.chunk_index,
                        "char_start": chunk.char_start,
                        "char_end": chunk.char_end,
                        "parent_id": doc_id,
                        "source": metadata.get('source', 'unknown'),
                    }
                )

        return all_chunks
    

if __name__ == "__main__":
    sample_text = """
    Arsenal usually rely on structured possession, high pressing, quick wide combinations, 
    and aggressive counter-pressing after losing the ball. Their midfield control and full-back 
    positioning are important parts of their attacking buildup.
    
    Bayern Munich usually play with intensity, vertical attacks, strong wing play, and aggressive pressing. 
    Their forward line looks to attack space quickly and create chances through crosses and cutbacks.
    
    Manchester City focus on positional play, patient buildup, short passing, overloads in midfield, 
    and controlling territory. They often use high defensive lines and press immediately after losing possession.
    """
    
    print("Testing paragraph strategy:")
    chunker = DocumentChunker(chunk_size=200, overlap=30, strategy="paragraph")
    chunks = chunker.chunk_document(sample_text, {"source": "test_doc"})
    print(f"Created {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i}: {len(chunk.text)} chars - {chunk.text[:50]}...")