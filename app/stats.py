"""
stats.py - 统计看板接口
提供任务总数、完成率、逾期数等统计数据

刻意缺陷：
  - 统计接口存在 N+1 查询问题
    （遍历任务逐条调用 to_dict()，每次触发标签关联查询）
"""

from flask import Blueprint, jsonify
from datetime import datetime
from app.models import Task
from app.auth import get_current_user

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("", methods=["GET"])
def get_stats():
    """
    获取任务统计看板数据

    ⚠️ 刻意缺陷：N+1 查询问题
    下方先 .all() 取出全部任务，再循环中调用 task.to_dict()，
    而 to_dict() 内部访问 task.tags（lazy load），
    导致每条任务额外触发一次 SQL 查询标签 → N+1。

    正确做法应使用 joinedload 预加载：
        from sqlalchemy.orm import joinedload
        tasks = Task.query.options(joinedload(Task.tags)) \\
            .filter_by(user_id=user.id).all()
    或使用聚合查询直接 COUNT。
    """
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    # ---- N+1 查询开始 ----
    tasks = Task.query.filter_by(user_id=user.id).all()

    total = len(tasks)
    pending_count = 0
    doing_count = 0
    done_count = 0
    overdue_count = 0
    now = datetime.utcnow()

    task_list = []
    for task in tasks:
        # 每次调用 to_dict() 都会触发 task.tags 的 lazy load → N+1
        task_dict = task.to_dict()
        task_list.append(task_dict)

        if task.status == "pending":
            pending_count += 1
        elif task.status == "doing":
            doing_count += 1
        elif task.status == "done":
            done_count += 1

        if task.due_date and task.due_date < now and task.status != "done":
            overdue_count += 1
    # ---- N+1 查询结束 ----

    completion_rate = round((done_count / total * 100), 2) if total > 0 else 0.0

    return (
        jsonify(
            {
                "total": total,
                "pending": pending_count,
                "doing": doing_count,
                "done": done_count,
                "overdue": overdue_count,
                "completion_rate": completion_rate,
                "tasks": task_list,
            }
        ),
        200,
    )


@stats_bp.route("/summary", methods=["GET"])
def get_summary():
    """
    获取任务统计摘要（无 N+1，使用聚合查询，供对比参考）
    """
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    total = Task.query.filter_by(user_id=user.id).count()
    done = Task.query.filter_by(user_id=user.id, status="done").count()
    pending = Task.query.filter_by(user_id=user.id, status="pending").count()
    doing = Task.query.filter_by(user_id=user.id, status="doing").count()

    now = datetime.utcnow()
    overdue = (
        Task.query.filter(
            Task.user_id == user.id,
            Task.due_date < now,
            Task.status != "done",
        ).count()
    )

    completion_rate = round((done / total * 100), 2) if total > 0 else 0.0

    return (
        jsonify(
            {
                "total": total,
                "pending": pending,
                "doing": doing,
                "done": done,
                "overdue": overdue,
                "completion_rate": completion_rate,
            }
        ),
        200,
    )
