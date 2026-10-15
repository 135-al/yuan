"""
attachments.py - 任务附件模块
支持文件上传、下载、列表、删除

接口：
  POST   /api/tasks/<task_id>/attachments          上传附件
  GET    /api/tasks/<task_id>/attachments          获取附件列表
  GET    /api/tasks/<task_id>/attachments/<id>/download  下载附件
  DELETE /api/tasks/<task_id>/attachments/<id>     删除附件
"""

import os
import uuid

from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from datetime import datetime

from app import db
from app.models import Task, Attachment
from app.auth import get_current_user
from app.logs import log_operation

attachments_bp = Blueprint("attachments", __name__)


def _allowed_file(filename):
    """检查文件扩展名是否允许"""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in Attachment.ALLOWED_EXTENSIONS


@attachments_bp.route("/<int:task_id>/attachments", methods=["POST"])
def upload_attachment(task_id):
    """上传任务附件"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    task = Task.query.get(task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    if task.user_id != user.id:
        return jsonify({"error": "forbidden"}), 403

    if "file" not in request.files:
        return jsonify({"error": "no file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    if not _allowed_file(file.filename):
        return (
            jsonify({"error": f"file type not allowed. Allowed: {list(Attachment.ALLOWED_EXTENSIONS)}"}),
            400,
        )

    # 读取文件内容检查大小
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > Attachment.MAX_FILE_SIZE:
        return jsonify({"error": f"file too large. Max size: {Attachment.MAX_FILE_SIZE // (1024*1024)}MB"}), 400

    # 生成安全文件名和存储路径
    original_name = secure_filename(file.filename)
    ext = original_name.rsplit(".", 1)[1].lower() if "." in original_name else ""
    stored_filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, stored_filename)
    file.save(file_path)

    # 数据库记录
    attachment = Attachment(
        task_id=task_id,
        user_id=user.id,
        filename=original_name,
        stored_filename=stored_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
    )
    db.session.add(attachment)

    # 记录操作日志
    log_operation(
        user=user,
        action="upload",
        resource_type="attachment",
        resource_id=attachment.id,
        detail={"task_id": task_id, "filename": original_name, "size": file_size},
    )

    db.session.commit()

    return jsonify({"message": "File uploaded successfully", "attachment": attachment.to_dict()}), 201


@attachments_bp.route("/<int:task_id>/attachments", methods=["GET"])
def get_attachments(task_id):
    """获取任务附件列表"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    task = Task.query.get(task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    if task.user_id != user.id:
        return jsonify({"error": "forbidden"}), 403

    attachments = Attachment.query.filter_by(task_id=task_id).order_by(Attachment.created_at.desc()).all()

    return jsonify({"attachments": [a.to_dict() for a in attachments], "count": len(attachments)}), 200


@attachments_bp.route("/<int:task_id>/attachments/<int:attachment_id>/download", methods=["GET"])
def download_attachment(task_id, attachment_id):
    """下载附件"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    task = Task.query.get(task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    if task.user_id != user.id:
        return jsonify({"error": "forbidden"}), 403

    attachment = Attachment.query.get(attachment_id)
    if attachment is None or attachment.task_id != task_id:
        return jsonify({"error": "attachment not found"}), 404

    if not os.path.exists(attachment.file_path):
        return jsonify({"error": "file not found on disk"}), 404

    return send_file(
        attachment.file_path,
        as_attachment=True,
        download_name=attachment.filename,
    )


@attachments_bp.route("/<int:task_id>/attachments/<int:attachment_id>", methods=["DELETE"])
def delete_attachment(task_id, attachment_id):
    """删除附件"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    task = Task.query.get(task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    if task.user_id != user.id:
        return jsonify({"error": "forbidden"}), 403

    attachment = Attachment.query.get(attachment_id)
    if attachment is None or attachment.task_id != task_id:
        return jsonify({"error": "attachment not found"}), 404

    # 删除磁盘文件
    if os.path.exists(attachment.file_path):
        os.remove(attachment.file_path)

    log_operation(
        user=user,
        action="delete",
        resource_type="attachment",
        resource_id=attachment.id,
        detail={"task_id": task_id, "filename": attachment.filename},
    )

    db.session.delete(attachment)
    db.session.commit()

    return jsonify({"message": "Attachment deleted successfully"}), 200
