"""
test_api.py - 任务管理系统 API 自动化测试

覆盖范围：
  - 用户注册（正常 / 重复 / 缺字段）
  - 用户登录（正常 / 错误密码 / 缺字段）
  - Token 验证（无 Token / 无效 Token / 过期 Token）
  - 任务创建（正常 / 空 title 缺陷 / 无 Token / 带标签）
  - 任务查询（列表 / 单个 / 不存在 / 越权访问）
  - 任务更新（正常 / 不存在 / 越权）
  - 状态流转（正常流 pending→doing→done / 异常回退 done→pending 缺陷）
  - 任务删除（正常 / 不存在 / 越权删除缺陷）
  - 统计看板（正常 / 无 Token）
  - 刻意缺陷验证（7 个已知缺陷）
"""

import time
import pytest
import allure
import requests


# ===========================================================================
# Allure 层级定义
# ===========================================================================

allure.epic("任务管理系统")
allure.label("owner", "QA Automation")
allure.label("platform", "Flask + SQLite")


# ===========================================================================
# 1. 用户注册
# ===========================================================================

@allure.feature("用户注册")
class TestRegister:

    @allure.story("正常注册")
    @allure.title("注册新用户应返回 201 和 token")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_register_success(self, base_url):
        resp = requests.post(f"{base_url}/api/auth/register", json={
            "username": f"newuser_{int(time.time())}",
            "email": f"newuser_{int(time.time())}@test.com",
            "password": "Passw0rd",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "token" in data
        assert data["user"]["username"].startswith("newuser_")

    @allure.story("异常注册")
    @allure.title("重复用户名应返回 409")
    @allure.severity(allure.severity_level.NORMAL)
    def test_register_duplicate_username(self, base_url, user_a):
        resp = requests.post(f"{base_url}/api/auth/register", json={
            "username": user_a["username"],
            "email": f"other_{int(time.time())}@test.com",
            "password": "Passw0rd",
        })
        assert resp.status_code == 409
        assert "already exists" in resp.json()["error"]

    @allure.story("异常注册")
    @allure.title("缺少邮箱应返回 400")
    @allure.severity(allure.severity_level.NORMAL)
    def test_register_missing_email(self, base_url):
        resp = requests.post(f"{base_url}/api/auth/register", json={
            "username": "noemail",
            "password": "Passw0rd",
        })
        assert resp.status_code == 400

    @allure.story("异常注册")
    @allure.title("缺少密码应返回 400")
    @allure.severity(allure.severity_level.NORMAL)
    def test_register_missing_password(self, base_url):
        resp = requests.post(f"{base_url}/api/auth/register", json={
            "username": "nopass",
            "email": "nopass@test.com",
        })
        assert resp.status_code == 400

    @allure.story("异常注册")
    @allure.title("空请求体应返回 400")
    @allure.severity(allure.severity_level.MINOR)
    def test_register_empty_body(self, base_url):
        resp = requests.post(f"{base_url}/api/auth/register", json={})
        assert resp.status_code == 400


# ===========================================================================
# 2. 用户登录
# ===========================================================================

@allure.feature("用户登录")
class TestLogin:

    @allure.story("正常登录")
    @allure.title("正确凭据登录应返回 200 和 token")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_success(self, base_url, user_a):
        resp = requests.post(f"{base_url}/api/auth/login", json={
            "username": user_a["username"],
            "password": user_a["password"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["username"] == user_a["username"]

    @allure.story("异常登录")
    @allure.title("错误密码应返回 401")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_wrong_password(self, base_url, user_a):
        resp = requests.post(f"{base_url}/api/auth/login", json={
            "username": user_a["username"],
            "password": "WrongPassword123",
        })
        assert resp.status_code == 401
        assert "invalid" in resp.json()["error"]

    @allure.story("异常登录")
    @allure.title("不存在的用户应返回 401")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_nonexistent_user(self, base_url):
        resp = requests.post(f"{base_url}/api/auth/login", json={
            "username": "ghost_user_xyz",
            "password": "whatever",
        })
        assert resp.status_code == 401

    @allure.story("异常登录")
    @allure.title("缺少密码应返回 400")
    @allure.severity(allure.severity_level.MINOR)
    def test_login_missing_password(self, base_url, user_a):
        resp = requests.post(f"{base_url}/api/auth/login", json={
            "username": user_a["username"],
        })
        assert resp.status_code == 400

    @allure.story("异常登录 - 刻意缺陷")
    @allure.title("登录无限流，连续多次请求不会被限速")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_no_rate_limit(self, base_url, user_a):
        """刻意缺陷⑥：登录接口无限流，可暴力破解"""
        statuses = []
        for _ in range(20):
            resp = requests.post(f"{base_url}/api/auth/login", json={
                "username": user_a["username"],
                "password": "wrong",
            })
            statuses.append(resp.status_code)
        # 所有请求都应返回 401，没有被限速（无 429）
        assert 429 not in statuses
        assert all(s == 401 for s in statuses)


# ===========================================================================
# 3. Token 验证
# ===========================================================================

@allure.feature("Token 验证")
class TestToken:

    @allure.story("无 Token 访问")
    @allure.title("无 Token 创建任务应返回 401")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_no_token_create_task(self, anonymous_client):
        resp = anonymous_client.post("/api/tasks", json={"title": "test"})
        assert resp.status_code == 401

    @allure.story("无 Token 访问")
    @allure.title("无 Token 获取任务列表应返回 401")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_no_token_get_tasks(self, anonymous_client):
        resp = anonymous_client.get("/api/tasks")
        assert resp.status_code == 401

    @allure.story("无 Token 访问")
    @allure.title("无 Token 获取统计应返回 401")
    @allure.severity(allure.severity_level.NORMAL)
    def test_no_token_get_stats(self, anonymous_client):
        resp = anonymous_client.get("/api/stats")
        assert resp.status_code == 401

    @allure.story("无效 Token")
    @allure.title("无效 Token 应返回 401")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_invalid_token(self, base_url):
        client = _make_client(base_url, "invalid.token.here")
        resp = client.get("/api/tasks")
        assert resp.status_code == 401

    @allure.story("有效 Token")
    @allure.title("/api/auth/me 返回当前用户信息")
    @allure.severity(allure.severity_level.NORMAL)
    def test_me_with_valid_token(self, client_a, user_a):
        resp = client_a.get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["user"]["username"] == user_a["username"]


# ===========================================================================
# 4. 任务创建
# ===========================================================================

@allure.feature("任务创建")
class TestCreateTask:

    @allure.story("正常创建")
    @allure.title("创建任务应返回 201 和完整任务对象")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_task_success(self, client_a):
        resp = client_a.post("/api/tasks", json={
            "title": "Test Task",
            "description": "A test task",
            "status": "pending",
            "priority": "high",
        })
        assert resp.status_code == 201
        task = resp.json()["task"]
        assert task["title"] == "Test Task"
        assert task["status"] == "pending"
        assert task["priority"] == "high"
        assert task["id"] is not None

    @allure.story("正常创建")
    @allure.title("创建带标签的任务")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_task_with_tags(self, client_a):
        resp = client_a.post("/api/tasks", json={
            "title": "Tagged Task",
            "tags": ["bug", "urgent"],
        })
        assert resp.status_code == 201
        tag_names = [t["name"] for t in resp.json()["task"]["tags"]]
        assert "bug" in tag_names
        assert "urgent" in tag_names

    @allure.story("异常创建 - 刻意缺陷")
    @allure.title("空 title 应被拒绝但实际返回 201（缺陷③）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_create_task_empty_title_defect(self, client_a):
        """刻意缺陷③：创建任务不校验 title 非空"""
        resp = client_a.post("/api/tasks", json={
            "title": "",
            "description": "empty title task",
        })
        # 缺陷：空 title 应返回 400，但实际返回 201
        assert resp.status_code == 201
        assert resp.json()["task"]["title"] == ""

    @allure.story("异常创建")
    @allure.title("无 Token 创建任务应返回 401")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_task_no_token(self, anonymous_client):
        resp = anonymous_client.post("/api/tasks", json={"title": "test"})
        assert resp.status_code == 401

    @allure.story("正常创建")
    @allure.title("创建任务默认状态为 pending")
    @allure.severity(allure.severity_level.MINOR)
    def test_create_task_default_status(self, client_a):
        resp = client_a.post("/api/tasks", json={"title": "Default Status Task"})
        assert resp.status_code == 201
        assert resp.json()["task"]["status"] == "pending"


# ===========================================================================
# 5. 任务查询
# ===========================================================================

@allure.feature("任务查询")
class TestGetTasks:

    @allure.story("正常查询")
    @allure.title("获取任务列表应返回 200 和 tasks 数组")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_tasks_success(self, client_a, created_task):
        resp = client_a.get("/api/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        assert "count" in data
        assert data["count"] >= 1

    @allure.story("正常查询")
    @allure.title("按状态过滤任务")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_tasks_filter_by_status(self, client_a):
        client_a.post("/api/tasks", json={"title": "Pending", "status": "pending"})
        resp = client_a.get("/api/tasks", params={"status": "pending"})
        assert resp.status_code == 200
        tasks = resp.json()["tasks"]
        assert all(t["status"] == "pending" for t in tasks)

    @allure.story("正常查询")
    @allure.title("获取单个任务详情")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_single_task(self, client_a, created_task):
        resp = client_a.get(f"/api/tasks/{created_task['id']}")
        assert resp.status_code == 200
        assert resp.json()["task"]["id"] == created_task["id"]

    @allure.story("异常查询")
    @allure.title("查询不存在的任务应返回 404")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_nonexistent_task(self, client_a):
        resp = client_a.get("/api/tasks/99999")
        assert resp.status_code == 404

    @allure.story("异常查询")
    @allure.title("用户 A 查看用户 B 的任务应返回 403")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_other_user_task_forbidden(self, client_a, client_b):
        # 用户 B 创建任务
        resp_b = client_b.post("/api/tasks", json={"title": "B's task"})
        task_id = resp_b.json()["task"]["id"]
        # 用户 A 尝试查看
        resp = client_a.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 403

    @allure.story("异常查询 - 刻意缺陷")
    @allure.title("任务列表无分页，一次性返回全部")
    @allure.severity(allure.severity_level.MINOR)
    def test_tasks_no_pagination(self, client_a):
        """刻意缺陷④：任务列表无分页"""
        # 创建多个任务
        for i in range(5):
            client_a.post("/api/tasks", json={"title": f"Task {i}"})
        resp = client_a.get("/api/tasks")
        data = resp.json()
        # 无 page/per_page 参数，全部返回
        assert "page" not in data
        assert "total_pages" not in data


# ===========================================================================
# 6. 任务更新
# ===========================================================================

@allure.feature("任务更新")
class TestUpdateTask:

    @allure.story("正常更新")
    @allure.title("更新任务标题和描述")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_task_success(self, client_a, created_task):
        resp = client_a.put(f"/api/tasks/{created_task['id']}", json={
            "title": "Updated Title",
            "description": "Updated description",
        })
        assert resp.status_code == 200
        assert resp.json()["task"]["title"] == "Updated Title"

    @allure.story("正常更新")
    @allure.title("更新任务优先级")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_task_priority(self, client_a, created_task):
        resp = client_a.put(f"/api/tasks/{created_task['id']}", json={
            "priority": "low",
        })
        assert resp.status_code == 200
        assert resp.json()["task"]["priority"] == "low"

    @allure.story("异常更新")
    @allure.title("更新不存在的任务应返回 404")
    @allure.severity(allure.severity_level.NORMAL)
    def test_update_nonexistent_task(self, client_a):
        resp = client_a.put("/api/tasks/99999", json={"title": "X"})
        assert resp.status_code == 404

    @allure.story("异常更新")
    @allure.title("用户 A 更新用户 B 的任务应返回 403")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_other_user_task_forbidden(self, client_a, client_b):
        resp_b = client_b.post("/api/tasks", json={"title": "B's task"})
        task_id = resp_b.json()["task"]["id"]
        resp = client_a.put(f"/api/tasks/{task_id}", json={"title": "Hacked"})
        assert resp.status_code == 403


# ===========================================================================
# 7. 状态流转
# ===========================================================================

@allure.feature("状态流转")
class TestStatusTransition:

    @allure.story("正常流转")
    @allure.title("状态流转 pending -> doing -> done")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_normal_status_flow(self, client_a, created_task):
        task_id = created_task["id"]

        # pending -> doing
        resp = client_a.patch(f"/api/tasks/{task_id}/status", json={"status": "doing"})
        assert resp.status_code == 200
        assert resp.json()["task"]["status"] == "doing"

        # doing -> done
        resp = client_a.patch(f"/api/tasks/{task_id}/status", json={"status": "done"})
        assert resp.status_code == 200
        assert resp.json()["task"]["status"] == "done"

    @allure.story("异常流转")
    @allure.title("无效状态值应返回 400")
    @allure.severity(allure.severity_level.NORMAL)
    def test_invalid_status_value(self, client_a, created_task):
        resp = client_a.patch(
            f"/api/tasks/{created_task['id']}/status",
            json={"status": "invalid"},
        )
        assert resp.status_code == 400

    @allure.story("异常流转 - 刻意缺陷")
    @allure.title("状态可从 done 回退到 pending（缺陷②）")
    @allure.severity(allure.severity_level.NORMAL)
    def test_status_done_to_pending_defect(self, client_a, created_task):
        """刻意缺陷②：状态可从 done 直接改回 pending"""
        task_id = created_task["id"]
        # 先走到 done
        client_a.patch(f"/api/tasks/{task_id}/status", json={"status": "doing"})
        client_a.patch(f"/api/tasks/{task_id}/status", json={"status": "done"})
        # 尝试从 done 回退到 pending —— 应被拒绝但实际成功
        resp = client_a.patch(
            f"/api/tasks/{task_id}/status", json={"status": "pending"}
        )
        # 缺陷：应返回 400，但实际返回 200
        assert resp.status_code == 200
        assert resp.json()["task"]["status"] == "pending"

    @allure.story("异常流转")
    @allure.title("无 Token 更新状态应返回 401")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_update_status_no_token(self, anonymous_client, created_task):
        resp = anonymous_client.patch(
            f"/api/tasks/{created_task['id']}/status",
            json={"status": "doing"},
        )
        assert resp.status_code == 401


# ===========================================================================
# 8. 任务删除
# ===========================================================================

@allure.feature("任务删除")
class TestDeleteTask:

    @allure.story("正常删除")
    @allure.title("删除自己的任务应返回 200")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_own_task(self, client_a):
        # 先创建
        resp = client_a.post("/api/tasks", json={"title": "To Delete"})
        task_id = resp.json()["task"]["id"]
        # 再删除
        resp = client_a.delete(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        # 确认已删除
        resp = client_a.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 404

    @allure.story("异常删除")
    @allure.title("删除不存在的任务应返回 404")
    @allure.severity(allure.severity_level.NORMAL)
    def test_delete_nonexistent_task(self, client_a):
        resp = client_a.delete("/api/tasks/99999")
        assert resp.status_code == 404

    @allure.story("异常删除 - 刻意缺陷")
    @allure.title("用户 A 可删除用户 B 的任务（缺陷①）")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_other_user_task_defect(self, client_a, client_b):
        """刻意缺陷①：删除任务时无归属校验，可删别人任务"""
        # 用户 B 创建任务
        resp_b = client_b.post("/api/tasks", json={"title": "B's task"})
        task_id = resp_b.json()["task"]["id"]
        # 用户 A 删除 B 的任务 —— 应返回 403 但实际返回 200
        resp = client_a.delete(f"/api/tasks/{task_id}")
        # 缺陷：应返回 403，但实际返回 200
        assert resp.status_code == 200
        # 确认已被删除
        resp = client_b.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 404

    @allure.story("异常删除")
    @allure.title("无 Token 删除任务应返回 401")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_no_token(self, anonymous_client, created_task):
        resp = anonymous_client.delete(f"/api/tasks/{created_task['id']}")
        assert resp.status_code == 401


# ===========================================================================
# 9. 统计看板
# ===========================================================================

@allure.feature("统计看板")
class TestStats:

    @allure.story("正常统计")
    @allure.title("获取统计数据应返回完整看板")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_stats_success(self, client_a, created_task):
        resp = client_a.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "pending" in data
        assert "doing" in data
        assert "done" in data
        assert "overdue" in data
        assert "completion_rate" in data
        assert data["total"] >= 1

    @allure.story("正常统计")
    @allure.title("空任务列表统计应为 0")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_stats_empty(self, client_a):
        resp = client_a.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["completion_rate"] == 0.0

    @allure.story("正常统计")
    @allure.title("统计摘要接口返回聚合数据")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_stats_summary(self, client_a, created_task):
        resp = client_a.get("/api/stats/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    @allure.story("异常统计")
    @allure.title("无 Token 获取统计应返回 401")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_stats_no_token(self, anonymous_client):
        resp = anonymous_client.get("/api/stats")
        assert resp.status_code == 401

    @allure.story("统计准确性")
    @allure.title("创建多个不同状态任务后统计准确")
    @allure.severity(allure.severity_level.NORMAL)
    def test_stats_accuracy(self, client_a):
        # 创建 3 个任务
        client_a.post("/api/tasks", json={"title": "T1", "status": "pending"})
        client_a.post("/api/tasks", json={"title": "T2", "status": "doing"})
        client_a.post("/api/tasks", json={"title": "T3", "status": "done"})

        resp = client_a.get("/api/stats/summary")
        data = resp.json()
        assert data["total"] >= 3
        assert data["pending"] >= 1
        assert data["doing"] >= 1
        assert data["done"] >= 1


# ===========================================================================
# 10. 刻意缺陷汇总验证
# ===========================================================================

@allure.feature("刻意缺陷验证")
class TestKnownDefects:

    @allure.story("缺陷① - 删除无归属校验")
    @allure.title("用户可删除其他用户的任务")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_defect_delete_without_ownership(self, client_a, client_b):
        resp_b = client_b.post("/api/tasks", json={"title": "B's task"})
        task_id = resp_b.json()["task"]["id"]
        resp = client_a.delete(f"/api/tasks/{task_id}")
        assert resp.status_code == 200  # 应该 403

    @allure.story("缺陷② - 状态可回退")
    @allure.title("done 状态可回退到 pending")
    @allure.severity(allure.severity_level.NORMAL)
    def test_defect_status_rollback(self, client_a, created_task):
        task_id = created_task["id"]
        client_a.patch(f"/api/tasks/{task_id}/status", json={"status": "doing"})
        client_a.patch(f"/api/tasks/{task_id}/status", json={"status": "done"})
        resp = client_a.patch(
            f"/api/tasks/{task_id}/status", json={"status": "pending"}
        )
        assert resp.status_code == 200  # 应该 400

    @allure.story("缺陷③ - title 不校验非空")
    @allure.title("空 title 任务创建成功")
    @allure.severity(allure.severity_level.NORMAL)
    def test_defect_empty_title(self, client_a):
        resp = client_a.post("/api/tasks", json={"title": ""})
        assert resp.status_code == 201  # 应该 400

    @allure.story("缺陷④ - 任务列表无分页")
    @allure.title("任务列表无分页参数")
    @allure.severity(allure.severity_level.MINOR)
    def test_defect_no_pagination(self, client_a):
        resp = client_a.get("/api/tasks")
        data = resp.json()
        assert "page" not in data
        assert "per_page" not in data

    @allure.story("缺陷⑤ - 统计 N+1 查询")
    @allure.title("统计接口返回任务列表（N+1 查询问题）")
    @allure.severity(allure.severity_level.MINOR)
    def test_defect_n_plus_one(self, client_a, created_task):
        """统计接口返回了完整 task_list，存在 N+1 查询"""
        resp = client_a.get("/api/stats")
        data = resp.json()
        # stats 接口返回了 tasks 数组，说明遍历了全部任务
        assert "tasks" in data

    @allure.story("缺陷⑥ - 登录无限流")
    @allure.title("连续 20 次错误登录不被限速")
    @allure.severity(allure.severity_level.NORMAL)
    def test_defect_no_rate_limit(self, base_url, user_a):
        statuses = []
        for _ in range(20):
            resp = requests.post(f"{base_url}/api/auth/login", json={
                "username": user_a["username"],
                "password": "wrong",
            })
            statuses.append(resp.status_code)
        assert 429 not in statuses

    @allure.story("缺陷⑦ - JWT 过期时间过长")
    @allure.title("JWT 过期时间为 7 天")
    @allure.severity(allure.severity_level.NORMAL)
    def test_defect_long_jwt_expiry(self, client_a):
        import jwt as pyjwt
        # 从登录响应获取 token 并解码（不验证签名）
        # token 已在 client_a 中
        token = client_a.token
        payload = pyjwt.decode(token, options={"verify_signature": False})
        exp = payload["exp"]
        iat = payload["iat"]
        delta_seconds = exp - iat
        delta_days = delta_seconds / 86400
        # 7 天 = 604800 秒
        assert delta_days > 6  # 超过 6 天说明是 7 天过期


# ===========================================================================
# 辅助函数
# ===========================================================================

def _make_client(base_url, token):
    """创建带指定 token 的 ApiClient

    注意：必须用「包限定名」导入。写成 `from conftest import ApiClient`
    会被 Python 解析成 sys.path 上任意一个 conftest，一旦同批收集的
    其他测试目录也有 conftest.py（如 concurrency_tests/），就会导入错对象。
    """
    from api_tests.conftest import ApiClient
    return ApiClient(base_url, token=token)
