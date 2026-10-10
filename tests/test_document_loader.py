import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rag_qa.core.document_loader import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
    build_chunk_id,
    build_document_id,
    load_documents_from_directory,
)
from rag_qa.core.vector_store import REQUIRED_COLLECTION_FIELDS, validate_collection_schema


class FakeDocument:
    def __init__(self, page_content):
        self.page_content = page_content
        self.metadata = {}


class FakeTextLoader:
    def __init__(self, file_path, **_kwargs):
        self.file_path = file_path

    def load(self):
        return [FakeDocument(Path(self.file_path).read_text(encoding="utf-8"))]


class DocumentLoaderTests(unittest.TestCase):
    def test_required_formats_are_supported(self):
        self.assertTrue({".md", ".pdf", ".txt", ".docx"}.issubset(SUPPORTED_DOCUMENT_EXTENSIONS))

    def test_document_id_is_stable_for_a_relative_path(self):
        first = build_document_id("legal", "contracts/guide.md")
        second = build_document_id("legal", "contracts/guide.md")
        self.assertEqual(first, second)

    def test_chunk_ids_do_not_collide_within_a_document(self):
        document_id = build_document_id("legal", "contracts/guide.md")
        self.assertNotEqual(
            build_chunk_id(document_id, 0, 0),
            build_chunk_id(document_id, 0, 1),
        )

    def test_directory_load_preserves_file_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "guide.txt"
            file_path.write_text("合同内容", encoding="utf-8")
            with patch(
                "rag_qa.core.document_loader._get_document_loaders",
                return_value={".txt": FakeTextLoader},
            ):
                documents = load_documents_from_directory(directory, source="legal")

        self.assertEqual(len(documents), 1)
        metadata = documents[0].metadata
        self.assertEqual(metadata["source"], "legal")
        self.assertEqual(metadata["file_name"], "guide.txt")
        self.assertEqual(metadata["file_type"], "txt")
        self.assertEqual(metadata["document_id"], build_document_id("legal", "guide.txt"))

    def test_schema_validation_reports_missing_fields(self):
        class FakeClient:
            def describe_collection(self, _collection_name):
                return {"fields": [{"name": "id"}]}

        with self.assertRaisesRegex(RuntimeError, "schema 不兼容"):
            validate_collection_schema(FakeClient(), "legal_rag")

    def test_schema_validation_accepts_canonical_schema(self):
        class FakeClient:
            def describe_collection(self, _collection_name):
                return {"fields": [{"name": name} for name in REQUIRED_COLLECTION_FIELDS]}

        validate_collection_schema(FakeClient(), "legal_rag")


if __name__ == "__main__":
    unittest.main()
