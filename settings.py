from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                              QLineEdit, QRadioButton, QGroupBox, QTabWidget, QWidget)
from utils import logger

class AppSettings:
    """应用程序设置管理"""
    
    def __init__(self):
        self.settings = QSettings('MySQLQueryTool', 'Settings')
        
    def get_api_key(self):
        """获取API密钥"""
        return self.settings.value('api_key', '')
        
    def set_api_key(self, api_key):
        """设置API密钥"""
        self.settings.setValue('api_key', api_key)
        
    def get_api_base_url(self):
        """获取API基础URL，根据API类型返回不同的默认值"""
        api_type = self.get_api_type()
        if api_type == 'ollama':
            return self.settings.value('ollama_api_base_url', 'http://localhost:11434')
        else:
            return self.settings.value('openai_api_base_url', 'https://api.openai.com/v1')
        
    def set_api_base_url(self, api_base_url):
        """设置API基础URL，根据当前API类型保存到不同的键"""
        api_type = self.get_api_type()
        if api_type == 'ollama':
            self.settings.setValue('ollama_api_base_url', api_base_url)
        else:
            self.settings.setValue('openai_api_base_url', api_base_url)
        
    def get_model(self):
        """获取模型名称，根据API类型返回不同的默认值"""
        api_type = self.get_api_type()
        if api_type == 'ollama':
            return self.settings.value('ollama_model', 'llama3')
        else:
            return self.settings.value('openai_model', 'gpt-4o-mini')
        
    def set_model(self, model):
        """设置模型名称，根据当前API类型保存到不同的键"""
        api_type = self.get_api_type()
        if api_type == 'ollama':
            self.settings.setValue('ollama_model', model)
        else:
            self.settings.setValue('openai_model', model)
        
    def get_api_type(self):
        """获取API类型（OpenAI或Ollama）"""
        return self.settings.value('api_type', 'openai')
        
    def set_api_type(self, api_type):
        """设置API类型"""
        self.settings.setValue('api_type', api_type)
        
    def get_db_host(self):
        """获取数据库主机地址"""
        return self.settings.value('db_host', '')
        
    def set_db_host(self, host):
        """设置数据库主机地址"""
        self.settings.setValue('db_host', host)
        
    def get_db_user(self):
        """获取数据库用户名"""
        return self.settings.value('db_user', '')
        
    def set_db_user(self, user):
        """设置数据库用户名"""
        self.settings.setValue('db_user', user)
        
    def get_db_password(self):
        """获取数据库密码"""
        return self.settings.value('db_password', '')
        
    def set_db_password(self, password):
        """设置数据库密码"""
        self.settings.setValue('db_password', password)
        
    def get_db_name(self):
        """获取数据库名称"""
        return self.settings.value('db_name', '')
        
    def set_db_name(self, db_name):
        """设置数据库名称"""
        self.settings.setValue('db_name', db_name)
        
    def save_db_connection(self, host, user, password, db_name):
        """保存数据库连接信息"""
        self.set_db_host(host)
        self.set_db_user(user)
        self.set_db_password(password)
        self.set_db_name(db_name)
        logger.info("已保存数据库连接信息")

