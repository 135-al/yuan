"""
test_tag_race.py - 并发缺陷复现：标签「先查后插」竞态

缺陷⑧（并发）：
    app/tasks.py 创建/更新任务时对标签采用「先查后插」写法：

        tag = Tag.query.filter_by(name=tag_name).first()
        if tag is None:
            tag = Tag(name=tag_name)
            db.session.add(tag)

    SELECT 与 INSERT 之间存在时间窗口。并发下多个请求同时查到 None，
    一起插入同名标签，触发 tags.name 唯一约束冲突 →
    sqlite3.IntegrityError: UNIQUE constraint failed: tags.name → 500。

    该缺陷只在并发下暴露，单请求功能测试无法发现。

用例策略：
    断言「并发创建任务应全部返回 201」。在未修复的系统上该断言不成立，
    因此标记 xfail（strict=False）——修复后会自动转为 xpass，
    可作为缺陷修复的回归验证信号。
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import allure
import pytest
import requests


def _new_user_token(base_url):
    """注册一个全新用户并返回其 Token（避免用例间数据串扰）"""
    suffix = uuid.uuid4().hex[:8]
    resp = requests.post(
        f"{base_url}/api/auth/register",
        json={
            "username": f"race_{suffix}",
            "email": f"race_{suffix}@test.com",
            "password": "Race@12345",
        },
    )
    assert resp.status_code == 201, f"注册失败: {resp.status_code} {resp.text}"
    return resp.json()["token"]


def _burst_create(base_url, token, tag, size):
    """
    使用同一个「全新标签」并发创建 size 个任务。

    所有线程在 Barrier 处对齐后同时发起请求，最大化竞态窗口。
    返回 [(status_code, body_snippet), ...]
    """
    barrier = threading.Barrier(size)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def worker(idx):
        barrier.wait()
        try:
            r = requests.post(
                f"{base_url}/api/tasks",
                json={"title": f"race-{tag}-{idx}", "priority": "medium", "tags": [tag]},
                headers=headers,
                timeout=30,
            )
            return r.status_code, r.text[:160]
        except Exception as exc:  # 连接异常也计入，避免掩盖问题
            return -1, repr(exc)

    with ThreadPoolExecutor(max_workers=size) as pool:
        return list(pool.map(worker, range(size)))


@allure.epic("任务管理系统")
@allure.feature("并发测试 - 标签竞态")
class TestTagRace:

    @allure.story("并发创建")
    @allure.title("【缺陷⑧】同一新标签并发创建任务不应触发 500")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.xfail(
        reason="已知缺陷⑧：标签先查后插竞态，并发插入同名标签触发唯一约束冲突 500",
        strict=False,
    )
    def test_concurrent_create_same_tag(self, base_url):
        token = _new_user_token(base_url)

        rounds, size = 3, 24
        failures = []

        for r in range(rounds):
            tag = f"race_{uuid.uuid4().hex[:8]}"
            results = _burst_create(base_url, token, tag, size)
            codes = [c for c, _ in results]

            bad = [(c, body) for c, body in results if c not in (200, 201)]
            if bad:
                failures.append((r, tag, codes.count(500), bad[0]))

            with allure.step(f"第 {r + 1} 轮（标签 {tag}，{size} 并发）"):
                allure.attach(
                    f"状态码分布: {sorted(set(codes))}\n"
                    f"500 计数: {codes.count(500)} / {size}",
                    name=f"round{r + 1}",
                    attachment_type=allure.attachment_type.TEXT,
                )

        assert not failures, (
            f"并发创建出现 500（缺陷⑧ 复现）："
            f"轮次={[f[0] for f in failures]}，"
            f"首个错误详情={failures[0][3]}"
        )

    @allure.story("并发创建")
    @allure.title("并发创建使用不同标签时全部成功（排除用例自身干扰）")
    def test_concurrent_create_distinct_tags(self, base_url):
        """对照组：标签各不相同，不应出现任何冲突，用于证明上述失败源于标签竞态"""
        token = _new_user_token(base_url)
        size = 24
        suffix = uuid.uuid4().hex[:6]

        barrier = threading.Barrier(size)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        def worker(idx):
            barrier.wait()
            try:
                r = requests.post(
                    f"{base_url}/api/tasks",
                    json={
                        "title": f"distinct-{suffix}-{idx}",
                        "priority": "low",
                        "tags": [f"tag_{suffix}_{idx}"],
                    },
                    headers=headers,
                    timeout=30,
                )
                return r.status_code
            except Exception:
                return -1

        with ThreadPoolExecutor(max_workers=size) as pool:
            codes = list(pool.map(worker, range(size)))

        assert codes.count(500) == 0, f"不同标签并发仍出现 500，说明存在其他并发问题: {codes}"
        assert all(c in (200, 201) for c in codes), f"存在非 2xx 响应: {sorted(set(codes))}"
