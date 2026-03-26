"""
Thread-Safe Web Interface for DeepSeek SQL Analyzer
Run with: python web_threadsafe.py
"""

from flask import Flask, render_template_string, request, jsonify
from threadsafe_analyzer import ThreadSafeDeepSeekAnalyzer
import pandas as pd
import traceback

app = Flask(__name__)

# Initialize analyzer (it handles thread-safety internally)
analyzer = ThreadSafeDeepSeekAnalyzer()

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>DeepSeek SQL Analyzer - Thread Safe</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
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
        .header p { opacity: 0.9; font-size: 1.1em; }
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
            transition: border-color 0.3s;
        }
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            font-weight: bold;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        button:active {
            transform: translateY(0);
        }
        .example-btn {
            background: #e1e8ed;
            color: #4a5568;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: normal;
        }
        .example-btn:hover {
            background: #cbd5e0;
            transform: translateY(-1px);
        }
        .examples {
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid #e1e8ed;
        }
        .examples strong {
            display: block;
            margin-bottom: 10px;
            color: #4a5568;
        }
        .result {
            background: #f7f9fc;
            border-radius: 15px;
            padding: 25px;
            margin-top: 20px;
            animation: fadeIn 0.5s;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .result h3 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        .sql-box {
            background: #2d3748;
            color: #68d391;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            overflow-x: auto;
            margin: 15px 0;
            font-size: 14px;
        }
        .analysis-box {
            background: white;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            margin: 15px 0;
            font-family: monospace;
            white-space: pre-wrap;
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
            padding: 12px;
            text-align: left;
        }
        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: bold;
        }
        tr:nth-child(even) {
            background: #f7f9fc;
        }
        tr:hover {
            background: #e1e8ed;
        }
        .error {
            background: #fed7d7;
            color: #c53030;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #c53030;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #667eea;
            font-size: 1.2em;
        }
        .stats {
            background: #e1e8ed;
            padding: 12px;
            border-radius: 8px;
            margin-top: 15px;
            font-size: 14px;
            color: #4a5568;
        }
        .download-btn {
            background: #48bb78;
            margin-top: 15px;
            display: inline-block;
        }
        .download-btn:hover {
            background: #38a169;
        }
        .footer {
            text-align: center;
            padding: 20px;
            color: #718096;
            font-size: 14px;
            border-top: 1px solid #e1e8ed;
            margin-top: 30px;
        }
        @media (max-width: 768px) {
            .content { padding: 20px; }
            th, td { padding: 8px; font-size: 12px; }
            .header h1 { font-size: 1.8em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 DeepSeek SQL Analyzer</h1>
            <p>Ask questions about your data in plain English - Thread Safe Version</p>
        </div>
        <div class="content">
            <div class="question-area">
                <textarea id="question" rows="3" placeholder="e.g., Show me all customers, What is total revenue?, Top 5 products by sales..."></textarea>
                <div class="button-group">
                    <button onclick="askQuestion()">🔍 Analyze</button>
                    <button onclick="clearResult()">🗑️ Clear</button>
                </div>
                
                <div class="examples">
                    <strong>💡 Example Questions:</strong>
                    <button class="example-btn" onclick="setQuestion('Show me all customers')">📋 All customers</button>
                    <button class="example-btn" onclick="setQuestion('How many customers do we have?')">👥 Count customers</button>
                    <button class="example-btn" onclick="setQuestion('What is total revenue?')">💰 Total revenue</button>
                    <button class="example-btn" onclick="setQuestion('Top 5 products by revenue')">🏆 Top products</button>
                    <button class="example-btn" onclick="setQuestion('Average order value')">📊 Avg order value</button>
                    <button class="example-btn" onclick="setQuestion('Sales by region')">🌍 Sales by region</button>
                    <button class="example-btn" onclick="setQuestion('Show me recent orders')">📦 Recent orders</button>
                </div>
            </div>
            
            <div id="loading" class="loading" style="display: none;">
                <div>🤔 Analyzing with DeepSeek...</div>
                <div style="font-size: 12px; margin-top: 10px;">This may take a few seconds</div>
            </div>
            
            <div id="result"></div>
        </div>
        <div class="footer">
            Powered by <strong>DeepSeek-R1:1.5B</strong> running locally via Ollama<br>
            Data stays on your machine - 100% private and secure
        </div>
    </div>
    
    <script>
        function setQuestion(text) {
            document.getElementById('question').value = text;
        }
        
        function clearResult() {
            document.getElementById('result').innerHTML = '';
            document.getElementById('loading').style.display = 'none';
        }
        
        async function askQuestion() {
            const question = document.getElementById('question').value;
            if (!question.trim()) {
                alert('Please enter a question');
                return;
            }
            
            // Show loading
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').innerHTML = '';
            
            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question: question})
                });
                
                const data = await response.json();
                displayResult(data);
            } catch (error) {
                document.getElementById('result').innerHTML = 
                    '<div class="error">❌ Network Error: ' + error.message + '</div>';
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }
        
        function displayResult(data) {
            if (data.success) {
                let html = '<div class="result">';
                
                // Analysis
                html += '<h3>📊 Analysis</h3>';
                html += '<div class="analysis-box">' + data.analysis.replace(/\\n/g, '<br>') + '</div>';
                
                // SQL Query
                html += '<h3>🔍 SQL Query</h3>';
                html += '<div class="sql-box">' + escapeHtml(data.sql) + '</div>';
                
                // Results Table
                if (data.results && data.results.length > 0) {
                    html += '<h3>📈 Results (' + data.row_count + ' rows)</h3>';
                    html += '<div style="overflow-x: auto;">';
                    html += '<table>';
                    
                    // Headers
                    const columns = Object.keys(data.results[0]);
                    html += '<thead><tr>';
                    for (let col of columns) {
                        html += '<th>' + escapeHtml(col) + '</th>';
                    }
                    html += '</tr></thead><tbody>';
                    
                    // Rows (limit to 50 for performance)
                    const maxRows = Math.min(data.results.length, 50);
                    for (let i = 0; i < maxRows; i++) {
                        html += '<tr>';
                        for (let col of columns) {
                            let val = data.results[i][col];
                            if (val === null) val = 'NULL';
                            if (typeof val === 'number') val = val.toFixed(2);
                            html += '<td>' + escapeHtml(String(val)) + '</td>';
                        }
                        html += '</tr>';
                    }
                    
                    html += '</tbody></table>';
                    html += '</div>';
                    
                    if (data.row_count > 50) {
                        html += '<div class="stats">📊 Showing 50 of ' + data.row_count + ' rows. Download CSV to see all.</div>';
                    }
                    
                    // Download button
                    html += '<button class="download-btn" onclick="downloadCSV()">💾 Download as CSV</button>';
                    
                    // Store data for download
                    window.currentResults = data.results;
                    window.currentColumns = columns;
                }
                
                html += '</div>';
                document.getElementById('result').innerHTML = html;
            } else {
                document.getElementById('result').innerHTML = 
                    '<div class="error">❌ Error: ' + escapeHtml(data.error) + '</div>';
            }
        }
        
        function downloadCSV() {
            if (!window.currentResults || !window.currentColumns) return;
            
            // Create CSV content
            let csv = window.currentColumns.join(',') + '\\n';
            for (let row of window.currentResults) {
                let rowData = [];
                for (let col of window.currentColumns) {
                    let val = row[col];
                    if (val === null) val = '';
                    if (typeof val === 'string' && (val.includes(',') || val.includes('"'))) {
                        val = '"' + val.replace(/"/g, '""') + '"';
                    }
                    rowData.push(val);
                }
                csv += rowData.join(',') + '\\n';
            }
            
            // Download
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `query_results_${new Date().getTime()}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
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
    """Thread-safe endpoint for analysis"""
    try:
        data = request.json
        question = data.get('question', '')
        
        if not question:
            return jsonify({'success': False, 'error': 'No question provided'})
        
        # Use the thread-safe analyzer
        result = analyzer.ask(question, verbose=False)
        
        if result["success"]:
            # Convert DataFrame to list of dicts for JSON
            if not result["results"].empty:
                # Limit to 500 rows for performance
                df_preview = result["results"].head(500)
                result["results"] = df_preview.to_dict(orient='records')
            
            return jsonify(result)
        else:
            return jsonify(result)
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    import webbrowser
    import threading
    
    print("=" * 70)
    print("🚀 Starting Thread-Safe DeepSeek SQL Analyzer")
    print("=" * 70)
    print("✅ Thread-safe SQLite connections enabled")
    print("✅ DeepSeek model: deepseek-r1:1.5b")
    print("=" * 70)
    print("🌐 Opening browser at http://localhost:5000")
    print("⚠️  Press Ctrl+C to stop the server")
    print("=" * 70)
    
    # Open browser automatically
    def open_browser():
        webbrowser.open_new('http://localhost:5000')
    
    threading.Timer(1.5, open_browser).start()
    
    # Run with threaded=False to avoid conflicts
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)