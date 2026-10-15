 任务管理系统（测试练习靶场）

基于 Flask + SQLAlchemy + SQLite + pytest 的任务管理系统，内置 7 个刻意缺陷，用于测试练习。

## 项目结构

```
task-system/
├── app/                      # 被测系统（Flask）
│   ├── __init__.py           # 应用工厂 + 蓝图注册 + 首页路由
│   ├── config.py             # 配置（JWT、数据库、上传目录）
│   ├── models.py             # 数据模型（User/Task/Tag/Attachment/Comment/OperationLog）
│   ├── auth.py               # 注册/登录/JWT 认证
│   ├── tasks.py              # 任务 CRUD + 状态流转 + 标签
│   ├── stats.py              # 统计看板（总数/完成率/逾期数）
│   ├── attachments.py        # 附件上传/下载/列表/删除
│   ├── comments.py           # 评论增删改查 + 层级回复
│   ├── logs.py               # 操作日志埋点 + 查询/统计
│   └── static/               # 前端 SPA（index.html + css + js）
├── tests/                    # 基础功能测试（pytest + test_client，30 用例）
├── api_tests/                # 接口自动化测试（requests + pytest + Allure，75 用例）
├── ui_tests/                 # UI 自动化测试（Playwright + PO，28 用例）
├── perf_tests/               # 性能测试（Locust 梯度压测 + 报告生成）
├── concurrency_tests/        # 并发测试（标签竞态缺陷复现，2 用例）
├── .github/workflows/ci.yml  # CI 流水线（GitHub Actions，4 个 Job）
├── run.py                    # 启动入口
├── run_tests.py              # 接口测试一键执行 + 出报告
├── gen_report.py             # Allure 数据 → 独立 HTML 报告
├── pytest.ini                # 基础测试配置
├── pytest_allure.ini         # 接口自动化配置
├── pytest_ui.ini             # UI 自动化配置
├── requirements.txt          # 运行依赖
├── requirements-test.txt     # 测试依赖
└── README.md
```

## 启动步骤

### 1. 安装依赖

```bash
cd task-system
pip install -r requirements.txt
```

### 2. 运行验证脚本（可选）

```bash
python check.py
```

### 3. 启动服务

```bash
python run.py
```

服务启动后访问 `http://127.0.0.1:5000`。

### 4. 运行测试

```bash
pytest -v
```

## API 接口一览

### 认证

| 方法   | 路径                | 说明       |
| ------ | ------------------- | ---------- |
| POST   | /api/auth/register  | 用户注册   |
| POST   | /api/auth/login     | 用户登录   |
| GET    | /api/auth/me        | 当前用户   |

### 任务

| 方法   | 路径                     | 说明           |
| ------ | ------------------------ | -------------- |
| POST   | /api/tasks               | 创建任务       |
| GET    | /api/tasks               | 获取任务列表   |
| GET    | /api/tasks/\<id\>        | 获取任务详情   |
| PUT    | /api/tasks/\<id\>        | 更新任务       |
| DELETE | /api/tasks/\<id\>        | 删除任务       |
| PATCH  | /api/tasks/\<id\>/status | 更新任务状态   |
| GET    | /api/tasks/tags          | 获取所有标签   |

### 统计

| 方法 | 路径             | 说明           |
| ---- | ---------------- | -------------- |
| GET  | /api/stats       | 统计看板（N+1）|
| GET  | /api/stats/summary | 统计摘要      |

## 使用示例

```bash
# 注册
curl -X POST http://127.0.0.1:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"pass123"}'

# 登录获取 Token
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"pass123"}'

# 创建任务
curl -X POST http://127.0.0.1:5000/api/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -d '{"title":"完成项目报告","priority":"high","tags":["工作","紧急"]}'

# 获取统计
curl http://127.0.0.1:5000/api/stats \
  -H "Authorization: Bearer <YOUR_TOKEN>"
```

## 刻意引入的缺陷清单

| # | 缺陷 | 位置 | 影响 |
|---|------|------|------|
| 1 | 删除任务无归属校验 | `tasks.py delete_task()` | 可删除其他用户任务 |
| 2 | 状态可从 done 改回 pending | `tasks.py update_status()` | 状态流转无约束 |
| 3 | 创建任务不校验 title 非空 | `tasks.py create_task()` | 可创建空标题任务 |
| 4 | 任务列表无分页 | `tasks.py get_tasks()` | 数据量大时性能差 |
| 5 | 统计接口 N+1 查询 | `stats.py get_stats()` | 每条任务触发额外 SQL |
| 6 | 登录接口无限流 | `auth.py login()` | 可暴力破解密码 |
| 7 | JWT 过期时间 7 天 | `config.py JWT_EXPIRATION_DELTA` | Token 泄露风险高 |

## 由测试发现的缺陷（非刻意埋设）

| # | 缺陷 | 发现方式 | 影响 |
|---|------|----------|------|
| 8 | 标签「先查后插」竞态 | Locust 并发压测 | 并发插入同名标签触发 `tags.name` 唯一约束冲突，创建任务偶发 500；单请求功能测试无法发现，已固化为 `concurrency_tests/` 下的复现用例 |

## 技术栈

