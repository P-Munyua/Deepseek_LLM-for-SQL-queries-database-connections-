"""
Conversational AI Assistant with Memory for SQL Analysis
Run with: streamlit run chat_assistant.py
"""

import streamlit as st
import pandas as pd
import sqlite3
import ollama
import re
import time
from datetime import datetime
import plotly.express as px
import hashlib

# Page configuration
st.set_page_config(
    page_title="DeepSeek Chat Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for chat interface
st.markdown("""
<style>
    /* Chat message styling */
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        animation: fadeIn 0.3s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 2rem;
    }
    
    .assistant-message {
        background: #f0f2f6;
        color: #1e1e1e;
        margin-right: 2rem;
        border-left: 4px solid #667eea;
    }
    
    .message-content {
        flex: 1;
    }
    
    .message-timestamp {
        font-size: 0.7rem;
        opacity: 0.7;
        margin-top: 0.5rem;
    }
    
    /* SQL code styling */
    .sql-code {
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 0.5rem;
        border-radius: 0.3rem;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        overflow-x: auto;
        margin: 0.5rem 0;
    }
    
    /* Data table styling */
    .dataframe-container {
        margin: 0.5rem 0;
        overflow-x: auto;
    }
    
    /* Thinking animation */
    .thinking {
        display: inline-block;
        width: 20px;
        text-align: center;
    }
    
    .thinking span {
        animation: blink 1.4s infinite;
        animation-fill-mode: both;
    }
    
    .thinking span:nth-child(2) { animation-delay: 0.2s; }
    .thinking span:nth-child(3) { animation-delay: 0.4s; }
    
    @keyframes blink {
        0% { opacity: 0.2; }
        20% { opacity: 1; }
        100% { opacity: 0.2; }
    }
    
    /* Sidebar styling */
    .sidebar-section {
        padding: 1rem;
        margin-bottom: 1rem;
        background: #f8f9fa;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Database helper class
class DatabaseHelper:
    """Thread-safe database operations"""
    
    def __init__(self, db_path="sales_data.db"):
        self.db_path = db_path
        self.schema = self._get_schema()
        self.table_info = self._get_table_info()
    
    def _get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def _get_schema(self):
        """Get database schema"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            
            schema_lines = []
            for (table_name,) in tables:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                col_names = [f"{col[1]} ({col[2]})" for col in columns]
                schema_lines.append(f"{table_name}: {', '.join(col_names)}")
            
            return "\n".join(schema_lines)
        finally:
            conn.close()
    
    def _get_table_info(self):
        """Get detailed table information"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            info = {}
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                info[table_name] = {
                    "row_count": row_count,
                    "columns": [col[1] for col in columns],
                    "column_types": {col[1]: col[2] for col in columns}
                }
            
            return info
        finally:
            conn.close()
    
    def execute_query(self, sql):
        """Execute SQL query safely"""
        if not sql or not sql.strip():
            return None, "Empty query"
        
        # Security check
        sql_upper = sql.upper()
        dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'REPLACE']
        for keyword in dangerous:
            if keyword in sql_upper:
                return None, f"Blocked: {keyword} operations not allowed"
        
        conn = self._get_connection()
        try:
            df = pd.read_sql_query(sql, conn)
            return df, None
        except Exception as e:
            return None, str(e)
        finally:
            conn.close()

# AI Assistant class
class SQLChatAssistant:
    """Conversational AI for SQL queries"""
    
    def __init__(self, db_helper, model="deepseek-r1:1.5b"):
        self.db_helper = db_helper
        self.model = model
        self.conversation_history = []
        self.temperature = 0.1
    
    def _extract_sql(self, text):
        """Extract SQL from AI response"""
        # Look for SQL code blocks
        sql_pattern = r'```sql\n(.*?)\n```'
        matches = re.findall(sql_pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip()
        
        # Look for SELECT statements
        select_pattern = r'(SELECT\s+.+?)(?:;|\n\n|$)'
        matches = re.findall(select_pattern, text, re.IGNORECASE | re.DOTALL)
        if matches:
            sql = matches[0].strip()
            if not sql.endswith(';'):
                sql += ';'
            return sql
        
        return None
    
    def _check_if_sql_needed(self, message):
        """Determine if message requires SQL query"""
        sql_keywords = ['show', 'list', 'get', 'find', 'how many', 'what is', 'total', 
                       'average', 'count', 'top', 'bottom', 'maximum', 'minimum',
                       'sales', 'revenue', 'customers', 'orders', 'products']
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in sql_keywords)
    
    def _get_fallback_response(self, message):
        """Provide fallback responses for common questions"""
        msg_lower = message.lower()
        
        if 'hello' in msg_lower or 'hi' in msg_lower:
            return "Hello! I'm your data assistant. I can help you query your database. Try asking things like:\n- Show me all customers\n- What's the total revenue?\n- Top 5 products by sales"
        
        elif 'help' in msg_lower:
            return """I can help you analyze your data! Here are some things you can ask:

📊 **Data Queries:**
- Show me all customers
- How many orders do we have?
- What's the total revenue?
- Top products by sales
- Average order value
- Sales by region

💬 **General Questions:**
- What can you do?
- How does this work?
- Show me examples

Just ask naturally, and I'll translate your questions into SQL queries!"""
        
        elif 'example' in msg_lower:
            return """Here are some example questions you can ask:

1. "Show me all customers from the North region"
2. "What's the total revenue for last month?"
3. "Which products have the highest sales?"
4. "How many orders are pending?"
5. "What's the average order value by region?"

Try asking one of these!"""
        
        elif 'thanks' in msg_lower or 'thank' in msg_lower:
            return "You're welcome! Is there anything else you'd like to know about your data?"
        
        return None
    
    def chat(self, user_message):
        """Process user message and return response"""
        
        # Add to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Check for fallback responses first
        fallback = self._get_fallback_response(user_message)
        if fallback:
            self.conversation_history.append({"role": "assistant", "content": fallback})
            return fallback, None, None
        
        # Check if we need SQL
        needs_sql = self._check_if_sql_needed(user_message)
        
        if not needs_sql:
            # General conversation
            prompt = f"""You are a helpful data assistant. The user is asking about their sales database.
            
Previous conversation context:
{self._get_context()}

User: {user_message}

Provide a friendly, helpful response. If you're not sure, suggest asking about the data."""
            
            response = self._call_llm(prompt)
            self.conversation_history.append({"role": "assistant", "content": response})
            return response, None, None
        
        # Need SQL - generate and execute
        sql = self._generate_sql(user_message)
        
        if not sql:
            return "I'm having trouble generating a SQL query for that. Could you rephrase your question?", None, None
        
        # Execute query
        df, error = self.db_helper.execute_query(sql)
        
        if error:
            error_response = f"I tried to query the database but got an error: {error}\n\nWould you like me to try a different approach?"
            self.conversation_history.append({"role": "assistant", "content": error_response})
            return error_response, sql, None
        
        # Generate natural language response
        analysis = self._analyze_results(user_message, sql, df)
        
        # Format response
        if df.empty:
            response = f"I ran the query, but found no results.\n\n```sql\n{sql}\n```"
        else:
            response = f"{analysis}\n\nFound **{len(df)}** records."
        
        self.conversation_history.append({"role": "assistant", "content": response})
        return response, sql, df
    
    def _get_context(self):
        """Get recent conversation context"""
        if len(self.conversation_history) <= 1:
            return "No previous conversation."
        
        recent = self.conversation_history[-6:-1]  # Last 3 exchanges
        context = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            context.append(f"{role}: {msg['content'][:200]}")
        
        return "\n".join(context)
    
    def _generate_sql(self, question):
        """Generate SQL from natural language"""
        prompt = f"""You are a SQL expert. Convert this question to a SQLite query.

Database Schema:
{self.db_helper.schema}

Table Statistics:
{self._get_table_stats()}

Question: {question}

Rules:
- Output ONLY the SQL query, no explanations
- Use SQLite syntax
- Match column names exactly
- For dates, use date() or strftime()
- If aggregating, use proper GROUP BY
- Limit results to reasonable amounts (max 100 rows)

SQL:"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": self.temperature,
                    "num_predict": 300,
                }
            )
            
            sql = response['message']['content'].strip()
            
            # Extract SQL
            sql = self._extract_sql(sql)
            
            # Clean up
            if sql:
                sql = sql.replace('```sql', '').replace('```', '').strip()
                if not sql.endswith(';'):
                    sql += ';'
            
            return sql
            
        except Exception as e:
            return None
    
    def _get_table_stats(self):
        """Get table statistics for better SQL generation"""
        stats = []
        for table_name, info in self.db_helper.table_info.items():
            stats.append(f"- {table_name}: {info['row_count']} rows, columns: {', '.join(info['columns'][:5])}")
        return "\n".join(stats)
    
    def _analyze_results(self, question, sql, df):
        """Analyze results and generate insights"""
        if df.empty:
            return "No results found."
        
        # Simple analysis first
        insights = []
        
        # Add basic stats
        insights.append(f"Found {len(df)} record(s)")
        
        # For numeric columns, add insights
        numeric_cols = df.select_dtypes(include=['number']).columns
        for col in numeric_cols[:2]:  # Top 2 numeric columns
            insights.append(f"• {col}: total = {df[col].sum():.2f}, avg = {df[col].mean():.2f}")
        
        # For categorical columns, add unique counts
        cat_cols = df.select_dtypes(include=['object']).columns
        for col in cat_cols[:2]:
            unique_count = df[col].nunique()
            if unique_count <= 5:
                top_values = df[col].value_counts().head(3)
                insights.append(f"• {col}: {unique_count} unique values (most common: {dict(top_values)})")
        
        # Use LLM for better analysis
        prompt = f"""Based on this data, provide a concise, natural language answer to the question.

Question: {question}
Data summary: {len(df)} rows, columns: {list(df.columns)}
Sample data (first 5 rows):
{df.head(5).to_string()}

Answer the question conversationally, highlighting key numbers and insights."""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3, "num_predict": 200}
            )
            llm_analysis = response['message']['content'].strip()
            return llm_analysis
        except:
            return "\n".join(insights)
    
    def _call_llm(self, prompt):
        """General LLM call for conversation"""
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7, "num_predict": 300}
            )
            return response['message']['content'].strip()
        except:
            return "I'm having trouble processing that. Could you try asking about your data?"

# Initialize session state
if 'assistant' not in st.session_state:
    db_helper = DatabaseHelper()
    st.session_state.assistant = SQLChatAssistant(db_helper)
    st.session_state.messages = []
    st.session_state.current_sql = None
    st.session_state.current_df = None

# Sidebar
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🤖 Assistant Info</h2>", unsafe_allow_html=True)
    
    # Model info
    with st.expander("📊 Database Overview", expanded=True):
        try:
            conn = sqlite3.connect('sales_data.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM customers")
            customers = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM orders")
            orders = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM products")
            products = cursor.fetchone()[0]
            conn.close()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Customers", customers)
                st.metric("Products", products)
            with col2:
                st.metric("Orders", orders)
                st.metric("Tables", 4)
        except:
            st.warning("Could not load stats")
    
    # Settings
    with st.expander("⚙️ Settings", expanded=True):
        temperature = st.slider(
            "Temperature",
            0.0, 1.0, 0.1, 0.05,
            help="Lower = more precise SQL, Higher = more creative"
        )
        st.session_state.assistant.temperature = temperature
        
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.current_sql = None
            st.session_state.current_df = None
            st.rerun()
    
    # Example questions
    with st.expander("💡 Example Questions", expanded=True):
        examples = [
            "Show me all customers",
            "How many orders do we have?",
            "What's the total revenue?",
            "Top 5 products by sales",
            "Average order value by region",
            "Show me customers from North region",
            "What can you help me with?"
        ]
        
        for ex in examples:
            if st.button(f"📝 {ex}", key=ex, use_container_width=True):
                # Add to chat
                st.session_state.messages.append({"role": "user", "content": ex})
                # Process
                with st.spinner("Thinking..."):
                    response, sql, df = st.session_state.assistant.chat(ex)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.session_state.current_sql = sql
                    st.session_state.current_df = df
                st.rerun()
    
    # Tips
    with st.expander("💡 Tips", expanded=False):
        st.markdown("""
        - **Ask naturally** - I understand plain English
        - **Be specific** - "Show me customers from North" works better than "customers"
        - **Ask about data** - I can query customers, orders, products, and sales
        - **Chat normally** - I can also have regular conversations!
        """)

# Main chat interface
st.markdown("""
<h1 style='text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
           -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
    🤖 DeepSeek Chat Assistant
</h1>
""", unsafe_allow_html=True)

st.markdown("<p style='text-align: center;'>Ask me anything about your data - I understand natural language!</p>", unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # If this was an assistant message with SQL results, show them
        if (message["role"] == "assistant" and 
            st.session_state.current_sql and 
            message == st.session_state.messages[-1] and
            st.session_state.current_df is not None and
            not st.session_state.current_df.empty):
            
            with st.expander("🔍 View SQL Query"):
                st.code(st.session_state.current_sql, language="sql")
            
            with st.expander("📊 View Data"):
                st.dataframe(st.session_state.current_df, use_container_width=True)
                
                # Quick visualization if applicable
                if len(st.session_state.current_df.columns) >= 2:
                    numeric_cols = st.session_state.current_df.select_dtypes(include=['number']).columns
                    cat_cols = st.session_state.current_df.select_dtypes(include=['object']).columns
                    
                    if numeric_cols and cat_cols:
                        fig = px.bar(
                            st.session_state.current_df.head(20),
                            x=cat_cols[0],
                            y=numeric_cols[0],
                            title="Quick Visualization"
                        )
                        st.plotly_chart(fig, use_container_width=True)

# Chat input
if prompt := st.chat_input("Ask me anything about your data..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Animated thinking dots
            thinking_placeholder = st.empty()
            thinking_placeholder.markdown("""
            <div class="thinking">
                Thinking<span>.</span><span>.</span><span>.</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Process
            response, sql, df = st.session_state.assistant.chat(prompt)
            
            # Clear thinking indicator
            thinking_placeholder.empty()
            
            # Display response
            st.markdown(response)
            
            # Store in session
            st.session_state.current_sql = sql
            st.session_state.current_df = df
            
            # Show SQL and data if available
            if sql and df is not None and not df.empty:
                with st.expander("🔍 View SQL Query"):
                    st.code(sql, language="sql")
                
                with st.expander("📊 View Data"):
                    st.dataframe(df, use_container_width=True)
                    
                    # Quick visualization
                    if len(df.columns) >= 2:
                        numeric_cols = df.select_dtypes(include=['number']).columns
                        cat_cols = df.select_dtypes(include=['object']).columns
                        
                        if numeric_cols and cat_cols:
                            try:
                                fig = px.bar(
                                    df.head(20),
                                    x=cat_cols[0],
                                    y=numeric_cols[0],
                                    title=f"{numeric_cols[0]} by {cat_cols[0]}"
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            except:
                                pass
    
    # Add assistant message to history
    st.session_state.messages.append({"role": "assistant", "content": response})

# Welcome message if no messages
if not st.session_state.messages:
    st.markdown("""
    <div style='text-align: center; padding: 3rem; background: #f8f9fa; border-radius: 1rem; margin: 2rem;'>
        <h3>👋 Welcome! I'm your data assistant</h3>
        <p>I can help you explore your database using natural language.</p>
        <p><strong>Try asking me:</strong></p>
        <code>Show me all customers from the North region</code><br>
        <code>What's the total revenue from orders?</code><br>
        <code>Which products have the highest sales?</code><br>
        <code>How many orders are pending?</code><br>
        <br>
        <p>Or just say <strong>hello</strong> or <strong>help</strong>!</p>
    </div>
    """, unsafe_allow_html=True)