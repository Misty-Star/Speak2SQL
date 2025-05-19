import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure
from utils import logger, handle_exception

# 配置matplotlib支持中文显示
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS', 'DejaVu Sans']  # 用来正常显示中文
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
    logger.info("已配置matplotlib中文字体支持")
except Exception as e:
    logger.warning(f"配置matplotlib中文字体支持失败: {str(e)}")

class DataVisualizer:
    """数据可视化处理类"""
    
    @staticmethod
    def create_visualization(df, figure=None):
        """根据数据特征创建合适的可视化图表"""
        try:
            if df is None or df.empty:
                logger.warning("尝试可视化空数据")
                return None
                
            # 创建或清空图形对象
            if figure is None:
                figure = Figure(figsize=(8, 6), dpi=100)
            else:
                figure.clear()
                
            # 获取数据特征
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns
            
            # 根据数据类型选择合适的可视化方式
            ax = figure.add_subplot(111)
            
            if len(numeric_cols) >= 2:
                # 两个数值列 -> 散点图
                sns.scatterplot(data=df, x=numeric_cols[0], y=numeric_cols[1], ax=ax)
                ax.set_title(f"{numeric_cols[0]} vs {numeric_cols[1]}")
                ax.set_xlabel(numeric_cols[0])
                ax.set_ylabel(numeric_cols[1])
                
            elif len(numeric_cols) == 1 and len(categorical_cols) >= 1:
                # 一个数值列和类别列 -> 分组柱状图
                sns.barplot(data=df, x=categorical_cols[0], y=numeric_cols[0], ax=ax)
                ax.set_title(f"{numeric_cols[0]} by {categorical_cols[0]}")
                ax.set_xlabel(categorical_cols[0])
                ax.set_ylabel(numeric_cols[0])
                # 如果类别过多，旋转标签
                if len(df[categorical_cols[0]].unique()) > 5:
                    plt.xticks(rotation=45, ha='right')
                
            elif len(numeric_cols) == 1:
                # 只有一个数值列 -> 直方图
                sns.histplot(data=df, x=numeric_cols[0], kde=True, ax=ax)
                ax.set_title(f"Distribution of {numeric_cols[0]}")
                ax.set_xlabel(numeric_cols[0])
                ax.set_ylabel("Count")
                
            elif len(categorical_cols) >= 1:
                # 只有一个类别列 -> 计数图或饼图
                value_counts = df[categorical_cols[0]].value_counts()
                
                # 如果类别太多，限制显示前10个
                if len(value_counts) > 10:
                    top_categories = value_counts.nlargest(9).index
                    mask = df[categorical_cols[0]].isin(top_categories)
                    df_plot = pd.DataFrame({
                        categorical_cols[0]: list(df.loc[mask, categorical_cols[0]]) + ["其他"],
                    })
                    
                    # 添加一行"其他"代表其余类别
                    counts = df[categorical_cols[0]].value_counts()
                    other_count = sum(counts[~counts.index.isin(top_categories)])
                    
                    # 饼图
                    labels = list(top_categories) + ["其他"]
                    sizes = list(counts[top_categories]) + [other_count]
                    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
                    ax.axis('equal')  # 等比例绘制，使饼图为圆形
                else:
                    # 饼图
                    ax.pie(
                        value_counts.values, 
                        labels=value_counts.index, 
                        autopct='%1.1f%%',
                        startangle=90
                    )
                    ax.axis('equal')
                    
                ax.set_title(f"Distribution of {categorical_cols[0]}")
            
            else:
                # 无法确定可视化类型
                ax.text(0.5, 0.5, "无法为此数据创建可视化", 
                       horizontalalignment='center', verticalalignment='center')
            
            figure.tight_layout()
            return figure
            
        except Exception as e:
            handle_exception(e, "数据可视化")
            return None
            
    @staticmethod
    def get_html_table(df, max_rows=100):
        """生成美观的HTML表格"""
        try:
            if df is None or df.empty:
                return "<p>无数据可显示</p>"
                
            # 限制显示的行数
            if len(df) > max_rows:
                display_df = df.head(max_rows)
                footer = f"<p>显示 {max_rows} 行，共 {len(df)} 行</p>"
            else:
                display_df = df
                footer = ""
                
            # 格式化表格
            styles = [
                "table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }",
                "th { background-color: #4CAF50; color: white; text-align: left; padding: 12px; }",
                "td { padding: 8px; border-bottom: 1px solid #ddd; }",
                "tr:nth-child(even) { background-color: #f2f2f2; }",
                "tr:hover { background-color: #ddd; }",
                ".numeric { text-align: right; }",
            ]
            
            # 生成HTML头部
            html = f"<style>{''.join(styles)}</style><table>"
            
            # 添加表头
            html += "<tr>"
            for col in display_df.columns:
                html += f"<th>{col}</th>"
            html += "</tr>"
            
            # 添加数据行
            for _, row in display_df.iterrows():
                html += "<tr>"
                for col in display_df.columns:
                    value = row[col]
                    # 为数值型数据添加右对齐样式
                    if pd.api.types.is_numeric_dtype(display_df[col].dtype):
                        html += f'<td class="numeric">{value}</td>'
                    else:
                        html += f"<td>{value}</td>"
                html += "</tr>"
                
            html += "</table>" + footer
            return html
            
        except Exception as e:
            handle_exception(e, "HTML表格生成")
            return f"<p>生成HTML表格时出错: {str(e)}</p>"
            
    @staticmethod
    def get_data_summary(df):
        """生成数据摘要统计信息"""
        try:
            if df is None or df.empty:
                return "无数据可分析"
                
            summary = []
            summary.append(f"总行数: {len(df)}")
            summary.append(f"总列数: {len(df.columns)}")
            
            # 数据类型统计
            dtype_counts = df.dtypes.value_counts().to_dict()
            dtype_info = []
            for dtype, count in dtype_counts.items():
                type_name = str(dtype)
                if 'int' in type_name:
                    dtype_info.append(f"{count} 整数列")
                elif 'float' in type_name:
                    dtype_info.append(f"{count} 浮点数列")
                elif 'object' in type_name or 'string' in type_name:
                    dtype_info.append(f"{count} 文本列")
                elif 'datetime' in type_name:
                    dtype_info.append(f"{count} 日期列")
                elif 'bool' in type_name:
                    dtype_info.append(f"{count} 布尔列")
                elif 'category' in type_name:
                    dtype_info.append(f"{count} 类别列")
                else:
                    dtype_info.append(f"{count} {type_name}列")
            
            summary.append(f"数据类型: {', '.join(dtype_info)}")
            
            # 数值列统计
            numeric_cols = df.select_dtypes(include=['int64', 'float64'])
            if not numeric_cols.empty:
                summary.append("\n数值列统计:")
                for col in numeric_cols.columns:
                    stats = df[col].describe()
                    summary.append(f"  {col}:")
                    summary.append(f"    平均值: {stats['mean']:.2f}")
                    summary.append(f"    中位数: {stats['50%']:.2f}")
                    summary.append(f"    最小值: {stats['min']:.2f}")
                    summary.append(f"    最大值: {stats['max']:.2f}")
            
            # 类别列统计
            categorical_cols = df.select_dtypes(include=['object', 'category'])
            if not categorical_cols.empty:
                summary.append("\n类别列统计:")
                for col in categorical_cols.columns:
                    value_counts = df[col].value_counts()
                    n_categories = len(value_counts)
                    
                    if n_categories <= 5:
                        # 展示所有类别
                        cat_info = []
                        for cat, count in value_counts.items():
                            cat_info.append(f"{cat}: {count}")
                        summary.append(f"  {col}: {n_categories} 类 ({', '.join(cat_info)})")
                    else:
                        # 只展示前3个类别
                        top_cats = []
                        for cat, count in value_counts.head(3).items():
                            top_cats.append(f"{cat}: {count}")
                        summary.append(f"  {col}: {n_categories} 类 (前3: {', '.join(top_cats)}, ...)")
            
            return "\n".join(summary)
            
        except Exception as e:
            handle_exception(e, "数据摘要生成")
            return f"生成数据摘要时出错: {str(e)}" 