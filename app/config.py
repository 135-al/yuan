"""
config.py - 应用配置
包含 Flask、SQLAlchemy、JWT 等配置项
"""


import os

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """基础配置类"""

    # Flask 密钥
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # SQLAlchemy 数据库
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "task.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT 配置
    # ⚠️ 刻意缺陷：JWT 过期时间设置为 7 天（过长，生产环境应设为 1-2 小时）
    JWT_EXPIRATION_DELTA = 7 * 24 * 60 * 60  # 7 天，单位秒

    # 分页默认值
    DEFAULT_PAGE_SIZE = 20

    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(basedir, "uploads")


class TestConfig(Config):
    """测试配置"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