class SettingsDialog(QDialog):
    """设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = AppSettings()
        self.parent = parent
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('设置')
        self.setFixedSize(600, 400)
        
        main_layout = QVBoxLayout()
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 创建API设置标签页
        api_tab = QWidget()
        api_layout = QVBoxLayout()
        
        # API类型选择
        api_type_group = QGroupBox("API类型")
        api_type_layout = QHBoxLayout()
        
        self.openai_radio = QRadioButton("OpenAI")
        self.ollama_radio = QRadioButton("Ollama")
        
        # 根据保存的设置设置选中状态
        if self.settings.get_api_type() == 'ollama':
            self.ollama_radio.setChecked(True)
        else:
            self.openai_radio.setChecked(True)
            
        self.openai_radio.toggled.connect(self.toggle_api_key_visibility)
        self.ollama_radio.toggled.connect(self.toggle_api_key_visibility)
        
        api_type_layout.addWidget(self.openai_radio)
        api_type_layout.addWidget(self.ollama_radio)
        api_type_group.setLayout(api_type_layout)
        
        api_layout.addWidget(api_type_group)
        
        # API Key设置
        api_key_layout = QHBoxLayout()
        self.api_key_label = QLabel('API Key:')
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setText(self.settings.get_api_key())
        
        api_key_layout.addWidget(self.api_key_label)
        api_key_layout.addWidget(self.api_key_input)
        
        # 将布局放入QWidget中，以便控制其可见性
        self.api_key_widget = QWidget()
        self.api_key_widget.setLayout(api_key_layout)
        api_layout.addWidget(self.api_key_widget)
        
        # API Base URL设置
        base_url_layout = QHBoxLayout()
        base_url_label = QLabel('API Base URL:')
        self.base_url_input = QLineEdit()
        
        base_url_layout.addWidget(base_url_label)
        base_url_layout.addWidget(self.base_url_input)
        
        api_layout.addLayout(base_url_layout)
        
        # 模型设置
        model_layout = QHBoxLayout()
        model_label = QLabel('模型名称:')
        self.model_input = QLineEdit()
        
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_input)
        
        api_layout.addLayout(model_layout)
        
        # 保存按钮
        save_btn = QPushButton('保存设置')
        save_btn.clicked.connect(self.save_settings)
        
        api_layout.addWidget(save_btn)
        api_tab.setLayout(api_layout)
        
        # 调试标签页
        debug_tab = QWidget()
        debug_layout = QVBoxLayout()
        
        # 测试API按钮
        test_api_btn = QPushButton('测试API')
        test_api_btn.setToolTip('测试API连接')
        test_api_btn.clicked.connect(self.test_api)
        debug_layout.addWidget(test_api_btn)
        
        # 查看数据库结构按钮
        view_schema_btn = QPushButton('查看数据库结构')
        view_schema_btn.setToolTip('查看当前数据库的表结构')
        view_schema_btn.clicked.connect(self.show_database_structure)
        debug_layout.addWidget(view_schema_btn)
        
        debug_layout.addStretch()
        debug_tab.setLayout(debug_layout)
        
        # 添加标签页
        tab_widget.addTab(api_tab, "API设置")
        tab_widget.addTab(debug_tab, "调试")
        
        main_layout.addWidget(tab_widget)
        self.setLayout(main_layout)
        
        # 根据当前选择的API类型设置API Key输入的可见性
        self.toggle_api_key_visibility()
        
    def toggle_api_key_visibility(self):
        """根据选择的API类型切换API Key输入框的可见性"""
        if self.openai_radio.isChecked():
            self.api_key_widget.setVisible(True)
            # 从设置中获取OpenAI的URL和模型
            openai_url = self.settings.settings.value('openai_api_base_url', 'https://api.openai.com/v1')
            openai_model = self.settings.settings.value('openai_model', 'gpt-4o-mini')
            self.base_url_input.setText(openai_url)
            self.model_input.setText(openai_model)
        else:
            self.api_key_widget.setVisible(False)
            # 从设置中获取Ollama的URL和模型
            ollama_url = self.settings.settings.value('ollama_api_base_url', 'http://localhost:11434')
            ollama_model = self.settings.settings.value('ollama_model', 'llama3')
            self.base_url_input.setText(ollama_url)
            self.model_input.setText(ollama_model)
        
    def save_settings(self):
        """保存设置"""
        # 保存API类型
        if self.openai_radio.isChecked():
            self.settings.set_api_type('openai')
        else:
            self.settings.set_api_type('ollama')
            
        self.settings.set_api_key(self.api_key_input.text())
        self.settings.set_api_base_url(self.base_url_input.text())
        self.settings.set_model(self.model_input.text())
        logger.info("已保存API设置")
        self.accept()
        
    def test_api(self):
        """调用主窗口的测试API功能"""
        self.accept()  # 先关闭设置对话框
        if self.parent:
            self.parent.test_api_connection()
            
    def show_database_structure(self):
        """调用主窗口的显示数据库结构功能"""
        self.accept()  # 先关闭设置对话框
        if self.parent:
            self.parent.show_database_structure() 