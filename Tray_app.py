import sys
import os
import threading
import time
import webbrowser
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
import subprocess

class InvoiceOCRTray:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.tray_icon = QSystemTrayIcon()
        
        # 设置图标
        icon_path = os.path.join(os.path.dirname(__file__), 'favicon.ico')
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        
        # 创建菜单
        menu = QMenu()
        
        # 打开网页
        open_action = QAction("打开发票OCR工具", self.app)
        open_action.triggered.connect(self.open_browser)
        menu.addAction(open_action)
        
        # 启动服务器
        start_action = QAction("启动服务器", self.app)
        start_action.triggered.connect(self.start_server)
        menu.addAction(start_action)
        
        # 退出
        exit_action = QAction("退出", self.app)
        exit_action.triggered.connect(self.quit_app)
        menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.setToolTip("发票OCR识别工具")
        self.tray_icon.show()
        
        # 自动启动服务器
        self.start_server()
        
    def start_server(self):
        """启动Dash服务器"""
        def run_server():
            # import your_app  # 导入你的Dash应用
            # 或者使用subprocess启动
            subprocess.Popen([sys.executable, "GUI-4.py"])
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(2)
        self.open_browser()
    
    def open_browser(self):
        """打开浏览器"""
        webbrowser.open('http://localhost:8050')
    
    def quit_app(self):
        """退出应用"""
        self.tray_icon.hide()
        self.app.quit()
        sys.exit()
    
    def run(self):
        sys.exit(self.app.exec_())

if __name__ == '__main__':
    tray_app = InvoiceOCRTray()
    tray_app.run()