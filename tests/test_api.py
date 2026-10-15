"""
test_api.py - API 测试用例（共 30 个）

覆盖范围：
  - 用户注册/登录/JWT 认证（1-11）
  - 任务 CRUD（12-19）
  - 任务状态流转（20-21）
  - 删除归属校验（22）
  - 标签（23）
  - 统计看板（24-25）
  - 刻意缺陷验证（26-30）
"""

import jwt
from datetime import datetime, timedelta


# ===========================================================================
# 1. 用户注册测试
# ===========================================================================

def test_register_success(client):
    """测试1: 正常注册"""
    resp = client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["user"]["username"] == "newuser"
    assert "token" in data


def test_register_missing_fields(client):
    """测试2: 注册缺少必填字段"""
    resp = client.post(
        "/api/auth/register",
        json={"username": "incomplete"},
    )
    assert resp.status_code == 400


def test_register_duplicate_username(client, auth_headers):
    """测试3: 重复用户名注册"""
    resp = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "another@example.com",
            "password": "pass123",
        },
    )
    assert resp.status_code == 409


def test_register_duplicate_email(client, auth_headers):
    """测试4: 重复邮箱注册"""
    resp = client.post(
        "/api/auth/register",
        json={
            "username": "anotheruser",
            "email": "test@example.com",
            "password": "pass123",
        },
    )
    assert resp.status_code == 409


# ===========================================================================
# 2. 登录测试
# ===========================================================================

def test_login_success(client, auth_headers):
    """测试5: 正常登录"""
    resp = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    assert resp.status_code == 200
    assert "token" in resp.get_json()


def test_login_wrong_password(client, auth_headers):
    """测试6: 密码错误"""
    resp = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "wrongpass"},
    )
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    """测试7: 登录不存在的用户"""
    resp = client.post(
        "/api/auth/login",
        json={"username": "ghost", "password": "pass"},
    )
    assert resp.status_code == 401


def test_login_missing_fields(client):
    """测试8: 登录缺少字段"""
    resp = client.post(
        "/api/auth/login",
        json={"username": "testuser"},
    )
    assert resp.status_code == 400


# ===========================================================================
# 3. JWT 认证测试
# ===========================================================================

def test_get_me_success(client, auth_headers):
    """测试9: 获取当前用户信息"""
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["user"]["username"] == "testuser"


def test_get_me_no_token(client):
    """测试10: 无 Token 访问"""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_get_me_invalid_token(client):
    """测试11: 无效 Token 访问"""
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401


# ===========================================================================
# 4. 任务 CRUD 测试
# ===========================================================================

