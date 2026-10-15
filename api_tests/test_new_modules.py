"""
test_new_modules.py - 新增模块测试用例
覆盖：文件上传、评论功能、操作日志

测试场景：
  - 附件上传/下载/列表/删除（正常 + 异常）
  - 评论增删改查（正常 + 越权 + 空内容）
  - 操作日志查询/过滤/统计
"""

import os
import tempfile
import json
import pytest
import allure


# ---------------------------------------------------------------------------
# 文件上传（任务附件）
# ---------------------------------------------------------------------------

@allure.feature("文件上传")
@allure.story("正常上传附件")
def test_upload_attachment_success(client_a, created_task):
    """上传一个 txt 文件到任务"""
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Hello, this is a test file.")
        tmp_path = f.name

    try:
        resp = client_a.upload(f"/api/tasks/{created_task['id']}/attachments", tmp_path)
        assert resp.status_code == 201
        data = resp.json()
        assert data["attachment"]["filename"].endswith(".txt")
        assert data["attachment"]["file_size"] > 0
        assert "download_url" in data["attachment"]
    finally:
        os.unlink(tmp_path)


@allure.feature("文件上传")
@allure.story("上传附件 - 无文件")
def test_upload_no_file(client_a, created_task):
    """未提供文件时应返回 400"""
    resp = client_a.post(f"/api/tasks/{created_task['id']}/attachments")
    assert resp.status_code == 400


@allure.feature("文件上传")
@allure.story("上传附件 - 无Token")
def test_upload_no_token(anonymous_client, created_task):
    """未登录上传应返回 401"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("test")
        tmp_path = f.name
    try:
        resp = anonymous_client.upload(f"/api/tasks/{created_task['id']}/attachments", tmp_path)
        assert resp.status_code == 401
    finally:
        os.unlink(tmp_path)


@allure.feature("文件上传")
@allure.story("上传附件 - 越权")
def test_upload_other_user_task(client_b, created_task):
    """用户B给用户A的任务上传附件应返回 403"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("test")
        tmp_path = f.name
    try:
        resp = client_b.upload(f"/api/tasks/{created_task['id']}/attachments", tmp_path)
        assert resp.status_code == 403
    finally:
        os.unlink(tmp_path)


@allure.feature("文件上传")
@allure.story("上传附件 - 不允许的文件类型")
def test_upload_invalid_file_type(client_a, created_task):
    """上传不允许的文件类型应返回 400"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".exe", delete=False) as f:
        f.write("fake exe")
        tmp_path = f.name
    try:
        resp = client_a.upload(f"/api/tasks/{created_task['id']}/attachments", tmp_path)
        assert resp.status_code == 400
    finally:
        os.unlink(tmp_path)


@allure.feature("文件上传")
@allure.story("获取附件列表")
def test_get_attachments(client_a, created_task):
    """获取任务附件列表"""
    # 先上传一个文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("test content")
        tmp_path = f.name
    try:
        client_a.upload(f"/api/tasks/{created_task['id']}/attachments", tmp_path)
        resp = client_a.get(f"/api/tasks/{created_task['id']}/attachments")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert len(data["attachments"]) >= 1
    finally:
        os.unlink(tmp_path)


@allure.feature("文件上传")
@allure.story("删除附件")
def test_delete_attachment(client_a, created_task):
    """删除附件"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("to be deleted")
        tmp_path = f.name
    try:
        upload_resp = client_a.upload(f"/api/tasks/{created_task['id']}/attachments", tmp_path)
        attachment_id = upload_resp.json()["attachment"]["id"]

        resp = client_a.delete(f"/api/tasks/{created_task['id']}/attachments/{attachment_id}")
        assert resp.status_code == 200

        # 确认已删除
        list_resp = client_a.get(f"/api/tasks/{created_task['id']}/attachments")
        ids = [a["id"] for a in list_resp.json()["attachments"]]
        assert attachment_id not in ids
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# 评论功能
# ---------------------------------------------------------------------------

