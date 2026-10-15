"""
gen_report.py - 解析 allure-results 生成独立 HTML 报告
无需 allure CLI，纯 Python 实现。
"""

import json
import os
import glob
from datetime import datetime
from collections import defaultdict

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "allure-results")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "allure-report.html")


def load_results():
    """加载所有 allure 结果文件"""
    test_cases = []
    containers = {}
    attachments = {}

    for fpath in glob.glob(os.path.join(RESULTS_DIR, "*")):
        fname = os.path.basename(fpath)
        if fname.endswith("-result.json"):
            with open(fpath, "r", encoding="utf-8") as f:
                test_cases.append(json.load(f))
        elif fname.endswith("-container.json"):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                containers[data.get("uuid", fname)] = data
        elif fname.endswith("-attachment.txt"):
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                attachments[fname.replace("-attachment.txt", "")] = f.read()

    return test_cases, containers, attachments


def build_hierarchy(test_cases, containers):
    """构建 Feature > Story > TestCase 层级"""
    # 建立 container 父子关系
    child_to_parent = {}
    for uuid, c in containers.items():
        for child in c.get("children", []):
            child_to_parent[child] = uuid

    # 查找每个 test case 的顶层 container（feature）
    features = defaultdict(lambda: defaultdict(list))

    for tc in test_cases:
        tc_uuid = tc.get("uuid", "")
        # 收集 labels
        labels = {l["name"]: l["value"] for l in tc.get("labels", [])}
        feature = labels.get("feature", "未分类")
        story = labels.get("story", "其他")
        features[feature][story].append(tc)

    return features


def get_severity(tc):
    labels = {l["name"]: l["value"] for l in tc.get("labels", [])}
    sev = labels.get("severity", "normal")
    return {"blocker": "阻塞", "critical": "严重", "normal": "一般", "minor": "次要", "trivial": "轻微"}.get(sev, sev)


def get_attachments(tc):
    """获取测试用例的附件"""
    atts = []
    for step in tc.get("testStage", {}).get("steps", []):
        for att in step.get("attachments", []):
            atts.append(att)
    for att in tc.get("testStage", {}).get("attachments", []):
        atts.append(att)
    return atts


def status_color(status):
    return {"passed": "#28a745", "failed": "#dc3545", "broken": "#ffc107", "skipped": "#6c757d"}.get(status, "#6c757d")


def status_label(status):
    return {"passed": "通过", "failed": "失败", "broken": "损坏", "skipped": "跳过"}.get(status, status)


