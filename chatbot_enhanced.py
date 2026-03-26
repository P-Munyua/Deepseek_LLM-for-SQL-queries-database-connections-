"""
Enhanced Chatbot with Working SQL Analysis
Run with: streamlit run chatbot_enhanced.py
"""

import streamlit as st
import pandas as pd
import sqlite3
import ollama
import re
import time
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="DeepSeek SQL Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Chat styling */
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    
    /* SQL code styling */
    .sql-code {
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        overflow-x: auto;
        margin: 0.5rem 0;
    }
    
    /* Data table styling */
    .dataframe {
        font-size: 0.85rem;
    }
    
    /* Thinking animation */
    @keyframes pulse {
        0% { opacity: 0.6; }
        50% { opacity: 1; }
        100% { opacity: 0.6; }
    }
    
    .thinking {
        animation: pulse 1.5s ease-in-out infinite;
        display: inline-block;
    }
    
    /* Success/error badges */
    .badge-success {
        background: #10b981;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-size: 0.7rem;
        display: inline-block;
        margin-left: 0.5rem;
    }
    
    .badge-error {
        background: #ef4444;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-size: 0.7rem;
        display: inline-block;
        margin-left: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Database Helper Class (Thread-Safe)
class DatabaseHelper:
    """Thread-safe database operations"""
    
    def __init__(self, db_path="sales_data.db"):
        self.db_path = db_path
        self.schema = self._get_schema()
        
    def _get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def _get_schema(self):
        """Get database schema for SQL generation"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            
            schema_lines = []
            for (table_name,) in tables:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                # Get sample data
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 2")
                samples = cursor.fetchall()
                
                col_info = []
                for col in columns:
                    col_info.append(f"{col[1]} ({col[2]})")
                
                schema_lines.append(f"""
Table: {table_name}
Columns: {', '.join(col_info)}
Sample rows: {samples if samples else 'No data'}
""")
            
            return "\n".join(schema_lines)
        finally:
            conn.close()
    
    def execute_query(self, sql):
        """Execute SQL query safely"""
        if not sql or not sql.strip():
            return None, "Empty query"
        
        # Security check
        sql_upper = sql.upper()
        dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'REPLACE', 'TRUNCATE']
        for keyword in dangerous:
            if keyword in sql_upper:
                return None, f"⚠️ Security: {keyword} operations are not allowed"
        
        conn = self._get_connection()
        try:
            df = pd.read_sql_query(sql, conn)
            return df, None
        except Exception as e:
            return None, str(e)
        finally:
            conn.close()
    
    def get_table_stats(self):
        """Get basic table statistics"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            stats = {}
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                stats[table_name] = count
            
            return stats
        finally:
            conn.close()

# SQL Generator Class
class SQLGenerator:
    """Handles SQL generation from natural language"""
    
    def __init__(self, db_helper, model="deepseek-r1:1.5b"):
        self.db_helper = db_helper
        self.model = model
    
    def _extract_sql(self, text):
        """Extract SQL from LLM response"""
        # Remove markdown code blocks
        text = re.sub(r'```sql\n?', '', text)
        text = re.sub(r'```\n?', '', text)
        
        # Look for SELECT statement
        match = re.search(r'(SELECT\s+.+?)(?:;|\n\n|$)', text, re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(1).strip()
            if not sql.endswith(';'):
                sql += ';'
            return sql
        
        # Look for WITH statement (CTE)
        match = re.search(r'(WITH\s+.+?)(?:;|\n\n|$)', text, re.IGNORECASE | re.DOTALL)
        if match:
            sql = match.group(1).strip()
            if not sql.endswith(';'):
                sql += ';'
            return sql
        
        return None
    
    def _get_fallback_sql(self, question):
        """Generate fallback SQL for common questions"""
        q = question.lower()
        
        # Customer queries
        if 'customer' in q:
            if 'count' in q or 'how many' in q:
                return "SELECT COUNT(*) as total_customers FROM customers;"
            elif 'region' in q and ('north' in q or 'south' in q or 'east' in q or 'west' in q):
                region = next((r for r in ['north', 'south', 'east', 'west'] if r in q), None)
                if region:
                    return f"SELECT * FROM customers WHERE LOWER(region) = '{region}';"
            else:
                return "SELECT * FROM customers LIMIT 10;"
        
        # Order queries
        elif 'order' in q:
            if 'count' in q or 'how many' in q:
                return "SELECT COUNT(*) as total_orders FROM orders;"
            elif 'pending' in q:
                return "SELECT * FROM orders WHERE status = 'pending' LIMIT 10;"
            elif 'completed' in q:
                return "SELECT * FROM orders WHERE status = 'completed' LIMIT 10;"
            else:
                return "SELECT * FROM orders LIMIT 10;"
        
        # Revenue/Sales queries
        elif 'revenue' in q or 'sales' in q or 'total' in q:
            if 'region' in q:
                return """SELECT c.region, SUM(o.total_amount) as total_sales
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.region
ORDER BY total_sales DESC;"""
            else:
                return "SELECT SUM(total_amount) as total_revenue FROM orders;"
        
        # Product queries
        elif 'product' in q:
            if 'top' in q or 'best' in q:
                return """SELECT p.product_name, SUM(oi.quantity * oi.price) as revenue
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
GROUP BY p.product_name
ORDER BY revenue DESC
LIMIT 5;"""
            else:
                return "SELECT * FROM products LIMIT 10;"
        
        # Average queries
        elif 'average' in q or 'avg' in q:
            if 'order' in q:
                return "SELECT AVG(total_amount) as avg_order_value FROM orders;"
        
        # Default
        return "SELECT * FROM orders LIMIT 5;"
    
    def generate_sql(self, question):
        """Generate SQL from natural language question"""
        
        # Build prompt for DeepSeek
        prompt = f"""You are a SQLite expert. Convert this question to a SQL query.

Database Schema:
{self.db_helper.schema}

Important Rules:
1. Output ONLY the SQL query, no explanations or extra text
2. Use SQLite syntax
3. Use exact column names from the schema
4. For dates, use date() or strftime() functions
5. Always use proper JOINs when combining tables
6. Add LIMIT to avoid huge result sets (max 100 rows)
7. End with semicolon

Question: {question}

SQL Query:"""
        
        try:
            # Call DeepSeek
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": 0.1,  # Low temperature for consistent SQL
                    "num_predict": 300,
                    "top_k": 10,
                    "top_p": 0.9
                }
            )
            
            sql = response['message']['content'].strip()
            
            # Extract SQL from response
            extracted_sql = self._extract_sql(sql)
            if extracted_sql:
                sql = extracted_sql
            
            # Validate SQL
            if not sql or not sql.upper().startswith(('SELECT', 'WITH')):
                print(f"Invalid SQL generated, using fallback")
                sql = self._get_fallback_sql(question)
            
            return sql
            
        except Exception as e:
            print(f"SQL generation error: {e}")
            return self._get_fallback_sql(question)

