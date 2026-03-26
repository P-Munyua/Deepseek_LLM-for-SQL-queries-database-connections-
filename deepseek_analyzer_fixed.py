"""
DeepSeek SQL Analyzer - Working version for Streamlit
"""

import sqlite3
import pandas as pd
import ollama
import re
from typing import Dict, Any, List
import json

class DeepSeekSQLAnalyzer:
    """Main analyzer class for DeepSeek SQL operations"""
    
    def __init__(self, database_path: str = "sales_data.db", model: str = "deepseek-r1:1.5b"):
        self.database_path = database_path
        self.model = model
        self.conn = sqlite3.connect(database_path)
        self.temperature = 0.1
        
        # Get database schema
        self.schema = self._get_simple_schema()
        
    def _get_simple_schema(self) -> str:
        """Get simplified database schema"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_lines = []
        for (table_name,) in tables:
            if table_name.startswith('sqlite_'):
                continue
                
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            col_names = [col[1] for col in columns]
            schema_lines.append(f"{table_name}({', '.join(col_names)})")
        
        return "\n".join(schema_lines)
    
    def _get_fallback_sql(self, question: str) -> str:
        """Provide fallback SQL for common questions"""
        q_lower = question.lower()
        
        if 'customer' in q_lower and ('count' in q_lower or 'how many' in q_lower):
            return "SELECT COUNT(*) as total_customers FROM customers;"
        elif 'customer' in q_lower:
            return "SELECT * FROM customers LIMIT 10;"
        elif 'revenue' in q_lower or 'total sales' in q_lower:
            return "SELECT SUM(total_amount) as total_revenue FROM orders;"
        elif 'product' in q_lower and 'top' in q_lower:
            return """SELECT p.product_name, SUM(oi.quantity * oi.price) as revenue
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
GROUP BY p.product_name
ORDER BY revenue DESC
LIMIT 5;"""
        elif 'order' in q_lower:
            return "SELECT * FROM orders LIMIT 10;"
        elif 'region' in q_lower:
            return """SELECT c.region, SUM(o.total_amount) as total_sales
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.region
ORDER BY total_sales DESC;"""
        elif 'average order' in q_lower:
            return "SELECT AVG(total_amount) as avg_order_value FROM orders;"
        else:
            return "SELECT * FROM orders LIMIT 5;"
    
    def _extract_sql(self, text: str) -> str:
        """Extract SQL from model response"""
        # Remove markdown code blocks
        text = re.sub(r'```sql\n?', '', text)
        text = re.sub(r'```\n?', '', text)
        
        # Look for SELECT statement
        match = re.search(r'(SELECT\s+.+?)(?:;|\n\n|$)', text, re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(1)
            if not sql.endswith(';'):
                sql += ';'
            return sql
        
        # If no SELECT found, try to find any line with SELECT
        lines = text.split('\n')
        for line in lines:
            if 'SELECT' in line.upper():
                if not line.endswith(';'):
                    line += ';'
                return line
        
        return text.strip()
    
    def generate_sql(self, question: str) -> str:
        """Generate SQL from natural language question"""
        prompt = f"""Database tables:
{self.schema}

Question: {question}

Write a SQLite query to answer this question.
Only output the SQL query, no explanations.

SQL:"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": self.temperature,
                    "num_predict": 200,
                }
            )
            
            sql = response['message']['content'].strip()
            sql = self._extract_sql(sql)
            
            if not sql or sql == "":
                sql = self._get_fallback_sql(question)
            
            return sql
            
        except Exception as e:
            print(f"Error generating SQL: {e}")
            return self._get_fallback_sql(question)
    
    def execute_sql(self, sql: str) -> pd.DataFrame:
        """Execute SQL query safely"""
        if not sql or sql.strip() == "":
            raise ValueError("Empty SQL query")
        
        # Security check
        sql_upper = sql.upper()
        dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'REPLACE']
        
        for keyword in dangerous:
            if keyword in sql_upper:
                raise ValueError(f"Unsafe query blocked: contains {keyword}")
        
        try:
            return pd.read_sql_query(sql, self.conn)
        except Exception as e:
            raise Exception(f"Query failed: {str(e)}")
    
    def analyze_results(self, question: str, sql: str, results: pd.DataFrame) -> str:
        """Generate analysis of results"""
        if results.empty:
            return "No data found for this query."
        
        # Create a simple summary
        summary_lines = []
        summary_lines.append(f"📊 Found {len(results)} records")
        
        # Add column info
        summary_lines.append(f"📋 Columns: {', '.join(results.columns)}")
        
        # For numeric columns, add basic stats
        numeric_cols = results.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            summary_lines.append("\n📈 Summary Statistics:")
            for col in numeric_cols[:3]:  # Show first 3 numeric columns
                summary_lines.append(f"   {col}: min={results[col].min():.2f}, max={results[col].max():.2f}, avg={results[col].mean():.2f}")
        
        # For small datasets, show the data
        if len(results) <= 10:
            summary_lines.append("\n📋 Data:")
            summary_lines.append(results.to_string())
        else:
            summary_lines.append(f"\n📋 First 10 rows:")
            summary_lines.append(results.head(10).to_string())
            summary_lines.append(f"\n... and {len(results) - 10} more rows")
        
        return "\n".join(summary_lines)
    
    def ask(self, question: str, verbose: bool = False) -> Dict[str, Any]:
        """Main method to ask a question"""
        try:
            # Generate SQL
            sql = self.generate_sql(question)
            
            # Execute SQL
            results = self.execute_sql(sql)
            
            # Analyze results
            analysis = self.analyze_results(question, sql, results)
            
            return {
                "success": True,
                "question": question,
                "sql": sql,
                "results": results,
                "analysis": analysis,
                "row_count": len(results),
                "columns": list(results.columns) if not results.empty else []
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "question": question,
                "sql": "",
                "results": pd.DataFrame(),
                "analysis": f"Error: {str(e)}",
                "row_count": 0
            }
    
    def close(self):
        """Close database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()


# For backward compatibility
DeepSeekSQLAnalyzer = DeepSeekSQLAnalyzer