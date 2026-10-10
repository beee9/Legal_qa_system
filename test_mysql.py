import pymysql
import sys

try:
    print("测试连接...")
    conn = pymysql.connect(
        host='127.0.0.1',
        port=3307,
        user='root',
        password='12345678',
        database='legal_qa'
    )
    print("✅ 连接成功！")
    cursor = conn.cursor()
    cursor.execute('SELECT DATABASE(), USER();')
    result = cursor.fetchone()
    print(f"数据库: {result[0]}")
    print(f"用户: {result[1]}")
    conn.close()
except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    traceback.print_exc()
