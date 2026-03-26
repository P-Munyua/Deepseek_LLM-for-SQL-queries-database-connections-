"""
Streamlit Web Interface for DeepSeek SQL Analyzer (Thread-Safe)
Run with: streamlit run web_app_fixed_threadsafe.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from deepseek_analyzer_threadsafe import DeepSeekSQLAnalyzer
import time
import traceback

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
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .result-box {
        background: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #667eea;
    }
    .sql-box {
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 15px;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        overflow-x: auto;
        font-size: 14px;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    .stAlert {
        padding: 10px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'analyzer' not in st.session_state:
    try:
        st.session_state.analyzer = DeepSeekSQLAnalyzer()
        st.session_state.history = []
        st.session_state.current_results = None
        st.session_state.initialized = True
    except Exception as e:
        st.error(f"Failed to initialize analyzer: {e}")
        st.session_state.initialized = False

if 'temperature' not in st.session_state:
    st.session_state.temperature = 0.1

# Title with animation
st.markdown("""
<h1 style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
           -webkit-background-clip: text;
           -webkit-text-fill-color: transparent;
           font-size: 3em;'>
    🤖 DeepSeek-R1:1.5B SQL Analyzer
</h1>
""", unsafe_allow_html=True)

st.markdown("### Ask questions about your data in plain English!")

# Sidebar
with st.sidebar:
    st.header("📊 Database Information")
    
    # Show database stats (with fresh connection)
    if st.session_state.initialized:
        try:
            # Create temporary connection for stats
            import sqlite3
            conn = sqlite3.connect('sales_data.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM customers")
            customers = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM orders")
            orders = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM products")
            products = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM order_items")
            items = cursor.fetchone()[0]
            
            conn.close()
            
            # Display metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("👥 Customers", customers)
                st.metric("📦 Products", products)
            with col2:
                st.metric("📊 Orders", orders)
                st.metric("🛍️ Items", items)
                
        except Exception as e:
            st.warning(f"Could not load database stats: {e}")
    
    st.divider()
    
    # Settings
    st.header("⚙️ Settings")
    st.session_state.temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.1,
        step=0.05,
        help="Lower = more deterministic SQL, Higher = more creative"
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
        "What's the most expensive product?",
        "How many orders are completed?",
        "Show me customers from North region"
    ]
    
    for eq in example_questions:
        if st.button(eq, key=f"example_{eq[:20]}"):
            st.session_state.current_question = eq
            st.rerun()
    
    st.divider()
    
    # Clear history button
    if st.button("🗑️ Clear History", type="secondary"):
        st.session_state.history = []
        st.session_state.current_results = None
        st.success("History cleared!")
        st.rerun()

# Main content area
col1, col2 = st.columns([4, 1])

with col1:
    # Question input
    question = st.text_area(
        "💬 **Ask a question about your data:**",
        value=st.session_state.get('current_question', ''),
        placeholder="e.g., Show me the top 5 products by revenue...",
        height=100,
        key="question_input",
        help="Type your question in plain English"
    )

with col2:
    st.write("")
    st.write("")
    st.write("")
    analyze_button = st.button("🔍 **Analyze**", type="primary", use_container_width=True)

# Process the question
if analyze_button and question:
    with st.spinner("🤔 Analyzing with DeepSeek..."):
        try:
            # Create progress indicators
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.info("⏳ Generating SQL from your question...")
            progress_bar.progress(25)
            time.sleep(0.3)
            
            # Get result
            result = st.session_state.analyzer.ask(question)
            
            status_text.info("🔍 Executing query on database...")
            progress_bar.progress(50)
            time.sleep(0.3)
            
            status_text.info("📊 Analyzing results...")
            progress_bar.progress(75)
            time.sleep(0.3)
            
            # Store in session
            st.session_state.current_results = result
            st.session_state.history.append({
                "question": question,
                "result": result,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            progress_bar.progress(100)
            status_text.success("✅ Analysis complete!")
            time.sleep(0.5)
            
            # Clear progress
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            st.error(f"Error during analysis: {str(e)}")
            st.error(traceback.format_exc())

# Display current results
if st.session_state.current_results:
    result = st.session_state.current_results
    
    if result["success"]:
        # Success display
        st.success("✅ Analysis complete!")
        
        # Analysis section
        st.subheader("📊 Analysis")
        st.markdown(f"<div class='result-box'>{result['analysis']}</div>", unsafe_allow_html=True)
        
        # SQL Query section
        with st.expander("🔍 View SQL Query", expanded=False):
            st.markdown(f"<div class='sql-box'>{result['sql']}</div>", unsafe_allow_html=True)
            st.caption(f"Generated by DeepSeek-R1:1.5B | Temperature: {st.session_state.temperature}")
        
        # Results table
        if not result["results"].empty:
            st.subheader("📈 Results")
            
            # Show dataframe with formatting
            df = result["results"]
            
            # Display row count
            st.caption(f"Showing {len(df)} rows")
            
            # Show the dataframe
            st.dataframe(
                df,
                use_container_width=True,
                height=min(500, 35 * min(len(df), 20) + 38)
            )
            
            # Download buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                csv = df.to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv,
                    file_name=f"query_results_{int(time.time())}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col2:
                # Excel download
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Results')
                excel_data = output.getvalue()
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_data,
                    file_name=f"query_results_{int(time.time())}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            with col3:
                # JSON download
                json_data = df.to_json(orient='records', indent=2)
                st.download_button(
                    label="📄 Download JSON",
                    data=json_data,
                    file_name=f"query_results_{int(time.time())}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            # Visualization section
            if len(df.columns) >= 2:
                st.subheader("📊 Visualization")
                
                # Auto-detect column types
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                
                if numeric_cols and categorical_cols:
                    vis_col1, vis_col2 = st.columns(2)
                    
                    with vis_col1:
                        chart_type = st.selectbox(
                            "Chart Type",
                            ["Bar Chart", "Line Chart", "Pie Chart", "Scatter Plot"],
                            key="chart_type"
                        )
                    
                    with vis_col2:
                        x_axis = st.selectbox("X-Axis", categorical_cols, key="x_axis")
                        y_axis = st.selectbox("Y-Axis", numeric_cols, key="y_axis")
                    
                    # Create chart
                    try:
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
                            showlegend=True,
                            hovermode='closest'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Could not create visualization: {e}")
                else:
                    st.info("Add numeric and categorical columns for visualization")
        else:
            st.info("No results found for this query.")
            
    else:
        # Error display
        st.error(f"❌ Error: {result['error']}")
        if result.get('sql'):
            with st.expander("View generated SQL"):
                st.code(result['sql'], language="sql")
        
        # Troubleshooting tips
        with st.expander("🔧 Troubleshooting Tips"):
            st.markdown("""
            - Try rephrasing your question more simply
            - Check if the column names exist in the database
            - Use the example questions as a template
            - Lower the temperature setting for more consistent results
            """)

# Display history
if st.session_state.history:
    st.divider()
    st.subheader("📝 Conversation History")
    
    # Show last 5 questions
    for i, item in enumerate(reversed(st.session_state.history[-5:])):
        with st.expander(f"**Q:** {item['question']} *({item['timestamp']})*"):
            if item['result']['success']:
                st.write(item['result']['analysis'])
                st.code(item['result']['sql'], language="sql")
                
                # Show small preview
                if not item['result']['results'].empty:
                    st.dataframe(item['result']['results'].head(3), use_container_width=True)
            else:
                st.error(f"Error: {item['result']['error']}")

# Footer
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 20px;'>
        <p>🚀 Powered by <strong>DeepSeek-R1:1.5B</strong> running locally via Ollama</p>
        <p>🔒 Your data stays on your machine - 100% private and secure</p>
        <p>⚡ Thread-safe connections for Streamlit compatibility</p>
    </div>
    """,
    unsafe_allow_html=True
)