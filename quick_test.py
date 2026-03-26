"""
Quick test script to verify everything is working
"""

import sqlite3
import ollama

def test_database():
    """Test database connection"""
    print("📊 Testing database...")
    conn = sqlite3.connect('sales_data.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM customers")
    customers = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    orders = cursor.fetchone()[0]
    
    print(f"   ✓ Database OK: {customers} customers, {orders} orders")
    conn.close()
    return True

def test_deepseek():
    """Test DeepSeek connection"""
    print("🤖 Testing DeepSeek model...")
    try:
        response = ollama.chat(
            model="deepseek-r1:1.5b",
            messages=[{"role": "user", "content": "Say 'OK' if you can hear me"}],
            options={"num_predict": 10}
        )
        print(f"   ✓ DeepSeek model responding")
        print(f"   Response: {response['message']['content'][:50]}")
        return True
    except Exception as e:
        print(f"   ❌ DeepSeek error: {e}")
        return False

def main():
    print("=" * 60)
    print("🧪 DeepSeek SQL Analyzer - Quick Test")
    print("=" * 60)
    
    db_ok = test_database()
    deepseek_ok = test_deepseek()
    
    if db_ok and deepseek_ok:
        print("\n✅ All systems ready!")
        print("\nYou can now run:")
        print("   python deepseek_analyzer.py    (CLI version)")
        print("   streamlit run web_app.py        (Web interface)")
    else:
        print("\n❌ Some checks failed. Please fix issues before proceeding.")

if __name__ == "__main__":
    main()