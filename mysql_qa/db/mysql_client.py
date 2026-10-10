# 导入 MySQL 连接库
import pymysql
# 导入pandas
import pandas as pd
import sys, os
# 线程本地存储：每个线程持有独立连接，避免共享游标在并发下互相串扰
import threading

# 获取当前文件所在目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取core文件所在的目录的绝对路径
rag_qa_path = os.path.dirname(current_dir)
sys.path.insert(0, rag_qa_path)
# 获取根目录文件所在的绝对位置
project_root = os.path.dirname(rag_qa_path)
sys.path.insert(0, project_root)

# 导入配置和日志
from base import Config, logger


class MySQLClient:
    """线程安全的 MySQL 客户端：按线程惰性建立独立连接。

    pymysql 的连接与游标不是线程安全的；FastAPI 的线程池 / WebSocket
    后台线程会并发调用本客户端。这里用 threading.local 让每个线程拥有
    自己独立的 connection + cursor，`close()` 统一回收所有线程的连接。
    """

    def __init__(self):
        # 初始化日志
        self.logger = logger
        # 线程本地连接
        self._local = threading.local()
        # 记录所有已建立的连接，供 close() 统一关闭
        self._connections = set()
        self._lock = threading.Lock()

    def _get_connection(self):
        """获取当前线程的连接，未建立或已断开则新建。"""
        conn = getattr(self._local, "connection", None)
        if conn is None or not conn.open:
            cfg = Config()
            # 调试输出
            print(f"DEBUG - MySQL 连接参数:")
            print(f"  host: {cfg.MYSQL_HOST}")
            print(f"  port: {cfg.MYSQL_PORT}")
            print(f"  user: {cfg.MYSQL_USER}")
            print(f"  password: '{cfg.MYSQL_PASSWORD}' (长度: {len(cfg.MYSQL_PASSWORD)})")
            print(f"  database: {cfg.MYSQL_DATABASE}")

            conn = pymysql.connect(
                host=cfg.MYSQL_HOST,
                user=cfg.MYSQL_USER,
                password=cfg.MYSQL_PASSWORD,
                database=cfg.MYSQL_DATABASE,
                port=cfg.MYSQL_PORT,
            )
            self._local.connection = conn
            self._local.cursor = conn.cursor()
            with self._lock:
                self._connections.add(conn)
            self.logger.info("MySQL 连接成功（新线程）")
        return conn

    @property
    def connection(self):
        """当前线程的连接（惰性建立）。"""
        return self._get_connection()

    @property
    def cursor(self):
        """当前线程的游标（惰性建立）。"""
        self._get_connection()
        return self._local.cursor

    def create_table(self):
        create_table_query = '''
                             CREATE TABLE IF NOT EXISTS jpkb
                             (
                                 id
                                 INT
                                 AUTO_INCREMENT
                                 PRIMARY
                                 KEY,
                                 subject_name
                                 VARCHAR
                             (
                                 20
                             ),
                                 question VARCHAR
                             (
                                 1000
                             ),
                                 answer VARCHAR
                             (
                                 1000
                             )
                                 ) \
                             '''
        try:
            self.cursor.execute(create_table_query)
            self.connection.commit()
            self.logger.info("表创建成功")
        except pymysql.MySQLError as e:
            self.logger.error(f"表创建失败: {e}")
            raise

    def insert_data(self, csv_path):
        try:
            data = pd.read_csv(csv_path)
            # 数据单条写入
            for _, row in data.iterrows():
                insert_query = "INSERT INTO jpkb (subject_name, question, answer) VALUES (%s, %s, %s)"
                self.cursor.execute(insert_query, (row['学科名称'], row['问题'], row['答案']))
            self.connection.commit()
            self.logger.info("数据插入成功")
        except Exception as e:
            self.logger.error(f"数据插入失败: {e}")
            self.connection.rollback()  # 数据的回滚
            raise

    def fetch_questions(self):
        # 获取所有问题
        try:
            # 执行查询
            self.cursor.execute("SELECT question FROM jpkb")
            # 获取结果
            results = self.cursor.fetchall()
            # 记录获取成功
            self.logger.info("成功获取问题")
            # 返回结果
            return results
        except pymysql.MySQLError as e:
            # 记录查询失败
            self.logger.error(f"查询失败: {e}")
            # 返回空列表
            return []

    def fetch_answer(self, question):
        # 获取指定问题的答案
        try:
            # 执行查询
            self.cursor.execute("SELECT answer FROM jpkb WHERE question=%s", (question,))
            # 获取结果
            result = self.cursor.fetchone()
            # 返回答案或 None
            return result[0] if result else None
        except pymysql.MySQLError as e:
            # 记录答案获取失败
            self.logger.error(f"答案获取失败: {e}")
            # 返回 None
            return None

    def close(self):
        # 关闭所有线程建立的连接
        with self._lock:
            conns = list(self._connections)
            self._connections.clear()
        for conn in conns:
            try:
                if conn.open:
                    conn.close()
            except pymysql.MySQLError as e:
                # 记录关闭失败
                self.logger.error(f"关闭连接失败: {e}")
        # 清空当前线程的本地引用
        self._local.connection = None
        self._local.cursor = None
        self.logger.info("MySQL 所有连接已关闭")


if __name__ == '__main__':
    mysql_client = MySQLClient()
    mysql_client.create_table()
    mysql_client.insert_data('../data/JP学科知识问答.csv')
