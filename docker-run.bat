@echo off
REM ============================================================
REM   本文件以 UTF-8 编码保存，需先切到 65001 代码页，
REM   否则 Windows 中文环境（GBK 936）下会输出乱码。
chcp 65001 >nul
REM ============================================================

REM ============================================================
REM   任务管理系统 —— Docker 一键助手（Windows）
REM
REM   用法：
REM     docker-run.bat up          启动被测系统（后台），访问 http://localhost:5000
REM     docker-run.bat down        停止并移除容器
REM     docker-run.bat api         跑接口自动化测试（75 用例 + 覆盖率）
REM     docker-run.bat ui          跑 UI 自动化测试（28 用例，连容器服务）
REM     docker-run.bat unit        跑基础功能测试（30 用例）
REM     docker-run.bat race        跑并发缺陷复现
REM     docker-run.bat perf        跑梯度性能压测（10/30/50）
REM     docker-run.bat all         全套：起服务 + 跑完所有测试层
REM     docker-run.bat clean       清容器 + 清卷（数据会丢！）
REM     docker-run.bat logs        查看被测系统日志
REM     docker-run.bat ps          查看服务状态
REM
REM   报告输出：./reports/
REM ============================================================

setlocal enabledelayedexpansion

set CMD=%1
if "%CMD%"=="" set CMD=up

REM 记录开始时间，用于统计耗时
set START_TIME=%time%

if "%CMD%"=="up"     goto :up
if "%CMD%"=="down"   goto :down
if "%CMD%"=="api"    goto :api
if "%CMD%"=="ui"     goto :ui
if "%CMD%"=="unit"   goto :unit
if "%CMD%"=="race"   goto :race
if "%CMD%"=="perf"   goto :perf
if "%CMD%"=="all"    goto :all
if "%CMD%"=="clean"  goto :clean
if "%CMD%"=="logs"   goto :logs
if "%CMD%"=="ps"     goto :ps

echo.
echo   [x] 未知命令: %CMD%
echo.
echo   可用命令: up / down / api / ui / unit / race / perf / all / clean / logs / ps
echo.
goto :end

REM ------------------------------------------------------------
:up
echo.
echo   [>] 启动被测系统 —— http://localhost:5000
echo.
docker compose up -d --build app
if errorlevel 1 goto :err
timeout /t 3 /nobreak >nul
docker compose ps app
echo.
echo   [i] 打开 http://localhost:5000 访问 SPA，http://localhost:5000/console 访问 API 控制台
goto :end

REM ------------------------------------------------------------
:down
echo.
echo   [>] 停止并移除容器（数据保留在卷中）
echo.
docker compose down
goto :end

REM ------------------------------------------------------------
:api
echo.
echo   [>] 接口自动化测试（75 用例 + 覆盖率）
echo.
docker compose --profile test run --rm api-tests
goto :check

REM ------------------------------------------------------------
:ui
echo.
echo   [>] UI 自动化测试（28 用例，跨容器访问 app 服务）
echo.
docker compose --profile test run --rm ui-tests
goto :check

REM ------------------------------------------------------------
:unit
echo.
echo   [>] 基础功能测试（30 用例，Flask test_client）
echo.
docker compose --profile test run --rm unit-tests
goto :check

REM ------------------------------------------------------------
:race
echo.
echo   [>] 并发缺陷复现（标签竞态，xfail = 缺陷已复现）
echo.
docker compose --profile test run --rm concurrency-tests
goto :check

REM ------------------------------------------------------------
:perf
echo.
echo   [>] 梯度性能压测（Locust 10/30/50 并发）
echo   [i] 压测期间请勿使用本机做其他高负载任务，否则指标会失真
echo.
docker compose --profile perf run --rm perf-tests
goto :check

REM ------------------------------------------------------------
:all
echo.
echo   [>] 全套执行：起服务 + 单元测试 + 接口测试 + UI 测试 + 并发测试
echo   [i] 性能压测未包含（耗时且抢占资源），需要请单独跑 perf
echo.
docker compose --profile test up --abort-on-container-exit --exit-code-from api-tests
echo.
echo   [>] 单元测试
docker compose --profile test run --rm unit-tests
echo.
echo   [>] UI 测试
docker compose --profile test run --rm ui-tests
echo.
echo   [>] 并发测试
docker compose --profile test run --rm concurrency-tests
echo.
echo   [>] 报告已输出到 .\reports\
goto :check

REM ------------------------------------------------------------
:clean
echo.
echo   [!] 即将删除容器、网络与数据卷 —— task.db 与上传附件会一并清除
echo.
set /p CONFIRM=确认请输入 y（其他任意键取消）:
if /i not "%CONFIRM%"=="y" (
    echo   已取消。
    goto :end
)
docker compose down -v --remove-orphans
echo   [OK] 已清理，下次 up 会得到全新数据库。
goto :end

REM ------------------------------------------------------------
:logs
docker compose logs -f app
goto :end

REM ------------------------------------------------------------
:ps
docker compose ps -a
goto :end

REM ------------------------------------------------------------
:check
if errorlevel 1 (
    echo.
    echo   [FAIL] 测试未能全部通过，详情见上方输出与 .\reports\
    exit /b 1
)
echo.
echo   [PASS] 完成。报告位置：
echo     .\reports\api-allure-results\       接口测试 Allure 数据
echo     .\reports\api-coverage.xml          接口测试覆盖率
echo     .\reports\ui-allure-results\        UI 测试 Allure 数据
echo     .\reports\ui-artifacts\             UI 失败截图 / Trace
echo     .\reports\concurrency-allure-results\
goto :end

:err
echo.
echo   [x] Docker 执行失败。常见原因：
echo     1) Docker Desktop 未启动 —— 请先启动并等待托盘图标停止动画
echo     2) 首次构建需拉取基础镜像，网络不通会失败
echo     3) 端口 5000 被本机其他程序占用 —— 可用 APP_PORT=5001 换端口
goto :end

:end
echo.
echo   耗时起点 %START_TIME% / 终点 %time%
echo.
endlocal
