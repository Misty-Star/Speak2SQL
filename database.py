import re
import pandas as pd
import mysql.connector
from utils import logger, handle_exception

class DatabaseConnection:
    """处理MySQL数据库连接和查询"""
    
    def __init__(self):
        self.connection = None
        
    def connect(self, host, user, password, database):
        """连接到MySQL数据库"""
        try:
            logger.info(f"尝试连接数据库: {host}/{database}")
            self.connection = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database
            )
            logger.info("数据库连接成功")
            return True
        except mysql.connector.Error as err:
            error_msg = handle_exception(err, "数据库连接")
            return False
    
    def is_connected(self):
        """检查是否已连接到数据库"""
        return self.connection is not None and self.connection.is_connected()
            
    def execute_query(self, query):
        """执行SQL查询"""
        try:
            # 确保SQL是有效的
            query = self.validate_sql(query)
            logger.info(f"执行SQL: {query}")
            
            cursor = self.connection.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            cursor.close()
            df = pd.DataFrame(results, columns=columns)
            logger.info(f"查询结果: {len(df)} 行")
            return df
        except mysql.connector.Error as err:
            handle_exception(err, "查询执行")
            return None
        
    def validate_sql(self, query):
        """验证并清理SQL语句"""
        # 移除可能的引号
        query = query.strip('\'"')
        
        # 确保以分号结尾
        if not query.rstrip().endswith(';'):
            query = query.rstrip() + ';'
        
        # 移除可能的多行注释
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        
        # 移除可能的单行注释
        query = re.sub(r'--.*?$', '', query, flags=re.MULTILINE)
        
        return query
        
    def get_schema_info(self):
        """获取数据库结构信息"""
        try:
            if not self.is_connected():
                logger.warning("尝试获取结构信息时数据库未连接")
                return None
                
            # 获取数据库表结构信息
            cursor = self.connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            if not tables:
                logger.warning("数据库中没有表")
                return None
                
            schema_info = []
            
            # 获取所有表的详细信息
            for table in tables:
                table_name = table[0]
                table_info = {
                    'table': table_name,
                    'columns': [],
                    'primary_key': [],
                    'foreign_keys': [],
                    'indexes': [],
                    'sample_data': []
                }
                
                # 获取列信息（包括数据类型、是否为NULL、默认值等）
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                
                for col in columns:
                    column_name = col[0]
                    data_type = col[1]
                    is_nullable = col[2]
                    key_type = col[3]
                    default_value = col[4]
                    extra = col[5]
                    
                    column_info = {
                        'name': column_name,
                        'type': data_type,
                        'nullable': is_nullable,
                        'key': key_type,
                        'default': default_value,
                        'extra': extra
                    }
                    
                    table_info['columns'].append(column_info)
                    
                    # 收集主键信息
                    if key_type == 'PRI':
                        table_info['primary_key'].append(column_name)
                
                # 获取索引信息
                cursor.execute(f"SHOW INDEX FROM {table_name}")
                indices = cursor.fetchall()
                for idx in indices:
                    index_name = idx[2]
                    column_name = idx[4]
                    non_unique = idx[1]
                    
                    # 跳过已在其他地方存储的主键索引
                    if index_name == 'PRIMARY':
                        continue
                        
                    table_info['indexes'].append({
                        'name': index_name,
                        'column': column_name,
                        'unique': non_unique == 0
                    })
                
                # 获取外键关系
                try:
                    cursor.execute(f"""
                        SELECT 
                            COLUMN_NAME, 
                            REFERENCED_TABLE_NAME, 
                            REFERENCED_COLUMN_NAME 
                        FROM 
                            INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                        WHERE 
                            TABLE_SCHEMA = DATABASE() AND
                            TABLE_NAME = '{table_name}' AND 
                            REFERENCED_TABLE_NAME IS NOT NULL
                    """)
                    fkeys = cursor.fetchall()
                    for fk in fkeys:
                        table_info['foreign_keys'].append({
                            'column': fk[0],
                            'referenced_table': fk[1],
                            'referenced_column': fk[2]
                        })
                except Exception as e:
                    # 某些MySQL版本或设置可能不支持查询外键信息
                    logger.warning(f"无法获取表 {table_name} 的外键信息: {str(e)}")
                
                # 获取一些示例数据（最多5行）用于增强模型对数据的理解
                try:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                    sample_rows = cursor.fetchall()
                    column_names = [desc[0] for desc in cursor.description]
                    
                    # 将样本数据转换为字典列表
                    for row in sample_rows:
                        row_data = {}
                        for i, value in enumerate(row):
                            # 转换为字符串，以便于JSON序列化
                            if isinstance(value, (bytes, bytearray)):
                                value = f"BINARY({len(value)} bytes)"
                            elif value is not None:
                                value = str(value)
                            row_data[column_names[i]] = value
                        table_info['sample_data'].append(row_data)
                except Exception as e:
                    logger.warning(f"获取表 {table_name} 的示例数据出错: {str(e)}")
                
                schema_info.append(table_info)
                
            cursor.close()
            
            # 将结构信息格式化为字典，方便AI理解
            final_schema = {
                'database_name': self.connection.database,
                'tables': schema_info,
                'table_count': len(schema_info)
            }
            
            # 构建自然语言描述
            nl_description = self.generate_schema_description(final_schema)
            final_schema['description'] = nl_description
            
            logger.info(f"成功获取数据库结构，包含 {len(schema_info)} 张表")
            return str(final_schema)
        except Exception as e:
            handle_exception(e, "获取数据库结构")
            return None
            
    def generate_schema_description(self, schema):
        """生成数据库结构的自然语言描述"""
        db_name = schema['database_name']
        table_count = schema['table_count']
        
        description = f"数据库 {db_name} 包含 {table_count} 张表。\n\n"
        
        for table in schema['tables']:
            table_name = table['table']
            col_count = len(table['columns'])
            
            description += f"表 {table_name} 有 {col_count} 列数据。"
            
            # 添加主键信息
            if table['primary_key']:
                pk_str = ", ".join(table['primary_key'])
                description += f" 主键是: {pk_str}。"
            
            # 添加外键信息
            if table['foreign_keys']:
                fk_str = []
                for fk in table['foreign_keys']:
                    fk_str.append(f"{fk['column']} 引用 {fk['referenced_table']}.{fk['referenced_column']}")
                description += f" 外键关系: {', '.join(fk_str)}。"
            
            # 添加列信息
            description += " 列包括: "
            col_descriptions = []
            for col in table['columns']:
                col_desc = f"{col['name']} ({col['type']})"
                if col['key'] == 'PRI':
                    col_desc += ", 主键"
                if col['nullable'] == 'NO':
                    col_desc += ", 非空"
                col_descriptions.append(col_desc)
            
            description += ", ".join(col_descriptions) + "。\n\n"
        
        return description
        
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("数据库连接已关闭")
            self.connection = None 

    def execute_modification(self, sql):
        """执行数据修改操作，包括INSERT, UPDATE, DELETE等
        
        Args:
            sql: SQL修改语句
            
        Returns:
            tuple: (成功标志, 受影响行数或错误消息)
        """
        try:
            if not self.is_connected():
                logger.warning("尝试执行修改操作时数据库未连接")
                return False, "数据库未连接"
                
            # 验证SQL是数据修改语句
            sql = self.validate_sql(sql)
            operation_type = self.detect_operation_type(sql)
            
            if operation_type not in ["INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"]:
                logger.warning(f"不支持的操作类型: {operation_type}")
                return False, f"不支持的操作类型: {operation_type}"
                
            logger.info(f"执行修改操作: {sql}")
            
            cursor = self.connection.cursor()
            cursor.execute(sql)
            affected_rows = cursor.rowcount
            
            # 提交事务
            self.connection.commit()
            
            cursor.close()
            
            logger.info(f"修改操作执行成功，影响了 {affected_rows} 行")
            return True, affected_rows
        except mysql.connector.Error as err:
            # 回滚事务
            if self.connection and self.connection.is_connected():
                self.connection.rollback()
                
            error_msg = handle_exception(err, "执行修改操作")
            return False, error_msg
            
    def execute_transaction(self, sql_list):
        """执行一组SQL语句作为事务
        
        Args:
            sql_list: 包含多条SQL语句的列表
            
        Returns:
            tuple: (成功标志, 结果或错误消息)
        """
        try:
            if not self.is_connected():
                logger.warning("尝试执行事务时数据库未连接")
                return False, "数据库未连接"
                
            if not sql_list:
                return False, "没有SQL语句需要执行"
                
            logger.info(f"开始执行事务，包含 {len(sql_list)} 条SQL")
            
            # 开始事务
            cursor = self.connection.cursor()
            results = []
            
            for sql in sql_list:
                cursor.execute(sql)
                operation_type = self.detect_operation_type(sql)
                
                if operation_type.startswith("SELECT"):
                    # 如果是查询，获取结果
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    results.append({
                        'operation_type': 'SELECT',
                        'data': pd.DataFrame(rows, columns=columns)
                    })
                else:
                    # 如果是修改操作，获取影响的行数
                    results.append({
                        'operation_type': operation_type,
                        'affected_rows': cursor.rowcount
                    })
            
            # 提交事务
            self.connection.commit()
            
            cursor.close()
            
            logger.info("事务执行成功")
            return True, results
        except mysql.connector.Error as err:
            # 回滚事务
            if self.connection and self.connection.is_connected():
                self.connection.rollback()
                logger.warning("事务已回滚")
                
            error_msg = handle_exception(err, "执行事务")
            return False, error_msg
            
    def detect_operation_type(self, sql):
        """检测SQL语句的操作类型
        
        Args:
            sql: SQL语句
            
        Returns:
            str: 操作类型
        """
        sql = sql.strip().upper()
        
        if sql.startswith("SELECT"):
            return "SELECT"
        elif sql.startswith("INSERT"):
            return "INSERT"
        elif sql.startswith("UPDATE"):
            return "UPDATE"
        elif sql.startswith("DELETE"):
            return "DELETE"
        elif sql.startswith("CREATE TABLE"):
            return "CREATE"
        elif sql.startswith("ALTER TABLE"):
            return "ALTER"
        elif sql.startswith("DROP TABLE"):
            return "DROP"
        else:
            return "UNKNOWN" 