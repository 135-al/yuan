# GitHub 推送操作指南

> 本机上执行的所有网络检测都在受限沙箱内完成，**不代表你本机真实网络**。
> 请以你在本机 PowerShell 中运行 `push-to-github.bat` 的实际结果为准。

---

## 第 1 步：在网页端新建空仓库

登录 GitHub 后，有两种入口：

- **入口 A**：右上角 `+` 号 → `New repository`
- **入口 B**：直接访问 `https://github.com/new`

按下面填写：

| 字段 | 怎么填 | 为什么 |
|---|---|---|
| Repository name | `flask-task-system-testbed` | 名字自取，建议带 testbed 字样，一眼看出是测试靶场 |
| Description | `Flask 任务管理系统 —— 五层自动化测试体系（接口 / UI / 并发 / 性能 / CI）` | 面试官第一眼看到的就是这句 |
| 公开性 | **Public**（公开） | 简历要放链接，必须公开才点得开 |
| Add a README file | **不要勾** | 本地已有 README，勾了会产生冲突 |
| Add .gitignore | **不要勾** | 本地已配置好，勾了会覆盖 |
| Choose a license | 建议 `MIT` | 可选。勾了显得工程更完整，但会多一次 merge |

> ⚠️ **最容易踩的坑**：只要勾了上面三项中任意一项，GitHub 就会创建一个带提交的仓库，
> 此时 `git push` 会因历史不相关被拒绝。保持**完全空白**是唯一正确做法。

点 **Create repository**，之后页面会跳到一个「Quick setup」页面，**先别急着复制命令，看第 2 步**。

---

## 第 2 步：本机执行推送

已为你准备了三个脚本，按推荐顺序尝试：

```bat
push-to-github.bat        :: 自动诊断三条通道，选通的推（推荐先跑这个）
push-to-github.bat https  :: 强制走 HTTPS
push-to-github.bat ssh    :: 强制走 SSH over 443
```

脚本会自动完成通道探测、remote 设置、推送，并在失败时给出具体诊断。

---

## 第 3 步：把 SSH 公钥加到 GitHub（仅 SSH 方式需要）

你的公钥已经生成好了，内容如下（整行复制）：

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBCh8RnHewNSfcYcBFQ9Cy8w3HtAe+RoYKINtkOzTNOQ lenovoo@task-system
```

粘贴位置：GitHub 右上角头像 → **Settings** → 左侧 **SSH and GPG keys** → **New SSH key**
Title 随便填（如 `lenovoo-pc`），Key type 保持 `Authentication Key`，把上面那行粘贴进 Key 框 → **Add SSH key**。

> 公钥放在仓库里是安全的，**私钥 `~/.ssh/id_ed25519` 绝不能外传**。

---

## 手动执行方式（不用脚本时）

把 `<你的用户名>` 替换成真实 GitHub 用户名。

### HTTPS 方式

```bash
cd E:/Users/lenovoo/task-system
git remote remove origin 2>/dev/null
git remote add origin https://github.com/<你的用户名>/flask-task-system-testbed.git
git branch -M main
git push -u origin main
```

> 密码框出现时，**不能填登录密码**。GitHub 已禁用密码验证，必须填 Personal Access Token。
> 生成位置：Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token
> 勾选 `repo` 权限即可。

### SSH over 443 方式（HTTPS 不通时用它）

```bash
# SSH 配置已写好（~/.ssh/config），直接用 :
git remote remove origin 2>/dev/null
git remote add origin git@github.com:<你的用户名>/flask-task-system-testbed.git
git branch -M main
git push -u origin main
```

---

## 推送后：验证 CI 是否真的跑起来

push 完成的瞬间流水线自动触发。查看：仓库页面 → **Actions** 标签页。

**重点看 UI 那个 job** —— `playwright install --with-deps` 需要 apt 装系统依赖，
是四条流水线里唯一可能在真实 runner 上意外失败的环节。

| Job | 预期结果 | 本地已验证 |
|---|---|---|
| api-tests | 105 passed | ✅ |
| ui-tests | 28 passed | ✅ |
| concurrency-tests | 1 passed + 1 xfailed | ✅ |
| perf-tests | 梯度压测跑通 | ✅ |

---

## 如果三条通道都不通

说明你浏览器能访问是靠某种本机不走命令行的路径（浏览器扩展、或者浏览器自带网络优化）。
这种情况下有两个选择：

1. **在代理软件里开启「系统代理 / 全局模式」**（不是 PAC 模式），开完重跑 `push-to-github.bat`
2. **换国内平台托管** —— 从简历效果看这未必是坏事：面试官大概率也打不开 GitHub，
   链接点不动等于简历上那条不存在。可选 Gitee / CNB，CI 语法需要改写，我可以接手。

---

## 公开前的安全复核（已通过 ✅）

| 检查项 | 结果 |
|---|---|
| 敏感凭据扫描 | 干净。仅 `perf_tests/locustfile.py` 有压测用假密码 `Perf@12345`，属必需测试数据 |
| `.venv/` 是否排除 | ✅ 已排除（否则仓库会多 200MB+） |
| `task.db` / `.ceiling` | ✅ 已排除 |
| 待推送体积 | 59 个文件，约 1.3 MB |
