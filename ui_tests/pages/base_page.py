"""
base_page.py - 页面对象基类

统一约定：
  - 所有定位器一律基于 data-testid，避免样式/文案变更导致用例断裂
  - 提供 wait_for_view / tid / screenshot 等通用能力
"""

import allure


class BasePage:
    """页面对象基类"""

    #: 该页面对应的视图 testid（子类覆盖）
    VIEW = None

    def __init__(self, page, base_url):
        self.page = page
        self.base_url = base_url

    # ------------------------------------------------------------------
    # 基础操作
    # ------------------------------------------------------------------

    def open(self, path="/"):
        """打开页面"""
        self.page.goto(self.base_url + path)
        return self

    def tid(self, test_id):
        """按 data-testid 定位（Playwright 内置 test id 约定）"""
        return self.page.get_by_test_id(test_id)

    def wait_for_view(self, timeout=8000):
        """等待当前视图渲染完成"""
        if self.VIEW:
            self.tid(self.VIEW).wait_for(state="visible", timeout=timeout)
        return self

    def wait_until(self, js_predicate, arg=None, timeout=8000):
        """
        等待页面内的 JS 断言成立（显式等待，替代 sleep）。

        :param js_predicate: JS 表达式，形如 "n => ... === n"
        :param arg: 传给 JS 的单个参数；Playwright Python 版要求以关键字传入，
                    需要多个值时请打包成 list/dict

        用例层不应直接调用 page.wait_for_function，统一走这里，
        避免「位置传参」这类低级错误重复出现。
        """
        self.page.wait_for_function(js_predicate, arg=arg, timeout=timeout)
        return self

    def screenshot(self, name):
        """截图并附加到 Allure 报告"""
        data = self.page.screenshot(full_page=True)
        allure.attach(data, name=name, attachment_type=allure.attachment_type.PNG)
        return data

    def toast_text(self):
        """读取当前 toast 提示文本"""
        return self.tid("toast").inner_text()

    def wait_toast(self, timeout=5000):
        self.tid("toast").wait_for(state="visible", timeout=timeout)
        return self.tid("toast").inner_text()
