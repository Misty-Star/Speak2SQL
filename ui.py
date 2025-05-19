import sys
import pandas as pd
import traceback
import json
import ast
import re

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QPushButton, QLabel, QLineEdit, QMessageBox, 
                             QDialog, QFrame, QTabWidget, QTableWidget, QTableWidgetItem,
                             QHeaderView, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from utils import logger, handle_exception, OperationHistory
from database import DatabaseConnection
from openai_handler import OpenAIHandler
from visualization import DataVisualizer
from settings import AppSettings, SettingsDialog

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.app_settings = AppSettings()
        self.db = DatabaseConnection()
        self.openai_handler = None
        self.history = OperationHistory()  # 初始化历史记录
        self.init_ui()
        self.apply_style()
        self.load_database_settings()
        self.init_api()
        # 尝试加载历史记录
        self.history.load_from_file()
        
    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle('MySQL自然语言查询工具')
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        
        # 顶部工具栏
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        # 数据库连接部分
        db_frame = self._create_db_section()
        layout.addWidget(db_frame)
        
        # 查询部分
        query_frame = self._create_query_section()
        layout.addWidget(query_frame)
        
        # 结果显示部分
        result_frame = self._create_result_section()
        layout.addWidget(result_frame)
        
        main_widget.setLayout(layout)
        
    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout()
        
        settings_btn = QPushButton('设置')
        settings_btn.setToolTip('配置API设置与调试功能')
        settings_btn.clicked.connect(self.show_settings)
        toolbar_layout.addWidget(settings_btn)
        
        # 添加新的历史记录按钮
        history_btn = QPushButton('历史记录')
        history_btn.setToolTip('查看操作历史记录')
        history_btn.clicked.connect(self.show_history)
        toolbar_layout.addWidget(history_btn)
        
        # 添加回退按钮
        self.undo_btn = QPushButton('↩ 回退')
        self.undo_btn.setToolTip('回退到上一个操作')
        self.undo_btn.clicked.connect(self.undo_operation)
        self.undo_btn.setEnabled(False)
        toolbar_layout.addWidget(self.undo_btn)
        
        # 添加前进按钮
        self.redo_btn = QPushButton('↪ 前进')
        self.redo_btn.setToolTip('重做下一个操作')
        self.redo_btn.clicked.connect(self.redo_operation)
        self.redo_btn.setEnabled(False)
        toolbar_layout.addWidget(self.redo_btn)
        
        toolbar_layout.addStretch()
        
        toolbar.setLayout(toolbar_layout)
        return toolbar
        
    def _create_db_section(self):
        """创建数据库连接部分"""
        db_frame = QFrame()
        db_frame.setFrameStyle(QFrame.Panel)
        db_layout = QHBoxLayout()
        
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText('主机地址')
        self.host_input.setToolTip('MySQL数据库主机地址，例如：localhost')
        
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText('用户名')
        self.user_input.setToolTip('MySQL数据库用户名')
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('密码')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setToolTip('MySQL数据库密码')
        
        self.database_input = QLineEdit()
        self.database_input.setPlaceholderText('数据库名')
        self.database_input.setToolTip('要连接的MySQL数据库名称')
        
        connect_btn = QPushButton('连接数据库')
        connect_btn.clicked.connect(self.connect_database)
        
        db_layout.addWidget(QLabel('主机:'))
        db_layout.addWidget(self.host_input)
        db_layout.addWidget(QLabel('用户:'))
        db_layout.addWidget(self.user_input)
        db_layout.addWidget(QLabel('密码:'))
        db_layout.addWidget(self.password_input)
        db_layout.addWidget(QLabel('数据库:'))
        db_layout.addWidget(self.database_input)
        db_layout.addWidget(connect_btn)
        
        db_frame.setLayout(db_layout)
        return db_frame
        
    def _create_query_section(self):
        """创建查询部分"""
        query_frame = QFrame()
        query_frame.setFrameStyle(QFrame.Panel)
        query_layout = QVBoxLayout()
        
        # 顶部按钮组
        top_btn_layout = QHBoxLayout()
        
        # 查询按钮
        query_btn = QPushButton('执行查询')
        query_btn.clicked.connect(self.execute_query)
        query_btn.setToolTip('执行只读查询，不修改数据')
        
        # 修改按钮
        modify_btn = QPushButton('修改数据')
        modify_btn.clicked.connect(self.execute_modification)
        modify_btn.setToolTip('执行数据修改操作，包括增删改')
        
        # 添加查看表按钮
        view_tables_btn = QPushButton('查看表')
        view_tables_btn.clicked.connect(self.show_tables)
        view_tables_btn.setToolTip('查看数据库中的所有表')
        
        top_btn_layout.addWidget(QLabel('操作类型:'))
        top_btn_layout.addWidget(query_btn)
        top_btn_layout.addWidget(modify_btn)
        top_btn_layout.addWidget(view_tables_btn)
        top_btn_layout.addStretch()
        
        # 自然语言查询输入框
        self.natural_query_input = QTextEdit()
        self.natural_query_input.setPlaceholderText('输入自然语言查询或修改指令...')
        self.natural_query_input.setMaximumHeight(100)
        self.natural_query_input.setToolTip('输入中文或英文自然语言，例如："查询所有用户的姓名和年龄" 或 "在用户表中添加一个叫张三的新用户"')
        
        query_layout.addLayout(top_btn_layout)
        query_layout.addWidget(QLabel('自然语言查询:'))
        query_layout.addWidget(self.natural_query_input)
        
        query_frame.setLayout(query_layout)
        return query_frame
        
    def _create_result_section(self):
        """创建结果显示部分"""
        result_frame = QFrame()
        result_frame.setFrameStyle(QFrame.Panel)
        result_layout = QVBoxLayout()
        
        # 创建标签页
        self.result_tabs = QTabWidget()
        
        # SQL结果标签页
        sql_tab = QWidget()
        sql_layout = QVBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        sql_layout.addWidget(self.result_text)
        sql_tab.setLayout(sql_layout)
        
        # 表格标签页
        table_tab = QWidget()
        table_layout = QVBoxLayout()
        
        # 添加字段信息区域
        self.fields_info_frame = QFrame()
        self.fields_info_frame.setFrameStyle(QFrame.StyledPanel)
        self.fields_info_frame.setMinimumHeight(120)  # 增加最小高度
        self.fields_info_frame.setMaximumHeight(150)  # 增加最大高度
        self.fields_info_frame.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-bottom: 5px;
            }
            QLabel {
                color: #2196F3;
                font-weight: bold;
            }
        """)
        fields_info_layout = QVBoxLayout()
        fields_info_layout.setContentsMargins(5, 5, 5, 5)
        fields_info_layout.setSpacing(2)
        
        # 标题
        fields_title_layout = QHBoxLayout()
        fields_title_label = QLabel("表字段信息")
        fields_title_label.setStyleSheet("font-size: 11pt;")
        fields_title_layout.addWidget(fields_title_label)
        
        # 刷新按钮
        self.refresh_table_btn = QPushButton("刷新")
        self.refresh_table_btn.setMaximumWidth(80)
        self.refresh_table_btn.setToolTip("重新加载当前表数据")
        self.refresh_table_btn.clicked.connect(self.refresh_current_table)
        fields_title_layout.addWidget(self.refresh_table_btn)
        fields_title_layout.addStretch()
        
        # 字段信息文本
        self.fields_info_text = QTextEdit()
        self.fields_info_text.setReadOnly(True)
        self.fields_info_text.setMinimumHeight(70)  # 增加最小高度
        self.fields_info_text.setMaximumHeight(100)  # 增加最大高度
        self.fields_info_text.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                font-family: 'Microsoft YaHei UI', monospace;
                font-size: 10pt;
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        
        fields_info_layout.addLayout(fields_title_layout)
        fields_info_layout.addWidget(self.fields_info_text)
        self.fields_info_frame.setLayout(fields_info_layout)
        
        # 初始隐藏字段信息区域，直到有表格数据显示
        self.fields_info_frame.setVisible(False)
        
        table_layout.addWidget(self.fields_info_frame)
        
        # 表格
        self.result_table = QTableWidget()
        
        # 配置表格属性
        self.result_table.setAlternatingRowColors(True)  # 交替行颜色
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)  # 选择整行
        self.result_table.setSelectionMode(QTableWidget.SingleSelection)  # 单选
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 禁止编辑
        self.result_table.setSortingEnabled(False)  # 禁用排序
        
        # 设置表格的字体和样式
        table_font = QFont('Microsoft YaHei UI', 9)
        self.result_table.setFont(table_font)
        
        # 优化性能设置
        self.result_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.result_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        
        table_layout.addWidget(self.result_table)
        table_tab.setLayout(table_layout)
        
        # 可视化标签页
        viz_tab = QWidget()
        viz_layout = QVBoxLayout()
        
        # 创建图表控件
        self.viz_figure = FigureCanvas(None)
        viz_layout.addWidget(self.viz_figure)
        
        # 创建数据摘要区域
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(200)
        viz_layout.addWidget(QLabel('数据摘要:'))
        viz_layout.addWidget(self.summary_text)
        
        viz_tab.setLayout(viz_layout)
        
        # 添加标签页
        self.result_tabs.addTab(sql_tab, "SQL结果")
        self.result_tabs.addTab(table_tab, "表格视图")
        self.result_tabs.addTab(viz_tab, "可视化")
        
        result_layout.addWidget(QLabel('查询结果:'))
        result_layout.addWidget(self.result_tabs)
        
        result_frame.setLayout(result_layout)
        return result_frame
        
    def apply_style(self):
        """应用样式"""
        # 设置全局字体
        font = QFont('Microsoft YaHei UI', 9)
        self.setFont(font)
        
        # 设置样式表
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QFrame {
                background-color: white;
                border-radius: 5px;
                padding: 10px;
                margin: 2px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 5px;
            }
            QLabel {
                color: #333;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 5px;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 5px 10px;
                margin-right: 2px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            QTabBar::tab:selected {
                background-color: #2196F3;
                color: white;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #ddd;
            }
        """)
        
    def init_api(self):
        """初始化API"""
        try:
            api_key = self.app_settings.get_api_key()
            api_base_url = self.app_settings.get_api_base_url()
            model = self.app_settings.get_model()
            api_type = self.app_settings.get_api_type()  # 获取API类型
            
            # 根据不同API类型处理
            if api_type == 'ollama':
                # Ollama模式下不需要API密钥
                self.openai_handler = OpenAIHandler(
                    api_key='',  # Ollama不需要API密钥
                    api_base_url=api_base_url,
                    model=model,
                    api_type='ollama'
                )
                logger.info("Ollama API 已初始化")
            elif api_key:  # OpenAI模式需要API密钥
                self.openai_handler = OpenAIHandler(
                    api_key=api_key,
                    api_base_url=api_base_url,
                    model=model,
                    api_type='openai'
                )
                logger.info("OpenAI API 已初始化")
        except Exception as e:
            handle_exception(e, "初始化API")
        
    def load_database_settings(self):
        """加载保存的数据库连接信息"""
        self.host_input.setText(self.app_settings.get_db_host())
        self.user_input.setText(self.app_settings.get_db_user())
        self.password_input.setText(self.app_settings.get_db_password())
        self.database_input.setText(self.app_settings.get_db_name())
        logger.debug("已加载保存的数据库连接信息")
        
    def connect_database(self):
        """连接数据库"""
        host = self.host_input.text()
        user = self.user_input.text()
        password = self.password_input.text()
        database = self.database_input.text()
        
        if not all([host, user, database]):
            QMessageBox.warning(self, '警告', '请填写数据库连接信息！')
            return
        
        if self.db.connect(host, user, password, database):
            # 连接成功后保存设置
            self.app_settings.save_db_connection(host, user, password, database)
            QMessageBox.information(self, '成功', '数据库连接成功！')
        else:
            QMessageBox.critical(self, '错误', '数据库连接失败！请检查连接信息。')
            
    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.init_api()
            QMessageBox.information(self, '成功', '设置已保存！')
            
    def show_history(self):
        """显示历史记录对话框"""
        dialog = HistoryDialog(self, self.history)
        dialog.exec_()
        
        # 根据历史记录状态更新按钮状态
        self.update_history_buttons()
        
    def update_history_buttons(self):
        """更新历史记录相关按钮的状态"""
        self.undo_btn.setEnabled(self.history.can_undo())
        self.redo_btn.setEnabled(self.history.can_redo())
        
    def undo_operation(self):
        """回退到上一个操作"""
        if not self.history.can_undo():
            return
            
        # 获取上一个操作
        operation = self.history.get_previous_operation()
        if not operation:
            return
            
        # 显示当前回到的操作
        QMessageBox.information(self, '回退', f"已回退到: {operation.get('timestamp')} - {operation.get('natural_query')}")
        
        # 更新按钮状态
        self.update_history_buttons()
        
    def redo_operation(self):
        """前进到下一个操作"""
        if not self.history.can_redo():
            return
            
        # 获取下一个操作
        operation = self.history.get_next_operation()
        if not operation:
            return
            
        # 重新执行该操作
        op_type = operation.get('operation_type', '').upper()
        sql = operation.get('sql', '')
        natural_query = operation.get('natural_query', '')
        
        if op_type == 'SELECT':
            # 执行查询
            self.execute_sql_query(sql, natural_query, add_to_history=False)
        else:
            # 执行修改
            self.execute_modification_query(sql, natural_query, op_type, add_to_history=False)
            
        # 更新按钮状态
        self.update_history_buttons()
        
    def execute_query(self):
        """执行自然语言查询（只读）"""
        if not self.openai_handler:
            QMessageBox.warning(self, '警告', '请先在设置中配置API！')
            return
            
        natural_query = self.natural_query_input.toPlainText()
        if not natural_query:
            QMessageBox.warning(self, '警告', '请输入查询内容！')
            return
            
        try:
            # 检查数据库连接
            if not self.db.is_connected():
                QMessageBox.warning(self, '警告', '请先连接数据库！')
                return
                
            # 获取数据库结构信息
            schema_info = self.db.get_schema_info()
            if not schema_info:
                QMessageBox.warning(self, '警告', '无法获取数据库结构信息，请确认数据库中有表！')
                return
                
            logger.info(f"开始处理自然语言查询: {natural_query}")
            logger.debug(f"数据库结构: {schema_info[:200]}...")
            
            # 显示等待消息
            self.result_text.setText("正在处理查询，请稍候...")
            self.result_text.repaint()
            
            # 将自然语言转换为SQL
            sql_query = self.openai_handler.natural_to_sql(natural_query, schema_info)
            if not sql_query:
                QMessageBox.critical(self, '错误', '无法生成SQL查询，请检查API设置！')
                return
                
            # 执行SQL查询
            self.execute_sql_query(sql_query, natural_query)
            
        except Exception as e:
            error_msg = handle_exception(e, "查询执行")
            QMessageBox.critical(self, '错误', f'查询执行失败：{str(e)}')
            
    def execute_sql_query(self, sql_query, natural_query, add_to_history=True):
        """执行SQL查询
        
        Args:
            sql_query: SQL查询语句
            natural_query: 原始的自然语言查询
            add_to_history: 是否添加到历史记录
        """
        try:
            logger.info(f"执行SQL查询: {sql_query}")
            
            # 尝试提取表名
            table_name = self.extract_table_name(sql_query)
            
            # 检查结果
            results = self.db.execute_query(sql_query)
            if results is None:
                self.result_text.setText(f"SQL: {sql_query}\n\n查询执行出错，请检查SQL语法")
                QMessageBox.critical(self, '错误', '查询执行出错，请检查SQL语法')
                return
                
            if results.empty:
                self.result_text.setText(f"SQL: {sql_query}\n\n查询执行成功，但没有返回任何数据")
                QMessageBox.information(self, '提示', '查询执行成功，但没有返回任何数据')
                
                # 添加到历史记录
                if add_to_history:
                    self.history.add_operation(
                        operation_type="SELECT",
                        query=sql_query,
                        natural_query=natural_query,
                        affected_rows=0,
                        result="查询成功，无结果"
                    )
                    self.update_history_buttons()
                return
                
            # 预处理结果，确保数据格式正确
            try:
                # 清理DataFrame中的特殊类型
                for col in results.columns:
                    # 将二进制数据转换为字符串描述
                    if results[col].dtype == 'object':
                        results[col] = results[col].apply(
                            lambda x: f"BINARY({len(x)} bytes)" if isinstance(x, (bytes, bytearray)) else x
                        )
                logger.info("DataFrame预处理完成")
            except Exception as e:
                logger.warning(f"DataFrame预处理时出错: {str(e)}")
                
            # 显示SQL结果和数据表格
            self.result_text.setText(f"SQL: {sql_query}\n\n结果:\n{results.to_string()}")
            self.display_table_results(results, table_name)
            
            # 生成数据摘要
            summary = DataVisualizer.get_data_summary(results)
            self.summary_text.setText(summary)
            
            # 可视化结果
            self.visualize_results(results)
            
            # 切换到表格视图
            self.result_tabs.setCurrentIndex(1)
            
            # 添加到历史记录
            if add_to_history:
                self.history.add_operation(
                    operation_type="SELECT",
                    query=sql_query,
                    natural_query=natural_query,
                    affected_rows=len(results),
                    result=f"查询成功，返回 {len(results)} 行"
                )
                self.update_history_buttons()
            
        except Exception as e:
            error_msg = handle_exception(e, "SQL查询执行")
            QMessageBox.critical(self, '错误', f'查询执行失败：{str(e)}')
            
    def execute_modification(self):
        """执行自然语言修改操作（增删改）"""
        if not self.openai_handler:
            QMessageBox.warning(self, '警告', '请先在设置中配置API！')
            return
            
        natural_query = self.natural_query_input.toPlainText()
        if not natural_query:
            QMessageBox.warning(self, '警告', '请输入修改指令！')
            return
            
        try:
            # 检查数据库连接
            if not self.db.is_connected():
                QMessageBox.warning(self, '警告', '请先连接数据库！')
                return
                
            # 获取数据库结构信息
            schema_info = self.db.get_schema_info()
            if not schema_info:
                QMessageBox.warning(self, '警告', '无法获取数据库结构信息，请确认数据库中有表！')
                return
                
            logger.info(f"开始处理自然语言修改操作: {natural_query}")
            
            # 显示等待消息
            self.result_text.setText("正在处理修改指令，请稍候...")
            self.result_text.repaint()
            
            # 将自然语言转换为SQL修改语句
            sql_result = self.openai_handler.natural_to_modify_sql(natural_query, schema_info)
            if not sql_result:
                QMessageBox.critical(self, '错误', '无法生成SQL修改语句，请检查API设置或修改指令！')
                return
                
            # 获取SQL和操作类型
            sql = sql_result.get('sql', '')
            operation_type = sql_result.get('operation_type', '').upper()
            affected_table = sql_result.get('affected_table', '')
            rollback_sql = sql_result.get('rollback_sql', '')
            description = sql_result.get('description', '')
            
            # 确认修改操作
            if operation_type in ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP']:
                msg = f"将执行以下{operation_type}操作:\n\n{sql}\n\n描述: {description}"
                if rollback_sql:
                    msg += f"\n\n回滚SQL: {rollback_sql}"
                    
                reply = QMessageBox.question(self, '确认修改操作', msg, 
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply != QMessageBox.Yes:
                    self.result_text.setText("修改操作已取消")
                    return
                    
                # 执行修改操作
                self.execute_modification_query(sql, natural_query, operation_type, rollback_sql, description)
            else:
                QMessageBox.warning(self, '警告', f'不支持的操作类型: {operation_type}')
                
        except Exception as e:
            error_msg = handle_exception(e, "自然语言修改操作")
            QMessageBox.critical(self, '错误', f'修改操作失败：{str(e)}')
            
    def execute_modification_query(self, sql, natural_query, operation_type, rollback_sql=None, 
                                description=None, add_to_history=True):
        """执行SQL修改语句
        
        Args:
            sql: SQL修改语句
            natural_query: 原始的自然语言查询
            operation_type: 操作类型
            rollback_sql: 回滚SQL
            description: 操作描述
            add_to_history: 是否添加到历史记录
        """
        try:
            # 执行修改操作
            success, result = self.db.execute_modification(sql)
            
            if not success:
                self.result_text.setText(f"SQL: {sql}\n\n执行失败: {result}")
                QMessageBox.critical(self, '错误', f'修改操作执行失败: {result}')
                return
                
            # 显示结果
            affected_rows = result if isinstance(result, int) else 0
            result_text = f"SQL: {sql}\n\n执行成功，影响了 {affected_rows} 行"
            
            if description:
                result_text += f"\n\n操作描述: {description}"
                
            if rollback_sql:
                result_text += f"\n\n回滚SQL: {rollback_sql}"
                
            self.result_text.setText(result_text)
            
            # 清空其他视图
            self.result_table.clear()
            self.result_table.setRowCount(0)
            self.result_table.setColumnCount(0)
            
            # 切换到SQL结果标签页
            self.result_tabs.setCurrentIndex(0)
            
            # 成功提示
            QMessageBox.information(self, '成功', f'修改操作执行成功，影响了 {affected_rows} 行')
            
            # 添加到历史记录
            if add_to_history:
                result_summary = f"执行成功，影响了 {affected_rows} 行"
                self.history.add_operation(
                    operation_type=operation_type,
                    query=sql,
                    natural_query=natural_query,
                    affected_rows=affected_rows,
                    result=result_summary,
                    rollback_sql=rollback_sql
                )
                # 保存历史记录
                self.history.save_to_file()
                # 更新按钮状态
                self.update_history_buttons()
                
            # 如果是SELECT操作类型，则刷新表中数据
            if operation_type in ['INSERT', 'UPDATE', 'DELETE']:
                # 尝试查询修改后的表
                table_name = self.extract_table_name(sql)
                if table_name:
                    try:
                        refresh_sql = f"SELECT * FROM {table_name} LIMIT 100;"
                        # 执行刷新查询，传递表名
                        results = self.db.execute_query(refresh_sql)
                        if results is not None and not results.empty:
                            self.result_text.setText(f"SQL: {sql}\n\n执行成功，影响了 {affected_rows} 行\n\n当前表数据:")
                            self.display_table_results(results, table_name)
                            self.result_tabs.setCurrentIndex(1)  # 切换到表格视图
                    except Exception as e:
                        logger.warning(f"刷新表 {table_name} 失败: {str(e)}")
            
        except Exception as e:
            error_msg = handle_exception(e, "修改操作执行")
            QMessageBox.critical(self, '错误', f'修改操作执行失败: {str(e)}')
            
    def extract_table_name(self, sql):
        """从SQL语句中提取表名"""
        try:
            sql = sql.strip().upper()
            
            if sql.startswith("INSERT INTO"):
                # INSERT INTO table_name ...
                match = re.search(r"INSERT INTO\s+(\w+)", sql)
                if match:
                    return match.group(1)
            elif sql.startswith("UPDATE"):
                # UPDATE table_name ...
                match = re.search(r"UPDATE\s+(\w+)", sql)
                if match:
                    return match.group(1)
            elif sql.startswith("DELETE FROM"):
                # DELETE FROM table_name ...
                match = re.search(r"DELETE FROM\s+(\w+)", sql)
                if match:
                    return match.group(1)
            elif sql.startswith("SELECT"):
                # SELECT ... FROM table_name ...
                match = re.search(r"FROM\s+(\w+)", sql)
                if match:
                    return match.group(1)
            
            return None
        except Exception:
            return None
        
    def display_table_results(self, df, table_name=None):
        """在表格中显示查询结果
        
        Args:
            df: 数据框
            table_name: 表名（可选）
        """
        try:
            # 清空表格
            self.result_table.clear()
            self.result_table.setRowCount(0)
            self.result_table.setColumnCount(0)
            
            if df is None or df.empty:
                self.fields_info_frame.setVisible(False)
                return
            
            logger.info(f"准备显示表格数据, 行数: {len(df)}, 列数: {len(df.columns)}")
            
            # 显示字段信息
            self._display_fields_info(df, table_name)
                
            # 设置列数和列标题
            self.result_table.setColumnCount(len(df.columns))
            self.result_table.setHorizontalHeaderLabels(df.columns)
            
            # 预处理：确定每列是否为数值类型
            numeric_columns = {}
            for col_idx, col_name in enumerate(df.columns):
                try:
                    # 尝试多种方法判断是否为数值列
                    is_numeric = False
                    
                    # 方法1: 使用pandas API (如果可用)
                    if hasattr(pd, 'api') and hasattr(pd.api, 'types') and hasattr(pd.api.types, 'is_numeric_dtype'):
                        is_numeric = pd.api.types.is_numeric_dtype(df[col_name])
                    # 方法2: 检查dtype的kind属性
                    elif hasattr(df[col_name].dtype, 'kind'):
                        is_numeric = df[col_name].dtype.kind in 'iufc'
                    # 方法3: 尝试将第一个非空值转换为float
                    else:
                        first_non_null = df[col_name].dropna().iloc[0] if not df[col_name].dropna().empty else None
                        if first_non_null is not None:
                            try:
                                float(first_non_null)
                                is_numeric = True
                            except (ValueError, TypeError):
                                is_numeric = False
                                
                    numeric_columns[col_idx] = is_numeric
                    logger.debug(f"列 '{col_name}' (dtype: {df[col_name].dtype}) 被识别为 {'数值' if is_numeric else '非数值'} 类型")
                except Exception as e:
                    numeric_columns[col_idx] = False
                    logger.warning(f"判断列 '{col_name}' 类型时出错: {str(e)}")
            
            # 设置行数
            self.result_table.setRowCount(len(df))
            
            # 填充数据并设置颜色
            for row in range(len(df)):
                for col in range(len(df.columns)):
                    # 安全转换值为字符串
                    value = df.iloc[row, col]
                    if value is None:
                        str_value = ""
                    else:
                        try:
                            str_value = str(value)
                        except Exception:
                            str_value = "错误数据"
                    
                    item = QTableWidgetItem(str_value)
                    
                    # 为数值型数据右对齐
                    if numeric_columns.get(col, False):
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    else:
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        
                    self.result_table.setItem(row, col, item)
                    
            # 调整列宽以适应内容
            self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            
            # 确保刷新显示
            self.result_table.viewport().update()
            
            logger.info(f"表格显示成功，显示了 {len(df)} 行数据")
            
        except Exception as e:
            error_msg = handle_exception(e, "表格显示")
            logger.error(f"表格显示错误: {str(e)}")
            
    def _display_fields_info(self, df, table_name=None):
        """显示字段信息
        
        Args:
            df: 数据框
            table_name: 表名（可选）
        """
        try:
            # 准备字段信息内容
            field_info_text = ""
            
            # 如果知道表名，显示表名
            if table_name:
                field_info_text += f"表名: {table_name}\n"
            
            # 构建字段信息
            fields = []
            for col_idx, col_name in enumerate(df.columns):
                # 获取数据类型
                dtype_str = str(df[col_name].dtype)
                
                # 简化数据类型显示
                if 'int' in dtype_str:
                    dtype_display = '整数'
                elif 'float' in dtype_str:
                    dtype_display = '浮点数'
                elif 'datetime' in dtype_str:
                    dtype_display = '日期时间'
                elif 'bool' in dtype_str:
                    dtype_display = '布尔值'
                elif 'object' in dtype_str:
                    dtype_display = '文本'
                else:
                    dtype_display = dtype_str
                
                # 添加字段信息
                fields.append(f"{col_name} ({dtype_display})")
            
            # 每行显示最多3个字段，按逗号分隔
            field_chunks = []
            chunk_size = 3
            for i in range(0, len(fields), chunk_size):
                chunk = fields[i:i+chunk_size]
                field_chunks.append(", ".join(chunk))
            
            # 拼接所有字段信息
            field_info_text += "\n".join(field_chunks)
            
            # 显示字段信息
            self.fields_info_text.setText(field_info_text)
            self.fields_info_frame.setVisible(True)
            
        except Exception as e:
            logger.warning(f"显示字段信息时出错: {str(e)}")
            # 出错时隐藏字段信息区域
            self.fields_info_frame.setVisible(False)
        
    def visualize_results(self, df):
        """可视化查询结果"""
        try:
            # 创建可视化图表
            fig = DataVisualizer.create_visualization(df)
            if fig:
                self.viz_figure.figure = fig
                self.viz_figure.draw()
            
        except Exception as e:
            handle_exception(e, "可视化生成")
            
    def test_api_connection(self):
        """测试API连接"""
        api_key = self.app_settings.get_api_key()
        api_base_url = self.app_settings.get_api_base_url()
        model = self.app_settings.get_model()
        api_type = self.app_settings.get_api_type()
        
        # 如果是OpenAI模式，需要检查API密钥
        if api_type == 'openai' and not api_key:
            QMessageBox.warning(self, '警告', '请先在设置中配置API密钥！')
            return
        
        # 如果是Ollama模式，需要检查API URL
        if api_type == 'ollama' and not api_base_url:
            QMessageBox.warning(self, '警告', '请先在设置中配置Ollama API URL！')
            return
        
        try:
            self.result_text.setText("正在测试API连接...")
            self.result_text.repaint()
            
            # 如果还没初始化，先初始化处理器
            if not self.openai_handler:
                if api_type == 'ollama':
                    self.openai_handler = OpenAIHandler('', api_base_url, model, 'ollama')
                else:
                    self.openai_handler = OpenAIHandler(api_key, api_base_url, model, 'openai')
            
            # 执行测试
            success, content = self.openai_handler.test_connection()
            
            if success:
                QMessageBox.information(self, 'API测试成功', f'API连接正常!\n返回: {content}')
            else:
                QMessageBox.critical(self, '错误', f'API测试失败: {content}')
                
            self.result_text.setText("")
            
        except Exception as e:
            error_msg = handle_exception(e, "API测试")
            QMessageBox.critical(self, '错误', f'API测试失败：{str(e)}')
            
    def show_database_structure(self):
        """显示当前连接的数据库结构"""
        if not self.db.is_connected():
            QMessageBox.warning(self, '警告', '请先连接数据库！')
            return
            
        try:
            # 获取数据库结构信息
            schema_info = self.db.get_schema_info()
            if not schema_info:
                QMessageBox.warning(self, '警告', '无法获取数据库结构信息，请确认数据库中有表！')
                return
                
            # 从schema_info中提取自然语言描述
            schema_dict = ast.literal_eval(schema_info)
            description = schema_dict.get('description', '无法获取结构描述')
            
            # 创建对话框显示结构信息
            schema_dialog = QDialog(self)
            schema_dialog.setWindowTitle('数据库结构')
            schema_dialog.setMinimumSize(800, 600)
            
            dialog_layout = QVBoxLayout()
            
            schema_text = QTextEdit()
            schema_text.setReadOnly(True)
            schema_text.setText(description)
            schema_text.setLineWrapMode(QTextEdit.WidgetWidth)
            
            dialog_layout.addWidget(QLabel('数据库结构信息:'))
            dialog_layout.addWidget(schema_text)
            
            # 添加关闭按钮
            close_btn = QPushButton('关闭')
            close_btn.clicked.connect(schema_dialog.accept)
            dialog_layout.addWidget(close_btn)
            
            schema_dialog.setLayout(dialog_layout)
            schema_dialog.exec_()
            
        except Exception as e:
            error_msg = handle_exception(e, "显示数据库结构")
            QMessageBox.critical(self, '错误', f'显示数据库结构失败：{str(e)}')

    def refresh_current_table(self):
        """刷新当前显示的表数据"""
        # 从字段信息中获取当前表名
        field_info_text = self.fields_info_text.toPlainText()
        table_name_match = re.search(r"表名:\s+(\w+)", field_info_text)
        
        if not table_name_match:
            QMessageBox.warning(self, '警告', '未找到当前表名，无法刷新')
            return
            
        table_name = table_name_match.group(1)
        
        try:
            # 检查数据库连接
            if not self.db.is_connected():
                QMessageBox.warning(self, '警告', '请先连接数据库！')
                return
                
            # 执行查询
            refresh_sql = f"SELECT * FROM {table_name} LIMIT 1000;"
            logger.info(f"刷新表 {table_name}")
            
            # 显示等待消息
            self.result_text.setText(f"正在刷新表 {table_name}...")
            self.result_text.repaint()
            
            # 执行查询
            results = self.db.execute_query(refresh_sql)
            
            if results is None:
                QMessageBox.critical(self, '错误', f'刷新表 {table_name} 失败')
                return
                
            if results.empty:
                self.result_text.setText(f"表 {table_name} 不包含任何数据")
                QMessageBox.information(self, '提示', f'表 {table_name} 不包含任何数据')
                return
                
            # 更新显示
            self.result_text.setText(f"表 {table_name} 刷新成功，查询到 {len(results)} 行数据")
            self.display_table_results(results, table_name)
            
            # 切换到表格视图
            self.result_tabs.setCurrentIndex(1)
            
            QMessageBox.information(self, '成功', f'表 {table_name} 刷新成功')
            
        except Exception as e:
            error_msg = handle_exception(e, f"刷新表 {table_name}")
            QMessageBox.critical(self, '错误', f'刷新表失败：{str(e)}')

    # 添加查看表功能
    def show_tables(self):
        """显示数据库中的所有表并选择一个查看"""
        if not self.db.is_connected():
            QMessageBox.warning(self, '警告', '请先连接数据库！')
            return
            
        try:
            # 获取所有表
            query = "SHOW TABLES"
            tables_df = self.db.execute_query(query)
            
            if tables_df is None or tables_df.empty:
                QMessageBox.warning(self, '警告', '数据库中没有表！')
                return
                
            # 提取表名
            table_names = tables_df.iloc[:, 0].tolist()
            
            if not table_names:
                QMessageBox.warning(self, '警告', '数据库中没有表！')
                return
                
            # 创建表选择对话框
            table_dialog = QDialog(self)
            table_dialog.setWindowTitle('选择表')
            table_dialog.setMinimumWidth(300)
            
            dialog_layout = QVBoxLayout()
            
            # 添加表说明
            dialog_layout.addWidget(QLabel(f'数据库中共有 {len(table_names)} 个表:'))
            
            # 创建表列表按钮
            button_group = QVBoxLayout()
            
            # 使用普通函数替代Lambda函数
            def create_click_handler(table_name_str):
                def handler():
                    self._view_table_content(table_name_str, table_dialog)
                return handler
            
            for table_name in table_names:
                # 确保表名是字符串
                table_name_str = str(table_name)
                btn = QPushButton(table_name_str)
                # 使用普通函数而不是Lambda
                btn.clicked.connect(create_click_handler(table_name_str))
                button_group.addWidget(btn)
                
            # 添加滚动区域
            scroll_area = QWidget()
            scroll_area.setLayout(button_group)
            
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(scroll_area)
            
            dialog_layout.addWidget(scroll)
            
            # 添加取消按钮
            cancel_btn = QPushButton('取消')
            cancel_btn.clicked.connect(table_dialog.reject)
            dialog_layout.addWidget(cancel_btn)
            
            table_dialog.setLayout(dialog_layout)
            table_dialog.exec_()
            
        except Exception as e:
            error_msg = handle_exception(e, "获取表列表")
            QMessageBox.critical(self, '错误', f'获取表列表失败：{str(e)}')
            
    def _view_table_content(self, table_name, dialog=None):
        """查看指定表的内容
        
        Args:
            table_name: 表名
            dialog: 对话框实例，如果提供则关闭
        """
        try:
            if dialog:
                dialog.accept()
                
            # 确保表名是字符串
            table_name = str(table_name)
                
            # 显示等待消息
            self.result_text.setText(f"正在加载表 {table_name} 的内容...")
            self.result_text.repaint()
            
            # 查询表内容
            query = f"SELECT * FROM `{table_name}` LIMIT 1000"
            results = self.db.execute_query(query)
            
            if results is None:
                QMessageBox.critical(self, '错误', f'查询表 {table_name} 失败')
                return
                
            if results.empty:
                self.result_text.setText(f"表 {table_name} 不包含任何数据")
                QMessageBox.information(self, '提示', f'表 {table_name} 不包含任何数据')
                return
                
            # 显示查询结果
            self.result_text.setText(f"表 {table_name} 查询成功，共 {len(results)} 行数据")
            self.display_table_results(results, table_name)
            
            # 切换到表格视图
            self.result_tabs.setCurrentIndex(1)
            
        except Exception as e:
            error_msg = handle_exception(e, f"查看表 {table_name}")
            QMessageBox.critical(self, '错误', f'查看表失败：{str(e)}')

class HistoryDialog(QDialog):
    """历史记录对话框"""
    
    def __init__(self, parent=None, history=None):
        super().__init__(parent)
        self.parent = parent
        self.history = history
        self.selected_operation = None
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('操作历史记录')
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # 创建历史记录表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(['时间', '操作类型', '自然语言查询', '影响行数', '结果'])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SingleSelection)
        self.history_table.setAlternatingRowColors(True)
        
        # 双击事件
        self.history_table.cellDoubleClicked.connect(self.on_history_double_click)
        
        layout.addWidget(QLabel('历史操作记录:'))
        layout.addWidget(self.history_table)
        
        # SQL预览
        self.sql_preview = QTextEdit()
        self.sql_preview.setReadOnly(True)
        self.sql_preview.setMaximumHeight(150)
        layout.addWidget(QLabel('SQL语句:'))
        layout.addWidget(self.sql_preview)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.replay_btn = QPushButton('重新执行')
        self.replay_btn.clicked.connect(self.replay_operation)
        self.replay_btn.setEnabled(False)
        
        self.revert_btn = QPushButton('撤销操作')
        self.revert_btn.clicked.connect(self.revert_operation)
        self.revert_btn.setEnabled(False)
        
        self.export_btn = QPushButton('导出历史')
        self.export_btn.clicked.connect(self.export_history)
        
        self.close_btn = QPushButton('关闭')
        self.close_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.replay_btn)
        btn_layout.addWidget(self.revert_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # 加载历史记录
        self.load_history()
        
    def load_history(self):
        """加载历史记录到表格"""
        if not self.history:
            return
            
        operations = self.history.get_all_operations()
        if not operations:
            return
            
        self.history_table.setRowCount(len(operations))
        
        for i, op in enumerate(operations):
            # 时间
            self.history_table.setItem(i, 0, QTableWidgetItem(op.get('timestamp', '')))
            # 操作类型
            self.history_table.setItem(i, 1, QTableWidgetItem(op.get('operation_type', '')))
            # 自然语言查询
            self.history_table.setItem(i, 2, QTableWidgetItem(op.get('natural_query', '')))
            # 影响行数
            self.history_table.setItem(i, 3, QTableWidgetItem(str(op.get('affected_rows', 0))))
            # 结果
            self.history_table.setItem(i, 4, QTableWidgetItem(op.get('result', '')))
            
        # 当前操作高亮显示
        current_index = self.history.current_index
        if current_index >= 0 and current_index < len(operations):
            self.history_table.selectRow(current_index)
            self.update_sql_preview(operations[current_index])
            
        # 根据操作类型设置行的背景色
        for i, op in enumerate(operations):
            op_type = op.get('operation_type', '').upper()
            for col in range(5):
                item = self.history_table.item(i, col)
                if not item:
                    continue
                    
                if op_type == 'SELECT':
                    item.setBackground(QColor(240, 255, 240))  # 浅绿色
                elif op_type in ['INSERT', 'CREATE']:
                    item.setBackground(QColor(240, 248, 255))  # 浅蓝色
                elif op_type in ['UPDATE', 'ALTER']:
                    item.setBackground(QColor(255, 250, 240))  # 浅黄色
                elif op_type in ['DELETE', 'DROP']:
                    item.setBackground(QColor(255, 240, 245))  # 浅红色
                    
        # 连接选择事件
        self.history_table.itemSelectionChanged.connect(self.on_selection_changed)
        
    def on_selection_changed(self):
        """处理选择变化事件"""
        selected_rows = self.history_table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_operation = None
            self.replay_btn.setEnabled(False)
            self.revert_btn.setEnabled(False)
            self.sql_preview.clear()
            return
            
        row = selected_rows[0].row()
        operations = self.history.get_all_operations()
        if 0 <= row < len(operations):
            self.selected_operation = operations[row]
            self.update_sql_preview(self.selected_operation)
            
            # 启用相关按钮
            self.replay_btn.setEnabled(True)
            
            # 检查是否有回滚SQL
            has_rollback = self.selected_operation.get('rollback_sql', None) is not None
            self.revert_btn.setEnabled(has_rollback)
        
    def update_sql_preview(self, operation):
        """更新SQL预览"""
        if not operation:
            self.sql_preview.clear()
            return
            
        sql = operation.get('sql', '')
        self.sql_preview.setText(sql)
        
    def on_history_double_click(self, row, column):
        """处理双击历史记录事件"""
        operations = self.history.get_all_operations()
        if 0 <= row < len(operations):
            self.selected_operation = operations[row]
            self.replay_operation()
        
    def replay_operation(self):
        """重新执行选中的操作"""
        if not self.selected_operation or not self.parent:
            return
            
        self.accept()  # 关闭对话框
        
        # 调用主窗口方法执行操作
        op_type = self.selected_operation.get('operation_type', '').upper()
        sql = self.selected_operation.get('sql', '')
        natural_query = self.selected_operation.get('natural_query', '')
        
        if op_type == 'SELECT':
            # 执行查询
            self.parent.execute_sql_query(sql, natural_query)
        else:
            # 执行修改
            self.parent.execute_modification_query(sql, natural_query, op_type)
            
    def revert_operation(self):
        """撤销选中的操作"""
        if not self.selected_operation or not self.parent:
            return
            
        rollback_sql = self.selected_operation.get('rollback_sql', None)
        if not rollback_sql:
            QMessageBox.warning(self, '警告', '此操作没有回滚SQL')
            return
            
        # 确认
        op_type = self.selected_operation.get('operation_type', '').upper()
        msg = f"确定要撤销此 {op_type} 操作吗？\n这将执行以下SQL:\n{rollback_sql}"
        reply = QMessageBox.question(self, '确认撤销', msg, 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
            
        self.accept()  # 关闭对话框
        
        # 执行回滚SQL
        natural_query = f"撤销: {self.selected_operation.get('natural_query', '')}"
        reversed_type = self.get_reversed_operation_type(op_type)
        self.parent.execute_modification_query(rollback_sql, natural_query, reversed_type)
        
    def get_reversed_operation_type(self, op_type):
        """获取反向操作类型"""
        op_map = {
            'INSERT': 'DELETE',
            'DELETE': 'INSERT',
            'UPDATE': 'UPDATE',
            'CREATE': 'DROP',
            'DROP': 'CREATE',
            'ALTER': 'ALTER'
        }
        return op_map.get(op_type, 'UNKNOWN')
        
    def export_history(self):
        """导出历史记录"""
        if not self.history:
            QMessageBox.warning(self, '警告', '没有历史记录可导出')
            return
            
        filename = "operation_history.json"
        if self.history.save_to_file(filename):
            QMessageBox.information(self, '成功', f'历史记录已导出到：{filename}')
        else:
            QMessageBox.critical(self, '错误', '导出历史记录失败') 