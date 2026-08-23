# 导入日志库
import logging
from logging.handlers import RotatingFileHandler
# 导入路径操作库
import os
# 导入配置类
from base.config import Config

# 日志轮转：单文件上限 + 备份数量
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5MB
LOG_BACKUP_COUNT = 3


def setup_logging(log_file=Config().LOG_FILE, level=logging.INFO):
    # 创建日志目录
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    # 获取日志器
    logger = logging.getLogger("LegalQA")
    # 设置日志级别
    logger.setLevel(level)
    # 避免重复添加处理器
    if not logger.handlers:
        # 创建文件处理器（带轮转，防止日志无限增长）
        file_handler = RotatingFileHandler(
            log_file, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding='utf-8')
        file_handler.setLevel(level)
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        # 统一日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    # 返回日志器
    return logger


# 初始化日志器
logger = setup_logging()


def process_data(data):
    logger.debug(f"开始处理数据: {data}")
    if not data:
        logger.error("数据为空，无法处理")
        return None
    logger.info("数据处理完成")
    return data.upper()


def main():
    logger.info("程序启动")
    result = process_data("hello")
    if result:
        logger.info(f"处理结果: {result}")
    else:
        logger.warning("处理失败")
    logger.info("程序结束")


if __name__ == "__main__":
    main()
