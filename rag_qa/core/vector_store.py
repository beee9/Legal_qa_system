# -*- coding: utf-8 -*-
"""法律 RAG 的 Milvus 混合向量存储。

与 Itcast_qa_system 保持一致：BGE-M3 dense+sparse、父子块、Milvus hybrid_search、Reranker。
"""
import hashlib
import os
import sys

import torch
from milvus_model.hybrid import BGEM3EmbeddingFunction
from pymilvus import AnnSearchRequest, DataType, MilvusClient, WeightedRanker
from sentence_transformers import CrossEncoder
from langchain_core.documents import Document

current_dir = os.path.dirname(os.path.abspath(__file__))
rag_qa_path = os.path.dirname(current_dir)
project_root = os.path.dirname(rag_qa_path)
sys.path.insert(0, rag_qa_path)
sys.path.insert(0, project_root)

from base import Config, logger

conf = Config()

REQUIRED_COLLECTION_FIELDS = frozenset({
    "id", "text", "dense_vector", "sparse_vector", "parent_id", "parent_content",
    "source", "timestamp", "document_id", "file_path", "file_name", "file_type",
    "law_name", "law_short_name", "article_no", "law_level", "version", "status",
    "effective_date", "expiry_date", "region", "chapter", "section", "source_url",
})


def _collection_field_names(description):
    return {
        field["name"]
        for field in description.get("fields", [])
        if field.get("name")
    }


def validate_collection_schema(client, collection_name):
    description = client.describe_collection(collection_name)
    missing = REQUIRED_COLLECTION_FIELDS - _collection_field_names(description)
    if missing:
        fields = ", ".join(sorted(missing))
        raise RuntimeError(
            f"集合 {collection_name} 的 schema 不兼容，缺少字段: {fields}。"
            "请使用 scripts\\ingest_documents.py 的 --recreate 参数重建，"
            "或指定一个新的 --collection。"
        )


def ensure_collection(client, collection_name, dense_dim=1024, recreate=False):
    if client.has_collection(collection_name):
        if not recreate:
            validate_collection_schema(client, collection_name)
            return False
        client.drop_collection(collection_name)

    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field("id", DataType.VARCHAR, max_length=128, is_primary=True)
    schema.add_field("text", DataType.VARCHAR, max_length=8192)
    schema.add_field("dense_vector", DataType.FLOAT_VECTOR, dim=dense_dim)
    schema.add_field("sparse_vector", DataType.SPARSE_FLOAT_VECTOR)
    schema.add_field("parent_id", DataType.VARCHAR, max_length=128)
    schema.add_field("parent_content", DataType.VARCHAR, max_length=8192)
    schema.add_field("source", DataType.VARCHAR, max_length=256)
    schema.add_field("timestamp", DataType.VARCHAR, max_length=64)
    schema.add_field("document_id", DataType.VARCHAR, max_length=128)
    schema.add_field("file_path", DataType.VARCHAR, max_length=2048)
    schema.add_field("file_name", DataType.VARCHAR, max_length=512)
    schema.add_field("file_type", DataType.VARCHAR, max_length=32)
    schema.add_field("law_name", DataType.VARCHAR, max_length=200)
    schema.add_field("law_short_name", DataType.VARCHAR, max_length=100)
    schema.add_field("article_no", DataType.VARCHAR, max_length=50)
    schema.add_field("law_level", DataType.VARCHAR, max_length=50)
    schema.add_field("version", DataType.VARCHAR, max_length=20)
    schema.add_field("status", DataType.VARCHAR, max_length=20)
    schema.add_field("effective_date", DataType.VARCHAR, max_length=50)
    schema.add_field("expiry_date", DataType.VARCHAR, max_length=50)
    schema.add_field("region", DataType.VARCHAR, max_length=100)
    schema.add_field("chapter", DataType.VARCHAR, max_length=200)
    schema.add_field("section", DataType.VARCHAR, max_length=200)
    schema.add_field("source_url", DataType.VARCHAR, max_length=500)

    index_params = client.prepare_index_params()
    index_params.add_index(
        "dense_vector",
        index_type="IVF_FLAT",
        metric_type="IP",
        params={"nlist": 128},
    )
    index_params.add_index(
        "sparse_vector",
        index_type="SPARSE_INVERTED_INDEX",
        metric_type="IP",
    )
    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params,
    )
    return True