def test_create_task_success(client, auth_headers):
    """测试12: 创建任务成功"""
    resp = client.post(
        "/api/tasks",
        json={"title": "Buy groceries", "description": "Milk and bread"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.get_json()["task"]["title"] == "Buy groceries"
    assert resp.get_json()["task"]["status"] == "pending"


def test_create_task_no_auth(client):
    """测试13: 未认证创建任务"""
    resp = client.post("/api/tasks", json={"title": "No auth task"})
    assert resp.status_code == 401


def test_create_task_with_tags(client, auth_headers):
    """测试14: 创建带标签的任务"""
    resp = client.post(
        "/api/tasks",
        json={"title": "Tagged task", "tags": ["urgent", "work"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    tags = resp.get_json()["task"]["tags"]
    assert len(tags) == 2
    tag_names = [t["name"] for t in tags]
    assert "urgent" in tag_names
    assert "work" in tag_names


def test_get_tasks(client, auth_headers):
    """测试15: 获取任务列表"""
    # 创建几个任务
    for i in range(3):
        client.post(
            "/api/tasks",
            json={"title": f"Task {i}"},
            headers=auth_headers,
        )
    resp = client.get("/api/tasks", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["count"] == 3


def test_get_task_by_id(client, auth_headers):
    """测试16: 获取单个任务"""
    create_resp = client.post(
        "/api/tasks",
        json={"title": "Find me"},
        headers=auth_headers,
    )
    task_id = create_resp.get_json()["task"]["id"]

    resp = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["task"]["title"] == "Find me"


def test_get_task_not_found(client, auth_headers):
    """测试17: 获取不存在的任务"""
    resp = client.get("/api/tasks/99999", headers=auth_headers)
    assert resp.status_code == 404


def test_get_task_forbidden(client, auth_headers, auth_headers2):
    """测试18: 获取其他用户的任务（应拒绝）"""
    create_resp = client.post(
        "/api/tasks",
        json={"title": "User1 task"},
        headers=auth_headers,
    )
    task_id = create_resp.get_json()["task"]["id"]

    resp = client.get(f"/api/tasks/{task_id}", headers=auth_headers2)
    assert resp.status_code == 403


def test_update_task(client, auth_headers):
    """测试19: 更新任务"""
    create_resp = client.post(
        "/api/tasks",
        json={"title": "Original"},
        headers=auth_headers,
    )
    task_id = create_resp.get_json()["task"]["id"]

    resp = client.put(
        f"/api/tasks/{task_id}",
        json={"title": "Updated", "description": "New desc"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()["task"]["title"] == "Updated"


# ===========================================================================
# 5. 状态流转测试
# ===========================================================================

def test_update_task_status(client, auth_headers):
    """测试20: 更新任务状态 pending -> doing"""
    create_resp = client.post(
        "/api/tasks",
        json={"title": "Status task"},
        headers=auth_headers,
    )
    task_id = create_resp.get_json()["task"]["id"]

    resp = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"status": "doing"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()["task"]["status"] == "doing"


def test_delete_task(client, auth_headers):
    """测试21: 删除任务"""
    create_resp = client.post(
        "/api/tasks",
        json={"title": "Delete me"},
        headers=auth_headers,
    )
    task_id = create_resp.get_json()["task"]["id"]

    resp = client.delete(f"/api/tasks/{task_id}", headers=auth_headers)
    assert resp.status_code == 200

    # 确认已删除
    resp = client.get(f"/api/tasks/{task_id}", headers=auth_headers)
    assert resp.status_code == 404


# ===========================================================================
# 6. 刻意缺陷验证测试
# ===========================================================================

def test_delete_other_user_task(client, auth_headers, auth_headers2):
    """
    测试22（刻意缺陷）: 删除其他用户的任务
    缺陷：delete_task 无归属校验，应返回 403 但实际返回 200
    """
    create_resp = client.post(
        "/api/tasks",
        json={"title": "User1's task"},
        headers=auth_headers,
    )
    task_id = create_resp.get_json()["task"]["id"]

    # 用户2 删除用户1 的任务
    resp = client.delete(f"/api/tasks/{task_id}", headers=auth_headers2)
    # ⚠️ 缺陷表现：返回 200（删除成功），正确应返回 403
    assert resp.status_code == 200


def test_create_task_empty_title(client, auth_headers):
    """
    测试23（刻意缺陷）: 创建空标题任务
    缺陷：不校验 title 非空，应返回 400 但实际返回 201
    """
    resp = client.post(
        "/api/tasks",
        json={"title": ""},
        headers=auth_headers,
    )
    # ⚠️ 缺陷表现：返回 201（创建成功），正确应返回 400
    assert resp.status_code == 201


def test_status_done_to_pending(client, auth_headers):
    """
    测试24（刻意缺陷）: 状态从 done 直接改回 pending
    缺陷：无状态机校验，应拒绝但实际允许
    """
    create_resp = client.post(
        "/api/tasks",
        json={"title": "State machine task", "status": "pending"},
        headers=auth_headers,
    )
    task_id = create_resp.get_json()["task"]["id"]

    # pending -> doing（合法）
    client.patch(
        f"/api/tasks/{task_id}/status",
        json={"status": "doing"},
        headers=auth_headers,
    )
    # doing -> done（合法）
    client.patch(
        f"/api/tasks/{task_id}/status",
        json={"status": "done"},
        headers=auth_headers,
    )
    # done -> pending（非法，应被拒绝）
    resp = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"status": "pending"},
        headers=auth_headers,
    )
    # ⚠️ 缺陷表现：返回 200（成功），正确应返回 400
    assert resp.status_code == 200
    assert resp.get_json()["task"]["status"] == "pending"


def test_tasks_no_pagination(client, auth_headers):
    """
    测试25（刻意缺陷）: 任务列表无分页
    缺陷：一次性返回全部任务，无 page/per_page 参数
    """
    for i in range(50):
        client.post(
            "/api/tasks",
            json={"title": f"Task {i}"},
            headers=auth_headers,
        )

    resp = client.get("/api/tasks", headers=auth_headers)
    data = resp.get_json()
    # ⚠️ 缺陷表现：一次性返回 50 条，无分页信息
    assert data["count"] == 50
    # 正确做法应支持分页：?page=1&per_page=20
    assert "page" not in data
    assert "per_page" not in data


def test_stats_n_plus_one(client, auth_headers):
    """
    测试26（刻意缺陷）: 统计接口 N+1 查询
    缺陷：循环中调用 to_dict() 触发 N+1，但功能上仍返回正确数据
    """
    for i in range(5):
        client.post(
            "/api/tasks",
            json={"title": f"Task {i}", "tags": [f"tag{i}"]},
            headers=auth_headers,
        )

    resp = client.get("/api/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 5
    # 返回了全部任务数据（N+1 问题的副作用）
    assert len(data["tasks"]) == 5


def test_login_no_rate_limit(client, auth_headers):
    """
    测试27（刻意缺陷）: 登录无频率限制
    缺陷：连续多次错误登录不会被锁定/限流
    """
    for _ in range(20):
        resp = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrong"},
        )
        # ⚠️ 缺陷表现：每次都返回 401，从未返回 429（Too Many Requests）
        assert resp.status_code == 401

    # 正确密码仍可登录（未被锁定）
    resp = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    assert resp.status_code == 200


def test_jwt_long_expiry(client, auth_headers):
    """
    测试28（刻意缺陷）: JWT 过期时间过长（7天）
    """
    resp = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    token = resp.get_json()["token"]

    # 解码 Token 查看 exp（不验证签名，因为测试用不同的 SECRET_KEY）
    payload = jwt.decode(token, options={"verify_signature": False})
    exp = datetime.utcfromtimestamp(payload["exp"])
    iat = datetime.utcfromtimestamp(payload["iat"])
    delta = exp - iat

    # ⚠️ 缺陷表现：过期时间为 7 天
    assert delta.days == 7
    # 正确做法应 <= 1 天（或更短）


# ===========================================================================
# 7. 统计看板测试
# ===========================================================================

def test_stats_correctness(client, auth_headers):
    """测试29: 统计数据正确性"""
    # 创建 3 个任务
    client.post("/api/tasks", json={"title": "T1", "status": "pending"}, headers=auth_headers)
    client.post("/api/tasks", json={"title": "T2", "status": "doing"}, headers=auth_headers)
    client.post("/api/tasks", json={"title": "T3", "status": "done"}, headers=auth_headers)

    resp = client.get("/api/stats", headers=auth_headers)
    data = resp.get_json()
    assert data["total"] == 3
    assert data["pending"] == 1
    assert data["doing"] == 1
    assert data["done"] == 1
    assert data["completion_rate"] == 33.33


def test_stats_overdue(client, auth_headers):
    """测试30: 逾期任务统计"""
    # 创建一个已逾期且未完成的任务
    past_date = (datetime.utcnow() - timedelta(days=5)).isoformat()
    client.post(
        "/api/tasks",
        json={"title": "Overdue task", "due_date": past_date, "status": "pending"},
        headers=auth_headers,
    )
    # 创建一个已逾但已完成的任务（不应计入逾期）
    client.post(
        "/api/tasks",
        json={"title": "Done task", "due_date": past_date, "status": "done"},
        headers=auth_headers,
    )

    resp = client.get("/api/stats", headers=auth_headers)
    data = resp.get_json()
    assert data["overdue"] == 1  # 只有第一个任务算逾期
