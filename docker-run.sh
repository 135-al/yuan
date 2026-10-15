#!/usr/bin/env bash
# ============================================================
#   任务管理系统 —— Docker 一键助手（Linux / macOS / Git Bash）
#
#   用法：
#     ./docker-run.sh up          启动被测系统，访问 http://localhost:5000
#     ./docker-run.sh down        停止并移除容器
#     ./docker-run.sh api         接口自动化测试（75 用例 + 覆盖率）
#     ./docker-run.sh ui          UI 自动化测试（28 用例，连容器服务）
#     ./docker-run.sh unit        基础功能测试（30 用例）
#     ./docker-run.sh race        并发缺陷复现
#     ./docker-run.sh perf        梯度性能压测（10/30/50）
#     ./docker-run.sh all         全套跑测
#     ./docker-run.sh clean       清容器 + 清卷（数据会丢！）
#     ./docker-run.sh logs        查看日志
#     ./docker-run.sh ps          查看服务状态
#
#   报告输出：./reports/
# ============================================================

set -euo pipefail

CMD="${1:-up}"

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

report_hint() {
  echo ""
  echo "  [>] 报告输出目录: ./reports/"
  echo "      reports/api-allure-results/         接口测试 Allure 数据"
  echo "      reports/api-coverage.xml            接口测试覆盖率"
  echo "      reports/ui-allure-results/          UI 测试 Allure 数据"
  echo "      reports/ui-artifacts/               UI 失败截图 / Trace"
  echo "      reports/concurrency-allure-results/ 并发测试 Allure 数据"
}

case "$CMD" in
  up)
    echo "  [>] 启动被测系统 -> http://localhost:5000"
    compose up -d --build app
    sleep 3
    compose ps app
    echo ""
    echo "  [i] SPA:    http://localhost:5000"
    echo "     控制台:  http://localhost:5000/console"
    ;;
  down)
    echo "  [>] 停止并移除容器（数据保留在卷中）"
    compose down
    ;;
  api)
    echo "  [>] 接口自动化测试（75 用例 + 覆盖率）"
    compose --profile test run --rm api-tests
    report_hint
    ;;
  ui)
    echo "  [>] UI 自动化测试（28 用例，跨容器访问 app 服务）"
    compose --profile test run --rm ui-tests
    report_hint
    ;;
  unit)
    echo "  [>] 基础功能测试（30 用例，Flask test_client）"
    compose --profile test run --rm unit-tests
    report_hint
    ;;
  race)
    echo "  [>] 并发缺陷复现（标签竞态，xfail = 缺陷已复现）"
    compose --profile test run --rm concurrency-tests
    report_hint
    ;;
  perf)
    echo "  [>] 梯度性能压测（Locust 10/30/50 并发）"
    echo "  [i] 压测期间请勿在本机跑其他高负载任务，否则指标失真"
    compose --profile perf run --rm perf-tests
    report_hint
    ;;
  all)
    echo "  [>] 全套执行（不含压测，压测耗时且抢占资源，需单独跑）"
    compose --profile test run --rm unit-tests
    compose --profile test run --rm api-tests
    compose --profile test run --rm ui-tests
    compose --profile test run --rm concurrency-tests
    report_hint
    ;;
  clean)
    echo "  [!] 即将删除容器、网络与数据卷 —— task.db 与上传附件会一并清除"
    read -r -p "      确认请输入 y：" CONFIRM
    if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
      echo "      已取消。"
      exit 0
    fi
    compose down -v --remove-orphans
    echo "  [OK] 已清理，下次 up 会得到全新数据库。"
    ;;
  logs)
    compose logs -f app
    ;;
  ps)
    compose ps -a
    ;;
  *)
    echo "  [x] 未知命令: $CMD"
    echo "      可用: up / down / api / ui / unit / race / perf / all / clean / logs / ps"
    exit 1
    ;;
esac
