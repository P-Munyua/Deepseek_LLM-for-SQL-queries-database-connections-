"""
Streamlit Web Interface for DeepSeek SQL Analyzer
Run with: streamlit run web_app_fixed.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from deepseek_analyzer_fixed import DeepSeekSQLAnalyzer
import time

# Page configuration
st.set_page_config(
    page_title="DeepSeek SQL Analyzer",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 10px;
        font-weight: bold;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        transition: 0.3s;
    }
    .result-box {
        background: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .sql-box {
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 15px;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        overflow-x: auto;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'analyzer' not in st.session_state:
    try:
        st.session_state.analyzer = DeepSeekSQLAnalyzer()
        st.session_state.history = []
        st.session_state.current_results = None
    except Exception as e:
        st.error(f"Failed to initialize analyzer: {e}")
        st.stop()

if 'temperature' not in st.session_state:
    st.session_state.temperature = 0.1

# Title
st.title("🤖 DeepSeek-R1:1.5B SQL Analyzer")
st.markdown("### Ask questions about your data in plain English!")

# Sidebar
with st.sidebar:
    st.header("📊 Database Information")
    
    # Show database stats
    try:
        conn = st.session_state.analyzer.conn
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM customers")
        customers = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM orders")
        orders = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM products")
        products = cursor.fetchone()[0]
        
        st.metric("Customers", customers)
        st.metric("Orders", orders)
        st.metric("Products", products)
    except:
        st.warning("Could not load database stats")
    
    st.divider()
    
    # Settings
    st.header("⚙️ Settings")
    st.session_state.temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.1,
        step=0.05,
        help="Lower = more deterministic, Higher = more creative"
    )
    if st.session_state.analyzer:
        st.session_state.analyzer.temperature = st.session_state.temperature
    
    st.divider()
    
    # Example questions
    st.header("💡 Example Questions")
    example_questions = [
        "Show me all customers",
        "How many customers do we have?",
        "What is total revenue?",
        "Top 5 products by revenue",
        "Average order value",
        "Sales by region",
        "Show me recent orders",
        "What's the most expensive product?"
    ]
    
    for eq in example_questions:
        if st.button(eq, key=f"example_{eq[:20]}"):
            st.session_state.current_question = eq
            st.rerun()
    
    st.divider()
    
    # Clear history button
    if st.button("🗑️ Clear History", type="secondary"):
        st.session_state.history = []
        st.rerun()

# Main content area
col1, col2 = st.columns([3, 1])

with col1:
    # Question input
    question = st.text_area(
        "💬 Ask a question about your data:",
        value=st.session_state.get('current_question', ''),
        placeholder="e.g., Show me the top 5 products by revenue...",
        height=100,
        key="question_input"
    )

with col2:
    st.write("")
    st.write("")
    analyze_button = st.button("🔍 Analyze", type="primary", use_container_width=True)

# Process the question
if analyze_button and question:
    with st.spinner("🤔 Analyzing with DeepSeek..."):
        try:
            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("⏳ Generating SQL...")
            progress_bar.progress(30)
            time.sleep(0.5)
            
            # Get result
            result = st.session_state.analyzer.ask(question)
            
            status_text.text("🔍 Executing query...")
            progress_bar.progress(60)
            time.sleep(0.5)
            
            status_text.text("📊 Analyzing results...")
            progress_bar.progress(90)
            time.sleep(0.5)
            
            # Store in session
            st.session_state.current_results = result
            st.session_state.history.append({
                "question": question,
                "result": result,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            progress_bar.progress(100)
            status_text.text("✅ Complete!")
            time.sleep(0.5)
            
            # Clear progress
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            st.error(f"Error during analysis: {e}")

# Display current results
if st.session_state.current_results:
    result = st.session_state.current_results
    
    if result["success"]:
        # Success display
        st.success("✅ Analysis complete!")
        
        # Analysis
        st.subheader("📊 Analysis")
        st.markdown(f"<div class='result-box'>{result['analysis']}</div>", unsafe_allow_html=True)
        
        # SQL Query
        with st.expander("🔍 View SQL Query"):
            st.markdown(f"<div class='sql-box'>{result['sql']}</div>", unsafe_allow_html=True)
        
        # Results table
        if not result["results"].empty:
            st.subheader("📈 Results")
            
            # Show dataframe
            df = result["results"]
            st.dataframe(df, use_container_width=True, height=min(400, 35 * len(df) + 38))
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="💾 Download as CSV",
                data=csv,
                file_name=f"query_results_{int(time.time())}.csv",
                mime="text/csv",
            )
            
            # Visualization section
            if len(df.columns) >= 2:
                st.subheader("📊 Visualization")
                
                # Auto-detect column types
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                
                if numeric_cols and categorical_cols:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        chart_type = st.selectbox(
                            "Chart type",
                            ["Bar Chart", "Line Chart", "Pie Chart", "Scatter Plot"],
                            key="chart_type"
                        )
                    
                    with col2:
                        x_axis = st.selectbox("X-axis", categorical_cols, key="x_axis")
                        y_axis = st.selectbox("Y-axis", numeric_cols, key="y_axis")
                    
                    # Create chart
                    if chart_type == "Bar Chart":
                        fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} by {x_axis}")
                    elif chart_type == "Line Chart":
                        fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} over {x_axis}")
                    elif chart_type == "Pie Chart":
                        fig = px.pie(df, values=y_axis, names=x_axis, title=f"{y_axis} distribution")
                    else:  # Scatter Plot
                        fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
                    
                    fig.update_layout(
                        template="plotly_white",
                        height=500,
                        showlegend=True
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Not enough data for visualization (need at least one numeric and one categorical column)")
        else:
            st.info("No results found for this query.")
            
    else:
        # Error display
        st.error(f"❌ Error: {result['error']}")
        if result.get('sql'):
            with st.expander("View generated SQL"):
                st.code(result['sql'], language="sql")

# Display history
if st.session_state.history:
    st.divider()
    st.subheader("📝 Conversation History")
    
    for i, item in enumerate(reversed(st.session_state.history[-5:])):  # Show last 5
        with st.expander(f"Q: {item['question']} ({item['timestamp']})"):
            if item['result']['success']:
                st.write(item['result']['analysis'])
                st.code(item['result']['sql'], language="sql")
                
                # Show small preview
                if not item['result']['results'].empty:
                    st.dataframe(item['result']['results'].head(5), use_container_width=True)
            else:
                st.error(f"Error: {item['result']['error']}")

# Footer
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 20px;'>
    Powered by <strong>DeepSeek-R1:1.5B</strong> running locally via Ollama<br>
    Data stays on your machine - 100% private and secure
    </div>
    """,
    unsafe_allow_html=True
)