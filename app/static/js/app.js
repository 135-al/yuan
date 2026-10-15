/* =========================================================
   TaskFlow - 前端逻辑（原生 JS，无框架依赖）
   ========================================================= */

const API = {
  token: localStorage.getItem('tf_token') || null,
  user: JSON.parse(localStorage.getItem('tf_user') || 'null'),
};

let currentTaskId = null;

/* ---------------- 工具函数 ---------------- */

function $(sel) { return document.querySelector(sel); }

function toast(msg, type = '') {
  const el = $('#toast');
  el.textContent = msg;
  el.className = 'toast ' + type;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.className = 'toast hidden'; }, 2600);
}

async function api(method, path, body, isForm = false) {
  const headers = {};
  if (API.token) headers['Authorization'] = 'Bearer ' + API.token;
  if (!isForm && body !== undefined) headers['Content-Type'] = 'application/json';

  const resp = await fetch(path, {
    method,
    headers,
    body: isForm ? body : (body !== undefined ? JSON.stringify(body) : undefined),
  });

  let data = {};
  try { data = await resp.json(); } catch (e) { data = {}; }

  if (resp.status === 401 && API.token) {
    logout(true);
    toast('登录已失效，请重新登录', 'error');
  }
  return { status: resp.status, ok: resp.ok, data };
}

/* ---------------- 视图切换 ---------------- */

function showView(name) {
  ['auth', 'dashboard', 'task', 'logs'].forEach(v => {
    const el = $('#view-' + v);
    if (el) el.classList.toggle('hidden', v !== name);
  });
  const authed = name !== 'auth';
  $('#topbar').classList.toggle('hidden', !authed);
  document.querySelectorAll('.nav-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.view === name);
  });
}

/* ---------------- 登录 / 注册 ---------------- */

async function login() {
  const username = $('#login-username').value.trim();
  const password = $('#login-password').value;
  const msg = $('#auth-message');

  if (!username || !password) {
    msg.className = 'auth-message error';
    msg.textContent = '请输入用户名和密码';
    return;
  }

  const { ok, data } = await api('POST', '/api/auth/login', { username, password });
  if (ok) {
    API.token = data.token;
    API.user = data.user;
    localStorage.setItem('tf_token', data.token);
    localStorage.setItem('tf_user', JSON.stringify(data.user));
    msg.className = 'auth-message ok';
    msg.textContent = '';
    enterApp();
  } else {
    msg.className = 'auth-message error';
    msg.textContent = data.error || '登录失败';
  }
}

async function register() {
  const username = $('#reg-username').value.trim();
  const email = $('#reg-email').value.trim();
  const password = $('#reg-password').value;
  const msg = $('#auth-message');

  if (!username || !email || !password) {
    msg.className = 'auth-message error';
    msg.textContent = '请填写完整的注册信息';
    return;
  }

  const { ok, data } = await api('POST', '/api/auth/register', { username, email, password });
  if (ok) {
    msg.className = 'auth-message ok';
    msg.textContent = '注册成功，正在登录…';
    API.token = data.token;
    API.user = data.user;
    localStorage.setItem('tf_token', data.token);
    localStorage.setItem('tf_user', JSON.stringify(data.user));
    setTimeout(enterApp, 400);
  } else {
    msg.className = 'auth-message error';
    msg.textContent = data.error || '注册失败';
  }
}

function logout(silent = false) {
  API.token = null;
  API.user = null;
  localStorage.removeItem('tf_token');
  localStorage.removeItem('tf_user');
  if (!silent) toast('已退出登录');
  showView('auth');
}

function enterApp() {
  $('#current-user').textContent = API.user ? API.user.username : '';
  showView('dashboard');
  refreshAll();
}

/* ---------------- 看板 ---------------- */

async function refreshAll() {
  await Promise.all([loadStats(), loadTasks()]);
}

async function loadStats() {
  const { ok, data } = await api('GET', '/api/stats');
  if (!ok) return;
  $('#stat-total').textContent = data.total;
  $('#stat-pending').textContent = data.pending;
  $('#stat-doing').textContent = data.doing;
  $('#stat-done').textContent = data.done;
  $('#stat-overdue').textContent = data.overdue;
  $('#stat-rate').textContent = data.completion_rate + '%';
}

const STATUS_TEXT = { pending: '待办', doing: '进行中', done: '已完成' };
const NEXT_STATUS = { pending: 'doing', doing: 'done', done: 'pending' };
const NEXT_TEXT = { pending: '开始', doing: '完成', done: '重开' };

