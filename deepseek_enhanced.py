"""
Enhanced DeepSeek SQL Analyzer with better prompt engineering
"""

import sqlite3
import pandas as pd
import ollama
import re
from typing import Dict, Any, List
import json
from datetime import datetime

class EnhancedDeepSeekAnalyzer:
    """Enhanced version with prompt engineering and better error handling"""
    
    def __init__(self, database_path: str = "sales_data.db", model: str = "deepseek-r1:1.5b"):
        self.conn = sqlite3.connect(database_path)
        self.model = model
        self.schema = self._get_schema()
        self.example_queries = self._get_example_queries()
        
        print(f"✅ Enhanced DeepSeek Analyzer ready")
        
    def _get_schema(self) -> str:
        """Get detailed schema with examples"""
        cursor = self.conn.cursor()
        schema_parts = []
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for (table_name,) in tables:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # Get sample data
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            samples = cursor.fetchall()
            
            schema_parts.append(f"""
Table: {table_name}
Columns: {', '.join([f"{col[1]} ({col[2]})" for col in columns])}
Sample data: {samples if samples else 'No data'}
""")
        
        return "\n".join(schema_parts)
    
    def _get_example_queries(self) -> str:
        """Provide few-shot examples for better SQL generation"""
        return """
Example 1:
Question: "How many customers do we have?"
SQL: SELECT COUNT(*) as total_customers FROM customers;

Example 2:
Question: "Show me total sales by region"
SQL: SELECT c.region, SUM(o.total_amount) as total_sales 
FROM customers c 
JOIN orders o ON c.customer_id = o.customer_id 
GROUP BY c.region 
ORDER BY total_sales DESC;

Example 3:
Question: "What are the top 5 products by revenue?"
SQL: SELECT p.product_name, SUM(oi.quantity * oi.price) as revenue
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
GROUP BY p.product_name
ORDER BY revenue DESC
LIMIT 5;
"""
    
    def generate_sql(self, question: str) -> str:
        """Generate SQL with few-shot learning"""
        
        prompt = f"""You are a SQLite expert. Convert this question to SQL.

Database Schema:
{self.schema}

Examples of good SQL queries:
{self.example_queries}

Now answer this question:
{question}

Rules:
- Output ONLY the SQL query
- Use SQLite syntax
- Use exact column names from schema
- For dates, use strftime() or date() functions
- Include proper JOINs when needed

SQL:"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a SQL expert. Output only SQL queries."},
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": 0.1,
                    "num_predict": 400,
                    "top_k": 10,
                    "top_p": 0.9
                }
            )
            
            sql = response['message']['content'].strip()
            
            # Clean and validate
            sql = self._clean_sql(sql)
            
            # Basic validation
            if not sql.upper().startswith('SELECT'):
                sql = self._fix_sql_start(sql)
            
            return sql
            
        except Exception as e:
            return f"-- ERROR: {str(e)}"
    
    def _clean_sql(self, sql: str) -> str:
        """Clean and extract SQL"""
        # Remove markdown
        sql = re.sub(r'```sql\n?', '', sql)
        sql = re.sub(r'```\n?', '', sql)
        
        # Remove common prefixes
        sql = re.sub(r'^(SQL:|Query:|Here is|The SQL|This query)', '', sql, flags=re.IGNORECASE)
        
        # Extract SELECT statement
        match = re.search(r'(SELECT\s+.+?)(?:;|\n\n|$)', sql, re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(1)
        
        # Ensure semicolon at end
        if not sql.strip().endswith(';'):
            sql += ';'
        
        return sql.strip()
    
    def _fix_sql_start(self, sql: str) -> str:
        """Fix SQL that doesn't start with SELECT"""
        # Look for SELECT anywhere in the text
        match = re.search(r'(SELECT\s+.+?)(?:;|\n\n|$)', sql, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
        return sql
    
    def execute_with_retry(self, sql: str, max_retries: int = 2) -> pd.DataFrame:
        """Execute SQL with retry logic"""
        
        for attempt in range(max_retries):
            try:
                return pd.read_sql_query(sql, self.conn)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                
                # Try to fix common SQL errors
                if "no such column" in str(e).lower():
                    # Try to fix column names
                    sql = self._fix_column_names(sql)
                elif "near" in str(e).lower():
                    # Try to fix syntax
                    sql = self._fix_syntax(sql)
                
                print(f"   Retry {attempt + 1}: {str(e)}")
        
        raise Exception("Max retries exceeded")
    
    def _fix_column_names(self, sql: str) -> str:
        """Attempt to fix column name issues"""
        # Get actual columns from database
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # Simple mapping (you can expand this)
        corrections = {
            'revenue': 'total_amount',
            'sales': 'total_amount',
            'amount': 'total_amount',
            'product': 'product_name',
            'customer': 'name'
        }
        
        for wrong, correct in corrections.items():
            sql = re.sub(rf'\b{wrong}\b', correct, sql, flags=re.IGNORECASE)
        
        return sql
    
    def _fix_syntax(self, sql: str) -> str:
        """Fix common syntax errors"""
        # Remove extra parentheses
        sql = re.sub(r'\(\s*SELECT', '(SELECT', sql)
        
        # Fix GROUP BY with aliases
        sql = re.sub(r'GROUP BY (\w+) AS', r'GROUP BY \1', sql)
        
        return sql
    
    def analyze(self, question: str) -> Dict[str, Any]:
        """Main analysis method"""
        
        print(f"\n🔍 Analyzing: {question}")
        
        # Step 1: Generate SQL
        print("   Generating SQL...")
        sql = self.generate_sql(question)
        print(f"   SQL: {sql[:100]}..." if len(sql) > 100 else f"   SQL: {sql}")
        
        # Step 2: Execute
        print("   Executing query...")
        try:
            results = self.execute_with_retry(sql)
            print(f"   ✓ Found {len(results)} rows")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sql": sql,
                "question": question
            }
        
        # Step 3: Generate insight
        print("   Generating insights...")
        insight = self._generate_insight(question, sql, results)
        
        return {
            "success": True,
            "question": question,
            "sql": sql,
            "results": results,
            "insight": insight,
            "row_count": len(results)
        }
    
    def _generate_insight(self, question: str, sql: str, results: pd.DataFrame) -> str:
        """Generate business insight"""
        
        if results.empty:
            return "No data found for this query."
        
        # Prepare summary
        summary = {
            "row_count": len(results),
            "columns": list(results.columns),
            "sample": results.head(5).to_dict(orient='records')
        }
        
        # Add statistics for numeric columns
        numeric_cols = results.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            summary["statistics"] = results[numeric_cols].describe().to_dict()
        
        prompt = f"""Provide a concise business insight based on this data:

Question: {question}
Data Summary: {json.dumps(summary, indent=2, default=str)}

Insight (2-3 sentences, focus on key numbers):"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a business analyst. Give concise, number-focused insights."},
                    {"role": "user", "content": prompt}
                ],
                options={"temperature": 0.3, "num_predict": 150}
            )
            
            return response['message']['content'].strip()
            
        except Exception as e:
            return f"Data shows {len(results)} records. Review the numbers for insights. (Analysis error: {str(e)})"


# Interactive test
def test_analyzer():
    """Test the enhanced analyzer"""
    
    analyzer = EnhancedDeepSeekAnalyzer()
    
    test_questions = [
        "How many customers do we have?",
        "What is the total revenue from all orders?",
        "Show me the top 3 products by revenue",
        "What's the average order value?",
        "How many orders are completed vs pending?"
    ]
    
    print("\n" + "="*70)
    print("🧪 Testing Enhanced DeepSeek Analyzer")
    print("="*70)
    
    for question in test_questions:
        result = analyzer.analyze(question)
        
        print(f"\n📊 Result:")
        if result["success"]:
            print(f"   Insight: {result['insight']}")
            print(f"   SQL: {result['sql'][:100]}...")
            print(f"   Rows: {result['row_count']}")
        else:
            print(f"   ❌ Error: {result['error']}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    test_analyzer()