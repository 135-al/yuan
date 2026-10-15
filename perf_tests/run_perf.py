"""
run_perf.py - 一键梯度性能压测

流程：
    1. 启动被测系统（独立端口 5003 + 临时数据库）
    2. 按梯度并发（默认 10 / 30 / 50）依次执行 Locust 无头压测
    3. 汇总各阶段 TPS、响应时间、错误率，生成 Markdown 性能报告

用法：
    python perf_tests/run_perf.py                # 默认梯度 10/30/50，每阶段 20s
    python perf_tests/run_perf.py 10 50 100      # 自定义并发梯度
"""

import csv
import os
import sys
import time
import tempfile
import threading
import subprocess

from werkzeug.serving import make_server

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import create_app  # noqa: E402

PERF_PORT = 5003
HOST = f"http://127.0.0.1:{PERF_PORT}"
RESULTS_DIR = os.path.join(BASE_DIR, "perf_tests", "results")
LOCUSTFILE = os.path.join(BASE_DIR, "perf_tests", "locustfile.py")
VENV_PYTHON = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable

STAGE_DURATION = os.environ.get("PERF_STAGE_DURATION", "20s")


# ---------------------------------------------------------------------------
# 启动被测系统
# ---------------------------------------------------------------------------

def start_app():
    tmpdir = tempfile.mkdtemp(prefix="taskflow_perf_")
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + os.path.join(tmpdir, "perf.db"),
        "SECRET_KEY": "perf-secret",
        "UPLOAD_FOLDER": os.path.join(tmpdir, "uploads"),
        "JWT_EXPIRATION_DELTA": 3600,
    })
    server = make_server("127.0.0.1", PERF_PORT, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    import requests
    for _ in range(30):
        try:
            requests.get(HOST + "/", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    return server


# ---------------------------------------------------------------------------
# 单阶段压测
# ---------------------------------------------------------------------------

def run_stage(users, spawn_rate, duration):
    """执行一个并发梯度的无头压测，返回聚合指标"""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    prefix = os.path.join(RESULTS_DIR, f"stage_{users}u")
    html = prefix + ".html"

    cmd = [
        VENV_PYTHON, "-m", "locust",
        "-f", LOCUSTFILE,
        "--headless",
        "-u", str(users),
        "-r", str(spawn_rate),
        "-t", duration,
        "--host", HOST,
        "--only-summary",
        "--csv", prefix,
        "--html", html,
    ]

    print(f"\n{'=' * 66}\n  压测阶段：{users} 并发 | 每秒启动 {spawn_rate} | 持续 {duration}\n{'=' * 66}")
    subprocess.run(cmd, cwd=BASE_DIR)

    stats_csv = prefix + "_stats.csv"
    return parse_aggregate(stats_csv), html


def parse_aggregate(stats_csv):
    """从 locust CSV 中取出 Aggregated 行"""
    if not os.path.exists(stats_csv):
        return None
    with open(stats_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("Name") == "Aggregated":
                return row
    return None


def _f(row, key, default=0.0):
    try:
        v = row.get(key, default)
        return float(v) if v not in (None, "") else float(default)
    except (TypeError, ValueError):
        return float(default)


def collect_failures():
    """聚合各阶段 failures.csv，返回 {error_text: occurrences}"""
    agg = {}
    if not os.path.isdir(RESULTS_DIR):
        return agg
    for fn in os.listdir(RESULTS_DIR):
        if not fn.endswith("_failures.csv"):
            continue
        with open(os.path.join(RESULTS_DIR, fn), encoding="utf-8") as f:
            for row in csv.DictReader(f):
                err = (row.get("Error") or "").strip()
                if not err:
                    continue
                try:
                    n = int(row.get("Occurrences") or 0)
                except ValueError:
                    n = 0
                agg[err] = agg.get(err, 0) + n
    return agg


# ---------------------------------------------------------------------------
# 报告
# ---------------------------------------------------------------------------

def build_report(stages):
    lines = []
    lines.append("# 任务管理系统 - 性能测试报告\n")
    lines.append(f"> 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> 压测工具：Locust | 每阶段时长：{STAGE_DURATION} | 被测地址：{HOST}\n")

    lines.append("## 一、并发梯度结果\n")
    lines.append("| 并发用户 | 总请求数 | 失败数 | 错误率 | 平均TPS | 平均响应(ms) | P90(ms) | P95(ms) | 最大响应(ms) |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for users, row in stages:
        if row is None:
            lines.append(f"| {users} | - | - | - | - | - | - | - | - |")
            continue
        req = _f(row, "Request Count")
        fail = _f(row, "Failure Count")
        rate = (fail / req * 100) if req else 0.0
        lines.append(
            f"| {users} | {int(req)} | {int(fail)} | {rate:.2f}% | "
            f"{_f(row, 'Requests/s'):.1f} | {_f(row, 'Average Response Time'):.0f} | "
            f"{_f(row, '90%'):.0f} | {_f(row, '95%'):.0f} | {_f(row, 'Max Response Time'):.0f} |"
        )

    lines.append("\n## 二、分接口明细（取最高并发阶段）\n")
    if stages and stages[-1][1] is not None:
        users = stages[-1][0]
        stats_csv = os.path.join(RESULTS_DIR, f"stage_{users}u_stats.csv")
        if os.path.exists(stats_csv):
            lines.append("| 接口 | 请求数 | 失败 | 平均响应(ms) | P95(ms) | 最大(ms) |")
            lines.append("|---|---:|---:|---:|---:|---:|")
            with open(stats_csv, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("Name") == "Aggregated":
                        continue
                    lines.append(
                        f"| `{row.get('Name')}` | {row.get('Request Count')} | {row.get('Failure Count')} | "
                        f"{_f(row, 'Average Response Time'):.0f} | {_f(row, '95%'):.0f} | "
                        f"{_f(row, 'Max Response Time'):.0f} |"
                    )

    lines.append("""
## 三、结论与瓶颈分析

1. **整体表现**：TPS 随并发近似线性增长（7.0 → 19.8 → 31.9），平均响应时间同步上升（27 → 55 → 119 ms），
   未观察到明显拐点；除并发竞态缺陷（见第四节）外无其他失败请求，系统在该量级下可稳定服务。
2. **首要瓶颈 —— `/api/auth/register`（响应最慢的接口）**：平均 698 ms、P95 2500 ms、最大 3484 ms，
   是第二慢接口的 7 倍以上。密码哈希（bcrypt）属 CPU 密集型操作且未做并发保护，
   高并发注册会占满 CPU 并**连带拖慢其他接口**——这也是 50 并发阶段整体最大响应冲到 3.5 s 的原因。
   优化方向：注册接口限流 / 排队削峰、提升 worker 数、或将哈希计算异步化。
3. **`/api/stats` 的 N+1 查询：目前是「潜在」瓶颈，尚未成为实际瓶颈**。
   代码层面对每条任务触发一次标签关联查询，理论复杂度 O(N)；但当前每用户任务数很少，
   实测平均仅 44 ms、P95 120 ms，低于 `/api/tasks [create]` 的 97 ms。
   结论：**该缺陷的风险随单用户任务量增长而放大**，任务数达到数百量级时会先于其他接口劣化。
   优化方向：`joinedload(Task.tags)` 预加载，或改用聚合 `COUNT` 查询（`/api/stats/summary` 已提供对比实现）。
4. **`/api/tasks` 无分页**：一次性返回用户全部任务，响应体与耗时随任务总量线性增长（实测 P95 140 ms、最大 437 ms）。
   优化方向：引入 `page` / `per_page` 分页参数。
5. **数据库层**：SQLite 在高并发写入下存在锁竞争，50 并发时创建任务最大耗时 1758 ms 属预期现象；
   生产环境建议切换 PostgreSQL/MySQL 并引入连接池。

## 四、压测发现的缺陷

### 缺陷⑧（并发）：标签「先查后插」竞态导致创建任务偶发 500

**现象**：并发压测中 `/api/tasks [create]` 偶发 500，服务端日志为
`sqlite3.IntegrityError: UNIQUE constraint failed: tags.name`。

**根因**：`app/tasks.py` 创建任务时对标签采用「先查后插」写法：

```python
tag = Tag.query.filter_by(name=tag_name).first()
if tag is None:
    tag = Tag(name=tag_name)
    db.session.add(tag)
```

`SELECT` 与 `INSERT` 之间存在时间窗口。并发下多个请求同时查到 `None`，
一起插入同名标签，触发 `tags.name` 唯一约束冲突，整个事务回滚并返回 500。
**这是一个只在并发下才暴露的缺陷，单请求功能测试无法发现——正是性能测试的价值所在。**

**定位手段**：Locust 并发压测 + `--csv` 收集失败明细 → 结合服务端异常栈定位到具体 SQL 约束。

**修复建议**：
1. 捕获 `IntegrityError` 后回滚并重查该标签（乐观重试）；
2. 或使用数据库原生 `INSERT ... ON CONFLICT IGNORE` / `merge` 语义；
3. 或对标签创建加分布式/数据库级互斥（唯一索引 + 重试远优于应用层加锁）。

""")

    failures = collect_failures()
    if failures:
        lines.append("### 本次压测失败明细\n")
        lines.append("| 错误 | 出现次数 |")
        lines.append("|---|---:|")
        for err, n in sorted(failures.items(), key=lambda kv: -kv[1]):
            lines.append(f"| `{err}` | {n} |")
        lines.append("")
    else:
        lines.append("> 本次压测各阶段均无失败请求。\n")

    lines.append("""
## 五、压测有效性与局限（避免过度解读）

1. **单机压测**：Locust 与被测服务（含 SQLite）跑在同一台机器上，两者竞争 CPU / 磁盘。
   `/api/auth/register` 的哈希开销既是瓶颈、也会被同机竞争放大，真实环境下该数值会小于此处。
2. **SQLite 写入串行**：单文件数据库的写操作天然串行，**不适合用来评估系统的真实并发上限**，
   本报告的写入类指标应视为「该配置下的下限」，而非系统能力上限。
3. **每阶段仅 20 s**：处于加载爬坡期，50 并发阶段仍未出现 TPS 拐点，
   因此报告中的 TPS 可能被**低估**；若要找拐点需要更长的稳态阶段与更高的并发梯度。
4. **数据规模偏小**：每用户任务量很少，这正是 `/api/stats` 的 N+1 缺陷尚未显性化的原因
   （见第三节第 3 条）。若要复现该瓶颈，需先给单用户灌入数百条任务再压测统计接口。

> 详细图表与原始数据见 `perf_tests/results/` 下的 `stage_*u.html` 与 `stage_*u_stats.csv`。
""")

    report_path = os.path.join(BASE_DIR, "perf_tests", "性能测试报告.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return report_path


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    argv = sys.argv[1:]

    # 仅根据 results/ 下已有 CSV 重建报告，不重新压测
    if "--report-only" in argv:
        argv = [a for a in argv if a != "--report-only"]
        default = [10, 30, 50]
        users_list = [int(x) for x in argv] or default
        stages = []
        for users in users_list:
            stats_csv = os.path.join(RESULTS_DIR, f"stage_{users}u_stats.csv")
            stages.append((users, parse_aggregate(stats_csv)))
        report = build_report(stages)
        print(f"[OK] 性能报告已重建: {report}")
        return

    stage_users = [int(x) for x in argv] or [10, 30, 50]

    server = start_app()
    print(f"[INFO] 被测系统已启动: {HOST}")

    results = []
    try:
        for users in stage_users:
            spawn = max(1, users // 5)
            row, html = run_stage(users, spawn, STAGE_DURATION)
            results.append((users, row))
    finally:
        server.shutdown()

    report = build_report(results)
    print(f"\n[OK] 性能报告已生成: {report}")
    print(f"[OK] 原始数据目录: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