- Flask 3.0 - Web 框架
- Flask-SQLAlchemy 3.1 - ORM
- Flask-CORS 4.0 - 跨域支持
- PyJWT 2.8 - JWT 认证
- SQLite - 数据库

## 测试体系

本项目同时是一个**测试练习靶场**，在系统内置 7 个刻意缺陷的基础上，
搭建了「接口 + UI + 性能 + 并发 + CI」五位一体的自动化测试体系，
并额外发现 1 个非预期的并发竞态缺陷（详见 `concurrency_tests/`）。

| 层级 | 目录 | 用例数 | 技术栈 |
|---|---|---:|---|
| 基础功能测试 | `tests/` | 30 | pytest + Flask test_client |
| 接口自动化 | `api_tests/` | 75 | requests + pytest + Allure |
| UI 自动化 | `ui_tests/` | 28 | Playwright + Page Object |
| 并发测试 | `concurrency_tests/` | 2 | threading + Barrier + requests |
| 性能测试 | `perf_tests/` | 6 类事务 | Locust |

> 完整说明见 **[测试体系说明.md](测试体系说明.md)**，简历素材见 **[简历项目描述.md](简历项目描述.md)**。

### 快速运行（本地 venv）

```bash
# 接口自动化测试（+ 生成 allure-report.html）
python run_tests.py

# UI 自动化测试（首次需先安装浏览器内核）
python -m playwright install chromium
python -m pytest -c pytest_ui.ini

# 性能压测（默认 10/30/50 并发梯度）
python perf_tests/run_perf.py
python perf_tests/run_perf.py --report-only    # 仅用已有 CSV 重建报告

# 并发测试（xfail = 已知缺陷已成功复现）
python -m pytest concurrency_tests -v -rx

# 覆盖率
python -m pytest api_tests --cov=app --cov-report=term-missing
```

### Docker 一键运行（无需本地 venv / 浏览器）

```bash
# 首次：构建镜像
docker compose build

# 启动被测系统，访问 http://localhost:5000
docker-run.bat up           # Windows
./docker-run.sh up          # Linux / macOS / Git Bash

# 跑各层测试
docker-run.bat api          # 接口自动化（75 用例 + 覆盖率）
docker-run.bat ui           # UI 自动化（28 用例，跨容器访问 app 服务）
docker-run.bat unit         # 基础功能测试
docker-run.bat race         # 并发缺陷复现
docker-run.bat perf         # 梯度性能压测
docker-run.bat all          # 全套
```

**核心编排思路**：
- `app` 服务是「被测系统」，配健康检查；`ui-tests` 通过 `UI_BASE_URL` 连过来做跨容器集成验证
- 接口 / 并发 / 性能 层在各自容器内自起 Flask（依赖白盒 DB fixture），互不冲突可并行
- 所有报告（Allure 数据 / 覆盖率 / 失败截图 / Trace）统一落到宿主机 `./reports/`，容器销毁后报告仍在
- 用 `profiles` 隔离：默认 `up` 只起 app；测试、压测按需引入

> 详细设计见 **[测试体系说明.md](测试体系说明.md)** 第七节。

### 持续集成

`.github/workflows/ci.yml` 定义了四段流水线：接口回归 + 覆盖率、UI 回归、性能压测、并发测试，
产物（Allure 报告 / 失败截图 / Trace / 性能报告）自动归档到 Actions Artifacts。

```yaml
on:
  push:            branches: [ main, master, develop ]
  pull_request:    branches: [ main, master, develop ]
  workflow_dispatch:  # 手动触发，可自定义压测梯度
```

#### CI 流水线本地验证状态

四条流水线的**命令已在本地逐条实跑**，逻辑与通过率均已确认：

| Job | CI 命令 | 本地实跑结果 |
|---|---|---|
| api-tests | `pytest api_tests tests -c pytest_allure.ini --cov=app` | ✅ **105 passed** |
| ui-tests | `pytest -c pytest_ui.ini` | ✅ **28 passed** |
| concurrency-tests | `pytest concurrency_tests -v -rx --alluredir=...` | ✅ **1 passed, 1 xfailed**（缺陷⑧ 如期复现） |
| perf-tests | `python perf_tests/run_perf.py` | ✅ 梯度跑通 |

尚未覆盖的部分属于 **GitHub 运行环境特有**：Linux 路径语义、`playwright install --with-deps`
的系统依赖安装、`workflow_dispatch` 入参注入。需在真实 Actions 上首次运行时确认。

#### 推送到 GitHub 并触发 CI

```bash
# 本机未装 gh CLI，请在 GitHub 网页新建空仓库（不要勾选 README/.gitignore），然后：
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git branch -M main
git push -u origin main

# 之后每次 push 自动触发流水线；也可在 Actions 页面手动 workflow_dispatch 触发，
# 并可自定义 perf_stage_users（如 "20 50 100"）调整压测梯度。
```

> ⚠️ 仓库默认是公开的。若改为 private 请注意：`.coverage*` 与 `*.db` 已被 `.gitignore` 排除，
> 虚拟环境 `.venv/` 同样不会入库 —— 已核对，58 个纳入文件均无敏感或大体积产物。

