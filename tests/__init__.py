"""基础功能测试包。

此目录与 api_tests 均含 test_api.py，若不加 __init__.py，
pytest 默认的 prepend 导入模式会因「同名模块」而报 import file mismatch。
加包标识后模块名变为 tests.test_api / api_tests.test_api，可同批收集。
"""
