"""
Streamlit Web Interface for DeepSeek SQL Analyzer
Run with: streamlit run web_app.py
"""

import streamlit as st
import pandas as pd
from deepseek_analyzer import DeepSeekSQLAnalyzer
import plotly.express as px
import plotly.graph_objects as go

# Page config
st.set_page_config(
    page_title="DeepSeek SQL Analyzer",
    page_icon="🤖",
    layout="wide"
)

# Title
st.title("🤖 DeepSeek-R1:1.5B SQL Analyzer")
st.markdown("Ask questions about your data in plain English!")

# Initialize session state
if 'analyzer' not in st.session_state:
    try:
        st.session_state.analyzer = DeepSeekSQLAnalyzer()
        st.session_state.history = []
    except Exception as e:
        st.error(f"Failed to initialize: {e}")
        st.stop()

# Sidebar
with st.sidebar:
    st.header("📊 Database Info")
    
    # Show schema
    with st.expander("View Schema"):
        st.code(st.session_state.analyzer.schema, language="sql")
    
    st.header("💡 Example Questions")
    example_questions = [
        "How many customers do we have?",
        "What is total revenue?",
        "Show me top 5 products",
        "Average order value by region",
        "Monthly sales trend"
    ]
    
    for eq in example_questions:
        if st.button(eq, use_container_width=True):
            st.session_state.current_question = eq
            st.rerun()
    
    st.header("⚙️ Settings")
    temperature = st.slider("Temperature", 0.0, 1.0, 0.1, 0.05)
    if temperature != st.session_state.analyzer.temperature:
        st.session_state.analyzer.temperature = temperature

# Main chat interface
st.header("💬 Ask a Question")

# Question input
question = st.text_input(
    "Enter your question:",
    value=st.session_state.get('current_question', ''),
    placeholder="e.g., What were the top 5 products by revenue last month?"
)

col1, col2, col3 = st.columns([1,1,4])
with col1:
    analyze_button = st.button("🔍 Analyze", type="primary", use_container_width=True)
with col2:
    clear_button = st.button("🗑️ Clear History", use_container_width=True)

if clear_button:
    st.session_state.history = []
    st.rerun()

# Process question
if analyze_button and question:
    with st.spinner("Analyzing with DeepSeek..."):
        result = st.session_state.analyzer.ask(question)
        
        # Add to history
        st.session_state.history.append({
            "question": question,
            "result": result
        })

# Display history
if st.session_state.history:
    st.header("📝 Conversation")
    
    for i, item in enumerate(reversed(st.session_state.history)):
        with st.container():
            st.markdown(f"### ❓ Question {len(st.session_state.history) - i}")
            st.markdown(f"**{item['question']}**")
            
            result = item['result']
            
            if result["success"]:
                # Display analysis
                st.markdown("#### 📊 Analysis")
                st.success(result["analysis"])
                
                # Display SQL
                with st.expander("🔍 View SQL Query"):
                    st.code(result["sql"], language="sql")
                
                # Display results
                st.markdown("#### 📈 Results")
                df = result["results"]
                
                if not df.empty:
                    # Show dataframe
                    st.dataframe(df, use_container_width=True)
                    
                    # Auto-visualization
                    if len(df.columns) >= 2:
                        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
                        
                        if numeric_cols and categorical_cols:
                            with st.expander("📊 Visualization"):
                                chart_type = st.selectbox(
                                    "Chart type",
                                    ["Bar", "Line", "Pie"],
                                    key=f"chart_{i}"
                                )
                                
                                x_col = st.selectbox("X-axis", categorical_cols, key=f"x_{i}")
                                y_col = st.selectbox("Y-axis", numeric_cols, key=f"y_{i}")
                                
                                if chart_type == "Bar":
                                    fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
                                elif chart_type == "Line":
                                    fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
                                else:
                                    fig = px.pie(df, values=y_col, names=x_col, title=f"{y_col} distribution")
                                
                                st.plotly_chart(fig, use_container_width=True)
                    
                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="💾 Download as CSV",
                        data=csv,
                        file_name=f"query_results_{i}.csv",
                        mime="text/csv",
                        key=f"download_{i}"
                    )
                else:
                    st.info("No results found for this query.")
            else:
                st.error(f"❌ Error: {result['error']}")
                with st.expander("View generated SQL"):
                    st.code(result.get('sql', 'No SQL generated'), language="sql")
            
            st.divider()

# Footer
st.markdown("---")
st.markdown(
    "Powered by **DeepSeek-R1:1.5B** running locally via Ollama | "
    "Data is processed locally - no data leaves your machine"
)