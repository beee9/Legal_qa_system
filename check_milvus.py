from pymilvus import connections, Collection

connections.connect(host="localhost", port="19530")

collection_name = "legal_rag"
try:
    collection = Collection(collection_name)
    print(f"集合名称: {collection_name}")
    print(f"\n字段信息:")
    schema = collection.schema
    for field in schema.fields:
        print(f"  - {field.name}: {field.dtype} (主键: {field.is_primary})")
    
    print(f"\n总数据量: {collection.num_entities}")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
