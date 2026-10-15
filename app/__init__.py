"""
app/__init__.py - Flask 应用工厂
负责创建 Flask 应用、初始化扩展、注册蓝图
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# 全局 SQLAlchemy 实例（在 models.py 中引用）
db = SQLAlchemy()


def create_app(test_config=None):
    """
    应用工厂函数

    Args:
        test_config: 可选的配置字典，用于覆盖默认配置（测试用）
    """
    app = Flask(__name__)

    # 加载默认配置
    from app.config import Config

    app.config.from_object(Config)

    # 覆盖配置（测试场景）
    if test_config:
        app.config.update(test_config)

    # 初始化扩展
    CORS(app)
    db.init_app(app)

    # 注册蓝图
    from app.auth import auth_bp
    from app.tasks import tasks_bp
    from app.stats import stats_bp
    from app.attachments import attachments_bp
    from app.comments import comments_bp
    from app.logs import logs_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(tasks_bp, url_prefix="/api/tasks")
    app.register_blueprint(stats_bp, url_prefix="/api/stats")
    app.register_blueprint(attachments_bp, url_prefix="/api/tasks")
    app.register_blueprint(comments_bp, url_prefix="/api/tasks")
    app.register_blueprint(logs_bp, url_prefix="/api/logs")

    # 根路由 - Web 应用（SPA，供 UI 自动化测试使用）
    @app.route("/")
    def index():
        import os
        from flask import send_from_directory

        static_dir = os.path.join(os.path.dirname(__file__), "static")
        return send_from_directory(static_dir, "index.html")

    # 备用路由 - API 控制台（在线调试用）
    @app.route("/console")
    def console():
        from flask import render_template_string

        return render_template_string(INDEX_HTML)

    # 创建数据库表
    with app.app_context():
        db.create_all()

    return app


INDEX_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>任务管理系统 - API 控制台</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: -apple-system, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif;
         background:#f5f6fa; color:#333; padding:20px; }
  h1 { font-size:22px; margin-bottom:4px; }
  .subtitle { color:#888; font-size:14px; margin-bottom:20px; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; max-width:1100px; }
  .card { background:#fff; border-radius:10px; padding:18px; box-shadow:0 1px 4px rgba(0,0,0,.08); }
  .card h2 { font-size:15px; margin-bottom:12px; border-bottom:2px solid #4a90d9; padding-bottom:6px; }
  .api-item { padding:8px 0; border-bottom:1px solid #eee; }
  .api-item:last-child { border-bottom:none; }
  .method { display:inline-block; width:58px; font-weight:700; font-size:12px; }
  .method.GET { color:#2e7d32; }
  .method.POST { color:#1565c0; }
  .method.PATCH { color:#ef6c00; }
  .method.DELETE { color:#c62828; }
  .path { font-family:monospace; font-size:13px; color:#555; }
  .desc { font-size:12px; color:#aaa; margin-left:66px; }
  label { display:block; font-size:13px; font-weight:600; margin:8px 0 4px; }
  input, textarea { width:100%; padding:7px 10px; border:1px solid #ddd; border-radius:6px; font-size:13px; }
  textarea { font-family:monospace; resize:vertical; min-height:60px; }
  button { margin-top:12px; padding:8px 20px; background:#4a90d9; color:#fff; border:none;
           border-radius:6px; cursor:pointer; font-size:14px; }
  button:hover { background:#357abd; }
  .result { margin-top:12px; background:#1e1e1e; color:#4fc3f7; padding:14px; border-radius:6px;
            font-family:monospace; font-size:12px; white-space:pre-wrap; max-height:400px; overflow:auto; }
  .status { display:inline-block; padding:2px 10px; border-radius:4px; font-size:12px; font-weight:700; }
  .status.ok { background:#e8f5e9; color:#2e7d32; }
  .status.err { background:#fbe9e7; color:#c62828; }
  .badge { display:inline-block; background:#e3f2fd; color:#1565c0; padding:2px 8px;
           border-radius:4px; font-size:12px; margin-left:8px; }
</style>
</head>
<body>
  <h1>任务管理系统 <span class="badge">测试练习靶场</span></h1>
  <p class="subtitle">Flask + SQLAlchemy + SQLite + JWT &mdash; 服务运行中</p>

  <div class="grid">
    <div class="card">
      <h2>API 接口列表</h2>
      <div class="api-item">
        <span class="method POST">POST</span><span class="path">/api/auth/register</span>
        <div class="desc">用户注册（username, email, password）</div>
      </div>
      <div class="api-item">
        <span class="method POST">POST</span><span class="path">/api/auth/login</span>
        <div class="desc">用户登录，返回 JWT token</div>
      </div>
      <div class="api-item">
        <span class="method GET">GET</span><span class="path">/api/auth/me</span>
        <div class="desc">获取当前用户信息（需 token）</div>
      </div>
      <div class="api-item">
        <span class="method GET">GET</span><span class="path">/api/tasks</span>
        <div class="desc">查询任务列表（需 token）</div>
      </div>
      <div class="api-item">
        <span class="method POST">POST</span><span class="path">/api/tasks</span>
        <div class="desc">创建任务（title, description, status, priority）</div>
      </div>
      <div class="api-item">
        <span class="method PATCH">PATCH</span><span class="path">/api/tasks/&lt;id&gt;/status</span>
        <div class="desc">更新任务状态（pending &rarr; doing &rarr; done）</div>
      </div>
      <div class="api-item">
        <span class="method DELETE">DELETE</span><span class="path">/api/tasks/&lt;id&gt;</span>
        <div class="desc">删除任务</div>
      </div>
      <div class="api-item">
        <span class="method GET">GET</span><span class="path">/api/stats</span>
        <div class="desc">统计看板（总数/完成率/逾期数）</div>
      </div>
      <div class="api-item">
        <span class="method POST">POST</span><span class="path">/api/tasks/&lt;id&gt;/attachments</span>
        <div class="desc">上传任务附件（multipart/form-data）</div>
      </div>
      <div class="api-item">
        <span class="method GET">GET</span><span class="path">/api/tasks/&lt;id&gt;/attachments</span>
        <div class="desc">获取任务附件列表</div>
      </div>
      <div class="api-item">
        <span class="method GET">GET</span><span class="path">/api/tasks/&lt;id&gt;/attachments/&lt;aid&gt;/download</span>
        <div class="desc">下载附件</div>
      </div>
      <div class="api-item">
        <span class="method POST">POST</span><span class="path">/api/tasks/&lt;id&gt;/comments</span>
        <div class="desc">添加评论（支持 parent_id 回复）</div>
      </div>
      <div class="api-item">
        <span class="method GET">GET</span><span class="path">/api/tasks/&lt;id&gt;/comments</span>
        <div class="desc">获取评论列表（含回复）</div>
      </div>
      <div class="api-item">
        <span class="method GET">GET</span><span class="path">/api/logs</span>
        <div class="desc">查询操作日志（支持 action/resource_type 过滤）</div>
      </div>
      <div class="api-item">
        <span class="method GET">GET</span><span class="path">/api/logs/stats</span>
        <div class="desc">操作日志统计（按类型分组）</div>
      </div>
    </div>

    <div class="card">
      <h2>在线测试</h2>
      <label>用户名</label>
      <input id="username" value="demo">
      <label>密码</label>
      <input id="password" value="demo123" type="password">
      <button onclick="doLogin()">登录获取 Token</button>
      <label>Token</label>
      <input id="token" placeholder="登录后自动填入">
      <label>创建任务 (JSON)</label>
      <textarea id="taskBody">{"title": "新任务", "description": "测试任务", "status": "pending", "priority": "medium"}</textarea>
      <button onclick="createTask()">创建任务</button>
      <button onclick="getTasks()" style="background:#2e7d32">查询任务列表</button>
      <button onclick="getStats()" style="background:#7b1fa2">统计看板</button>
      <button onclick="getLogs()" style="background:#555">操作日志</button>
      <button onclick="getComments()" style="background:#e65100">任务评论</button>
      <label>任务ID</label>
      <input id="taskId" value="1" placeholder="输入任务ID">
      <label>评论内容</label>
      <textarea id="commentBody" placeholder='{"content": "测试评论"}'>{"content": "测试评论"}</textarea>
      <button onclick="addComment()" style="background:#e65100">添加评论</button>
      <div id="result" class="result">等待操作...</div>
    </div>
  </div>

<script>
function showResult(status, data) {
  const el = document.getElementById('result');
  const cls = (status >= 200 && status < 300) ? 'ok' : 'err';
  el.innerHTML = '<span class="status ' + cls + '">HTTP ' + status + '</span>\\n\\n' +
    JSON.stringify(data, null, 2);
}

async function api(method, path, body) {
  const token = document.getElementById('token').value;
  const headers = {'Content-Type': 'application/json'};
  if (token) headers['Authorization'] = 'Bearer ' + token;
  const resp = await fetch(path, {
    method, headers,
    body: body ? JSON.stringify(body) : undefined
  });
  const data = await resp.json().catch(() => ({}));
  showResult(resp.status, data);
  return { status: resp.status, data };
}

async function doLogin() {
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const { status, data } = await api('POST', '/api/auth/login', {username, password});
  if (data.token) {
    document.getElementById('token').value = data.token;
    showResult(status, { message: '登录成功，Token 已填入', user: data.user });
    // 自动拉取任务列表，填入第一个任务ID
    const { data: taskData } = await api('GET', '/api/tasks');
    if (taskData.tasks && taskData.tasks.length > 0) {
      document.getElementById('taskId').value = taskData.tasks[0].id;
    }
  }
}

async function createTask() {
  const body = JSON.parse(document.getElementById('taskBody').value);
  const { status, data } = await api('POST', '/api/tasks', body);
  if (status === 201 && data.task) {
    document.getElementById('taskId').value = data.task.id;
  }
}

function getTasks() { api('GET', '/api/tasks'); }
function getStats() { api('GET', '/api/stats'); }

async function addComment() {
  const taskId = document.getElementById('taskId').value;
  const body = JSON.parse(document.getElementById('commentBody').value);
  await api('POST', '/api/tasks/' + taskId + '/comments', body);
}

async function getComments() {
  const taskId = document.getElementById('taskId').value;
  await api('GET', '/api/tasks/' + taskId + '/comments');
}

async function getLogs() {
  await api('GET', '/api/logs?limit=20');
}
</script>
</body>
</html>
"""
