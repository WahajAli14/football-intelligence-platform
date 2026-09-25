"""Document Loader - Load documents from various sources (text, PDF, raw, football docs)"""
import subprocess
import shutil
from unstructured.partition.pdf import partition_pdf
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.data.football_docs import football_documents

__all__ = ["DocumentLoader"]


class DocumentLoader:
    """
    Load documents from various sources.
    
    Supports:
    - Text files (.txt)
    - PDFs (.pdf) - requires pypdf or unstructured
    - Raw text strings
    - Existing football documents
    """

    @staticmethod
    def load_text_file(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load a single text file.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Dict with id, title, text, source, type
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            return {
                "id": Path(file_path).stem,
                "title": Path(file_path).stem.replace("_", " ").title(),
                "text": content,
                "source": file_path,
                "type": "text"
            }
        except FileNotFoundError:
            print(f"⚠️ File not found: {file_path}")
            return None
        except Exception as e:
            print(f"⚠️ Error loading {file_path}: {e}")
            return None
        
    @staticmethod
    def load_pdf(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load a PDF and exract text.
        """
        try:
            text = ""
            if shutil.which("pdftotext"):
                try:
                    result = subprocess.run(
                        [
                            "pdftotext",
                            "-enc",
                            "UTF-8",
                            file_path,
                            "-"
                        ],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    text = result.stdout.replace("\f", "\n\n")

                except subprocess.CalledProcessError as e:
                    print(f"⚠️ Error extracting text from PDF {file_path} using pdftotext: {e}")

            if not text.strip():
                try:
                    elements = partition_pdf(file_path)
                    text = "\n\n".join([str(element) for element in elements])
                except ImportError:
                    print("⚠️ Install pypdf or unstructured: pip install pypdf unstructured")

            if not text.strip():
                print(f"⚠️ No text extracted from PDF: {file_path}")
                return None

            return {
                "id": Path(file_path).stem,
                "title": Path(file_path).stem.replace("_", " ").title(),
                "text": text,
                "source": file_path,
                "type": "pdf"
            }
        except Exception as e:
            print(f"⚠️ Error loading PDF {file_path}: {e}")
            return None
        
    @staticmethod
    def load_text_files(directory: str, recursive: bool = False) -> List[Dict[str, Any]]:
        """
        Load all text files in a directory.
        
        Args:
            directory: Path to the directory
            recursive: Whether to search subdirectories
            
        Returns:
            List of dicts with id, title, text, source, type
        """
        documents = []
        pattern = "**/*.txt" if recursive else "*.txt"
        
        for file in Path(directory).glob(pattern):
            doc = DocumentLoader.load_text_file(str(file))
            if doc:
                documents.append(doc)
        
        return documents
    
    @staticmethod
    def load_pdfs(directory: str, recursive: bool = False) -> List[Dict[str, Any]]:
        """
        Load all PDFs in a directory.
        
        Args:
            directory: Path to the directory
            recursive: Whether to search subdirectories
            
        Returns:
            List of dicts with id, title, text, source, type
        """
        documents = []
        pattern = "**/*.pdf" if recursive else "*.pdf"
        
        for file in Path(directory).glob(pattern):
            doc = DocumentLoader.load_pdf(str(file))
            if doc:
                documents.append(doc)
        
        return documents

    @staticmethod
    def load_from_directory(
        directory: str,
        extensions: List[str] = [".txt"],
        recursive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Load all files with specified extensions from a directory.
        
        Args:
            directory: Directory path
            extensions: List of extensions (e.g., [".txt", ".pdf"])
            recursive: Include subdirectories
            
        Returns:
            List of document dicts
        """

        documents = []
        pattern = "**/*" if recursive else "*"

        
        for file in Path(directory).glob(pattern):
            if file.suffix.lower() in extensions:
                if file.suffix.lower() == ".txt":
                    doc = DocumentLoader.load_text_file(str(file))
                elif file.suffix.lower() == ".pdf":
                    doc = DocumentLoader.load_pdf(str(file))
                else:
                    continue
                
                if doc:
                    documents.append(doc)
        
        return documents
    
    @staticmethod
    def from_raw_text(text:str, doc_id: str = "doc_1", title: str = "Document") -> Dict[str, Any]:
        """
        Create a document from raw text.

        Args:
            text: Raw text string
            doc_id: Document ID
            title: Document title

        Returns:
            Document dict
        """

        return {
            "id": doc_id,
            "title": title,
            "text": text,
            "source": "raw_text",
            "type": "raw"
        }

    @staticmethod
    def from_football_docs()-> List[Dict[str, Any]]:
        """
        Load documents from the football_docs dataset.

        Returns:
            List of document dicts
        """
        try:
            docs = [doc.copy() for doc in football_documents]

            for doc in docs:
                doc["source"] = "football_docs.py"

            return docs
        except Exception as e:
            print(f"Error loading football documents: {e}")
            return []


if __name__ == "__main__":
    # Test: Load football documents
    print("=" * 50)
    print("📚 Testing DocumentLoader")
    print("=" * 50)
    
    docs = DocumentLoader.from_football_docs()
    print(f"\nLoaded {len(docs)} documents:")
    for doc in docs:
        print(f"  - {doc['id']}: {doc['title']} ({len(doc['text'])} chars)")
        print(f"    Source: {doc.get('source', 'unknown')}")
        print(f"    Type: {doc.get('type', 'unknown')}")
    
    print("\n" + "=" * 50)
    print("✅ DocumentLoader test complete")
