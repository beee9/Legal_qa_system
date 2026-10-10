import hashlib
import os
from datetime import datetime
from pathlib import Path

from base.config import Config
from base.logger import logger


conf = Config()

SUPPORTED_DOCUMENT_EXTENSIONS = frozenset({
    ".txt", ".md", ".markdown", ".pdf", ".docx", ".ppt", ".pptx", ".jpg", ".png",
})


def build_document_id(source, relative_path):
    normalized_path = relative_path.replace(os.sep, "/")
    identity = f"{source}\0{normalized_path}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def build_chunk_id(document_id, parent_index, child_index):
    identity = f"{document_id}\0{parent_index}\0{child_index}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _get_document_loaders():
    try:
        from langchain_community.document_loaders import TextLoader
        from langchain_community.document_loaders.markdown import UnstructuredMarkdownLoader
        from rag_qa.edu_document_loaders import OCRDOCLoader, OCRIMGLoader, OCRPDFLoader, OCRPPTLoader
    except ImportError as exc:
        raise RuntimeError(
            "文档导入依赖缺失，请先执行: pip install -r config\\requirements.txt"
        ) from exc

    return {
        ".txt": TextLoader,
        ".pdf": OCRPDFLoader,
        ".docx": OCRDOCLoader,
        ".ppt": OCRPPTLoader,
        ".pptx": OCRPPTLoader,
        ".jpg": OCRIMGLoader,
        ".png": OCRIMGLoader,
        ".md": UnstructuredMarkdownLoader,
        ".markdown": UnstructuredMarkdownLoader,
    }


def load_documents_from_directory(directory_path, source=None):
    base_path = Path(directory_path).resolve()
    if not base_path.is_dir():
        raise FileNotFoundError(f"知识库目录不存在: {base_path}")

    source = source or base_path.name.replace("_data", "")
    document_loaders = _get_document_loaders()
    documents = []

    for root, directories, files in os.walk(base_path):
        directories.sort()
        for filename in sorted(files):
            file_path = Path(root) / filename
            extension = file_path.suffix.lower()
            loader_class = document_loaders.get(extension)
            if loader_class is None:
                logger.warning("不支持的文件类型: %s", file_path)
                continue

            try:
                if extension == ".txt":
                    loader = loader_class(str(file_path), encoding="utf-8", autodetect_encoding=True)
                else:
                    loader = loader_class(str(file_path))

                relative_path = file_path.relative_to(base_path).as_posix()
                document_id = build_document_id(source, relative_path)
                timestamp = datetime.now().isoformat()
                loaded_docs = loader.load()
                for document in loaded_docs:
                    document.metadata.update({
                        "source": source,
                        "file_path": str(file_path),
                        "file_name": filename,
                        "file_type": extension.lstrip("."),
                        "document_id": document_id,
                        "timestamp": timestamp,
                    })
                documents.extend(loaded_docs)
                logger.info("成功加载文件: %s", file_path)
            except Exception as exc:
                logger.error("加载文件 %s 失败: %s", file_path, exc)

    return documents


def process_documents(
    directory_path,
    parent_chunk_size=conf.PARENT_CHUNK_SIZE,
    child_chunk_size=conf.CHILD_CHUNK_SIZE,
    chunk_overlap=conf.CHUNK_OVERLAP,
    source=None,
):
    try:
        from langchain_text_splitters import MarkdownTextSplitter
        from rag_qa.edu_text_spliter import ChineseRecursiveTextSplitter
    except ImportError as exc:
        raise RuntimeError(
            "文档切分依赖缺失，请先执行: pip install -r config\\requirements.txt"
        ) from exc

    documents = load_documents_from_directory(directory_path, source=source)
    logger.info("加载的文档数量: %s", len(documents))

    parent_splitter = ChineseRecursiveTextSplitter(
        chunk_size=parent_chunk_size,
        chunk_overlap=chunk_overlap,
    )
    child_splitter = ChineseRecursiveTextSplitter(
        chunk_size=child_chunk_size,
        chunk_overlap=chunk_overlap,
    )
    markdown_parent_splitter = MarkdownTextSplitter(
        chunk_size=parent_chunk_size,
        chunk_overlap=chunk_overlap,
    )
    markdown_child_splitter = MarkdownTextSplitter(
        chunk_size=child_chunk_size,
        chunk_overlap=chunk_overlap,
    )

    child_chunks = []
    for document in documents:
        file_type = document.metadata.get("file_type", "")
        is_markdown = file_type in {"md", "markdown"}
        parent_splitter_to_use = markdown_parent_splitter if is_markdown else parent_splitter
        child_splitter_to_use = markdown_child_splitter if is_markdown else child_splitter
        document_id = document.metadata["document_id"]

        parent_docs = parent_splitter_to_use.split_documents([document])
        for parent_index, parent_doc in enumerate(parent_docs):
            parent_id = f"{document_id}:parent:{parent_index}"
            parent_doc.metadata["parent_id"] = parent_id
            parent_doc.metadata["parent_content"] = parent_doc.page_content

            sub_chunks = child_splitter_to_use.split_documents([parent_doc])
            for child_index, sub_chunk in enumerate(sub_chunks):
                sub_chunk.metadata["parent_id"] = parent_id
                sub_chunk.metadata["parent_content"] = parent_doc.page_content
                sub_chunk.metadata["id"] = build_chunk_id(document_id, parent_index, child_index)
                child_chunks.append(sub_chunk)

    logger.info("子块数量: %s", len(child_chunks))
    return child_chunks
