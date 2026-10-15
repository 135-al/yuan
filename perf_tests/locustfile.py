"""
locustfile.py - 任务管理系统性能测试脚本

场景设计（贴近真实业务链路）：
    on_start  注册 → 登录 → 建立会话
    tasks     按权重模拟真实用户行为分布：
                - 浏览任务列表（高频）
                - 查看统计看板（高频；含 N+1 查询，任务量大时耗时会被放大）
                - 创建任务
                - 状态流转
                - 发表评论
                - 查看操作日志

运行（Web UI）：
    locust -f perf_tests/locustfile.py --host http://127.0.0.1:5000

运行（无头模式）：
    locust -f perf_tests/locustfile.py --headless -u 50 -r 5 -t 60s \\
           --host http://127.0.0.1:5000 --html perf_tests/report.html

推荐用 perf_tests/run_perf.py 一键跑梯度压测并生成报告。
"""

import uuid
import random

from locust import HttpUser, task, between, events


DEFAULT_HOST = "http://127.0.0.1:5000"


class TaskFlowUser(HttpUser):
    """模拟一个已登录的任务管理系统用户"""

    wait_time = between(1, 3)

    def on_start(self):
        """每个虚拟用户启动时：注册 + 登录，建立带 Token 的会话"""
        suffix = uuid.uuid4().hex[:10]
        self.username = f"perf_{suffix}"
        self.password = "Perf@12345"
        self.task_ids = []

        email = f"perf_{suffix}@perf.com"
        with self.client.post(
            "/api/auth/register",
            json={"username": self.username, "email": email, "password": self.password},
            name="/api/auth/register",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                self.token = resp.json()["token"]
                resp.success()
            elif resp.status_code == 409:
                # 已存在则直接登录
                resp.success()
                self.token = self._login()
            else:
                resp.failure(f"register failed: {resp.status_code} {resp.text}")

        if getattr(self, "token", None):
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            # 预置 3 个任务，便于后续做列表/统计/状态流转
            for i in range(3):
                self._create_task(f"perf-seed-{i}")

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _login(self):
        r = self.client.post(
            "/api/auth/login",
            json={"username": self.username, "password": self.password},
            name="/api/auth/login",
        )
        return r.json().get("token")

    def _create_task(self, title):
        r = self.client.post(
            "/api/tasks",
            json={"title": title, "priority": "medium", "tags": ["perf"]},
            name="/api/tasks [create]",
        )
        if r.status_code == 201:
            self.task_ids.append(r.json()["task"]["id"])

    def _pick_task(self):
        return random.choice(self.task_ids) if self.task_ids else None

    # ------------------------------------------------------------------
    # 业务任务（weight 越大，执行频率越高）
    # ------------------------------------------------------------------

    @task(5)
    def list_tasks(self):
        """浏览任务列表 —— 高频只读操作"""
        self.client.get("/api/tasks", name="/api/tasks [list]")

    @task(3)
    def view_stats(self):
        """查看统计看板 —— 代码含 N+1 查询，是随任务量增长的潜在瓶颈点"""
        self.client.get("/api/stats", name="/api/stats")

    @task(3)
    def create_task(self):
        """创建任务"""
        self._create_task(f"perf-task-{uuid.uuid4().hex[:6]}")

    @task(2)
    def update_status(self):
        """任务状态流转"""
        tid = self._pick_task()
        if tid is None:
            return
        status = random.choice(["pending", "doing", "done"])
        self.client.patch(
            f"/api/tasks/{tid}/status",
            json={"status": status},
            name="/api/tasks/[id]/status",
        )

    @task(1)
    def add_comment(self):
        """发表评论"""
        tid = self._pick_task()
        if tid is None:
            return
        self.client.post(
            f"/api/tasks/{tid}/comments",
            json={"content": f"压测评论 {uuid.uuid4().hex[:6]}"},
            name="/api/tasks/[id]/comments",
        )

    @task(1)
    def view_logs(self):
        """查看操作日志"""
        self.client.get("/api/logs?limit=20", name="/api/logs")


# ---------------------------------------------------------------------------
# 事件钩子：失败请求即时打印，便于定位
# ---------------------------------------------------------------------------

@events.request.add_listener
def _on_request(request_type, name, response_time, response_length,
                response, context, exception, **kwargs):
    if exception:
        print(f"[FAIL] {request_type} {name} -> {exception}")
    elif response is not None and response.status_code >= 500:
        print(f"[5XX ] {request_type} {name} -> {response.status_code}")
