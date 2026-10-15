"""
run_tests.py - 一键运行自动化测试并生成报告

用法:
    python run_tests.py

流程:
    1. 运行 pytest（含 allure 数据采集）
    2. 解析 allure-results 生成 HTML 报告
    3. 输出结果摘要
"""

import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable


def run_tests():
    """运行 pytest 测试套件"""
    print("=" * 60)
    print("  运行 API 自动化测试 (pytest + allure)")
    print("=" * 60)

    result = subprocess.run(
        [VENV_PYTHON, "-m", "pytest", "-c", "pytest_allure.ini"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )

    # 打印测试输出
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    # 解析结果
    passed = result.stdout.count(" PASSED")
    failed = result.stdout.count(" FAILED")
    errors = result.stdout.count(" ERROR")

    return passed, failed, errors, result.returncode


def generate_report():
    """生成 HTML 报告"""
    print("\n" + "=" * 60)
    print("  生成 Allure HTML 报告")
    print("=" * 60)

    result = subprocess.run(
        [VENV_PYTHON, "gen_report.py"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)


def main():
    passed, failed, errors, rc = run_tests()
    generate_report()

    print("\n" + "=" * 60)
    print("  测试结果摘要")
    print("=" * 60)
    print(f"  通过: {passed}")
    print(f"  失败: {failed}")
    print(f"  错误: {errors}")
    print(f"  总计: {passed + failed + errors}")
    print(f"  通过率: {round(passed / (passed + failed + errors) * 100, 1)}%")
    print(f"\n  报告文件: {os.path.join(BASE_DIR, 'allure-report.html')}")
    print("=" * 60)

    return rc


if __name__ == "__main__":
    sys.exit(main())
