#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MySQL自然语言查询工具 - 主程序入口
支持自然语言查询MySQL数据库并可视化结果
"""

import sys
from PySide6.QtWidgets import QApplication
from utils import logger, check_dependencies
from ui import MainWindow

def main():
    """程序主入口"""
    # 检查依赖
    if not check_dependencies():
        logger.critical("无法加载必要的依赖库，程序将退出")
        sys.exit(1)
    
    try:
        # 创建应用实例
        logger.info("正在启动应用程序...")
        app = QApplication(sys.argv)
        logger.info("QApplication创建成功")
        
        # 创建并显示主窗口
        window = MainWindow()
        logger.info("主窗口创建成功")
        
        window.show()
        logger.info("显示主窗口")
        
        # 进入主事件循环
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"程序启动错误: {str(e)}")
        import traceback
        logger.critical(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()