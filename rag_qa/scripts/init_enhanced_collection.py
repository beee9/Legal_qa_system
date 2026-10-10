"""
更新或创建支持完整元数据的Milvus集合
用于替换旧的legal_rag集合，增加法律条文元数据字段
"""
from pymilvus import MilvusClient, DataType, CollectionSchema, FieldSchema
import sys, os

current_dir = os.path.dirname(os.path.abspath(__file__))
rag_qa_path = os.path.dirname(current_dir)
sys.path.insert(0, rag_qa_path)
project_root = os.path.dirname(rag_qa_path)
sys.path.insert(0, project_root)

from base import Config, logger

conf = Config()


def create_enhanced_collection(collection_name="legal_rag_enhanced"):
    """创建增强版法律RAG集合，包含完整元数据"""
    
    client = MilvusClient(uri=f"http://{conf.MILVUS_HOST}:{conf.MILVUS_PORT}")
    
    # 如果集合已存在，先删除（谨慎操作）
    if client.has_collection(collection_name):
        logger.warning(f"集合 {collection_name} 已存在，将删除重建")
        client.drop_collection(collection_name)
    
    # 定义Schema
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=128, is_primary=True),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
        FieldSchema(name="subject", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
        
        # 法律元数据字段
        FieldSchema(name="law_name", dtype=DataType.VARCHAR, max_length=200),
        FieldSchema(name="law_short_name", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="article_no", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="law_level", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="version", dtype=DataType.VARCHAR, max_length=20),
        FieldSchema(name="status", dtype=DataType.VARCHAR, max_length=20),
        FieldSchema(name="effective_date", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="expiry_date", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="region", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="chapter", dtype=DataType.VARCHAR, max_length=200),
        FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=200),
        FieldSchema(name="source_url", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="parent_content", dtype=DataType.VARCHAR, max_length=8192),
    ]
    
    schema = CollectionSchema(
        fields=fields,
        description="增强版法律RAG集合，包含完整法律条文元数据"
    )
    
    # 创建集合
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="dense_vector",
        index_type="IVF_FLAT",
        metric_type="IP",
        params={"nlist": 128}
    )
    
    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params
    )
    
    logger.info(f"成功创建增强版集合: {collection_name}")
    
    # 创建标量索引以加速过滤
    client.create_index(
        collection_name=collection_name,
        index_params={
            "index_type": "INVERTED",
            "field_name": "law_short_name"
        }
    )
    
    client.create_index(
        collection_name=collection_name,
        index_params={
            "index_type": "INVERTED",
            "field_name": "article_no"
        }
    )
    
    client.create_index(
        collection_name=collection_name,
        index_params={
            "index_type": "INVERTED",
            "field_name": "status"
        }
    )
    
    logger.info(f"已创建标量索引")
    
    return client


def migrate_old_collection(old_collection="legal_rag", new_collection="legal_rag_enhanced"):
    """从旧集合迁移数据到新集合"""
    client = MilvusClient(uri=f"http://{conf.MILVUS_HOST}:{conf.MILVUS_PORT}")
    
    if not client.has_collection(old_collection):
        logger.warning(f"旧集合 {old_collection} 不存在，跳过迁移")
        return
    
    logger.info(f"开始从 {old_collection} 迁移数据到 {new_collection}")
    
    # 查询所有数据
    results = client.query(
        collection_name=old_collection,
        filter="",
        output_fields=["id", "text", "subject", "dense_vector"],
        limit=10000
    )
    
    logger.info(f"从旧集合获取 {len(results)} 条数据")
    
    # 转换为新格式（补充空元数据）
    new_data = []
    for item in results:
        new_data.append({
            "id": item["id"],
            "text": item["text"],
            "subject": item["subject"],
            "dense_vector": item["dense_vector"],
            # 补充空元数据
            "law_name": "",
            "law_short_name": "",
            "article_no": "",
            "law_level": "",
            "version": "v1",
            "status": "现行有效",
            "effective_date": "",
            "expiry_date": "",
            "region": "全国",
            "chapter": "",
            "section": "",
            "source_url": "",
            "parent_content": item["text"],
        })
    
    # 插入新集合
    if new_data:
        client.insert(collection_name=new_collection, data=new_data)
        logger.info(f"成功迁移 {len(new_data)} 条数据到 {new_collection}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="创建或迁移增强版Milvus集合")
    parser.add_argument("--create", action="store_true", help="创建新集合")
    parser.add_argument("--migrate", action="store_true", help="从旧集合迁移数据")
    parser.add_argument("--collection", type=str, default="legal_rag_enhanced", help="新集合名称")
    parser.add_argument("--old-collection", type=str, default="legal_rag", help="旧集合名称")
    
    args = parser.parse_args()
    
    if args.create:
        create_enhanced_collection(args.collection)
    
    if args.migrate:
        migrate_old_collection(args.old_collection, args.collection)
    
    if not args.create and not args.migrate:
        print("请使用 --create 创建新集合，或 --migrate 迁移旧数据")
        print("示例：")
        print("  python init_enhanced_collection.py --create")
        print("  python init_enhanced_collection.py --create --migrate")
