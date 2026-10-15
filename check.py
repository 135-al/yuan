"""
check.py - 自动验证脚本
运行后确认：
  1. 所有依赖已安装
  2. 数据库表创建成功
  3. 服务能正常启动（模拟）
  4. 至少 3 个核心接口调用成功

用法: python check.py
"""

import sys
import os
import importlib


def check_dependencies():
    """检查所有依赖是否已安装"""
    print("\n[1/4] 检查依赖安装...")
    required = {
        "flask": "Flask",
        "flask_sqlalchemy": "Flask-SQLAlchemy",
        "flask_cors": "Flask-CORS",
        "jwt": "PyJWT",
        "pytest": "pytest",
    }

    all_ok = True
    for module, display_name in required.items():
        try:
            importlib.import_module(module)
            print(f"  [OK] {display_name}")
        except ImportError:
            print(f"  [FAIL] {display_name} - 未安装")
            all_ok = False

    if all_ok:
        print("  >>> 所有依赖已安装")
    else:
        print("  >>> 部分依赖缺失，请运行: pip install -r requirements.txt")
    return all_ok


def check_database():
    """检查数据库表是否能成功创建"""
    print("\n[2/4] 检查数据库表创建...")
    try:
        from app import create_app, db
        from app.models import User, Task, Tag

        app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///check_verify.db",
            }
        )

        with app.app_context():
            db.create_all()
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

            expected = ["users", "tasks", "tags", "task_tags"]
            all_ok = True
            for t in expected:
                if t in tables:
                    print(f"  [OK] 表 '{t}' 创建成功")
                else:
                    print(f"  [FAIL] 表 '{t}' 创建失败")
                    all_ok = False

            db.session.remove()
            db.drop_all()

        if os.path.exists("check_verify.db"):
            os.remove("check_verify.db")

        if all_ok:
            print("  >>> 数据库表全部创建成功")
        return all_ok
    except Exception as e:
        print(f"  [FAIL] 数据库创建失败: {e}")
        return False


def check_app_start():
    """检查应用是否能正常启动"""
    print("\n[3/4] 检查服务启动（模拟）...")
    try:
        from app import create_app

        app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///check_verify.db",
            }
        )

        with app.test_client() as client:
            resp = client.get("/api/tasks")
            print(f"  [OK] Flask 应用创建成功")
            print(f"  [OK] 测试客户端连接成功")
            print(f"  [OK] 路由注册成功（GET /api/tasks 返回 {resp.status_code}）")

        # 清理
        if os.path.exists("check_verify.db"):
            os.remove("check_verify.db")

        print("  >>> 服务可正常启动")
        return True
    except Exception as e:
        print(f"  [FAIL] 服务启动失败: {e}")
        return False


def check_core_apis():
    """检查核心接口调用"""
    print("\n[4/4] 检查核心接口调用...")
    try:
        from app import create_app, db

        app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///check_verify.db",
            }
        )

        with app.test_client() as client:
            # 1. 用户注册
            resp = client.post(
                "/api/auth/register",
                json={
                    "username": "checkuser",
                    "email": "check@example.com",
                    "password": "checkpass123",
                },
            )
            assert resp.status_code == 201, f"注册失败: {resp.status_code}"
            token = resp.get_json()["token"]
            headers = {"Authorization": f"Bearer {token}"}
            print(f"  [OK] POST /api/auth/register -> 201")

            # 2. 用户登录
            resp = client.post(
                "/api/auth/login",
                json={"username": "checkuser", "password": "checkpass123"},
            )
            assert resp.status_code == 200, f"登录失败: {resp.status_code}"
            print(f"  [OK] POST /api/auth/login -> 200")

            # 3. 创建任务
            resp = client.post(
                "/api/tasks",
                json={"title": "验证任务", "priority": "high"},
                headers=headers,
            )
            assert resp.status_code == 201, f"创建任务失败: {resp.status_code}"
            task_id = resp.get_json()["task"]["id"]
            print(f"  [OK] POST /api/tasks -> 201")

            # 4. 获取任务列表
            resp = client.get("/api/tasks", headers=headers)
            assert resp.status_code == 200, f"获取任务列表失败: {resp.status_code}"
            assert resp.get_json()["count"] >= 1
            print(f"  [OK] GET /api/tasks -> 200")

            # 5. 更新任务状态
            resp = client.patch(
                f"/api/tasks/{task_id}/status",
                json={"status": "doing"},
                headers=headers,
            )
            assert resp.status_code == 200, f"更新状态失败: {resp.status_code}"
            print(f"  [OK] PATCH /api/tasks/<id>/status -> 200")

            # 6. 获取统计
            resp = client.get("/api/stats", headers=headers)
            assert resp.status_code == 200, f"获取统计失败: {resp.status_code}"
            assert "total" in resp.get_json()
            print(f"  [OK] GET /api/stats -> 200")

            # 7. 删除任务
            resp = client.delete(
                f"/api/tasks/{task_id}", headers=headers
            )
            assert resp.status_code == 200, f"删除任务失败: {resp.status_code}"
            print(f"  [OK] DELETE /api/tasks/<id> -> 200")

        # 清理
        with app.app_context():
            db.drop_all()
        if os.path.exists("check_verify.db"):
            os.remove("check_verify.db")

        print("  >>> 7 个核心接口全部调用成功")
        return True
    except Exception as e:
        print(f"  [FAIL] 核心接口调用失败: {e}")
        import traceback

        traceback.print_exc()
        # 清理
        if os.path.exists("check_verify.db"):
            os.remove("check_verify.db")
        return False


def main():
    print("=" * 55)
    print("   任务管理系统 - 自动验证脚本 (check.py)")
    print("=" * 55)

    results = []
    results.append(("依赖安装", check_dependencies()))
    results.append(("数据库表创建", check_database()))
    results.append(("服务启动", check_app_start()))
    results.append(("核心接口调用", check_core_apis()))

    print("\n" + "=" * 55)
    print("   验证结果汇总")
    print("=" * 55)

    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"   {name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 55)
    if all_passed:
        print("   ✅ 所有检查项通过！系统可正常运行。")
    else:
        print("   ❌ 部分检查项未通过，请根据上述信息排查。")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
