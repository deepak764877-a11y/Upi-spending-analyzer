import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import pandas as pd

app = Flask(__name__)

# System Configurations
app.secret_key = "upi_analyzer_secure_production_key_2026"
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
DATABASE = 'database.db'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16MB file size limit

def get_db_connection():
    """Establishes a connection to the SQLite database with dictionary rows."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database table schema securely."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def allowed_file(filename):
    """Validates if the file extension is strictly CSV."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def auto_categorize(description):
    """Performs rule-based dataset categorization on transaction text."""
    desc = str(description).lower()
    if any(keyword in desc for keyword in ['zomato', 'swiggy', 'food', 'restaurant', 'hotel', 'eats']):
        return 'Food'
    elif any(keyword in desc for keyword in ['uber', 'ola', 'irctc', 'petrol', 'fuel', 'metro', 'travel']):
        return 'Travel'
    elif any(keyword in desc for keyword in ['amazon', 'flipkart', 'myntra', 'blinkit', 'instamart', 'shopping']):
        return 'Shopping'
    elif any(keyword in desc for keyword in ['jio', 'airtel', 'recharge', 'electricity', 'bill', 'vi']):
        return 'Bills'
    else:
        return 'Others'

# --- WEB APPLICATION ROUTES ---

@app.route('/')
def home():
    """Fetches records from the database and renders the primary UI."""
    conn = get_db_connection()
    
    # Calculate aggregate summary stats
    stats = conn.execute('''
        SELECT SUM(amount) as total_spent, COUNT(id) as total_count 
        FROM transactions
    ''').fetchone()
    
    # Group by categories to get the summary distributions
    category_data = conn.execute('''
        SELECT category, SUM(amount) as total 
        FROM transactions 
        GROUP BY category
    ''').fetchall()
    
    conn.close()
    return render_template('index.html', stats=stats, category_data=category_data)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Securely uploads files, parses contents via Pandas, and updates SQLite."""
    if 'file' not in request.files:
        flash('No file part detected in the request.', 'danger')
        return redirect(url_for('home'))
        
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file.', 'warning')
        return redirect(url_for('home'))
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Absolute path normalization to eliminate OS file handling bugs
        base_dir = os.path.dirname(os.path.abspath(__file__))
        target_dir = os.path.join(base_dir, app.config['UPLOAD_FOLDER'])
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        file_path = os.path.join(target_dir, filename)
        file.save(file_path)
        
        try:
            # Load and read dataset using Pandas
            df = pd.read_csv(file_path)
            
            # FIX: Automatic column names cleaning (Removes spaces and converts to Title Case like 'Date')
            df.columns = df.columns.str.strip().str.title() 
            
            # Scheme validation checker (Dynamically accepts Date, Description, Amount)
            required_columns = ['Date', 'Description', 'Amount']
            if not all(col in df.columns for col in required_columns):
                flash('Invalid CSV columns! Ensure your file has exact columns: Date, Description, Amount', 'danger')
                if os.path.exists(file_path):
                    os.remove(file_path)
                return redirect(url_for('home'))
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Ingestion loop with data type conversion safety
            for _, row in df.iterrows():
                category = auto_categorize(row['Description'])
                
                # FIX: Cleaning amount string if currency signs or commas exist
                clean_amount = str(row['Amount']).replace('₹', '').replace(',', '').strip()
                
                cursor.execute('''
                    INSERT INTO transactions (transaction_date, description, amount, category)
                    VALUES (?, ?, ?, ?)
                ''', (str(row['Date']), str(row['Description']), float(clean_amount), category))
                
            conn.commit()
            conn.close()
            
            # Post-processing sandbox clean up
            if os.path.exists(file_path):
                os.remove(file_path)
            
            flash('Statement uploaded and parsed successfully!', 'success')
            
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            flash(f'An error occurred while processing the file: {str(e)}', 'danger')
            
    else:
        flash('Invalid file extension! Only structured .csv files are supported.', 'danger')
        
    return redirect(url_for('home'))

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(base_dir, UPLOAD_FOLDER)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    init_db()
    app.run(debug=True)