async function loadTasks() {
  const status = $('#filter-status').value;
  const qs = status ? '?status=' + status : '';
  const { ok, data } = await api('GET', '/api/tasks' + qs);
  const list = $('#task-list');
  list.innerHTML = '';

  if (!ok) return;
  const tasks = data.tasks || [];
  $('#task-empty').classList.toggle('hidden', tasks.length > 0);

  tasks.forEach(t => {
    const li = document.createElement('li');
    li.className = 'task-item';
    li.setAttribute('data-testid', 'task-item');
    li.setAttribute('data-task-id', t.id);
    li.innerHTML = `
      <span class="task-title" data-testid="task-item-title">${escapeHtml(t.title || '(空标题)')}</span>
      <span class="badge badge-${t.status}" data-testid="task-status">${STATUS_TEXT[t.status] || t.status}</span>
      <span class="badge-priority ${t.priority}" data-testid="task-priority-badge">${t.priority}</span>
      <span class="task-meta">💬 ${t.comment_count} · 📎 ${t.attachment_count}</span>
      <span class="task-actions">
        <button class="btn btn-ghost btn-sm" data-testid="btn-advance"
                data-id="${t.id}" data-next="${NEXT_STATUS[t.status]}">${NEXT_TEXT[t.status]}</button>
        <button class="btn btn-danger btn-sm" data-testid="btn-delete" data-id="${t.id}">删除</button>
      </span>`;
    li.querySelector('[data-testid="task-item-title"]').addEventListener('click', () => openTask(t.id));
    li.querySelector('[data-testid="btn-advance"]').addEventListener('click', e => {
      e.stopPropagation();
      advanceTask(t.id, NEXT_STATUS[t.status]);
    });
    li.querySelector('[data-testid="btn-delete"]').addEventListener('click', e => {
      e.stopPropagation();
      deleteTask(t.id);
    });
    list.appendChild(li);
  });
}

async function createTask() {
  const title = $('#task-title').value;
  const description = $('#task-desc').value;
  const priority = $('#task-priority').value;
  const tags = $('#task-tags').value.split(/[,，]/).map(s => s.trim()).filter(Boolean);

  const { ok, data } = await api('POST', '/api/tasks', { title, description, priority, tags });
  if (ok) {
    toast('任务创建成功', 'ok');
    $('#task-title').value = '';
    $('#task-desc').value = '';
    $('#task-tags').value = '';
    refreshAll();
  } else {
    toast(data.error || '创建失败', 'error');
  }
}

async function advanceTask(id, next) {
  const { ok } = await api('PATCH', `/api/tasks/${id}/status`, { status: next });
  if (ok) { toast('状态已更新', 'ok'); refreshAll(); }
  else toast('状态更新失败', 'error');
}

async function deleteTask(id) {
  const { ok } = await api('DELETE', `/api/tasks/${id}`);
  if (ok) { toast('任务已删除', 'ok'); refreshAll(); }
  else toast('删除失败', 'error');
}

/* ---------------- 任务详情 ---------------- */

async function openTask(id) {
  currentTaskId = id;
  showView('task');
  const { ok, data } = await api('GET', `/api/tasks/${id}`);
  if (!ok) { toast('加载任务失败', 'error'); return; }
  const t = data.task;
  $('#detail-title').textContent = t.title || '(空标题)';
  $('#detail-meta').textContent =
    `状态：${STATUS_TEXT[t.status]} · 优先级：${t.priority} · 创建于 ${(t.created_at || '').slice(0, 19).replace('T', ' ')}`;
  loadComments(id);
  loadAttachments(id);
}

async function loadComments(taskId) {
  const { ok, data } = await api('GET', `/api/tasks/${taskId}/comments`);
  const list = $('#comment-list');
  list.innerHTML = '';
  if (!ok) return;

  (data.comments || []).forEach(c => {
    const li = document.createElement('li');
    li.className = 'comment-item';
    li.setAttribute('data-testid', 'comment-item');
    li.innerHTML = `<div class="comment-head"><span class="comment-author">${escapeHtml(c.username || '')}</span></div>
                    <div class="comment-content" data-testid="comment-content">${escapeHtml(c.content)}</div>`;
    (c.replies || []).forEach(r => {
      const rl = document.createElement('div');
      rl.className = 'comment-reply';
      rl.setAttribute('data-testid', 'comment-reply');
      rl.innerHTML = `<div class="comment-head"><span class="comment-author">${escapeHtml(r.username || '')}</span></div>
                      <div class="comment-content">${escapeHtml(r.content)}</div>`;
      li.appendChild(rl);
    });
    list.appendChild(li);
  });
}