# Response Generator Class
class ResponseGenerator:
    """Generates natural language responses"""
    
    def __init__(self, model="deepseek-r1:1.5b"):
        self.model = model
    
    def generate_response(self, question, sql, df, error=None):
        """Generate natural language response"""
        
        if error:
            return self._generate_error_response(question, error)
        
        if df.empty:
            return f"I ran the query but found no results. Try asking differently or check if the data exists."
        
        # Create analysis prompt
        prompt = f"""You are a helpful data analyst. Answer the user's question based on the data.

User Question: {question}

SQL Used: {sql}

Data Summary:
- {len(df)} records found
- Columns: {', '.join(df.columns)}
- First 5 rows:
{df.head(5).to_string()}

Numeric Summary:
{df.describe().to_string() if len(df.select_dtypes(include=['number']).columns) > 0 else 'No numeric columns'}

Provide a friendly, conversational answer that:
1. Directly answers the question
2. Highlights key numbers and insights
3. Is concise but informative
4. Uses natural language

Answer:"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": 0.5,
                    "num_predict": 250
                }
            )
            return response['message']['content'].strip()
        except:
            # Fallback to simple response
            return f"I found {len(df)} records. Here's what I found:\n\n{df.head(10).to_string()}"
    
    def _generate_error_response(self, question, error):
        """Generate helpful error response"""
        
        prompt = f"""The user asked: "{question}"

There was an error: {error}

Provide a helpful, friendly response that:
1. Acknowledges the error
2. Suggests rephrasing the question
3. Gives an example of how to ask
4. Is encouraging

