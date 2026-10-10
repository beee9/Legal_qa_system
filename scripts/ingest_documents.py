"""将 Markdown、PDF、TXT、DOCX 文档切分并写入 Milvus。"""
import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from base.config import Config
from rag_qa.core.document_loader import SUPPORTED_DOCUMENT_EXTENSIONS, process_documents


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="构建多格式离线知识库")
    parser.add_argument("directory", type=Path, help="待导入文档的目录，会递归扫描")
    parser.add_argument("--source", help="检索时使用的来源标签，默认使用目录名")
    parser.add_argument("--collection", help="Milvus 集合名，默认读取 config.ini")
    parser.add_argument("--batch-size", type=int, default=32, help="向量写入批大小")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="写入前仅删除本次成功加载文件的旧切块，用于更新文档",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="删除并重建目标集合，集合内原有数据会丢失",
    )
    parser.epilog = "支持格式: " + ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.batch_size <= 0:
        raise ValueError("--batch-size 必须大于 0")

    chunks = process_documents(args.directory, source=args.source)
    if not chunks:
        print("未生成可入库的文档块，请检查目录、文件格式和日志。")
        return 1

    from pymilvus import MilvusClient
    from rag_qa.core.vector_store import VectorStore, ensure_collection

    config = Config()
    collection_name = args.collection or config.MILVUS_COLLECTION_NAME
    client = MilvusClient(
        uri=f"http://{config.MILVUS_HOST}:{config.MILVUS_PORT}",
        db_name=config.MILVUS_DATABASE_NAME,
    )
    created = ensure_collection(client, collection_name, recreate=args.recreate)
    vector_store = VectorStore(collection_name=collection_name)

    document_ids = {chunk.metadata["document_id"] for chunk in chunks}
    if args.replace:
        vector_store.delete_documents(document_ids)

    inserted = vector_store.add_documents(chunks, batch_size=args.batch_size)
    action = "创建" if created else "使用"
    print(
        f"{action}集合 {collection_name}，处理 {len(document_ids)} 份文件，"
        f"写入 {inserted} 个文档块。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
