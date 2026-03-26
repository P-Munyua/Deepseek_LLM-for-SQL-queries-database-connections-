"""
DeepSeek Chat Assistant - Full Conversational AI with SQL Analysis
Run with: streamlit run chat_app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from deepseek_chat_assistant import DeepSeekChatAssistant
from datetime import datetime
import time

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
        flex-direction: column;
    }
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: auto;
        margin-right: 0;
        max-width: 80%;
        align-self: flex-end;
    }
    .assistant-message {
        background: #f0f2f6;
        color: #1e1e1e;
        margin-right: auto;
        margin-left: 0;
        max-width: 80%;
        align-self: flex-start;
    }
    .message-header {
        font-size: 0.8rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .message-content {
        font-size: 1rem;
        line-height: 1.5;
    }
    .sql-box {
        background: #1e1e1e;
        color: #68d391;
        padding: 0.8rem;
        border-radius: 0.5rem;
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        margin-top: 0.5rem;
        overflow-x: auto;
    }
    .dataframe-container {
        margin-top: 0.5rem;
        background: white;
        border-radius: 0.5rem;
        padding: 0.5rem;
        overflow-x: auto;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .sidebar-section {
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    /* Scrollable chat container */
    .chat-container {
        height: 500px;
        overflow-y: auto;
        padding: 1rem;
        background: white;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'chat_assistant' not in st.session_state:
    try:
        st.session_state.chat_assistant = DeepSeekChatAssistant()
        st.session_state.messages = []
        st.session_state.conversation_started = True
    except Exception as e:
        st.error(f"Failed to initialize: {e}")
        st.session_state.conversation_started = False

if 'temperature' not in st.session_state:
    st.session_state.temperature = 0.7

# Sidebar
with st.sidebar:
    st.markdown("""
    <div class="metric-card">
        <h2>🤖 DeepSeek Chat</h2>
        <p>Conversational AI with Data Analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Database stats
    st.header("📊 Database Stats")
    try:
        import sqlite3
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
            st.metric("👥 Customers", customers)
            st.metric("📦 Products", products)
        with col2:
            st.metric("📊 Orders", orders)
    except:
        st.warning("Could not load database stats")
    
    st.divider()
    
    # Settings
    st.header("⚙️ Settings")
    st.session_state.temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.05,
        help="Higher = more creative, Lower = more focused"
    )
    if st.session_state.chat_assistant:
        st.session_state.chat_assistant.temperature = st.session_state.temperature
    
    st.divider()
    
    # Quick actions
    st.header("🚀 Quick Actions")
    
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        if st.session_state.chat_assistant:
            st.session_state.chat_assistant.clear_history()
            st.session_state.messages = []
            st.success("Conversation cleared!")
            time.sleep(1)
            st.rerun()
    
    if st.button("📝 Show History Summary", use_container_width=True):
        if st.session_state.chat_assistant:
            summary = st.session_state.chat_assistant.get_history_summary()
            st.info(summary)
    
    st.divider()
    
    # Example questions
    st.header("💡 Example Questions")
    examples = [
        "Hello! What can you do?",
        "How many customers do we have?",
        "Show me the top 5 products",
        "What's total revenue?",
        "Can you explain the sales trend?",
        "Tell me about our best customers",
        "What's the average order value?"
    ]
    
    for example in examples:
        if st.button(example, key=f"ex_{example[:20]}", use_container_width=True):
            st.session_state.example_question = example
            st.rerun()
    
    st.divider()
    
    # Assistant info
    with st.expander("ℹ️ About"):
        st.markdown("""
        **DeepSeek Chat Assistant** is an AI that can:
        - 💬 Have natural conversations
        - 📊 Analyze your database
        - 📈 Answer business questions
        - 🎯 Remember conversation context
        
        **Powered by:** DeepSeek-R1:1.5B (local)
        **Data:** 100% private, runs on your machine
        """)

# Main chat interface
st.markdown("""
<h1 style='text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
           -webkit-background-clip: text;
           -webkit-text-fill-color: transparent;'>
    🤖 DeepSeek Chat Assistant
</h1>
""", unsafe_allow_html=True)

st.markdown("### Your AI-powered data analyst and conversational companion")

# Chat container
chat_container = st.container()

# Display messages
with chat_container:
    if not st.session_state.messages:
        # Welcome message
        welcome = st.chat_message("assistant")
        welcome.markdown("""
        👋 **Hello! I'm your DeepSeek AI Assistant!**
        
        I can help you with:
        - 💬 **Natural conversation** - Just chat with me!
        - 📊 **Data analysis** - Ask about customers, orders, products
        - 📈 **Business insights** - Get answers from your sales data
        
        **Try asking me:**
        - "How many customers do we have?"
        - "Show me the top products"
        - "What's total revenue?"
        - Or just say "Hello!" to chat!
        
        *What would you like to know?* 🚀
        """)
    
    # Show existing messages
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(msg["content"])
                
                # Show SQL if available
                if msg.get("sql"):
                    with st.expander("🔍 View SQL Query"):
                        st.code(msg["sql"], language="sql")
                
                # Show results if available
                if msg.get("results") and len(msg["results"]) > 0:
                    with st.expander("📊 View Data"):
                        df = pd.DataFrame(msg["results"])
                        st.dataframe(df, use_container_width=True)
                        
                        # Auto-visualization for numeric data
                        if len(df.columns) >= 2:
                            numeric_cols = df.select_dtypes(include=['number']).columns
                            if len(numeric_cols) > 0:
                                fig = px.bar(df, x=df.columns[0], y=numeric_cols[0], 
                                           title="Data Visualization")
                                st.plotly_chart(fig, use_container_width=True)

# Chat input
if st.session_state.conversation_started:
    # Handle example question from sidebar
    if st.session_state.get('example_question'):
        user_input = st.session_state.example_question
        st.session_state.example_question = None
    else:
        user_input = st.chat_input("Ask me anything about your data or just chat...")
    
    if user_input:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Show assistant thinking
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    # Get response from assistant
                    response = st.session_state.chat_assistant.chat(user_input)
                    
                    # Display response
                    st.markdown(response["response"])
                    
                    # Show SQL if applicable
                    if response.get("sql_used"):
                        with st.expander("🔍 View SQL Query"):
                            st.code(response["sql_used"], language="sql")
                    
                    # Show results if applicable
                    if response.get("results") and len(response["results"]) > 0:
                        with st.expander("📊 View Data"):
                            df = pd.DataFrame(response["results"])
                            st.dataframe(df, use_container_width=True)
                            
                            # Auto-visualization
                            if len(df.columns) >= 2:
                                numeric_cols = df.select_dtypes(include=['number']).columns
                                if len(numeric_cols) > 0:
                                    try:
                                        fig = px.bar(df, x=df.columns[0], y=numeric_cols[0],
                                                   title="Quick Visualization")
                                        st.plotly_chart(fig, use_container_width=True)
                                    except:
                                        pass
                    
                    # Save to session
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response["response"],
                        "sql": response.get("sql_used"),
                        "results": response.get("results"),
                        "intent": response.get("intent")
                    })
                    
                except Exception as e:
                    error_msg = f"I encountered an error: {str(e)}. Could you try rephrasing?"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
        
        # Rerun to update display
        st.rerun()

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.8rem;'>
    <p>🤖 Powered by DeepSeek-R1:1.5B (local) | 💬 Conversational AI with SQL Analysis | 🔒 100% Private</p>
</div>
""", unsafe_allow_html=True)