Keep it concise and friendly."""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7, "num_predict": 150}
            )
            return response['message']['content'].strip()
        except:
            return f"I had trouble understanding that query. Could you rephrase it? For example, try asking: 'Show me all customers' or 'What's the total revenue?'"

# Conversation Manager
class ConversationManager:
    """Manages conversation context"""
    
    def __init__(self):
        self.history = []
        self.context = {}
    
    def add_message(self, role, content, sql=None, df=None):
        """Add message to history"""
        self.history.append({
            "role": role,
            "content": content,
            "sql": sql,
            "timestamp": datetime.now().isoformat(),
            "has_data": df is not None and not df.empty if df is not None else False
        })
    
    def get_context(self):
        """Get conversation context for LLM"""
        if not self.history:
            return "No previous conversation."
        
        # Get last 5 messages
        recent = self.history[-5:]
        context = []
        for msg in recent:
            context.append(f"{msg['role'].upper()}: {msg['content'][:200]}")
        
        return "\n".join(context)
    
    def clear(self):
        """Clear conversation history"""
        self.history = []
        self.context = {}

# Main Chatbot Class
class SQLChatbot:
    """Main chatbot class combining all components"""
    
    def __init__(self):
        self.db_helper = DatabaseHelper()
        self.sql_generator = SQLGenerator(self.db_helper)
        self.response_generator = ResponseGenerator()
        self.conversation = ConversationManager()
        self.model = "deepseek-r1:1.5b"
    
    def process_message(self, user_message):
        """Process user message and return response"""
        
        # Check if it's a general conversation
        if self._is_general_conversation(user_message):
            return self._handle_general_conversation(user_message)
        
        # Generate SQL
        sql = self.sql_generator.generate_sql(user_message)
        
        # Execute SQL
        df, error = self.db_helper.execute_query(sql)
        
        # Generate response
        if error:
            response = self.response_generator.generate_response(user_message, sql, None, error)
            self.conversation.add_message("user", user_message)
            self.conversation.add_message("assistant", response, sql)
            return response, None, None
        else:
            response = self.response_generator.generate_response(user_message, sql, df, None)
            self.conversation.add_message("user", user_message)
            self.conversation.add_message("assistant", response, sql, df)
            return response, sql, df
    
    def _is_general_conversation(self, message):
        """Check if message is general conversation (not data-related)"""
        msg_lower = message.lower()
        
        greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'greetings']
        questions = ['how are you', 'what can you do', 'help', 'who are you', 'what is your name']
        thanks = ['thanks', 'thank you', 'appreciate']
        farewells = ['bye', 'goodbye', 'see you', 'exit']
        
        all_general = greetings + questions + thanks + farewells
        
        return any(word in msg_lower for word in all_general)
    
    def _handle_general_conversation(self, message):
        """Handle general conversation"""
        msg_lower = message.lower()
        
        # Pre-defined responses for common queries
        if any(word in msg_lower for word in ['hello', 'hi', 'hey']):
            response = """👋 Hello! I'm your AI data assistant powered by DeepSeek.

I can help you analyze your sales database. Here's what I can do:

📊 **Data Analysis:**
- Show customers, orders, products
- Calculate totals and averages
- Find top products and customers
- Analyze sales by region

💡 **Try asking:**
- "Show me all customers"
- "What's the total revenue?"
- "Top 5 products by sales"
- "How many orders are pending?"

What would you like to know about your data?"""
        
        elif 'what can you do' in msg_lower or 'help' in msg_lower:
            response = """I'm your data analysis assistant! I can help you explore your database using natural language.

**Here are some things I can do:**

🔍 **Query Data:**
- Show me all customers
- Find orders by region
- List top products

📈 **Analyze Trends:**
- Calculate total revenue
- Average order value
- Sales by category

🎯 **Filter & Sort:**
- Customers from North region
- Orders from last month
- Products over $100

**Just ask me anything about your data in plain English!**"""
        
        elif any(word in msg_lower for word in ['thanks', 'thank']):
            response = "You're welcome! Is there anything else you'd like to know about your data? I'm happy to help! 😊"
        
        elif any(word in msg_lower for word in ['bye', 'goodbye']):
            response = "Goodbye! Feel free to come back if you have more questions about your data! 👋"
        
        else:
            response = f"I'm here to help you analyze your data! Try asking me things like:\n\n- Show me all customers\n- What's the total revenue?\n- Top 5 products\n- How many orders are completed?\n\nWhat would you like to know?"
        
        self.conversation.add_message("user", message)
        self.conversation.add_message("assistant", response)
        
        return response, None, None

# Initialize chatbot
if 'chatbot' not in st.session_state:
    st.session_state.chatbot = SQLChatbot()
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.markdown("### 🤖 Assistant Info")
    
    # Database stats
    with st.expander("📊 Database Stats", expanded=True):
        try:
            stats = st.session_state.chatbot.db_helper.get_table_stats()
            for table, count in stats.items():
                st.metric(f"📋 {table}", f"{count:,}")
        except:
            st.warning("Could not load stats")
    
    # Settings
    with st.expander("⚙️ Settings", expanded=True):
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chatbot.conversation.clear()
            st.rerun()
        
        st.info(f"Model: **DeepSeek-R1:1.5B**\n\nData: **Local SQLite**\n\nEverything runs on your machine")
    
    # Quick examples
    with st.expander("💡 Quick Examples", expanded=True):
        examples = [
            ("👥 All customers", "Show me all customers"),
            ("💰 Total revenue", "What is total revenue?"),
            ("🏆 Top products", "Show me top 5 products by revenue"),
            ("📍 Sales by region", "Show me total sales by region"),
            ("📊 Average order", "What's the average order value?"),
            ("✅ Pending orders", "How many orders are pending?"),
            ("👋 Hello", "Hello")
        ]
        
        for label, example in examples:
            if st.button(label, key=example, use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": example})
                st.rerun()
    
    # Tips
    with st.expander("💡 Tips for Better Results"):
        st.markdown("""
        - **Be specific**: "Show me customers from North" works better than "customers"
        - **Use natural language**: Just ask like you're talking to a person
        - **Ask follow-ups**: I remember context!
        - **Try different phrasings**: If one way doesn't work, try rephrasing
        """)

# Main chat interface
st.markdown("""
<h1 style='text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
           -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
    🤖 DeepSeek SQL Chatbot