@allure.feature("评论功能")
@allure.story("添加评论 - 正常")
def test_create_comment_success(client_a, created_task):
    """正常添加评论"""
    resp = client_a.post(
        f"/api/tasks/{created_task['id']}/comments",
        json={"content": "This is a test comment."},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["comment"]["content"] == "This is a test comment."
    assert data["comment"]["username"] is not None


@allure.feature("评论功能")
@allure.story("添加评论 - 空内容")
def test_create_comment_empty_content(client_a, created_task):
    """空内容应返回 400"""
    resp = client_a.post(
        f"/api/tasks/{created_task['id']}/comments",
        json={"content": ""},
    )
    assert resp.status_code == 400


@allure.feature("评论功能")
@allure.story("添加评论 - 无Token")
def test_create_comment_no_token(anonymous_client, created_task):
    """未登录添加评论应返回 401"""
    resp = anonymous_client.post(
        f"/api/tasks/{created_task['id']}/comments",
        json={"content": "test"},
    )
    assert resp.status_code == 401


@allure.feature("评论功能")
@allure.story("添加评论 - 越权")
def test_create_comment_other_user_task(client_b, created_task):
    """用户B给用户A的任务评论应返回 403"""
    resp = client_b.post(
        f"/api/tasks/{created_task['id']}/comments",
        json={"content": "intrusion"},
    )
    assert resp.status_code == 403


@allure.feature("评论功能")
@allure.story("回复评论")
def test_reply_comment(client_a, created_task):
    """添加评论的回复"""
    # 先创建顶级评论
    resp = client_a.post(
        f"/api/tasks/{created_task['id']}/comments",
        json={"content": "Parent comment"},
    )
    parent_id = resp.json()["comment"]["id"]

    # 添加回复
    reply_resp = client_a.post(
        f"/api/tasks/{created_task['id']}/comments",
        json={"content": "Reply to parent", "parent_id": parent_id},
    )
    assert reply_resp.status_code == 201
    assert reply_resp.json()["comment"]["parent_id"] == parent_id


@allure.feature("评论功能")
@allure.story("获取评论列表")
def test_get_comments(client_a, created_task):
    """获取评论列表（含回复）"""
    # 添加评论
    client_a.post(
        f"/api/tasks/{created_task['id']}/comments",
        json={"content": "Comment 1"},
    )
    client_a.post(
        f"/api/tasks/{created_task['id']}/comments",
        json={"content": "Comment 2"},
    )

    resp = client_a.get(f"/api/tasks/{created_task['id']}/comments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 2
    # 确认含 replies 字段
    for comment in data["comments"]:
        assert "replies" in comment


@allure.feature("评论功能")
@allure.story("修改评论")
def test_update_comment(client_a, created_task):
    """修改自己的评论"""
    create_resp = client_a.post(
        f"/api/tasks/{created_task['id']}/comments",
        json={"content": "Original"},
    )
    comment_id = create_resp.json()["comment"]["id"]

    resp = client_a.put(
        f"/api/tasks/{created_task['id']}/comments/{comment_id}",
        json={"content": "Updated content"},
    )
    assert resp.status_code == 200
    assert resp.json()["comment"]["content"] == "Updated content"


@allure.feature("评论功能")
@allure.story("删除评论")
def test_delete_comment(client_a, created_task):
    """删除自己的评论"""
    create_resp = client_a.post(
        f"/api/tasks/{created_task['id']}/comments",
        json={"content": "To be deleted"},
    )
    comment_id = create_resp.json()["comment"]["id"]

    resp = client_a.delete(f"/api/tasks/{created_task['id']}/comments/{comment_id}")
    assert resp.status_code == 200

    # 确认已删除
    list_resp = client_a.get(f"/api/tasks/{created_task['id']}/comments")
    ids = [c["id"] for c in list_resp.json()["comments"]]
    assert comment_id not in ids


@allure.feature("评论功能")
@allure.story("修改评论 - 越权")
def test_update_comment_other_user(client_a, client_b, created_task):
    """用户B不能修改用户A的评论"""
    create_resp = client_a.post(
        f"/api/tasks/{created_task['id']}/comments",
        json={"content": "User A's comment"},
    )
    comment_id = create_resp.json()["comment"]["id"]

    # 用户B没有任务权限，先确认 403
    resp = client_b.put(
        f"/api/tasks/{created_task['id']}/comments/{comment_id}",
        json={"content": "hacked"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 操作日志
# ---------------------------------------------------------------------------

@allure.feature("操作日志")
@allure.story("查询日志列表")
def test_get_logs(client_a):
    """查询操作日志列表"""
    resp = client_a.get("/api/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert "logs" in data
    assert "total" in data
    assert isinstance(data["logs"], list)


@allure.feature("操作日志")
@allure.story("查询日志 - 无Token")
def test_get_logs_no_token(anonymous_client):
    """未登录查询日志应返回 401"""
    resp = anonymous_client.get("/api/logs")
    assert resp.status_code == 401


@allure.feature("操作日志")
@allure.story("操作产生日志记录")
def test_operation_logged(client_a, created_task):
    """创建任务后应产生操作日志"""
    # created_task fixture 已创建任务，查询日志应有 create 记录
    resp = client_a.get("/api/logs?action=create&resource_type=task")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1

    # 验证日志内容
    log = data["logs"][0]
    assert log["action"] == "create"
    assert log["resource_type"] == "task"
    assert log["detail"] is not None


@allure.feature("操作日志")
@allure.story("按资源类型过滤日志")
def test_filter_logs_by_resource_type(client_a):
    """按 resource_type 过滤日志"""
    resp = client_a.get("/api/logs?resource_type=task")
    assert resp.status_code == 200
    data = resp.json()
    for log in data["logs"]:
        assert log["resource_type"] == "task"


@allure.feature("操作日志")
@allure.story("按操作类型过滤日志")
def test_filter_logs_by_action(client_a):
    """按 action 过滤日志"""
    resp = client_a.get("/api/logs?action=login")
    assert resp.status_code == 200
    data = resp.json()
    for log in data["logs"]:
        assert log["action"] == "login"


@allure.feature("操作日志")
@allure.story("日志统计接口")
def test_log_stats(client_a):
    """操作日志统计"""
    resp = client_a.get("/api/logs/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "by_action" in data
    assert "by_resource_type" in data
    assert data["total"] >= 0


@allure.feature("操作日志")
@allure.story("查询单条日志详情")
def test_get_log_detail(client_a):
    """查询单条日志详情"""
    # 先获取日志列表
    list_resp = client_a.get("/api/logs?limit=1")
    logs = list_resp.json()["logs"]
    if len(logs) == 0:
        pytest.skip("No logs available")

    log_id = logs[0]["id"]
    resp = client_a.get(f"/api/logs/{log_id}")
    assert resp.status_code == 200
    assert resp.json()["log"]["id"] == log_id


@allure.feature("操作日志")
@allure.story("状态更新产生日志")
def test_status_change_logged(client_a, created_task):
    """状态更新应产生操作日志"""
    # 更新状态
    client_a.patch(
        f"/api/tasks/{created_task['id']}/status",
        json={"status": "doing"},
    )

    # 查询日志
    resp = client_a.get("/api/logs?action=update_status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1

    log = data["logs"][0]
    assert log["detail"]["old_status"] == "pending"
    assert log["detail"]["new_status"] == "doing"


@allure.feature("操作日志")
@allure.story("日志分页")
def test_log_pagination(client_a):
    """日志分页参数"""
    resp = client_a.get("/api/logs?limit=5&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 5
    assert data["offset"] == 0
    assert len(data["logs"]) <= 5
