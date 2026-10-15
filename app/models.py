"""
models.py - 数据模型
包含 User、Task、Tag 三个模型及关联关系
"""

from datetime import datetime
from app import db
import hashlib

# 多对多关联表：Task <-> Tag
task_tags = db.Table(
    "task_tags",
    db.Column("task_id", db.Integer, db.ForeignKey("tasks.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)


class User(db.Model):
    """用户模型"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 一对多：一个用户拥有多个任务
    tasks = db.relationship(
        "Task", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        """设置密码（SHA-256 哈希存储）"""
        self.password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

    def check_password(self, password):
        """验证密码"""
        return self.password_hash == hashlib.sha256(
            password.encode("utf-8")
        ).hexdigest()

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Task(db.Model):
    """任务模型"""

    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    # ⚠️ 刻意缺陷：title 允许为空（nullable=True），创建时无非空校验
    title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending", nullable=False)
    priority = db.Column(db.String(10), default="medium")
    due_date = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 多对多：任务关联多个标签
    tags = db.relationship("Tag", secondary=task_tags, backref="tasks_list", lazy=True)

    # 合法状态与优先级
    VALID_STATUSES = ["pending", "doing", "done"]
    VALID_PRIORITIES = ["low", "medium", "high"]

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "user_id": self.user_id,
            "tags": [tag.to_dict() for tag in self.tags],
            "attachment_count": len(self.attachments) if self.attachments else 0,
            "comment_count": len(self.comments) if self.comments else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Tag(db.Model):
    """标签模型"""

    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7), default="#666666")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Attachment(db.Model):
    """任务附件模型"""

    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)          # 原始文件名
    stored_filename = db.Column(db.String(255), nullable=False)   # 存储文件名（UUID）
    file_path = db.Column(db.String(500), nullable=False)         # 相对路径
    file_size = db.Column(db.Integer, default=0)                  # 字节
    mime_type = db.Column(db.String(100), default="application/octet-stream")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    task = db.relationship("Task", backref="attachments", lazy=True)
    uploader = db.relationship("User", backref="attachments", lazy=True)

    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "doc", "docx", "xls", "xlsx", "zip", "md"}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "download_url": f"/api/tasks/{self.task_id}/attachments/{self.id}/download",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Comment(db.Model):
    """任务评论模型"""

    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=True)  # 支持回复
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    task = db.relationship("Task", backref="comments", lazy=True)
    author = db.relationship("User", backref="comments", lazy=True)
    replies = db.relationship(
        "Comment",
        backref=db.backref("parent", remote_side="Comment.id"),
        lazy=True,
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_replies=False):
        data = {
            "id": self.id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "username": self.author.username if self.author else None,
            "content": self.content,
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_replies:
            data["replies"] = [r.to_dict() for r in self.replies]
        return data


class OperationLog(db.Model):
    """操作日志模型"""

    __tablename__ = "operation_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)  # nullable: 未登录操作
    username = db.Column(db.String(80), nullable=True)  # 冗余存储用户名（用户删除后仍可查）
    action = db.Column(db.String(50), nullable=False)    # create / update / delete / login / register / upload ...
    resource_type = db.Column(db.String(30), nullable=True)  # task / user / comment / attachment
    resource_id = db.Column(db.Integer, nullable=True)
    detail = db.Column(db.Text)                           # JSON 字符串，记录变更详情
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # 关联
    user = db.relationship("User", backref="operation_logs", lazy=True)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "detail": json.loads(self.detail) if self.detail else None,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
