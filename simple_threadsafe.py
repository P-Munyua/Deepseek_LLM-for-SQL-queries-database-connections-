"""
Simple thread-safe SQL analyzer with built-in web server
Run with: python simple_threadsafe.py
"""

import sqlite3
import pandas as pd
import ollama
import re
from flask import Flask, render_template_string, request, jsonify
import threading
import os

app = Flask(__name__)

# Global database path
DB_PATH = os.path.abspath('sales_data.db')

def get_schema():
    """Get database schema (creates new connection each time)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
    
    conn.close()
    return "\n".join(schema_lines)

def generate_sql(question, schema):
    """Generate SQL using DeepSeek"""
    prompt = f"""Database tables:
{schema}

Question: {question}

Write SQLite query. Only output SQL, no explanation.

SQL:"""
    
    try:
        response = ollama.chat(
            model="deepseek-r1:1.5b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 200}
        )
        
        sql = response['message']['content'].strip()
        
        # Extract SQL
        match = re.search(r'(SELECT\s+.+?)(?:;|\n\n|$)', sql, re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(1)
            if not sql.endswith(';'):
                sql += ';'
        
        return sql
    except Exception as e:
        print(f"Error generating SQL: {e}")
        # Fallback SQL
        q_lower = question.lower()
        if 'customer' in q_lower and 'count' in q_lower:
            return "SELECT COUNT(*) as total FROM customers;"
        elif 'customer' in q_lower:
            return "SELECT * FROM customers LIMIT 10;"
        elif 'revenue' in q_lower:
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

def execute_sql(sql):
    """Execute SQL with fresh connection (thread-safe)"""
    if not sql or sql.strip() == "":
        raise ValueError("Empty SQL query")
    
    # Security check
    sql_upper = sql.upper()
    dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'REPLACE']
    
    for keyword in dangerous:
        if keyword in sql_upper:
            raise ValueError(f"Unsafe query blocked: contains {keyword}")
    
    # Create new connection for each query (thread-safe)
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()

# HTML Template (same as before)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>DeepSeek SQL Analyzer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .content { padding: 30px; }
        .question-area {
            background: #f7f9fc;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
        }
        textarea {
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e8ed;
            border-radius: 10px;
            font-size: 16px;
            font-family: inherit;
            resize: vertical;
        }
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
            font-weight: bold;
        }
        .example-btn {
            background: #e1e8ed;
            color: #4a5568;
            padding: 8px 16px;
            font-size: 14px;
            margin: 5px;
        }
        .result {
            background: #f7f9fc;
            border-radius: 15px;
            padding: 25px;
            margin-top: 20px;
        }
        .sql-box {
            background: #2d3748;
            color: #68d391;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            overflow-x: auto;
            margin: 15px 0;
        }
        .analysis-box {
            background: white;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            margin: 15px 0;
            white-space: pre-wrap;
            font-family: monospace;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            overflow-x: auto;
            display: block;
        }
        th, td {
            border: 1px solid #e1e8ed;
            padding: 10px;
            text-align: left;
        }
        th {
            background: #667eea;
            color: white;
        }
        .error {
            background: #fed7d7;
            color: #c53030;
            padding: 15px;
            border-radius: 8px;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #667eea;
        }
        .footer {
            text-align: center;
            padding: 20px;
            color: #718096;
            border-top: 1px solid #e1e8ed;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 DeepSeek SQL Analyzer</h1>
            <p>Thread-Safe Version - Ask questions about your data</p>
        </div>
        <div class="content">
            <div class="question-area">
                <textarea id="question" rows="3" placeholder="e.g., Show me all customers, What is total revenue?"></textarea>
                <button onclick="ask()">🔍 Analyze</button>
                <div style="margin-top: 15px;">
                    <strong>Examples:</strong>
                    <button class="example-btn" onclick="setQuestion('Show me all customers')">All customers</button>
                    <button class="example-btn" onclick="setQuestion('How many customers?')">Count customers</button>
                    <button class="example-btn" onclick="setQuestion('Total revenue')">Total revenue</button>
                    <button class="example-btn" onclick="setQuestion('Top 5 products')">Top products</button>
                    <button class="example-btn" onclick="setQuestion('Sales by region')">Sales by region</button>
                </div>
            </div>
            <div id="loading" class="loading" style="display:none;">🤔 Analyzing...</div>
            <div id="result"></div>
        </div>
        <div class="footer">
            Powered by DeepSeek-R1:1.5B | Thread-safe SQLite connections
        </div>
    </div>
    <script>
        function setQuestion(q) { document.getElementById('question').value = q; }
        async function ask() {
            const q = document.getElementById('question').value;
            if (!q.trim()) return;
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').innerHTML = '';
            try {
                const res = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question: q})
                });
                const data = await res.json();
                if (data.success) {
                    let html = '<div class="result">';
                    html += '<h3>📊 Analysis</h3><div class="analysis-box">' + (data.analysis || '').replace(/\\n/g, '<br>') + '</div>';
                    html += '<h3>🔍 SQL</h3><div class="sql-box">' + (data.sql || '') + '</div>';
                    if (data.results && data.results.length > 0) {
                        html += '<h3>📈 Results (' + data.row_count + ' rows)</h3><div style="overflow-x:auto;"><table><thead><tr>';
                        for (let col of Object.keys(data.results[0])) html += '<th>' + col + '</th>';
                        html += '</tr></thead><tbody>';
                        for (let row of data.results.slice(0,30)) {
                            html += '<tr>';
                            for (let val of Object.values(row)) html += '<td>' + (val !== null ? val : 'NULL') + '</td>';
                            html += '</tr>';
                        }
                        html += '</tbody></table></div>';
                    }
                    html += '</div>';
                    document.getElementById('result').innerHTML = html;
                } else {
                    document.getElementById('result').innerHTML = '<div class="error">❌ Error: ' + data.error + '</div>';
                }
            } catch(e) {
                document.getElementById('result').innerHTML = '<div class="error">❌ Error: ' + e.message + '</div>';
            }
            document.getElementById('loading').style.display = 'none';
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/analyze', methods=['POST'])
def analyze():
    """Thread-safe analysis endpoint"""
    try:
        data = request.json
        question = data.get('question', '')
        
        if not question:
            return jsonify({'success': False, 'error': 'No question'})
        
        # Get schema (new connection)
        schema = get_schema()
        
        # Generate SQL
        sql = generate_sql(question, schema)
        
        # Execute SQL (new connection)
        df = execute_sql(sql)
        
        # Generate analysis
        analysis = f"Found {len(df)} records.\n\n"
        if len(df) <= 10:
            analysis += df.to_string()
        else:
            analysis += df.head(10).to_string()
            analysis += f"\n\n... and {len(df) - 10} more rows"
        
        return jsonify({
            'success': True,
            'sql': sql,
            'results': df.head(100).to_dict(orient='records'),
            'analysis': analysis,
            'row_count': len(df)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    import webbrowser
    import threading
    
    print("=" * 70)
    print("🚀 Thread-Safe DeepSeek SQL Analyzer")
    print("=" * 70)
    print("✅ Using fresh database connections per request (thread-safe)")
    print("✅ Model: deepseek-r1:1.5b")
    print("=" * 70)
    print("🌐 Opening http://localhost:5000")
    print("⚠️  Press Ctrl+C to stop")
    print("=" * 70)
    
    def open_browser():
        webbrowser.open('http://localhost:5000')
    
    threading.Timer(1, open_browser).start()
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)