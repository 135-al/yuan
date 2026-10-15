"""
auth.py - 认证模块
包含用户注册、登录、JWT 生成与验证

刻意缺陷：
  - 登录接口无限流（可暴力破解）
  - JWT 过期时间 7 天（过长，见 config.py）
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import jwt
from app import db
from app.models import User
from app.logs import log_operation

auth_bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------------------
# JWT 工具函数
# ---------------------------------------------------------------------------

def generate_token(user):
    """生成 JWT Token"""
    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.utcnow()
        + timedelta(seconds=current_app.config["JWT_EXPIRATION_DELTA"]),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(
        payload, current_app.config["SECRET_KEY"], algorithm="HS256"
    )
    return token


def decode_token(token):
    """解码 JWT Token，返回 payload 或 None"""
    try:
        payload = jwt.decode(
            token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user():
    """
    从请求头中提取并验证 JWT，返回当前用户对象。
    验证失败返回 None。
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    payload = decode_token(token)
    if payload is None:
        return None
    user = User.query.get(payload.get("user_id"))
    return user


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

@auth_bp.route("/register", methods=["POST"])
def register():
    """用户注册"""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "username already exists"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already exists"}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    log_operation(
        user=user,
        action="register",
        resource_type="user",
        resource_id=user.id,
        detail={"username": username, "email": email},
    )

    db.session.commit()

    token = generate_token(user)
    return (
        jsonify(
            {
                "message": "User registered successfully",
                "user": user.to_dict(),
                "token": token,
            }
        ),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    用户登录

    ⚠️ 刻意缺陷：无登录限流（无频率限制），可被暴力破解。
    正确做法应使用 flask-limiter 或 Redis 计数器限制尝试次数。
    """
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user = User.query.filter_by(username=username).first()

    if user is None or not user.check_password(password):
        return jsonify({"error": "invalid username or password"}), 401

    token = generate_token(user)

    log_operation(
        user=user,
        action="login",
        resource_type="user",
        resource_id=user.id,
        detail={"username": username},
    )

    db.session.commit()

    return (
        jsonify(
            {
                "message": "Login successful",
                "user": user.to_dict(),
                "token": token,
            }
        ),
        200,
    )


@auth_bp.route("/me", methods=["GET"])
def me():
    """获取当前登录用户信息"""
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({"user": user.to_dict()}), 200