def generate_html(features, all_cases, attachments):
    total = len(all_cases)
    passed = sum(1 for t in all_cases if t["status"] == "passed")
    failed = sum(1 for t in all_cases if t["status"] == "failed")
    broken = sum(1 for t in all_cases if t["status"] == "broken")
    skipped = sum(1 for t in all_cases if t["status"] == "skipped")
    pass_rate = round(passed / total * 100, 1) if total > 0 else 0

    # 饼图 SVG
    import math
    pie_radius = 60
    pie_cx, pie_cy = 80, 80
    segments = []
    colors = {"passed": "#28a745", "failed": "#dc3545", "broken": "#ffc107", "skipped": "#6c757d"}
    counts = {"passed": passed, "failed": failed, "broken": broken, "skipped": skipped}
    start_angle = -90
    for status, count in counts.items():
        if count == 0:
            continue
        angle = count / total * 360
        end_angle = start_angle + angle
        x1 = pie_cx + pie_radius * math.cos(math.radians(start_angle))
        y1 = pie_cy + pie_radius * math.sin(math.radians(start_angle))
        x2 = pie_cx + pie_radius * math.cos(math.radians(end_angle))
        y2 = pie_cy + pie_radius * math.sin(math.radians(end_angle))
        large_arc = 1 if angle > 180 else 0
        segments.append(f'<path d="M{pie_cx},{pie_cy} L{x1:.1f},{y1:.1f} A{pie_radius},{pie_radius} 0 {large_arc} 1 {x2:.1f},{y2:.1f} Z" fill="{colors[status]}"/>')
        start_angle = end_angle

    pie_svg = f'<svg width="160" height="160">{"".join(segments)}<circle cx="{pie_cx}" cy="{pie_cy}" r="35" fill="#fff"/><text x="{pie_cx}" y="{pie_cy-5}" text-anchor="middle" font-size="22" font-weight="bold" fill="#333">{pass_rate}%</text><text x="{pie_cx}" y="{pie_cy+15}" text-anchor="middle" font-size="11" fill="#999">通过率</text></svg>'

    # 生成测试详情
    feature_html = []
    for feature, stories in sorted(features.items()):
        f_total = sum(len(tcs) for tcs in stories.values())
        f_passed = sum(1 for tcs in stories.values() for t in tcs if t["status"] == "passed")
        f_failed = sum(1 for tcs in stories.values() for t in tcs if t["status"] == "failed")

        feature_html.append(f'<div class="feature-card">')
        feature_html.append(f'<div class="feature-header" onclick="toggleFeature(this)">')
        feature_html.append(f'<span class="feature-title">{feature}</span>')
        feature_html.append(f'<span class="feature-stats">{f_total} 测试 | <span style="color:#28a745">{f_passed}通过</span>')
        if f_failed:
            feature_html.append(f' | <span style="color:#dc3545">{f_failed}失败</span>')
        feature_html.append(f'</span><span class="arrow">&#9660;</span></div>')
        feature_html.append(f'<div class="feature-body">')

        for story, tcs in sorted(stories.items()):
            feature_html.append(f'<div class="story-group">')
            feature_html.append(f'<div class="story-title">{story}</div>')
            feature_html.append(f'<table class="test-table"><tbody>')

            for tc in sorted(tcs, key=lambda t: t.get("name", "")):
                status = tc["status"]
                name = tc.get("name", "unknown")
                sev = get_severity(tc)
                dur = tc.get("time", {}).get("duration", 0)
                dur_ms = round(dur / 1000, 1) if dur else 0

                feature_html.append(f'<tr class="test-row" onclick="toggleDetail(this)">')
                feature_html.append(f'<td class="col-status"><span class="status-dot" style="background:{status_color(status)}"></span></td>')
                feature_html.append(f'<td class="col-name">{name}</td>')
                feature_html.append(f'<td class="col-sev">{sev}</td>')
                feature_html.append(f'<td class="col-status-text" style="color:{status_color(status)}">{status_label(status)}</td>')
                feature_html.append(f'<td class="col-dur">{dur_ms}ms</td>')
                feature_html.append(f'</tr>')

                # 详情行
                feature_html.append(f'<tr class="detail-row" style="display:none"><td colspan="5">')

                # 附件
                atts = get_attachments(tc)
                if atts:
                    for att in atts:
                        att_uid = att.get("source", "").replace("-attachment.txt", "")
                        content = attachments.get(att_uid, "")
                        feature_html.append(f'<div class="attachment-block">')
                        feature_html.append(f'<div class="att-name">{att.get("name", "attachment")}</div>')
                        feature_html.append(f'<pre class="att-content">{content}</pre>')
                        feature_html.append(f'</div>')

                # 状态详情
                status_msg = tc.get("statusDetails", {})
                if status_msg.get("message"):
                    feature_html.append(f'<div class="error-msg"><b>错误信息:</b><pre>{status_msg["message"]}</pre></div>')
                if status_msg.get("trace"):
                    feature_html.append(f'<details><summary>堆栈追踪</summary><pre class="trace">{status_msg["trace"]}</pre></details>')

                feature_html.append(f'</td></tr>')

            feature_html.append(f'</tbody></table></div>')

        feature_html.append(f'</div></div>')

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>任务管理系统 - API 自动化测试报告</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,"Segoe UI",Roboto,"Microsoft YaHei",sans-serif; background:#f0f2f5; color:#333; }}
  .header {{ background:linear-gradient(135deg,#4a90d9,#357abd); color:#fff; padding:24px 32px; }}
  .header h1 {{ font-size:22px; margin-bottom:4px; }}
  .header .meta {{ font-size:13px; opacity:.85; }}
  .dashboard {{ display:flex; align-items:center; gap:32px; background:#fff; margin:16px 24px; padding:20px 28px; border-radius:10px; box-shadow:0 2px 8px rgba(0,0,0,.06); }}
  .stat-cards {{ display:flex; gap:16px; flex:1; }}
  .stat-card {{ text-align:center; padding:12px 20px; border-radius:8px; min-width:90px; }}
  .stat-card .num {{ font-size:28px; font-weight:700; }}
  .stat-card .label {{ font-size:12px; color:#888; margin-top:2px; }}
  .stat-card.total {{ background:#e3f2fd; }} .stat-card.total .num {{ color:#1565c0; }}
  .stat-card.pass {{ background:#e8f5e9; }} .stat-card.pass .num {{ color:#2e7d32; }}
  .stat-card.fail {{ background:#fbe9e7; }} .stat-card.fail .num {{ color:#c62828; }}
  .stat-card.skip {{ background:#f5f5f5; }} .stat-card.skip .num {{ color:#757575; }}
  .feature-card {{ margin:0 24px 12px; background:#fff; border-radius:8px; overflow:hidden; box-shadow:0 1px 4px rgba(0,0,0,.06); }}
  .feature-header {{ display:flex; align-items:center; gap:12px; padding:12px 20px; background:#f8f9fa; cursor:pointer; border-bottom:1px solid #eee; }}
  .feature-header:hover {{ background:#f0f1f3; }}
  .feature-title {{ font-weight:600; font-size:15px; flex:1; }}
  .feature-stats {{ font-size:12px; color:#888; }}
  .arrow {{ font-size:10px; color:#999; transition:transform .2s; }}
  .feature-card.collapsed .arrow {{ transform:rotate(-90deg); }}
  .feature-card.collapsed .feature-body {{ display:none; }}
  .feature-body {{ padding:8px 0; }}
  .story-group {{ padding:4px 20px; }}
  .story-title {{ font-size:13px; font-weight:600; color:#555; margin:8px 0 4px; padding-left:8px; border-left:3px solid #4a90d9; }}
  .test-table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  .test-table td {{ padding:6px 8px; border-bottom:1px solid #f0f0f0; }}
  .test-row {{ cursor:pointer; }}
  .test-row:hover {{ background:#f8f9fa; }}
  .col-status {{ width:28px; }}
  .status-dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; }}
  .col-name {{ }}
  .col-sev {{ width:60px; color:#888; font-size:12px; }}
  .col-status-text {{ width:50px; font-weight:600; font-size:12px; }}
  .col-dur {{ width:60px; color:#aaa; font-size:12px; text-align:right; }}
  .detail-row td {{ background:#fafbfc; padding:12px 20px; }}
  .attachment-block {{ margin-bottom:10px; }}
  .att-name {{ font-size:12px; color:#4a90d9; font-weight:600; margin-bottom:4px; }}
  .att-content {{ background:#1e1e1e; color:#4fc3f7; padding:10px 14px; border-radius:6px; font-size:11px; font-family:monospace; white-space:pre-wrap; max-height:250px; overflow:auto; }}
  .error-msg {{ background:#fff5f5; border:1px solid #ffcdd2; border-radius:6px; padding:10px 14px; margin-bottom:8px; }}
  .error-msg pre {{ font-size:12px; font-family:monospace; white-space:pre-wrap; color:#c62828; margin-top:4px; }}
  .trace {{ font-size:11px; font-family:monospace; white-space:pre-wrap; color:#666; max-height:200px; overflow:auto; }}
  .footer {{ text-align:center; padding:20px; color:#aaa; font-size:12px; }}
</style>
</head>
<body>
<div class="header">
  <h1>任务管理系统 - API 自动化测试报告</h1>
  <div class="meta">Flask + requests + pytest + allure | 生成时间: {now}</div>
</div>

<div class="dashboard">
  {pie_svg}
  <div class="stat-cards">
    <div class="stat-card total"><div class="num">{total}</div><div class="label">总计</div></div>
    <div class="stat-card pass"><div class="num">{passed}</div><div class="label">通过</div></div>
    <div class="stat-card fail"><div class="num">{failed}</div><div class="label">失败</div></div>
    <div class="stat-card skip"><div class="num">{skipped}</div><div class="label">跳过</div></div>
  </div>
</div>

{''.join(feature_html)}

<div class="footer">Generated by gen_report.py | Allure Results Parser</div>

<script>
function toggleFeature(el) {{
  el.parentElement.classList.toggle('collapsed');
}}
function toggleDetail(row) {{
  const detail = row.nextElementSibling;
  if (detail && detail.classList.contains('detail-row')) {{
    detail.style.display = detail.style.display === 'none' ? '' : 'none';
  }}
}}
</script>
</body>
</html>"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Report generated: {OUTPUT_FILE}")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Pass Rate: {pass_rate}%")


if __name__ == "__main__":
    cases, containers, atts = load_results()
    features = build_hierarchy(cases, containers)
    generate_html(features, cases, atts)
