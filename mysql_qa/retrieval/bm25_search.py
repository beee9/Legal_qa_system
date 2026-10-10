# 导入 BM25 算法
from rank_bm25 import BM25Okapi
# 导入文本预处理
from mysql_qa.utils.preprocess import preprocess_text
# 导入日志
from base import logger


class BM25Search:
    def __init__(self, redis_client, mysql_client):
        # 初始化日志
        self.logger = logger
        # 初始化 Redis 客户端
        self.redis_client = redis_client
        # 初始化 MySQL 客户端
        self.mysql_client = mysql_client
        # 初始化 BM25 模型
        self.bm25 = None
        # 初始化问题列表
        self.questions = None
        # 初始化原始问题
        self.original_questions = None
        # 加载数据
        self._load_data()

    def _load_data(self):
        # 加载数据 redis key
        original_key = "qa_original_questions"
        tokenized_key = "qa_tokenized_questions"
        # 从 Redis 获取原始问题
        self.original_questions = self.redis_client.get_data(original_key)
        # 从 Redis 获取分词问题
        tokenized_questions = self.redis_client.get_data(tokenized_key)
        # 如果 Redis 中没有数据，从 MySQL 加载
        if not self.original_questions or not tokenized_questions:
            # 从 MySQL 获取问题
            self.original_questions = self.mysql_client.fetch_questions()
            if not self.original_questions:
                # 记录无问题警告
                self.logger.warning("未加载到问题")
                return
            # 分词问题
            tokenized_questions = [preprocess_text(q[0]) for q in self.original_questions]
            # 存储原始问题到 Redis
            self.redis_client.set_data(original_key, [(q[0]) for q in self.original_questions])
            # 存储分词问题到 Redis
            self.redis_client.set_data(tokenized_key, tokenized_questions)
        # 设置问题列表
        self.questions = tokenized_questions
        # 初始化 BM25 模型
        self.bm25 = BM25Okapi(self.questions)
        # 记录 BM25 初始化成功
        self.logger.info("BM25 模型初始化完成")

    # 高频弱信号词：出现频率高、但几乎不提供"语义相关性"信息的词。
    # BM25 常因这些词被拉高分而导致"分数高≠答对"，命中后需剔除它们再判相关性。
    # 除通用虚词外，还包含跨法律主题的通用动词/名词（认定/确定/赔偿/责任/规定等）——
    # 它们不标识具体主题，若被当作"业务实体词"，会把主题无关的问题误判为相关
    # （如「正当防卫如何认定」被「职业病如何认定」靠共同词"认定"碰中）。
    _WEAK_WORDS = set("公司 如何 怎么办 怎么 什么 请问 法律 问题 情况 相关 时候 可以 需要 "
                      "是否 还是 应该 哪些 关于 方面 规定 如下 包括 以及 或者 是的 的话 "
                      "一下 之后 现在 已经 进行 处理 解决 方式 办法 意思 "
                      "认定 确定 判断 鉴定 属于 构成 承担 适用 计算 赔偿 责任 标准 "
                      "行为 情形 条件 依据 程序 期限 金额 义务 权利 相关 事项".split())

    @staticmethod
    def _is_relevant_match(query, hit_question):
        """命中后的语义相关校验。
        原理：BM25 高分可能是靠通用词碰上的（如"公司""如何"），
        这里用 jieba 分词提取查询与命中条目中的"业务实体词"（2字以上、非弱信号词），
        用子串匹配判断二者是否真的同主题。
        返回 True=相关（可返回答案），False=疑似误命中（应降级走 RAG）。
        """
        from mysql_qa.utils.preprocess import preprocess_text
        q_ents = [t for t in preprocess_text(query)
                  if len(t) >= 2 and t not in BM25Search._WEAK_WORDS]
        h_ents = [t for t in preprocess_text(hit_question)
                  if len(t) >= 2 and t not in BM25Search._WEAK_WORDS]
        if not q_ents or not h_ents:
            # 无法提取有效实体词时，保守起见判为相关（避免误杀精确命中）
            return True

        # 子串匹配：任一查询实体词被命中实体词包含（或反之），算一次匹配
        match_count = 0
        for qe in q_ents:
            for he in h_ents:
                if qe in he or he in qe:
                    match_count += 1
                    break
        # 至少有一个实质业务词能对上，才认为语义相关
        return match_count > 0

    def search(self, query, threshold=6.0):
        # 搜索查询（法律场景：2632个问题的 softmax 分数会被稀释，改用原始 BM25 分数判断）
        # 精确/概念命中原始分通常 >=12，无关查询 <=4，取 6.0 为阈值
        if not query or not isinstance(query, str):
            # 记录无效查询
            self.logger.error("无效查询")
            # 返回 None 和 False
            return None, False
        # 检查 Redis 缓存
        cached_answer = self.redis_client.get_answer(query)
        if cached_answer:
            # 返回缓存答案
            return cached_answer, False
        try:
            # 分词查询
            query_tokens = preprocess_text(query)
            # 计算 BM25 原始分数
            scores = self.bm25.get_scores(query_tokens)
            # 获取最高分索引
            best_idx = scores.argmax()
            # 获取最高分（原始 BM25 分数）
            best_score = scores[best_idx]
            logger.info(f"搜索最高分 [{best_score:.3f}] 结果: {self.original_questions[best_idx]}")
            # 检查是否超过阈值（原始分数）
            if best_score >= threshold:
                # 获取原始问题
                original_question = self.original_questions[best_idx]
                # 命中后追加语义相关校验：BM25 高分可能靠通用词碰上（答非所问），
                # 若查询与命中条目没有实质业务词匹配，则判为误命中，降级走 RAG。
                if not self._is_relevant_match(query, original_question):
                    self.logger.warning(
                        f"BM25 高分但语义不相关，降级 RAG。分={best_score:.3f} 命中=[{original_question}]")
                    return None, True
                # 获取答案
                answer = self.mysql_client.fetch_answer(original_question)
                if answer:
                    # 缓存答案（24 小时 TTL，防止 Redis 无界增长）
                    self.redis_client.set_data(f"answer:{query}", answer, ttl=86400)
                    # 记录搜索成功
                    self.logger.info(f"搜索成功，BM25 分数: {best_score:.3f}")
                    # 返回答案和 False
                    return answer, False
            # 记录无可靠答案
            self.logger.info(f"未找到可靠答案，最高 BM25 分数: {best_score:.3f}")
            # 返回 None 和 True
            return None, True
        except Exception as e:
            # 记录搜索失败
            self.logger.error(f"搜索失败: {e}")
            # 返回 None 和 True
            return None, True
