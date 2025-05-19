import openai
import re
import requests
import json
from utils import logger, handle_exception

class OpenAIHandler:
    """处理OpenAI或Ollama API调用和自然语言转SQL"""
    
    def __init__(self, api_key, api_base_url, model="gpt-4o-mini", api_type="openai"):
        self.model = model
        self.api_base_url = api_base_url
        self.api_type = api_type  # 'openai' 或 'ollama'
        
        try:
            if self.api_type == 'openai':
                self.client = openai.OpenAI(
                    api_key=api_key,
                    base_url=api_base_url
                )
                logger.info(f"OpenAI客户端初始化成功，模型: {model}")
            else:  # ollama
                # Ollama不需要初始化客户端，只保存URL即可
                logger.info(f"Ollama模式初始化成功，模型: {model}")
        except Exception as e:
            error_msg = handle_exception(e, "API初始化")
            raise Exception(f"API初始化错误: {e}")
    
    def test_connection(self):
        """测试API连接"""
        try:
            if self.api_type == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "简单测试，请回复'连接成功'"}],
                    max_tokens=50
                )
                content = response.choices[0].message.content.strip()
            else:  # ollama
                url = f"{self.api_base_url}/api/chat"
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": "简单测试，请回复'连接成功'"}],
                    "stream": False
                }
                response = requests.post(url, json=payload)
                response.raise_for_status()  # 确保请求成功
                response_json = response.json()
                content = response_json.get('message', {}).get('content', '').strip()
                
            logger.info(f"API连接测试成功，返回: {content}")
            return True, content
        except Exception as e:
            error_msg = handle_exception(e, "API连接测试")
            return False, str(e)
    
    def natural_to_sql(self, natural_query, schema_info):
        """将自然语言转换为SQL查询"""
        try:
            logger.info(f"开始调用模型: {self.model}")
            logger.debug(f"提示词: 数据库结构:{schema_info[:100]}..., 查询:{natural_query}")
            
            # 构建更详细的系统提示
            system_prompt = """你是一个SQL专家，专门将用户的自然语言转换为精确的MySQL查询语句。
你的任务是理解详细的数据库结构（包括表、列、数据类型、关系等），并基于这些信息生成最优的SQL查询。

你应该：
1. 理解表之间的关系，正确使用JOIN
2. 选择合适的WHERE条件
3. 合理使用GROUP BY、HAVING、ORDER BY等子句
4. 需要时使用子查询或公共表表达式(CTE)
5. 考虑查询性能，尽量使用已有的索引

请只返回SQL语句，不要有任何其他解释，不要使用markdown格式，不要使用代码块。
请勿包含任何思考过程，也不要使用<think>、<thinking>、<thoughts>等标签。
直接返回干净的SQL语句，不要有任何前缀或后缀。"""

            # 用户提示
            user_prompt = f"""数据库结构信息：
{schema_info}

用户查询：
{natural_query}

请生成对应的MySQL查询语句，只返回SQL语句本身："""

            # 调用API
            if self.api_type == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,  # 降低随机性，使生成的SQL更确定
                    max_tokens=1000   # 确保有足够的token生成完整SQL
                )
            else:  # ollama
                url = f"{self.api_base_url}/api/chat"
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False,
                    "temperature": 0.1,
                    "max_tokens": 1000
                }
                response = requests.post(url, json=payload)
                response.raise_for_status()
                response = response.json()
                
            # 处理API返回
            sql = self._process_response(response)
            if not sql:
                logger.error("无法从API返回中提取SQL语句")
                return None
                
            # 清理SQL中的标记
            sql = self.clean_sql(sql)
            
            logger.info(f"生成的SQL: {sql}")
            return sql
            
        except Exception as e:
            handle_exception(e, "自然语言转SQL")
            return None
            
    def _process_response(self, response):
        """处理不同格式的API返回"""
        try:
            content = None
            
            if self.api_type == 'openai':
                # 尝试标准OpenAI格式
                content = response.choices[0].message.content.strip()
            else:  # ollama
                # 尝试解析Ollama返回格式
                if isinstance(response, dict):
                    content = response.get('message', {}).get('content', '').strip()
                    
            # 如果成功获取内容，预处理思考标签
            if content:
                # 添加对常见思考标签的预处理
                content = self._preprocess_thinking_tags(content)
                return content
                
        except (AttributeError, TypeError, IndexError):
            try:
                # 尝试解析可能的字符串或JSON格式
                if isinstance(response, str):
                    logger.info("返回值是字符串，尝试解析")
                    try:
                        json_data = json.loads(response)
                        if 'choices' in json_data and len(json_data['choices']) > 0:
                            content = json_data['choices'][0]['message']['content'].strip()
                        elif 'message' in json_data:
                            content = json_data['message']['content'].strip()
                            
                        # 预处理思考标签
                        if content:
                            content = self._preprocess_thinking_tags(content)
                            return content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        # 如果不是JSON或解析失败，直接将返回当作SQL
                        content = response.strip()
                        # 预处理思考标签
                        content = self._preprocess_thinking_tags(content)
                        return content
            except Exception as parse_error:
                logger.error(f"解析返回数据时出错: {parse_error}")
                # 尝试直接使用response作为SQL
                if isinstance(response, str):
                    content = response.strip()
                    # 预处理思考标签
                    content = self._preprocess_thinking_tags(content)
                    return content
        
        # 如果上述都失败
        logger.error(f"API返回原始内容: {response}")
        return None
        
    def _preprocess_thinking_tags(self, content):
        """预处理内容中的思考标签"""
        if not content:
            return content
            
        # 处理多种思考标签格式
        patterns = [
            r'<think>.*?</think>',
            r'<thinking>.*?</thinking>',
            r'<thoughts>.*?</thoughts>',
            r'\[THINKING\].*?\[/THINKING\]'
        ]
        
        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
            
        return content

    def clean_sql(self, sql):
        """清理SQL中的Markdown代码块标记和其他非SQL内容"""
        if not sql:
            return None
        
        # 记录原始输入，用于调试
        logger.debug(f"原始返回内容: {sql[:200]}...")
            
        # 移除思考标签中的内容 (适配各种可能的思考模型标签格式)
        # 处理<think>...</think>格式
        sql = re.sub(r'<think>.*?</think>', '', sql, flags=re.DOTALL | re.IGNORECASE)
        
        # 处理<thinking>...</thinking>格式
        sql = re.sub(r'<thinking>.*?</thinking>', '', sql, flags=re.DOTALL | re.IGNORECASE)
        
        # 处理<thoughts>...</thoughts>格式
        sql = re.sub(r'<thoughts>.*?</thoughts>', '', sql, flags=re.DOTALL | re.IGNORECASE)
        
        # 处理可能存在的[THINKING]...[/THINKING]格式
        sql = re.sub(r'\[THINKING\].*?\[/THINKING\]', '', sql, flags=re.DOTALL | re.IGNORECASE)
        
        # 移除markdown代码块标记
        sql = re.sub(r'^```\s*sql\s*', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'```\s*$', '', sql, flags=re.IGNORECASE) 
        
        # 移除任何SELECT或其他SQL关键字前的内容
        sql = re.sub(r'^.*?(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|SHOW|USE)', r'\1', sql, flags=re.IGNORECASE)
        
        # 确保结尾没有多余内容
        sql = sql.split(';')[0] + ';'
        
        logger.debug(f"清理后的SQL: {sql}")
        return sql 

    def natural_to_modify_sql(self, natural_query, schema_info, current_table=None):
        """将自然语言转换为数据修改SQL查询（INSERT, UPDATE, DELETE等）
        
        Args:
            natural_query: 自然语言查询
            schema_info: 数据库结构信息
            current_table: 当前选中的表（可选）
            
        Returns:
            dict: 包含SQL语句和操作类型的字典
        """
        try:
            logger.info(f"开始生成数据修改SQL: {natural_query}")
            
            # 构建系统提示
            system_prompt = """你是一个SQL专家，专门将用户的自然语言转换为精确的MySQL数据修改语句。
你的任务是理解详细的数据库结构（包括表、列、数据类型等），并基于这些信息生成正确的SQL修改语句。

你应该生成以下类型的SQL语句：
1. INSERT - 添加新数据
2. UPDATE - 修改现有数据
3. DELETE - 删除数据
4. CREATE TABLE - 创建新表
5. ALTER TABLE - 修改表结构
6. DROP TABLE - 删除表

请注意：
1. 确保SQL语句语法正确，并且与MySQL兼容
2. 对于INSERT和UPDATE语句，确保数据类型匹配
3. 对于DELETE语句，总是加上WHERE条件以避免误删全表
4. 返回的修改语句应当可以撤销，考虑生成相应的回滚SQL

请以以下JSON格式返回结果（不要使用markdown）：
{
  "operation_type": "INSERT|UPDATE|DELETE|CREATE|ALTER|DROP",
  "sql": "完整的SQL语句;",
  "affected_table": "受影响的表名",
  "rollback_sql": "用于撤销此操作的SQL（如果适用）",
  "description": "简短描述此操作的影响"
}

不要包含任何其他解释或思考过程。"""

            # 用户提示
            user_prompt = f"""数据库结构信息：
{schema_info}

用户请求：{natural_query}
"""
            # 如果提供了当前表，则添加到提示中
            if current_table:
                user_prompt += f"\n当前选中的表是: {current_table}"

            user_prompt += "\n\n请生成相应的MySQL数据修改语句，并以JSON格式返回:"

            # 调用API
            if self.api_type == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=1000
                )
            else:  # ollama
                url = f"{self.api_base_url}/api/chat"
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False,
                    "temperature": 0.1,
                    "max_tokens": 1000
                }
                response = requests.post(url, json=payload)
                response.raise_for_status()
                response = response.json()
                
            # 处理API返回
            content = self._process_response(response)
            if not content:
                logger.error("无法从API返回中提取内容")
                return None
                
            # 尝试解析JSON
            try:
                # 移除可能的思考标签
                content = self._preprocess_thinking_tags(content)
                
                # 移除markdown代码块标记
                content = re.sub(r'^```\s*json\s*', '', content, flags=re.IGNORECASE)
                content = re.sub(r'```\s*$', '', content, flags=re.IGNORECASE) 
                
                # 解析JSON
                result = json.loads(content.strip())
                
                # 验证必要的字段
                required_fields = ["operation_type", "sql"]
                for field in required_fields:
                    if field not in result:
                        logger.error(f"JSON响应缺少必要字段: {field}")
                        return None
                
                # 清理SQL中的引号
                if "sql" in result:
                    result["sql"] = result["sql"].strip('\'"')
                    # 确保以分号结尾
                    if not result["sql"].rstrip().endswith(';'):
                        result["sql"] = result["sql"].rstrip() + ';'
                
                logger.info(f"生成的数据修改SQL: {result['operation_type']} - {result['sql']}")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"无法解析API返回的JSON: {e}")
                logger.error(f"原始内容: {content}")
                return None
            except Exception as e:
                handle_exception(e, "解析SQL修改结果")
                return None
                
        except Exception as e:
            handle_exception(e, "自然语言转修改SQL")
            return None 