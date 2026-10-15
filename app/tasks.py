"""
tasks.py - 任务 CRUD 接口

刻意缺陷：
  - 删除任务时无归属校验（可删别人任务）
  - 状态可从 done 直接改回 pending（无状态机校验）
  - 创建任务不校验 title 非空
  - 任务列表无分页（一次性返回全部）
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from app import db
from app.models import Task, Tag
from app.auth import get_current_user
from app.logs import log_operation

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("", methods=["POST"])
def create_task():
    """创建任务"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json() or {}

    # ⚠️ 刻意缺陷：不校验 title 非空，允许空标题
    # 正确做法应为：
    #   title = data.get('title', '').strip()
    #   if not title:
    #       return jsonify({'error': 'title is required'}), 400

    task = Task(
        title=data.get("title", ""),  # 允许空字符串
        description=data.get("description", ""),
        status=data.get("status", "pending"),
        priority=data.get("priority", "medium"),
        due_date=(
            datetime.fromisoformat(data["due_date"])
            if data.get("due_date")
            else None
        ),
        user_id=user.id,
    )

    # 处理标签
    tag_names = data.get("tags", [])
    for tag_name in tag_names:
        tag = Tag.query.filter_by(name=tag_name).first()
        if tag is None:
            tag = Tag(name=tag_name)
            db.session.add(tag)
        task.tags.append(tag)

    db.session.add(task)
    db.session.flush()  # 获取 task.id

    log_operation(
        user=user,
        action="create",
        resource_type="task",
        resource_id=task.id,
        detail={"title": task.title, "status": task.status, "priority": task.priority},
    )

    db.session.commit()

    return (
        jsonify({"message": "Task created successfully", "task": task.to_dict()}),
        201,
    )


@tasks_bp.route("", methods=["GET"])
def get_tasks():
    """获取任务列表"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    # ⚠️ 刻意缺陷：无分页，一次性返回全部任务
    # 正确做法应为：
    #   page = request.args.get('page', 1, type=int)
    #   per_page = request.args.get('per_page', 20, type=int)
    #   pagination = query.paginate(page=page, per_page=per_page)

    query = Task.query.filter_by(user_id=user.id)

    # 按状态过滤
    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)

    # 按优先级过滤
    priority = request.args.get("priority")
    if priority:
        query = query.filter_by(priority=priority)

    tasks = query.order_by(Task.created_at.desc()).all()

    return (
        jsonify({"tasks": [task.to_dict() for task in tasks], "count": len(tasks)}),
        200,
    )


@tasks_bp.route("/<int:task_id>", methods=["GET"])
def get_task(task_id):
    """获取单个任务详情"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    task = Task.query.get(task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    if task.user_id != user.id:
        return jsonify({"error": "forbidden"}), 403

    return jsonify({"task": task.to_dict()}), 200


@tasks_bp.route("/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    """更新任务"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    task = Task.query.get(task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    if task.user_id != user.id:
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}

    if "title" in data:
        task.title = data["title"]
    if "description" in data:
        task.description = data["description"]
    if "status" in data:
        # ⚠️ 刻意缺陷：允许任意状态转换（done->pending 也可）
        # 正确做法应校验状态流转：pending->doing->done
        task.status = data["status"]
    if "priority" in data:
        task.priority = data["priority"]
    if "due_date" in data:
        task.due_date = (
            datetime.fromisoformat(data["due_date"]) if data["due_date"] else None
        )

    # 更新标签
    if "tags" in data:
        task.tags = []
        for tag_name in data["tags"]:
            tag = Tag.query.filter_by(name=tag_name).first()
            if tag is None:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            task.tags.append(tag)

    task.updated_at = datetime.utcnow()

    log_operation(
        user=user,
        action="update",
        resource_type="task",
        resource_id=task.id,
        detail={"changed_fields": list(data.keys())},
    )

    db.session.commit()

    return (
        jsonify({"message": "Task updated successfully", "task": task.to_dict()}),
        200,
    )


@tasks_bp.route("/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    """删除任务"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    task = Task.query.get(task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    # ⚠️ 刻意缺陷：无归属校验，可删除其他用户的任务
    # 正确做法应为：
    #   if task.user_id != user.id:
    #       return jsonify({'error': 'forbidden'}), 403

    log_operation(
        user=user,
        action="delete",
        resource_type="task",
        resource_id=task.id,
        detail={"title": task.title},
    )

    db.session.delete(task)
    db.session.commit()

    return jsonify({"message": "Task deleted successfully"}), 200


@tasks_bp.route("/<int:task_id>/status", methods=["PATCH"])
def update_status(task_id):
    """更新任务状态"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    task = Task.query.get(task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    if task.user_id != user.id:
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json() or {}
    new_status = data.get("status")

    if new_status not in Task.VALID_STATUSES:
        return (
            jsonify({"error": f"invalid status. Valid: {Task.VALID_STATUSES}"}),
            400,
        )

    # ⚠️ 刻意缺陷：无状态流转校验
    # 正确做法应定义合法转换：
    #   VALID_TRANSITIONS = {
    #       'pending': ['doing'],
    #       'doing': ['done', 'pending'],
    #       'done': [],  # 终态，不可回退
    #   }
    #   if new_status not in VALID_TRANSITIONS.get(task.status, []):
    #       return jsonify({'error': f'Cannot transition from {task.status} to {new_status}'}), 400

    old_status = task.status
    task.status = new_status
    task.updated_at = datetime.utcnow()

    log_operation(
        user=user,
        action="update_status",
        resource_type="task",
        resource_id=task.id,
        detail={"old_status": old_status, "new_status": new_status},
    )

    db.session.commit()

    return (
        jsonify({"message": "Status updated successfully", "task": task.to_dict()}),
        200,
    )


@tasks_bp.route("/tags", methods=["GET"])
def get_tags():
    """获取所有标签"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    tags = Tag.query.all()
    return jsonify({"tags": [tag.to_dict() for tag in tags], "count": len(tags)}), 200
