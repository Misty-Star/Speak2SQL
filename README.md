# MySQL自然语言查询工具

基于PyQt6开发的MySQL数据库可视化查询工具，支持自然语言查询和结果可视化。

## 功能特点

- 图形化界面操作
- 通过LLM将自然语言转换为SQL查询
- 自动保存数据库连接信息
- 查询结果表格显示
- 结果数据可视化展示
- 数据库结构浏览
- 模块化设计，便于维护

## 安装

1. 安装依赖项:
```bash
pip install -r requirements.txt
```

2. 配置LLM API:
   - 在程序设置中填写API密钥和基础URL
   - 或者创建`.env`文件添加:
   ```
   OPENAI_API_KEY=your_api_key_here
   OPENAI_API_BASE_URL=https://api.openai.com/v1  # 可选
   ```

## 使用方法

1. 启动程序:
```bash
python main.py
```

2. 连接数据库:
   - 填写MySQL连接信息并点击"连接数据库"
   - 连接成功后信息将被保存

3. 查询数据库:
   - 在自然语言查询框中输入您的问题，例如:
     - "查询所有用户的姓名和年龄"
     - "统计每个部门的员工数量"
     - "找出销售额最高的10个产品"
   - 点击"执行查询"按钮

4. 查看结果:
   - SQL标签页: 显示生成的SQL和原始结果
   - 表格标签页: 以表格方式显示结果
   - 可视化标签页: 显示数据可视化图表

## 项目结构

```
.
├── main.py             # 主程序入口
├── database.py         # 数据库连接模块
├── openai_handler.py   # OpenAI API处理模块
├── visualization.py    # 数据可视化模块
├── settings.py         # 设置管理模块
├── ui.py               # 用户界面模块
├── utils.py            # 工具函数模块
└── requirements.txt    # 依赖项列表
```

## 系统要求

- Python 3.8+
- MySQL数据库
- 有效的LLM API

## 许可证

MIT License 