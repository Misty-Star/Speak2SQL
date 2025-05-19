import sys
import logging
import traceback
import datetime
import json

# 配置日志
def setup_logging():
    """设置日志配置"""
    logging.basicConfig(
        level=logging.DEBUG, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("app.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# 创建logger实例
logger = setup_logging()

def handle_exception(e, context=""):
    """统一处理异常"""
    error_msg = f"{context} 错误: {str(e)}"
    logger.error(error_msg)
    logger.error(traceback.format_exc())
    return error_msg

def check_dependencies():
    """检查必要的依赖是否安装"""
    try:
        # UI 相关
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QSettings
        # 数据库相关
        import mysql.connector
        # 数据处理相关
        import pandas as pd
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
        import seaborn as sns
        # API相关
        import openai
        
        logger.info("所有模块导入成功")
        return True
    except ImportError as e:
        logger.error(f"依赖检查错误: {str(e)}")
        logger.error(traceback.format_exc())
        return False 

class OperationHistory:
    """操作历史记录管理"""
    
    def __init__(self, max_history=100):
        """初始化历史记录管理
        
        Args:
            max_history: 最大历史记录数量
        """
        self.history = []  # 存储所有操作记录
        self.current_index = -1  # 当前操作索引
        self.max_history = max_history
        
    def add_operation(self, operation_type, query, natural_query, affected_rows=0, result=None, rollback_sql=None):
        """添加一条操作记录
        
        Args:
            operation_type: 操作类型（SELECT, INSERT, UPDATE, DELETE等）
            query: 执行的SQL查询
            natural_query: 原始的自然语言查询
            affected_rows: 受影响的行数
            result: 操作结果的简短描述
            rollback_sql: 用于回滚此操作的SQL语句（如果适用）
        """
        # 如果当前不是在历史记录的最后，则清除后面的记录
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1]
            
        # 创建操作记录
        operation = {
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'operation_type': operation_type,
            'sql': query,
            'natural_query': natural_query,
            'affected_rows': affected_rows,
            'result': result,
            'rollback_sql': rollback_sql
        }
        
        # 添加到历史记录
        self.history.append(operation)
        
        # 如果历史记录超过最大限制，移除最早的记录
        if len(self.history) > self.max_history:
            self.history = self.history[1:]
            
        # 更新当前索引
        self.current_index = len(self.history) - 1
        
        logger.info(f"添加历史记录：{operation_type} ({self.current_index + 1}/{len(self.history)})")
        return operation
        
    def can_undo(self):
        """检查是否可以撤销操作"""
        return self.current_index >= 0
        
    def can_redo(self):
        """检查是否可以重做操作"""
        return self.current_index < len(self.history) - 1
        
    def get_previous_operation(self):
        """获取上一个操作记录"""
        if not self.can_undo():
            return None
            
        operation = self.history[self.current_index]
        self.current_index -= 1
        return operation
        
    def get_next_operation(self):
        """获取下一个操作记录"""
        if not self.can_redo():
            return None
            
        self.current_index += 1
        return self.history[self.current_index]
        
    def get_current_operation(self):
        """获取当前操作记录"""
        if self.current_index < 0 or self.current_index >= len(self.history):
            return None
            
        return self.history[self.current_index]
        
    def get_all_operations(self):
        """获取所有操作记录"""
        return self.history
        
    def clear_history(self):
        """清空历史记录"""
        self.history = []
        self.current_index = -1
        logger.info("清空操作历史记录")
        
    def save_to_file(self, filename="operation_history.json"):
        """将历史记录保存到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            logger.info(f"操作历史记录已保存到文件: {filename}")
            return True
        except Exception as e:
            handle_exception(e, "保存历史记录")
            return False
            
    def load_from_file(self, filename="operation_history.json"):
        """从文件加载历史记录"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.history = json.load(f)
            self.current_index = len(self.history) - 1 if self.history else -1
            logger.info(f"从文件加载了 {len(self.history)} 条历史记录")
            return True
        except FileNotFoundError:
            logger.warning(f"历史记录文件不存在: {filename}")
            return False
        except Exception as e:
            handle_exception(e, "加载历史记录")
            return False 