class VectorStore:
    def __init__(self, collection_name=conf.MILVUS_COLLECTION_NAME,
                 host=conf.MILVUS_HOST, port=conf.MILVUS_PORT,
                 database=conf.MILVUS_DATABASE_NAME):
        self.collection_name = collection_name
        self.host = host
        self.port = port
        self.database = database
        self.logger = logger
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.logger.info("使用设备：%s", self.device)

        model_dir = conf.models_dir
        self.embedding_function = BGEM3EmbeddingFunction(
            model_name_or_path=os.path.join(model_dir, "bge-m3"),
            use_fp16=self.device == "cuda",
            device=self.device,
        )
        self.dense_dim = self.embedding_function.dim["dense"]
        self.reranker = CrossEncoder(
            os.path.join(model_dir, "bge-reranker-v2-m3"),
            device=self.device,
        )

        self.client = MilvusClient(
            uri=f"http://{self.host}:{self.port}",
            db_name=self.database,
        )
        self._load_collection()

    def _load_collection(self):
        if not self.client.has_collection(self.collection_name):
            raise RuntimeError(
                f"集合 {self.collection_name} 不存在，请先运行 "
                "python scripts\\ingest_documents.py <知识库目录>"
            )
        validate_collection_schema(self.client, self.collection_name)
        self.client.load_collection(self.collection_name)
        self.logger.info("已加载 Milvus 混合检索集合：%s", self.collection_name)

    @staticmethod
    def _sparse_to_dict(sparse_rows, index):
        """兼容 scipy COO/CSR 以及 milvus-model 不同版本的稀疏向量格式。"""
        try:
            row = sparse_rows[index]
            if hasattr(row, "col"):
                indices, values = row.col, row.data
            else:
                indices, values = row.indices, row.data
        except Exception:
            row = sparse_rows.getrow(index)
            indices, values = row.indices, row.data
        return {int(i): float(v) for i, v in zip(indices, values)}

    def _embed(self, texts):
        return self.embedding_function(list(texts))

    def add_documents(self, documents, batch_size=32):
        """批量生成 dense/sparse 向量并 upsert 子块。"""
        total = 0
        for start in range(0, len(documents), batch_size):
            batch = documents[start:start + batch_size]
            texts = [doc.page_content for doc in batch]
            embeddings = self._embed(texts)
            rows = []

            for i, doc in enumerate(batch):
                metadata = doc.metadata or {}
                text = doc.page_content.strip()
                if not text:
                    continue
                rows.append({
                    "id": metadata.get("id") or hashlib.md5(text.encode("utf-8")).hexdigest(),
                    "text": text,
                    "dense_vector": embeddings["dense"][i],
                    "sparse_vector": self._sparse_to_dict(embeddings["sparse"], i),
                    "parent_id": metadata.get("parent_id", ""),
                    "parent_content": metadata.get("parent_content", text),
                    "source": metadata.get("source", "法律法规"),
                    "timestamp": metadata.get("timestamp", ""),
                    "document_id": metadata.get("document_id", ""),
                    "file_path": metadata.get("file_path", ""),
                    "file_name": metadata.get("file_name", ""),
                    "file_type": metadata.get("file_type", ""),
                    "law_name": metadata.get("law_name", ""),
                    "law_short_name": metadata.get("law_short_name", ""),
                    "article_no": metadata.get("article_no", ""),
                    "law_level": metadata.get("law_level", ""),
                    "version": metadata.get("version", "v1"),
                    "status": metadata.get("status", "现行有效"),
                    "effective_date": metadata.get("effective_date", ""),
                    "expiry_date": metadata.get("expiry_date", ""),
                    "region": metadata.get("region", "全国"),
                    "chapter": metadata.get("chapter", ""),
                    "section": metadata.get("section", ""),
                    "source_url": metadata.get("source_url", ""),
                })

            if rows:
                self.client.upsert(collection_name=self.collection_name, data=rows)
                total += len(rows)
                self.logger.info("Milvus 已写入 %s/%s 个子块", min(start + batch_size, len(documents)), len(documents))
        return total

    def delete_documents(self, document_ids):
        for document_id in sorted(set(document_ids)):
            self.client.delete(
                collection_name=self.collection_name,
                filter=f'document_id == "{document_id}"',
            )

    def hybrid_search_with_rerank(self, query, k=conf.RETRIEVAL_K, source_filter=None):
        embeddings = self._embed([query])
        dense = embeddings["dense"][0]
        sparse = self._sparse_to_dict(embeddings["sparse"], 0)
        expr = ""
        if source_filter:
            safe = source_filter.replace("'", "\\'")
            expr = f"source == '{safe}'"

        dense_req = AnnSearchRequest(
            data=[dense], anns_field="dense_vector",
            param={"metric_type": "IP", "params": {"nprobe": 10}},
            limit=k, expr=expr,
        )
        sparse_req = AnnSearchRequest(
            data=[sparse], anns_field="sparse_vector",
            param={"metric_type": "IP", "params": {}},
            limit=k, expr=expr,
        )
        hits = self.client.hybrid_search(
            collection_name=self.collection_name,
            reqs=[dense_req, sparse_req],
            ranker=WeightedRanker(0.7, 0.3),
            limit=k,
            output_fields=[
                "text", "parent_id", "parent_content", "source", "timestamp",
                "document_id", "file_path", "file_name", "file_type",
                "law_name", "law_short_name", "article_no", "law_level", "version",
                "status", "effective_date", "expiry_date", "region", "chapter",
                "section", "source_url",
            ],
        )[0]

        sub_chunks = [self._doc_from_hit(hit["entity"]) for hit in hits]
        parents = self._unique_parents(sub_chunks)
        if len(parents) < 2:
            return parents[:conf.CANDIDATE_M]
        scores = self.reranker.predict([[query, doc.page_content] for doc in parents])
        ranked = [doc for _, doc in sorted(zip(scores, parents), key=lambda x: x[0], reverse=True)]
        return ranked[:conf.CANDIDATE_M]

    @staticmethod
    def _unique_parents(chunks):
        seen, result = set(), []
        for chunk in chunks:
            content = chunk.metadata.get("parent_content") or chunk.page_content
            if content and content not in seen:
                result.append(Document(page_content=content, metadata=chunk.metadata))
                seen.add(content)
        return result

    @staticmethod
    def _doc_from_hit(hit):
        return Document(
            page_content=hit.get("text", ""),
            metadata={key: hit.get(key, "") for key in [
                "parent_id", "parent_content", "source", "timestamp", "law_name",
                "document_id", "file_path", "file_name", "file_type",
                "law_short_name", "article_no", "law_level", "version", "status",
                "effective_date", "expiry_date", "region", "chapter", "section",
                "source_url",
            ]},
        )
