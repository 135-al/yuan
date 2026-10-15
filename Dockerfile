# ============================================================
#  被测系统镜像 —— 任务管理系统（Flask 测试靶场）
#
#  设计要点（面试可展开）：
#   1. 依赖层与代码层分离：requirements.txt 不变时命中构建缓存，
#      改代码重构建只需秒级。这是 Docker 分层的最基本收益。
#   2. 非 root 用户运行：容器内进程遵循最小权限原则。
#   3. 零源码改动：不向被测系统注入 /health 路由、不改任何业务逻辑。
#      靶场系统的行为必须与本地运行完全一致，否则历史用例基线会失真。
#      健康检查因此改为直接探测根路由（返回 SPA）。
#   4. 数据路径可见化：DATABASE_URL 指向 /app/data（sqlite 绝对路径需四斜杠），
#      UPLOAD_FOLDER 无需覆盖 —— config.py 中 basedir 在容器内算出来
#      恰好是 /app，故默认即 /app/uploads，直接挂卷即可。
# ============================================================

FROM python:3.13-slim-bookworm

LABEL org.opencontainers.image.title="taskflow-app" \
      org.opencontainers.image.description="Flask 任务管理系统（自动化测试练习靶场）" \
      org.opencontainers.image.authors="task-system"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATABASE_URL=sqlite:////app/data/task.db

WORKDIR /app

# ---- 依赖先行：单独一层，最大化构建缓存命中率 ----
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ---- 非 root 运行用户（最小权限）----
RUN useradd --create-home --uid 10001 appuser

# ---- 代码后置：改动最频繁，放最后一层 ----
COPY app/ ./app/
COPY run.py check.py ./

# ---- 数据 / 上传目录：预先创建并授权给运行用户 ----
# task.db 落在 /app/data（由 DATABASE_URL 指定）
# 附件落在 /app/uploads（config.py 默认路径，直接挂卷）
RUN mkdir -p /app/data /app/uploads && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

# ---- 健康检查：探测根路由，不污染被测系统源码 ----
# 容器健康检查是编排依赖（depends_on: service_healthy）的判断依据
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=10 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/', timeout=2).status==200 else 1)"

CMD ["python", "run.py"]
