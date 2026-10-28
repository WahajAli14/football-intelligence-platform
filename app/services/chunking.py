"""Document Chunking Service - Split documents into smaller, meaningful chunks for processing and analysis."""

import re
from collections import Counter
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

__all__ = ["DocumentChunker", "Chunk", "clean_and_merge_chunks"]

_WORD_RE = re.compile(r"\w+")
_STANDALONE_NUMBER_RE = re.compile(r"\s*\d+\s*")
DEFAULT_MIN_MERGE_TOKENS = 8
DEFAULT_REPEAT_THRESHOLD = 3
MAX_BOILERPLATE_TOKENS = 6


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
            end_offset = -1
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
                current_chunk = self._take_overlap_sentences(current_chunk)
                current_length = sum(len(s) for s in current_chunk)
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

    def _take_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """
        Select complete trailing sentences to carry into the next chunk,
        targeting self.overlap characters without splitting a sentence.
        """
        overlap_sentences: List[str] = []
        overlap_length = 0
        for sentence in reversed(sentences):
            if overlap_length >= self.overlap:
                break
            overlap_sentences.insert(0, sentence)
            overlap_length += len(sentence)
        return overlap_sentences

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


def _token_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _is_standalone_number(text: str) -> bool:
    return bool(_STANDALONE_NUMBER_RE.fullmatch(text))


def clean_and_merge_chunks(
    chunk_dicts: List[Dict[str, Any]],
    min_tokens: int = DEFAULT_MIN_MERGE_TOKENS,
    repeat_threshold: int = DEFAULT_REPEAT_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    Post-process chunk_documents()'s output to remove extraction artifacts
    (standalone page numbers, repeated headers/footers) and merge remaining
    short fragments (headings, captions) into the content next to them,
    rather than leaving them as standalone retrievable units.

    Returns new chunk dictionaries without modifying the input chunks.
    Merging changes boundaries and IDs, preserves parent_id, and can exceed
    the original chunk_size. Use matching gold labels for cleaned chunks.
    This is intended for paragraph/PDF fragments; overlapping chunks from
    other strategies can repeat text when joined because no overlap is removed.

    Found necessary because PDF text extraction turns every page number,
    heading, and image caption into its own "paragraph" purely because it's
    visually isolated by blank lines - in the UEFA report corpus, 72% of
    chunks ended up with 5 or fewer content tokens before this ran. BM25 is
    especially vulnerable to this (a 1-word chunk that matches a query term
    gets the maximum possible term-density score, beating a real paragraph
    that mentions the same term once), but it's bad for dense retrieval too
    - a one-word chunk can only ever add noise. See EVAL_FINDINGS.md.

    min_tokens is a MERGE TRIGGER, not a deletion rule: a short-but-real
    sentence ("Arsenal recorded 14 high turnovers") gets merged with its
    neighbor, never dropped, because merging can only add surrounding
    context, not lose the sentence itself. Only two things are ever
    actually discarded:
      - a chunk that is nothing but a number (a lone page number)
      - a chunk whose exact text repeats >= repeat_threshold times across
        the whole corpus AND is short (<= 6 tokens) - running headers/
        footers/section banners, not real content occurring coincidentally.
    """
    if min_tokens <= 0:
        raise ValueError("min_tokens must be positive")
    if repeat_threshold < 2:
        raise ValueError("repeat_threshold must be at least 2")

    # Treat standalone numeric chunks as page-number artifacts.
    chunk_dicts = [c for c in chunk_dicts if not _is_standalone_number(c["text"])]

    # Repeated short boilerplate (e.g. a running section header appearing
    # on every page) - identified by exact repetition, not length alone,
    # so a short sentence that's merely similar to another isn't caught.
    normalized = [c["text"].strip().lower() for c in chunk_dicts]
    counts = Counter(normalized)
    chunk_dicts = [
        c for c, norm in zip(chunk_dicts, normalized)
        if not (
            _token_count(c["text"]) <= MAX_BOILERPLATE_TOKENS
            and counts[norm] >= repeat_threshold
        )
    ]

    by_parent: Dict[str, List[Dict[str, Any]]] = {}
    for c in chunk_dicts:
        by_parent.setdefault(c["parent_id"], []).append(c)

    merged_docs = []
    for parent_id, doc_chunks in by_parent.items():
        doc_chunks.sort(key=lambda c: c["chunk_index"])
        merged = []
        buffer_texts: List[str] = []
        buffer_start = None

        for c in doc_chunks:
            if buffer_start is None:
                buffer_start = c["char_start"]
            buffer_texts.append(c["text"])

            if _token_count("\n".join(buffer_texts)) >= min_tokens:
                merged.append({
                    **c,
                    "text": "\n".join(buffer_texts),
                    "char_start": buffer_start,
                    "char_end": c["char_end"],
                })
                buffer_texts = []
                buffer_start = None

        if buffer_texts:
            # Never reached min_tokens before the document ended - attach to
            # the last real merged chunk rather than dropping it; if this is
            # the only content in the whole document, keep it as-is.
            leftover_text = "\n".join(buffer_texts)
            if merged:
                merged[-1]["text"] = merged[-1]["text"] + "\n" + leftover_text
                merged[-1]["char_end"] = doc_chunks[-1]["char_end"]
            else:
                merged.append({**doc_chunks[-1], "text": leftover_text, "char_start": buffer_start})

        for i, c in enumerate(merged):
            c["chunk_index"] = i
            c["id"] = f"{parent_id}_chunk{i}"

        merged_docs.extend(merged)

    return merged_docs


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