async function addComment() {
  const content = $('#comment-input').value.trim();
  if (!content) { toast('评论内容不能为空', 'error'); return; }
  const { ok, data } = await api('POST', `/api/tasks/${currentTaskId}/comments`, { content });
  if (ok) {
    $('#comment-input').value = '';
    toast('评论已发布', 'ok');
    loadComments(currentTaskId);
  } else {
    toast(data.error || '评论失败', 'error');
  }
}

async function loadAttachments(taskId) {
  const { ok, data } = await api('GET', `/api/tasks/${taskId}/attachments`);
  const list = $('#attachment-list');
  list.innerHTML = '';
  if (!ok) return;
  (data.attachments || []).forEach(a => {
    const li = document.createElement('li');
    li.className = 'attachment-item';
    li.setAttribute('data-testid', 'attachment-item');
    li.innerHTML = `<span>📎</span>
      <a href="${a.download_url}?token=${API.token}" data-testid="attachment-link">${escapeHtml(a.filename)}</a>
      <span class="task-meta">${(a.file_size / 1024).toFixed(1)} KB</span>`;
    list.appendChild(li);
  });
}

async function uploadFile() {
  const input = $('#file-input');
  if (!input.files.length) { toast('请先选择文件', 'error'); return; }
  const fd = new FormData();
  fd.append('file', input.files[0]);
  const { ok, data } = await api('POST', `/api/tasks/${currentTaskId}/attachments`, fd, true);
  if (ok) {
    toast('附件上传成功', 'ok');
    input.value = '';
    loadAttachments(currentTaskId);
  } else {
    toast(data.error || '上传失败', 'error');
  }
}

/* ---------------- 操作日志 ---------------- */

async function loadLogs() {
  const action = $('#filter-action').value;
  const qs = action ? '?action=' + action : '';
  const { ok, data } = await api('GET', '/api/logs' + qs);
  const tbody = $('#log-list');
  tbody.innerHTML = '';
  if (!ok) return;

  const logs = data.logs || [];
  $('#log-empty').classList.toggle('hidden', logs.length > 0);

  logs.forEach(l => {
    const tr = document.createElement('tr');
    tr.setAttribute('data-testid', 'log-row');
    tr.innerHTML = `
      <td>${(l.created_at || '').slice(0, 19).replace('T', ' ')}</td>
      <td>${escapeHtml(l.username || '-')}</td>
      <td><span class="badge badge-doing">${l.action}</span></td>
      <td>${l.resource_type || '-'}#${l.resource_id ?? '-'}</td>
      <td class="task-meta">${escapeHtml(JSON.stringify(l.detail || {}))}</td>`;
    tbody.appendChild(tr);
  });
}

/* ---------------- 工具 ---------------- */

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* ---------------- 事件绑定 ---------------- */

document.addEventListener('DOMContentLoaded', () => {
  // 登录/注册 tab
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t === tab));
      const isLogin = tab.dataset.tab === 'login';
      $('#form-login').classList.toggle('hidden', !isLogin);
      $('#form-register').classList.toggle('hidden', isLogin);
      $('#auth-message').textContent = '';
    });
  });

  $('#btn-login').addEventListener('click', login);
  $('#btn-register').addEventListener('click', register);
  $('#login-password').addEventListener('keydown', e => { if (e.key === 'Enter') login(); });
  $('#reg-password').addEventListener('keydown', e => { if (e.key === 'Enter') register(); });

  // 顶部导航
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const v = btn.dataset.view;
      showView(v);
      if (v === 'dashboard') refreshAll();
      if (v === 'logs') loadLogs();
    });
  });
  $('#topbar').querySelector('[data-testid="btn-logout"]').addEventListener('click', () => logout());

  // 看板
  $('#btn-create-task').addEventListener('click', createTask);
  $('#btn-refresh').addEventListener('click', refreshAll);
  $('#filter-status').addEventListener('change', loadTasks);

  // 详情
  $('#btn-back').addEventListener('click', () => { showView('dashboard'); refreshAll(); });
  $('#btn-add-comment').addEventListener('click', addComment);
  $('#comment-input').addEventListener('keydown', e => { if (e.key === 'Enter') addComment(); });
  $('#btn-upload').addEventListener('click', uploadFile);

  // 日志
  $('#btn-refresh-logs').addEventListener('click', loadLogs);
  $('#filter-action').addEventListener('change', loadLogs);

  // 自动登录
  if (API.token && API.user) enterApp();
  else showView('auth');
});
