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
    elif 'uber' in desc or 'ola' in desc or 'petrol' in desc or 'fuel' in desc or 'hpcl' in desc or 'iocl' in desc:
        return 'Travel'
    elif 'amazon' in desc or 'flipkart' in desc or 'shopping' in desc:
        return 'Shopping'
    elif 'jio' in desc or 'airtel' in desc or 'bill' in desc:
        return 'Bills'
    else:
        return 'Others'

@app.route('/')
def home():
    init_db()
    
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    stats = cursor.execute('SELECT SUM(amount) as total_spent, COUNT(id) as total_count FROM transactions').fetchone()
    cats = cursor.execute('SELECT category, SUM(amount) as total FROM transactions GROUP BY category').fetchall()
    top_transactions = cursor.execute('SELECT description, amount, category FROM transactions ORDER BY amount DESC LIMIT 5').fetchall()
    all_raw = cursor.execute('SELECT date, amount FROM transactions').fetchall()
    
    conn.close()
    
    monthly_dict = {}
    for row in all_raw:
        raw_date = str(row['date']).replace('/', '-')
        
        if '-' in raw_date:
            parts = raw_date.split('-')
            month_key = f"{parts[0]}-{parts[1]}" if len(parts[0]) == 4 else f"{parts[2]}-{parts[1]}"
        else:
            month_key = "Unknown"
            
        monthly_dict[month_key] = monthly_dict.get(month_key, 0) + abs(float(row['amount']))
    
    month_labels = sorted(monthly_dict.keys())
    month_values = [monthly_dict[m] for m in month_labels]
    
    chart_labels = [row['category'] for row in cats]
    chart_values = [row['total'] for row in cats]
    
    return render_template(
        'index.html', 
        stats=stats, 
        category_data=cats,
        chart_labels=chart_labels,
        chart_values=chart_values,
        top_transactions=top_transactions,
        month_labels=month_labels,
        month_values=month_values
    )

@app.route('/upload', methods=['POST'])
def upload_file():
    init_db()
    
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