import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd

app = Flask(__name__)
app.secret_key = "mysecretkey"

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            description TEXT,
            amount REAL,
            category TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_category(description):
    desc = str(description).lower()
    if 'zomato' in desc or 'swiggy' in desc or 'food' in desc:
        return 'Food'
    elif 'uber' in desc or 'ola' in desc or 'petrol' in desc or 'fuel' in desc:
        return 'Travel'
    elif 'amazon' in desc or 'flipkart' in desc or 'shopping' in desc:
        return 'Shopping'
    elif 'jio' in desc or 'airtel' in desc or 'bill' in desc:
        return 'Bills'
    else:
        return 'Others'

@app.route('/')
def home():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    stats = cursor.execute('SELECT SUM(amount) as total_spent, COUNT(id) as total_count FROM transactions').fetchone()
    category_data = cursor.execute('SELECT category, SUM(amount) as total FROM transactions GROUP BY category').fetchall()
    conn.close()
    
    chart_labels = [row['category'] for row in category_data]
    chart_values = [row['total'] for row in category_data]
    
    return render_template(
        'index.html', 
        stats=stats, 
        category_data=category_data,
        chart_labels=chart_labels,
        chart_values=chart_values
    )

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if file:
        if not os.path.exists('uploads'):
            os.makedirs('uploads')
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)
        
        df = pd.read_csv(file_path)
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        for index, row in df.iterrows():
            category = get_category(row['Description'])
            cursor.execute(
                "INSERT INTO transactions (date, description, amount, category) VALUES (?, ?, ?, ?)",
                (str(row['Date']), str(row['Description']), float(row['Amount']), category)
            )
        conn.commit()
        conn.close()
        
        if os.path.exists(file_path):
            os.remove(file_path)
            
    return redirect(url_for('home'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)