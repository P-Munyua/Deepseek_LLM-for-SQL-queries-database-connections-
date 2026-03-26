"""
Fixed DeepSeek SQL Analyzer - Better prompting for SQL generation
"""

import sqlite3
import pandas as pd
import ollama
import re
from typing import Dict, Any, Optional

class FixedDeepSeekAnalyzer:
    """Fixed version with better SQL generation"""
    
    def __init__(self, database_path: str = "sales_data.db", model: str = "deepseek-r1:1.5b"):
        self.database_path = database_path
        self.model = model
        self.conn = sqlite3.connect(database_path)
        
        # Get database schema
        self.schema = self._get_simple_schema()
        
        print(f"✅ Initialized DeepSeek Analyzer with model: {model}")
        print(f"📊 Connected to database: {database_path}")
        
    def _get_simple_schema(self) -> str:
        """Get simplified schema that works better with small models"""
        cursor = self.conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_lines = []
        for (table_name,) in tables:
            # Skip sqlite internal tables
            if table_name.startswith('sqlite_'):
                continue
                
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            col_names = [col[1] for col in columns]
            schema_lines.append(f"{table_name}({', '.join(col_names)})")
        
        return "\n".join(schema_lines)
    
    def _generate_sql(self, question: str) -> str:
        """
        Generate SQL with better prompting for small models
        """
        # Simplified prompt for better results
        prompt = f"""Database tables:
{self.schema}

Question: {question}

Write a SQL query to answer this question. Use SQLite syntax.
Only output the SQL query, no explanation.

SQL:"""
        
        try:
            print("   Calling DeepSeek...")
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": 0.1,
                    "num_predict": 200,
                }
            )
            
            sql = response['message']['content'].strip()
            print(f"   Raw response: {sql[:100]}...")
            
            # Clean up the SQL
            sql = self._extract_sql(sql)
            
            if not sql or sql == "":
                # Fallback for common questions
                sql = self._get_fallback_sql(question)
            
            return sql
            
        except Exception as e:
            print(f"   Error: {e}")
            return self._get_fallback_sql(question)
    
    def _extract_sql(self, text: str) -> str:
        """Extract SQL from text response"""
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
        
        # If no SELECT found, try to clean the whole text
        lines = text.split('\n')
        for line in lines:
            if 'SELECT' in line.upper():
                if not line.endswith(';'):
                    line += ';'
                return line
        
        return text
    
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
        else:
            return "SELECT * FROM orders LIMIT 5;"
    
    def _execute_sql(self, sql: str) -> pd.DataFrame:
        """Execute SQL safely"""
        if not sql or sql.strip() == "":
            raise ValueError("Empty SQL query")
        
        # Security check
        sql_upper = sql.upper()
        dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE']
        
        for keyword in dangerous:
            if keyword in sql_upper:
                raise ValueError(f"Unsafe query blocked: contains {keyword}")
        
        try:
            return pd.read_sql_query(sql, self.conn)
        except Exception as e:
            raise Exception(f"Query failed: {str(e)}\nSQL: {sql}")
    
    def _analyze_results(self, question: str, sql: str, results: pd.DataFrame) -> str:
        """Generate simple analysis without LLM to avoid complexity"""
        if results.empty:
            return "No data found."
        
        # Simple text summary
        summary = f"Found {len(results)} rows.\n\n"
        
        if len(results) <= 10:
            summary += results.to_string()
        else:
            summary += results.head(10).to_string()
            summary += f"\n... and {len(results) - 10} more rows"
        
        return summary
    
    def ask(self, question: str, verbose: bool = True) -> Dict[str, Any]:
        """Ask a question and get results"""
        
        if verbose:
            print(f"\n🤔 Question: {question}")
        
        # Step 1: Generate SQL
        if verbose:
            print("   Generating SQL...")
        
        sql = self._generate_sql(question)
        
        if verbose:
            print(f"   SQL: {sql}")
        
        # Step 2: Execute SQL
        if verbose:
            print("   Executing query...")
        
        try:
            results = self._execute_sql(sql)
            if verbose:
                print(f"   ✓ Found {len(results)} rows")
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sql": sql,
                "question": question
            }
        
        # Step 3: Analyze results
        analysis = self._analyze_results(question, sql, results)
        
        return {
            "success": True,
            "question": question,
            "sql": sql,
            "results": results,
            "analysis": analysis,
            "row_count": len(results)
        }
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Simple CLI interface"""
    print("=" * 70)
    print("🤖 DeepSeek SQL Analyzer (Fixed Version)")
    print("=" * 70)
    print("Ask questions about your data!")
    print("Type 'quit' to exit, 'schema' to see database structure")
    print("-" * 70)
    
    try:
        analyzer = FixedDeepSeekAnalyzer()
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return
    
    while True:
        try:
            print()
            question = input("💬 Your question: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                break
            
            if question.lower() == 'schema':
                print("\n📊 Database Schema:")
                print(analyzer.schema)
                continue
            
            if not question:
                continue
            
            result = analyzer.ask(question)
            
            if result["success"]:
                print("\n" + "=" * 70)
                print("📊 RESULTS")
                print("=" * 70)
                print(result["analysis"])
                
                print("\n" + "-" * 70)
                print("🔍 SQL Used:")
                print(result["sql"])
                print("=" * 70)
            else:
                print(f"\n❌ Error: {result['error']}")
                
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    analyzer.close()
    print("\n👋 Goodbye!")


if __name__ == "__main__":
    main()