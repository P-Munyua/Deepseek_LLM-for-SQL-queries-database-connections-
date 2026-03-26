"""
DeepSeek Chat Assistant - Conversational AI with SQL Analysis
Combines natural conversation with database querying capabilities
"""

import sqlite3
import pandas as pd
import ollama
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

class DeepSeekChatAssistant:
    """Conversational AI assistant with SQL capabilities"""
    
    def __init__(self, database_path: str = "sales_data.db", model: str = "deepseek-r1:1.5b"):
        self.database_path = database_path
        self.model = model
        self.temperature = 0.7  # Higher for conversations
        self.conversation_history = []
        self.context = {}
        
        # System prompt for the assistant
        self.system_prompt = """You are a helpful AI assistant that can answer questions about data and have natural conversations.
You have access to a sales database with tables: customers, products, orders, order_items.

Capabilities:
- Answer general questions naturally
- Analyze sales data when users ask about metrics
- Remember context from previous messages
- Provide insights and recommendations

When users ask about data (sales, customers, products, orders, revenue), you should help them query the database.
For other questions, respond conversationally.

Be friendly, helpful, and concise."""
        
    def _get_connection(self):
        """Get a thread-safe database connection"""
        return sqlite3.connect(self.database_path, check_same_thread=False)
    
    def _get_schema(self) -> str:
        """Get simplified database schema"""
        conn = self._get_connection()
        try:
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
            
            return "\n".join(schema_lines)
        finally:
            conn.close()
    
    def _detect_intent(self, message: str) -> str:
        """Detect if user wants data analysis or conversation"""
        data_keywords = [
            'customer', 'order', 'product', 'revenue', 'sales', 'total', 'count',
            'how many', 'show me', 'list', 'top', 'average', 'sum', 'profit',
            'region', 'price', 'quantity', 'database', 'data', 'report'
        ]
        
        msg_lower = message.lower()
        for keyword in data_keywords:
            if keyword in msg_lower:
                return 'data_query'
        return 'conversation'
    
    def _generate_sql(self, question: str) -> str:
        """Generate SQL from natural language with context awareness"""
        schema = self._get_schema()
        
        # Include conversation context if available
        context_str = ""
        if self.conversation_history:
            recent = self.conversation_history[-3:]  # Last 3 exchanges
            context_str = "\nRecent conversation:\n" + "\n".join([
                f"User: {h['user']}\nAssistant: {h['assistant'][:100]}"
                for h in recent if 'assistant' in h
            ])
        
        prompt = f"""You are a SQL expert. Convert this question to SQLite query.

Database Schema:
{schema}
{context_str}

Question: {question}

Rules:
- Output ONLY the SQL query
- Use exact column names
- If question is not about data, output "NONE"

SQL:"""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "num_predict": 200}
            )
            
            sql = response['message']['content'].strip()
            
            # Extract SQL if present
            if sql.upper().startswith('SELECT') or 'SELECT' in sql.upper():
                match = re.search(r'(SELECT\s+.+?)(?:;|\n\n|$)', sql, re.IGNORECASE | re.DOTALL)
                if match:
                    sql = match.group(1)
                    if not sql.endswith(';'):
                        sql += ';'
                    return sql
            
            return "NONE"
            
        except:
            return "NONE"
    
    def _execute_sql(self, sql: str) -> pd.DataFrame:
        """Execute SQL query safely"""
        if not sql or sql == "NONE":
            return pd.DataFrame()
        
        # Security check
        sql_upper = sql.upper()
        dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'REPLACE']
        for keyword in dangerous:
            if keyword in sql_upper:
                raise ValueError(f"Unsafe query blocked")
        
        conn = self._get_connection()
        try:
            return pd.read_sql_query(sql, conn)
        finally:
            conn.close()
    
    def _format_results(self, results: pd.DataFrame, question: str) -> str:
        """Format query results as natural language"""
        if results.empty:
            return "No results found for your query."
        
        # Create natural language summary
        summary_parts = []
        
        # Add count
        summary_parts.append(f"I found {len(results)} record(s).")
        
        # Add column info
        if len(results) > 0:
            numeric_cols = results.select_dtypes(include=['number']).columns
            
            # Add statistics for numeric columns
            if len(numeric_cols) > 0:
                stats = []
                for col in numeric_cols[:3]:
                    stats.append(f"{col}: {results[col].min():.2f} to {results[col].max():.2f}")
                if stats:
                    summary_parts.append(f"Key metrics: {', '.join(stats)}")
        
        # Add data preview
        if len(results) <= 5:
            summary_parts.append("\nHere's what I found:")
            for idx, row in results.iterrows():
                row_str = " • " + ", ".join([f"{col}: {val}" for col, val in row.items()])
                summary_parts.append(row_str)
        else:
            summary_parts.append(f"\nHere are the first {min(5, len(results))} results:")
            for idx, row in results.head(5).iterrows():
                row_str = " • " + ", ".join([f"{col}: {val}" for col, val in row.items()])
                summary_parts.append(row_str)
            if len(results) > 5:
                summary_parts.append(f"... and {len(results) - 5} more results.")
        
        return "\n".join(summary_parts)
    
    def _generate_conversation_response(self, message: str) -> str:
        """Generate a conversational response"""
        # Build conversation context
        context = ""
        if self.conversation_history:
            recent = self.conversation_history[-5:]  # Last 5 exchanges
            context = "Previous conversation:\n"
            for h in recent:
                context += f"User: {h['user']}\nAssistant: {h['assistant']}\n"
        
        prompt = f"""{self.system_prompt}

{context}
Current user message: {message}

Respond naturally and helpfully. Be concise but friendly."""
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": self.temperature, "num_predict": 300}
            )
            
            return response['message']['content'].strip()
            
        except Exception as e:
            return f"I'm having trouble responding. Could you rephrase that? (Error: {str(e)})"
    
    def chat(self, user_message: str) -> Dict[str, Any]:
        """Main chat method - handles both conversation and data queries"""
        
        # Detect intent
        intent = self._detect_intent(user_message)
        
        response_data = {
            "user_message": user_message,
            "intent": intent,
            "response": "",
            "sql_used": None,
            "results": None,
            "timestamp": datetime.now().isoformat()
        }
        
        if intent == 'data_query':
            # Generate SQL
            sql = self._generate_sql(user_message)
            
            if sql != "NONE":
                try:
                    # Execute query
                    results = self._execute_sql(sql)
                    
                    if not results.empty:
                        # Format results as natural language
                        data_response = self._format_results(results, user_message)
                        
                        # Generate a friendly wrapper
                        prompt = f"""You are a helpful assistant. Present this data analysis to the user in a friendly way.

Data analysis results:
{data_response}

Original question: {user_message}

Provide a concise, friendly response that answers the question naturally."""
                        
                        response = ollama.chat(
                            model=self.model,
                            messages=[{"role": "user", "content": prompt}],
                            options={"temperature": 0.5, "num_predict": 200}
                        )
                        
                        response_data["response"] = response['message']['content'].strip()
                        response_data["sql_used"] = sql
                        response_data["results"] = results.head(20).to_dict(orient='records')
                        response_data["row_count"] = len(results)
                        
                    else:
                        response_data["response"] = "I couldn't find any data matching your question. Could you try rephrasing it?"
                        
                except Exception as e:
                    response_data["response"] = f"I had trouble running that query. {str(e)}"
            else:
                # Question wasn't about data, handle conversationally
                response_data["response"] = self._generate_conversation_response(user_message)
                response_data["intent"] = "conversation"
        else:
            # Pure conversation
            response_data["response"] = self._generate_conversation_response(user_message)
        
        # Store in conversation history
        self.conversation_history.append({
            "user": user_message,
            "assistant": response_data["response"],
            "timestamp": response_data["timestamp"],
            "intent": response_data["intent"]
        })
        
        # Keep history manageable (last 50 messages)
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]
        
        return response_data
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        return "Conversation history cleared!"
    
    def get_history_summary(self) -> str:
        """Get summary of conversation history"""
        if not self.conversation_history:
            return "No conversation history yet."
        
        summary = f"📝 Conversation Summary ({len(self.conversation_history)} exchanges)\n"
        summary += "=" * 50 + "\n"
        
        for i, exchange in enumerate(self.conversation_history[-10:], 1):
            summary += f"{i}. User: {exchange['user'][:50]}\n"
            summary += f"   Assistant: {exchange['assistant'][:50]}...\n"
            summary += f"   ({exchange['intent']})\n\n"
        
        return summary