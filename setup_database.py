"""
Create sample sales database for DeepSeek analysis
"""

import sqlite3
import random
from datetime import datetime, timedelta

def create_sample_database():
    """Create a sample SQLite database with sales data"""
    
    conn = sqlite3.connect('sales_data.db')
    cursor = conn.cursor()
    
    # Drop existing tables if they exist
    cursor.execute('DROP TABLE IF EXISTS order_items')
    cursor.execute('DROP TABLE IF EXISTS orders')
    cursor.execute('DROP TABLE IF EXISTS products')
    cursor.execute('DROP TABLE IF EXISTS customers')
    
    # Create tables
    cursor.execute('''
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT,
        region TEXT,
        signup_date DATE
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY,
        product_name TEXT,
        category TEXT,
        price REAL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        order_date DATE,
        total_amount REAL,
        status TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE order_items (
        order_item_id INTEGER PRIMARY KEY,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        price REAL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    )
    ''')
    
    # Insert customers
    regions = ['North', 'South', 'East', 'West']
    customers = []
    for i in range(1, 101):
        name = f"Customer_{i}"
        email = f"customer{i}@example.com"
        region = random.choice(regions)
        signup_date = datetime.now() - timedelta(days=random.randint(0, 730))
        customers.append((i, name, email, region, signup_date.strftime('%Y-%m-%d')))
    
    cursor.executemany('INSERT INTO customers VALUES (?,?,?,?,?)', customers)
    
    # Insert products
    products = [
        (1, 'Laptop Pro', 'Electronics', 1299.99),
        (2, 'Wireless Mouse', 'Electronics', 29.99),
        (3, 'Desk Chair', 'Furniture', 249.99),
        (4, 'Coffee Mug', 'Kitchen', 12.99),
        (5, 'Monitor 27"', 'Electronics', 349.99),
        (6, 'Mechanical Keyboard', 'Electronics', 89.99),
        (7, 'Standing Desk', 'Furniture', 499.99),
        (8, 'Water Bottle', 'Accessories', 19.99),
        (9, 'USB-C Hub', 'Electronics', 45.99),
        (10, 'Desk Lamp', 'Furniture', 39.99),
    ]
    cursor.executemany('INSERT INTO products VALUES (?,?,?,?)', products)
    
    # Insert orders and order items
    orders = []
    order_items = []
    order_id = 1
    item_id = 1
    
    for customer_id in range(1, 101):
        num_orders = random.randint(2, 8)
        for _ in range(num_orders):
            order_date = datetime.now() - timedelta(days=random.randint(0, 365))
            status = random.choice(['completed', 'completed', 'completed', 'shipped', 'pending'])
            
            # Generate order items
            total = 0
            num_items = random.randint(1, 4)
            for __ in range(num_items):
                product = random.choice(products)
                quantity = random.randint(1, 3)
                price = product[3]
                item_total = quantity * price
                total += item_total
                
                order_items.append((item_id, order_id, product[0], quantity, price))
                item_id += 1
            
            orders.append((order_id, customer_id, order_date.strftime('%Y-%m-%d'), total, status))
            order_id += 1
    
    cursor.executemany('INSERT INTO orders VALUES (?,?,?,?,?)', orders)
    cursor.executemany('INSERT INTO order_items VALUES (?,?,?,?,?)', order_items)
    
    conn.commit()
    
    # Show summary
    cursor.execute("SELECT COUNT(*) FROM customers")
    num_customers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products")
    num_products = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders")
    num_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM order_items")
    num_items = cursor.fetchone()[0]
    
    print(f"✅ Database created successfully!")
    print(f"   - {num_customers} customers")
    print(f"   - {num_products} products")
    print(f"   - {num_orders} orders")
    print(f"   - {num_items} order items")
    
    # Show sample
    print("\n📊 Sample data:")
    cursor.execute("SELECT * FROM orders LIMIT 3")
    for row in cursor.fetchall():
        print(f"   Order {row[0]}: Customer {row[1]}, Total ${row[3]}, Status {row[4]}")
    
    conn.close()

if __name__ == "__main__":
    create_sample_database()