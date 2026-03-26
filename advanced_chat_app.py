"""
Advanced DeepSeek Chat Assistant with Additional Features
- Code execution
- File upload
- Data visualization
- Multi-turn conversations
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from deepseek_chat_assistant import DeepSeekChatAssistant
import json
import io
import matplotlib.pyplot as plt

class AdvancedChatAssistant(DeepSeekChatAssistant):
    """Extended chat assistant with advanced features"""
    
    def analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of user message"""
        prompt = f"Analyze the sentiment of this message (positive/negative/neutral): {text}"
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3, "num_predict": 50}
            )
            return response['message']['content'].strip()
        except:
            return "neutral"
    
    def suggest_questions(self, context: str) -> List[str]:
        """Suggest follow-up questions based on context"""
        prompt = f"""Based on this conversation, suggest 3 relevant follow-up questions:

{context}

Suggestions (one per line):"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.7, "num_predict": 100}
            )
            suggestions = response['message']['content'].strip().split('\n')
            return [s.strip() for s in suggestions if s.strip()][:3]
        except:
            return []

# Initialize advanced assistant
if 'advanced_assistant' not in st.session_state:
    st.session_state.advanced_assistant = AdvancedChatAssistant()

# Custom CSS for better styling
st.markdown("""
<style>
    .st-emotion-cache-1v0mbdj {
        border-radius: 1rem;
    }
    .suggestion-button {
        background: #f0f2f6;
        border: 1px solid #e1e8ed;
        border-radius: 0.5rem;
        padding: 0.5rem;
        margin: 0.25rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    .suggestion-button:hover {
        background: #e1e8ed;
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

# Sidebar with advanced options
with st.sidebar:
    st.markdown("### 🎨 Advanced Features")
    
    # Sentiment analysis toggle
    show_sentiment = st.checkbox("Show Sentiment Analysis", value=True)
    
    # Auto-suggest questions
    auto_suggest = st.checkbox("Auto-suggest Questions", value=True)
    
    # Response style
    response_style = st.selectbox(
        "Response Style",
        ["Balanced", "Concise", "Detailed", "Technical"],
        help="How the AI should respond"
    )
    
    # Map style to temperature and prompt
    style_settings = {
        "Balanced": {"temp": 0.7, "style": "balanced and helpful"},
        "Concise": {"temp": 0.3, "style": "concise and brief"},
        "Detailed": {"temp": 0.8, "style": "detailed and thorough"},
        "Technical": {"temp": 0.5, "style": "technical and precise"}
    }
    
    selected_style = style_settings[response_style]
    st.session_state.advanced_assistant.temperature = selected_style["temp"]

# Main interface
st.title("🤖 Advanced AI Chat Assistant")
st.caption("Conversational AI with Data Analysis & Advanced Features")

# Create tabs for different views
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Analytics", "📝 History"])

with tab1:
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        if not st.session_state.messages:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.info("""
                🎉 **Welcome to Advanced AI Chat!**
                
                I can help you with:
                - 💬 Natural conversations
                - 📊 Data analysis and visualization
                - 📈 Business insights
                - 🎯 Smart suggestions
                
                **Try asking:**
                - "Show me top products"
                - "What's the revenue trend?"
                - "Tell me about our customers"
                """)
        
        # Display messages with enhanced formatting
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
                    
                    # Show sentiment if enabled
                    if show_sentiment and msg.get("sentiment"):
                        sentiment_color = {
                            "positive": "green",
                            "negative": "red", 
                            "neutral": "gray"
                        }.get(msg["sentiment"], "gray")
                        st.caption(f"🎭 Sentiment: :{sentiment_color}[{msg['sentiment']}]")
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])
                    
                    # Show SQL and results
                    if msg.get("sql"):
                        with st.expander("🔍 View SQL Query"):
                            st.code(msg["sql"], language="sql")
                    
                    if msg.get("results") and len(msg["results"]) > 0:
                        df = pd.DataFrame(msg["results"])
                        
                        # Create tabs for different views
                        result_tabs = st.tabs(["📋 Table", "📊 Chart", "📈 Stats"])
                        
                        with result_tabs[0]:
                            st.dataframe(df, use_container_width=True)
                        
                        with result_tabs[1]:
                            if len(df.columns) >= 2:
                                numeric_cols = df.select_dtypes(include=['number']).columns
                                if len(numeric_cols) > 0:
                                    chart_type = st.selectbox(
                                        "Chart Type",
                                        ["Bar", "Line", "Scatter", "Pie"],
                                        key=f"chart_{len(st.session_state.messages)}"
                                    )
                                    
                                    if chart_type == "Bar":
                                        fig = px.bar(df, x=df.columns[0], y=numeric_cols[0])
                                    elif chart_type == "Line":
                                        fig = px.line(df, x=df.columns[0], y=numeric_cols[0])
                                    elif chart_type == "Scatter":
                                        fig = px.scatter(df, x=df.columns[0], y=numeric_cols[0])
                                    else:
                                        fig = px.pie(df, values=numeric_cols[0], names=df.columns[0])
                                    
                                    st.plotly_chart(fig, use_container_width=True)
                        
                        with result_tabs[2]:
                            st.write("**Summary Statistics**")
                            st.write(df.describe())
                    
                    # Show suggestions
                    if auto_suggest and msg.get("suggestions"):
                        st.markdown("**💡 Suggested follow-up questions:**")
                        cols = st.columns(len(msg["suggestions"]))
                        for idx, suggestion in enumerate(msg["suggestions"]):
                            with cols[idx]:
                                if st.button(suggestion, key=f"sugg_{idx}_{len(st.session_state.messages)}"):
                                    st.session_state.suggestion_clicked = suggestion
                                    st.rerun()
    
    # Chat input
    user_input = st.chat_input("Ask me anything...")
    
    if user_input or st.session_state.get('suggestion_clicked'):
        if st.session_state.get('suggestion_clicked'):
            user_input = st.session_state.suggestion_clicked
            st.session_state.suggestion_clicked = None
        
        # Add user message
        sentiment = None
        if show_sentiment:
            sentiment = st.session_state.advanced_assistant.analyze_sentiment(user_input)
        
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "sentiment": sentiment
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
            if sentiment:
                sentiment_color = {"positive": "green", "negative": "red", "neutral": "gray"}.get(sentiment, "gray")
                st.caption(f"🎭 Sentiment: :{sentiment_color}[{sentiment}]")
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    response = st.session_state.advanced_assistant.chat(user_input)
                    
                    # Get suggestions
                    suggestions = None
                    if auto_suggest and st.session_state.messages:
                        context = "\n".join([f"{m['role']}: {m['content'][:100]}" for m in st.session_state.messages[-5:]])
                        suggestions = st.session_state.advanced_assistant.suggest_questions(context)
                    
                    # Display response
                    st.markdown(response["response"])
                    
                    # Add to session
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response["response"],
                        "sql": response.get("sql_used"),
                        "results": response.get("results"),
                        "suggestions": suggestions
                    })
                    
                    # Show suggestions immediately
                    if suggestions:
                        st.markdown("**💡 Suggested follow-up questions:**")
                        cols = st.columns(len(suggestions))
                        for idx, suggestion in enumerate(suggestions):
                            with cols[idx]:
                                if st.button(suggestion, key=f"sugg_new_{idx}"):
                                    st.session_state.suggestion_clicked = suggestion
                                    st.rerun()
                    
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
        
        st.rerun()

