# 导入配置解析库
import configparser
# 导入路径操作库
import os


class Config:
    # 基于当前文件位置推导项目根目录（base/ -> 项目根）
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @staticmethod
    def _load_dotenv():
        """加载项目根目录 .env 文件到环境变量（密钥不存 config.ini，存 .env 且已 gitignore）"""
        env_path = os.path.join(Config._PROJECT_ROOT, ".env")
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())

    # 初始化配置，加载 config.ini 文件
    def __init__(self, config_file=None):
        # 先加载 .env（密钥从环境变量读取）
        self._load_dotenv()
        # 默认加载本项目根目录下的 config.ini
        if config_file is None:
            config_file = os.path.join(self._PROJECT_ROOT, "config.ini")
        # 创建配置解析器
        self.config = configparser.ConfigParser()
        # 读取配置文件
        self.config.read(config_file,encoding='utf-8')  # windows包gbk错误，增加encoding=utf-8

        # MySQL 配置
        # MySQL 主机地址
        # 获取section 是mysql host变量失败返回localhost
        self.MYSQL_HOST = self.config.get('mysql', 'host', fallback='localhost')

        # MySQL 用户名
        self.MYSQL_USER = self.config.get('mysql', 'user', fallback='root')
        # MySQL 密码
        self.MYSQL_PASSWORD = self.config.get('mysql', 'password', fallback='123456')
        # MySQL 数据库名
        self.MYSQL_DATABASE = self.config.get('mysql', 'database', fallback='subjects_kg')

        # Redis 配置
        # Redis 主机地址
        self.REDIS_HOST = self.config.get('redis', 'host', fallback='localhost')
        # Redis 端口
        self.REDIS_PORT = self.config.getint('redis', 'port', fallback=6379)
        # Redis 密码
        self.REDIS_PASSWORD = self.config.get('redis', 'password', fallback='1234')
        # Redis 数据库编号
        self.REDIS_DB = self.config.getint('redis', 'db', fallback=0)

        # Milvus 配置
        # Milvus 主机地址
        self.MILVUS_HOST = self.config.get('milvus', 'host', fallback='localhost')
        # Milvus 端口
        self.MILVUS_PORT = self.config.get('milvus', 'port', fallback='19530')
        # Milvus 数据库名
        self.MILVUS_DATABASE_NAME = self.config.get('milvus', 'database_name', fallback='itcast')
        # Milvus 集合名
        self.MILVUS_COLLECTION_NAME = self.config.get('milvus', 'collection_name', fallback='edurag_final')

        # LLM 配置
        # LLM 模型名
        self.LLM_MODEL = self.config.get('llm', 'model', fallback='qwen-plus')
        # DashScope API 密钥（优先 .env 环境变量）
        self.DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY") or self.config.get('llm', 'dashscope_api_key', fallback=None)
        # DashScope API 地址（优先 .env 环境变量）
        self.DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL") or self.config.get(
            'llm', 'dashscope_base_url', fallback='https://dashscope.aliyuncs.com/compatible-mode/v1')

        # 检索参数
        # 父块大小
        self.PARENT_CHUNK_SIZE = self.config.getint('retrieval', 'parent_chunk_size', fallback=1200)
        # 子块大小
        self.CHILD_CHUNK_SIZE = self.config.getint('retrieval', 'child_chunk_size', fallback=300)
        # 块重叠大小
        self.CHUNK_OVERLAP = self.config.getint('retrieval', 'chunk_overlap', fallback=50)
        # 检索返回数量
        self.RETRIEVAL_K = self.config.getint('retrieval', 'retrieval_k', fallback=5)
        # 最终候选数量
        self.CANDIDATE_M = self.config.getint('retrieval', 'candidate_m', fallback=2)

        # 应用配置
        # 有效来源列表
        self.VALID_SOURCES = eval(
            self.config.get('app', 'valid_sources', fallback='["ai", "java", "test", "ops", "bigdata"]'))
        # 客服电话
        self.CUSTOMER_SERVICE_PHONE = self.config.get('app', 'customer_service_phone', fallback='12345678')
        # 日志文件路径
        self.LOG_FILE = self.config.get('logger', 'log_file', fallback='logs/app.log')

        # model path（相对项目根拼装，避免硬编码绝对路径）
        # 本地模型根目录：优先读 config.ini 的 [model].models_dir，
        # 缺省指向本项目 rag_qa/models；本项目该目录为空时，请在 config.ini 里指向真实模型位置。
        self.models_dir = self.config.get(
            'model', 'models_dir',
            fallback=os.path.join(self._PROJECT_ROOT, "rag_qa", "models"))
        self.bge_m3 = os.path.join(self.models_dir, "bge-m3")
        self.bge_reranker = os.path.join(self.models_dir, "bge-reranker-v2-m3")
        self.nlp_bert_doc_seg = os.path.join(self.models_dir,
                                             "nlp_bert_document-segmentation_chinese-base")
        self.bert_intent_cls = os.path.join(self._PROJECT_ROOT, "rag_qa", "core", "bert_query_classifier", "best_model")


if __name__ == '__main__':
    conf = Config()
    print(conf.LOG_FILE)
