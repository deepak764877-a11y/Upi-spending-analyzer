import os
import sqlite3
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
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
    if 'food' in desc or 'restaurant' in desc or 'swiggy' in desc or 'zomato' in desc:
        return 'Food'
    elif 'fuel' in desc or 'travel' in desc or 'uber' in desc or 'ola' in desc:
        return 'Travel'
    elif 'bill' in desc or 'recharge' in desc or 'electricity' in desc:
        return 'Bills'
    elif 'amazon' in desc or 'flipkart' in desc or 'shopping' in desc:
        return 'Shopping'
    return 'Others'
@app.route('/')
def home():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT category, SUM(amount) FROM transactions GROUP BY category")
    pie_data = cursor.fetchall()
    
    cursor.execute("SELECT strftime('%Y-%m', date) as month, SUM(amount) FROM transactions GROUP BY month")
    bar_data = cursor.fetchall()
    
    cursor.execute("SELECT SUM(amount) as total_spent, COUNT(id) as total_count FROM transactions")
    stats = cursor.fetchone()
    conn.close()
    
    return render_template('index.html', pie_data=pie_data, bar_data=bar_data, stats=stats)
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('home'))
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('home'))
    
    if file:
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        df = pd.read_csv(filepath)
        df.columns = df.columns.str.strip().str.lower()
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        for _, row in df.iterrows():
            raw_date = row.get('date', '')
            try:
                date_val = pd.to_datetime(raw_date, dayfirst=True).strftime('%Y-%m-%d')
            except:
                date_val = raw_date
                
            desc_val = row.get('description', '')
            amount_val = abs(float(row.get('amount', 0)))  # HDFC statements show debit as negative, abs() fixes it.
            category_val = get_category(desc_val)
            
            cursor.execute(
                "INSERT INTO transactions (date, description, amount, category) VALUES (?, ?, ?, ?)",
                (date_val, desc_val, amount_val, category_val)
            )
            
        conn.commit()
        conn.close()
        
        return redirect(url_for('home'))
@app.route('/clear-data', methods=['POST'])
def clear_data():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()
    return redirect(url_for('home'))
if __name__ == '__main__':
    init_db()
    app.run(debug=True) 