with tab2:
    # Analytics dashboard
    st.subheader("📊 Conversation Analytics")
    
    if st.session_state.messages:
        # Message counts
        user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
        assistant_msgs = [m for m in st.session_state.messages if m["role"] == "assistant"]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Messages", len(st.session_state.messages))
        with col2:
            st.metric("User Messages", len(user_msgs))
        with col3:
            st.metric("Assistant Messages", len(assistant_msgs))
        
        # Data queries vs conversations
        data_queries = sum(1 for m in assistant_msgs if m.get("sql"))
        conversations = len(assistant_msgs) - data_queries
        
        fig = go.Figure(data=[go.Pie(
            labels=['Data Queries', 'Conversations'],
            values=[data_queries, conversations],
            hole=0.3,
            marker_colors=['#667eea', '#764ba2']
        )])
        fig.update_layout(title="Query Types")
        st.plotly_chart(fig, use_container_width=True)
        
        # Most asked topics
        if user_msgs:
            topics = []
            for msg in user_msgs[-10:]:
                content = msg["content"].lower()
                if "customer" in content:
                    topics.append("Customers")
                elif "product" in content:
                    topics.append("Products")
                elif "order" in content or "revenue" in content:
                    topics.append("Sales")
                else:
                    topics.append("General")
            
            topic_counts = pd.Series(topics).value_counts()
            fig = px.bar(x=topic_counts.index, y=topic_counts.values, title="Recent Topics")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No conversation data yet. Start chatting to see analytics!")

with tab3:
    # Conversation history with export
    st.subheader("📝 Conversation History")
    
    if st.session_state.messages:
        # Export options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Export as JSON"):
                export_data = []
                for msg in st.session_state.messages:
                    export_msg = {
                        "role": msg["role"],
                        "content": msg["content"],
                        "timestamp": msg.get("timestamp", "")
                    }
                    if msg.get("sql"):
                        export_msg["sql"] = msg["sql"]
                    export_data.append(export_msg)
                
                json_str = json.dumps(export_data, indent=2)
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col2:
            if st.button("💾 Export as Text"):
                text_export = ""
                for msg in st.session_state.messages:
                    text_export += f"\n{'='*50}\n"
                    text_export += f"{msg['role'].upper()}: {msg['content']}\n"
                    if msg.get("sql"):
                        text_export += f"\nSQL: {msg['sql']}\n"
                
                st.download_button(
                    label="Download Text",
                    data=text_export,
                    file_name=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
        
        # Display history
        for i, msg in enumerate(st.session_state.messages):
            with st.expander(f"{msg['role'].upper()}: {msg['content'][:100]}..."):
                st.write("**Full message:**")
                st.write(msg["content"])
                if msg.get("sql"):
                    st.write("**SQL:**")
                    st.code(msg["sql"], language="sql")
                if msg.get("results"):
                    st.write("**Results preview:**")
                    df = pd.DataFrame(msg["results"])
                    st.dataframe(df.head(5))
    else:
        st.info("No messages yet")

# Run the app
if __name__ == "__main__":
    pass