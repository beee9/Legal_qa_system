# -*- coding:utf-8 -*-
# 法律场景适配版 VectorStore：dense-only 检索
# 说明：规避 milvus_model BGEM3EmbeddingFunction 与 flag_embedding 的 sparse 兼容 bug，
#       改用底层 FlagEmbedding.BGEM3FlagModel 生成 dense 向量；适配 dense-only 的 legal_rag 集合。
import torch.cuda
from FlagEmbedding import BGEM3FlagModel
from pymilvus import MilvusClient, DataType
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder
import hashlib
import sys, os

# 获取当前文件所在目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
rag_qa_path = os.path.dirname(current_dir)
sys.path.insert(0, rag_qa_path)
project_root = os.path.dirname(rag_qa_path)
sys.path.insert(0, project_root)

from base import Config, logger

conf = Config()

# 模型路径指向原项目（新项目 rag_qa/models 为空，模型在原项目）
MODEL_DIR = r"E:\陈杰\Itcast_qa_system\rag_qa\models"


class VectorStore:
    def __init__(self,
                 collection_name=conf.MILVUS_COLLECTION_NAME,
                 host=conf.MILVUS_HOST,
                 port=conf.MILVUS_PORT,
                 database=conf.MILVUS_DATABASE_NAME):
        self.collection_name = collection_name
        self.host = host
        self.port = port
        self.database = database
        self.logger = logger
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.logger.info(f"使用设备：{self.device}")

        # BGE-Reranker（重排序）
        reranker_path = os.path.join(MODEL_DIR, 'bge-reranker-v2-m3')
        self.reranker = CrossEncoder(reranker_path, device=self.device)

        # BGE-M3（底层 FlagEmbedding，规避 sparse bug；只用 dense）
        m3_path = os.path.join(MODEL_DIR, 'bge-m3')
        self.embedding_model = BGEM3FlagModel(m3_path, use_fp16=(self.device == 'cuda'))
        self.dense_dim = 1024  # bge-m3 dense 维度

        # Milvus 客户端（legal_rag 集合在默认库，使用默认 db_name）
        self.client = MilvusClient(uri=f"http://{self.host}:{self.port}")
        self._load_collection()

    def _embed(self, texts):
        """生成 dense 向量 (n, 1024)"""
        out = self.embedding_model.encode(list(texts), return_dense=True, return_sparse=False)
        return out["dense_vecs"]

    def _load_collection(self):
        # legal_rag 集合已由入库脚本创建（dense-only），直接加载
        if not self.client.has_collection(self.collection_name):
            raise RuntimeError(f"集合 {self.collection_name} 不存在，请先执行 Phase1-3 入库")
        self.client.load_collection(self.collection_name)
        self.logger.info(f"已加载集合 {self.collection_name}")

    def add_documents(self, documents):
        # 适用于后续增量入库（dense-only）
        texts = [doc.page_content for doc in documents]
        dense_vecs = self._embed(texts)
        data = []
        for i, doc in enumerate(documents):
            text_hash = hashlib.md5(doc.page_content.encode('utf-8')).hexdigest()
            data.append({
                "id": text_hash,
                "subject": doc.metadata.get("source", "unknown"),
                "text": doc.page_content,
                "dense_vector": dense_vecs[i],
            })
        if data:
            self.client.upsert(collection_name=self.collection_name, data=data)
            self.logger.info(f"已插入或更新 {len(data)} 个文档")

    def hybrid_search_with_rerank(self, query, k=conf.RETRIEVAL_K, source_filter=None):
        """dense-only 检索 + rerank（保持签名兼容 rag_system 调用）"""
        # 生成查询 dense 向量
        dense_query_vector = self._embed([query])[0]

        # 过滤表达式（subject 对应原 source 字段）
        filter_expr = f"subject == '{source_filter}'" if source_filter else ""

        # 纯 dense 检索
        results = self.client.search(
            collection_name=self.collection_name,
            data=[dense_query_vector],
            anns_field="dense_vector",
            search_params={"metric_type": "IP", "params": {"nprobe": 10}},
            limit=k,
            filter=filter_expr,
            output_fields=["text", "subject"]
        )[0]

        sub_chunks = [self._doc_from_hit(hit["entity"]) for hit in results]
        parent_docs = self._get_unique_parent_docs(sub_chunks)

        if len(parent_docs) < 2:
            return parent_docs[:conf.CANDIDATE_M]
        if parent_docs:
            pairs = [[query, doc.page_content] for doc in parent_docs]
            scores = self.reranker.predict(pairs)
            ranked_parent_docs = [doc for _, doc in sorted(zip(scores, parent_docs), reverse=True)]
        else:
            ranked_parent_docs = []
        return ranked_parent_docs[:conf.CANDIDATE_M]

    def _get_unique_parent_docs(self, sub_chunks):
        parent_contents = set()
        unique_docs = []
        for chunk in sub_chunks:
            parent_content = chunk.metadata.get("parent_content", chunk.page_content)
            if parent_content and parent_content not in parent_contents:
                unique_docs.append(Document(page_content=parent_content, metadata=chunk.metadata))
                parent_contents.add(parent_content)
        return unique_docs

    def _doc_from_hit(self, hit):
        return Document(
            page_content=hit.get("text"),
            metadata={
                "parent_id": hit.get("id"),
                "parent_content": hit.get("text"),
                "source": hit.get("subject"),
                "timestamp": "",
            }
        )


if __name__ == "__main__":
    vector_store = VectorStore()
    for q in ["合同违约了一般怎么处理？", "民法典第五百零九条是什么？"]:
        results = vector_store.hybrid_search_with_rerank(q)
        print(f"\n查询: {q}")
        for doc in results:
            print(f"  [{doc.metadata.get('source')}] {doc.page_content[:40]}")