</h1>
""", unsafe_allow_html=True)

st.markdown("<p style='text-align: center;'>Ask me anything about your data in plain English!</p>", unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Show SQL if available
        if "sql" in message and message["sql"]:
            with st.expander("🔍 View SQL Query"):
                st.code(message["sql"], language="sql")
        
        # Show data if available
        if "df" in message and message["df"] is not None and not message["df"].empty:
            with st.expander(f"📊 View Data ({len(message['df'])} rows)"):
                st.dataframe(message["df"], use_container_width=True)
                
                # Auto-visualization for small datasets
                if len(message["df"]) <= 20 and len(message["df"].columns) >= 2:
                    numeric_cols = message["df"].select_dtypes(include=['number']).columns
                    cat_cols = message["df"].select_dtypes(include=['object']).columns
                    
                    if numeric_cols and cat_cols:
                        try:
                            fig = px.bar(
                                message["df"].head(10),
                                x=cat_cols[0],
                                y=numeric_cols[0],
                                title="Quick Visualization"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        except:
                            pass

# Chat input
if prompt := st.chat_input("Ask me about your data..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get bot response
    with st.chat_message("assistant"):
        with st.spinner("🤔 Thinking..."):
            # Show thinking animation
            thinking_placeholder = st.empty()
            thinking_placeholder.markdown("""
            <div style="display: flex; align-items: center; gap: 8px;">
                <div class="thinking">🧠</div>
                <div>Analyzing your question and querying the database...</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Process message
            response, sql, df = st.session_state.chatbot.process_message(prompt)
            
            # Clear thinking indicator
            thinking_placeholder.empty()
            
            # Display response
            st.markdown(response)
            
            # Store message with data
            message_data = {
                "role": "assistant",
                "content": response,
                "sql": sql
            }
            
            if df is not None:
                message_data["df"] = df
            
            st.session_state.messages.append(message_data)
            
            # Show SQL and data
            if sql:
                with st.expander("🔍 View SQL Query"):
                    st.code(sql, language="sql")
            
            if df is not None and not df.empty:
                with st.expander(f"📊 View Data ({len(df)} rows)"):
                    st.dataframe(df, use_container_width=True)
                    
                    # Auto-visualization
                    if len(df) <= 20 and len(df.columns) >= 2:
                        numeric_cols = df.select_dtypes(include=['number']).columns
                        cat_cols = df.select_dtypes(include=['object']).columns
                        
                        if numeric_cols and cat_cols:
                            try:
                                fig = px.bar(
                                    df.head(10),
                                    x=cat_cols[0],
                                    y=numeric_cols[0],
                                    title="Quick Visualization"
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            except:
                                pass

# Welcome message
if not st.session_state.messages:
    st.markdown("""
    <div style='text-align: center; padding: 3rem; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                border-radius: 1rem; margin: 2rem 0;'>
        <h2 style='color: #667eea;'>👋 Welcome to Your Data Assistant!</h2>
        <p style='font-size: 1.1rem; margin: 1rem 0;'>
            I can help you explore your sales database using natural language.
        </p>
        <div style='background: white; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0;'>
            <p><strong>Try asking me things like:</strong></p>
            <code style='display: inline-block; margin: 0.25rem;'>Show me all customers</code>
            <code style='display: inline-block; margin: 0.25rem;'>What's the total revenue?</code>
            <code style='display: inline-block; margin: 0.25rem;'>Top 5 products by sales</code>
            <code style='display: inline-block; margin: 0.25rem;'>Sales by region</code>
            <code style='display: inline-block; margin: 0.25rem;'>How many orders are pending?</code>
        </div>
        <p style='color: #666; font-size: 0.9rem;'>
            💡 Just type your question in plain English and I'll handle the rest!
        </p>
    </div>
    """, unsafe_allow_html=True)