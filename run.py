"""
run.py - 应用启动入口
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    print("=" * 50)
    print("  任务管理系统启动中...")
    print("  API 地址: http://127.0.0.1:5000")
    print("  数据库: SQLite (task.db)")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
