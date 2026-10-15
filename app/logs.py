"""
logs.py - 操作日志模块
自动记录用户操作（谁在什么时候干了什么），支持查询和过滤。

接口：
  GET /api/logs              查询操作日志列表（支持过滤）
  GET /api/logs/<id>         查询单条日志详情
  GET /api/logs/stats        操作日志统计

log_operation() helper 供其他模块调用，自动记录：
  - 用户信息（id + username）
  - 操作类型（create/update/delete/login/register/upload...）
  - 资源类型与 ID（task/user/comment/attachment）
  - 变更详情（JSON）
  - IP 地址
  - 时间戳
"""

import json
from flask import Blueprint, request, jsonify
from datetime import datetime

from app import db
from app.models import OperationLog

logs_bp = Blueprint("logs", __name__)


def _get_current_user():
    """延迟导入 get_current_user 避免循环依赖（auth.py -> logs.py -> auth.py）"""
    from app.auth import get_current_user
    return get_current_user()


def log_operation(user, action, resource_type=None, resource_id=None, detail=None):
    """
    记录操作日志（不 commit，由调用方统一 commit）

    Args:
        user: User 对象，None 表示未登录操作
        action: 操作类型字符串（create/update/delete/login/register/upload...）
        resource_type: 资源类型（task/user/comment/attachment）
        resource_id: 资源 ID
        detail: 变更详情字典
    """
    ip = request.remote_addr if request else None

    entry = OperationLog(
        user_id=user.id if user else None,
        username=user.username if user else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
        ip_address=ip,
    )
    db.session.add(entry)
    return entry


# ---------------------------------------------------------------------------
# 查询接口
# ---------------------------------------------------------------------------

@logs_bp.route("", methods=["GET"])
def get_logs():
    """查询操作日志列表

    支持过滤参数：
      - action: 按操作类型过滤（create/update/delete/login...）
      - resource_type: 按资源类型过滤（task/comment/attachment...）
      - user_id: 按用户过滤
      - start_date: 开始日期（ISO 格式）
      - end_date: 结束日期（ISO 格式）
      - limit: 返回条数（默认 50，最大 200）
      - offset: 偏移量
    """
    user = _get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    query = OperationLog.query

    # 过滤
    action = request.args.get("action")
    if action:
        query = query.filter(OperationLog.action == action)

    resource_type = request.args.get("resource_type")
    if resource_type:
        query = query.filter(OperationLog.resource_type == resource_type)

    user_id = request.args.get("user_id", type=int)
    if user_id:
        query = query.filter(OperationLog.user_id == user_id)

    start_date = request.args.get("start_date")
    if start_date:
        try:
            dt = datetime.fromisoformat(start_date)
            query = query.filter(OperationLog.created_at >= dt)
        except ValueError:
            pass

    end_date = request.args.get("end_date")
    if end_date:
        try:
            dt = datetime.fromisoformat(end_date)
            query = query.filter(OperationLog.created_at <= dt)
        except ValueError:
            pass

    # 分页
    limit = min(request.args.get("limit", 50, type=int), 200)
    offset = request.args.get("offset", 0, type=int)

    total = query.count()
    logs = query.order_by(OperationLog.created_at.desc()).offset(offset).limit(limit).all()

    return jsonify({
        "logs": [log.to_dict() for log in logs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }), 200


@logs_bp.route("/<int:log_id>", methods=["GET"])
def get_log_detail(log_id):
    """查询单条操作日志详情"""
    user = _get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    log = OperationLog.query.get(log_id)
    if log is None:
        return jsonify({"error": "log not found"}), 404

    return jsonify({"log": log.to_dict()}), 200


@logs_bp.route("/stats", methods=["GET"])
def get_log_stats():
    """操作日志统计：按 action 和 resource_type 分组计数"""
    user = _get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    from sqlalchemy import func

    by_action = (
        db.session.query(OperationLog.action, func.count(OperationLog.id))
        .group_by(OperationLog.action)
        .all()
    )

    by_resource = (
        db.session.query(OperationLog.resource_type, func.count(OperationLog.id))
        .group_by(OperationLog.resource_type)
        .all()
    )

    total = OperationLog.query.count()

    return jsonify({
        "total": total,
        "by_action": {action: count for action, count in by_action},
        "by_resource_type": {(rt or "unknown"): count for rt, count in by_resource},
    }), 200
