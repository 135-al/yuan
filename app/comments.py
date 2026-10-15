"""
comments.py - 任务评论模块
支持评论的增删改查及层级回复

接口：
  POST   /api/tasks/<task_id>/comments          添加评论
  GET    /api/tasks/<task_id>/comments          获取评论列表（含回复）
  PUT    /api/tasks/<task_id>/comments/<id>     修改评论
  DELETE /api/tasks/<task_id>/comments/<id>     删除评论
"""

from flask import Blueprint, request, jsonify
from datetime import datetime

from app import db
from app.models import Task, Comment
from app.auth import get_current_user
from app.logs import log_operation

comments_bp = Blueprint("comments", __name__)


@comments_bp.route("/<int:task_id>/comments", methods=["POST"])
def create_comment(task_id):
    """添加评论"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    task = Task.query.get(task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    if task.user_id != user.id:
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}
    content = data.get("content", "").strip()

    if not content:
        return jsonify({"error": "content is required"}), 400

    parent_id = data.get("parent_id")
    if parent_id is not None:
        parent = Comment.query.get(parent_id)
        if parent is None or parent.task_id != task_id:
            return jsonify({"error": "parent comment not found"}), 404

    comment = Comment(
        task_id=task_id,
        user_id=user.id,
        content=content,
        parent_id=parent_id,
    )
    db.session.add(comment)

    log_operation(
        user=user,
        action="create",
        resource_type="comment",
        resource_id=None,  # commit 后才有 id
        detail={"task_id": task_id, "content_preview": content[:100]},
    )

    db.session.flush()  # 获取 comment.id
    # 更新日志的 resource_id
    from app.models import OperationLog
    log_entry = OperationLog.query.order_by(OperationLog.id.desc()).first()
    if log_entry:
        log_entry.resource_id = comment.id

    db.session.commit()

    return jsonify({"message": "Comment created successfully", "comment": comment.to_dict(include_replies=True)}), 201


@comments_bp.route("/<int:task_id>/comments", methods=["GET"])
def get_comments(task_id):
    """获取评论列表（含回复）"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    task = Task.query.get(task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    if task.user_id != user.id:
        return jsonify({"error": "forbidden"}), 403

    # 只查顶级评论，回复通过 include_replies 自动加载
    comments = (
        Comment.query.filter_by(task_id=task_id, parent_id=None)
        .order_by(Comment.created_at.asc())
        .all()
    )

    return jsonify({
        "comments": [c.to_dict(include_replies=True) for c in comments],
        "count": len(comments),
    }), 200


@comments_bp.route("/<int:task_id>/comments/<int:comment_id>", methods=["PUT"])
def update_comment(task_id, comment_id):
    """修改评论"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    task = Task.query.get(task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    if task.user_id != user.id:
        return jsonify({"error": "forbidden"}), 403

    comment = Comment.query.get(comment_id)
    if comment is None or comment.task_id != task_id:
        return jsonify({"error": "comment not found"}), 404

    if comment.user_id != user.id:
        return jsonify({"error": "forbidden: can only edit your own comments"}), 403

    data = request.get_json() or {}
    content = data.get("content", "").strip()

    if not content:
        return jsonify({"error": "content is required"}), 400

    old_content = comment.content
    comment.content = content
    comment.updated_at = datetime.utcnow()

    log_operation(
        user=user,
        action="update",
        resource_type="comment",
        resource_id=comment.id,
        detail={"task_id": task_id, "old_content_preview": old_content[:50], "new_content_preview": content[:50]},
    )

    db.session.commit()

    return jsonify({"message": "Comment updated successfully", "comment": comment.to_dict()}), 200


@comments_bp.route("/<int:task_id>/comments/<int:comment_id>", methods=["DELETE"])
def delete_comment(task_id, comment_id):
    """删除评论"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    task = Task.query.get(task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    if task.user_id != user.id:
        return jsonify({"error": "forbidden"}), 403

    comment = Comment.query.get(comment_id)
    if comment is None or comment.task_id != task_id:
        return jsonify({"error": "comment not found"}), 404

    if comment.user_id != user.id:
        return jsonify({"error": "forbidden: can only delete your own comments"}), 403

    log_operation(
        user=user,
        action="delete",
        resource_type="comment",
        resource_id=comment.id,
        detail={"task_id": task_id, "content_preview": comment.content[:50]},
    )

    db.session.delete(comment)
    db.session.commit()

    return jsonify({"message": "Comment deleted successfully"}), 200
