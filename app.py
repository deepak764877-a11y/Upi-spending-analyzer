import os
import io
import sqlite3
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = 'mysecretkey'

def get_category(description):
    desc = description.lower()
    if any(x in desc for x in ['swiggy', 'zomato', 'restaurant', 'food', 'cafe']):
        return 'Food'
    elif any(x in desc for x in ['electricity', 'jvvnl', 'airtel', 'jio', 'recharge', 'bill']):
        return 'Bills'
    elif any(x in desc for x in ['amazon', 'flipkart', 'myntra', 'shopping']):
        return 'Shopping'
    elif any(x in desc for x in ['uber', 'ola', 'petrol', 'fuel', 'travel', 'irctc']):
        return 'Travel'
    else:
        return 'Others'

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            description TEXT,
            category TEXT,
            amount REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            budget_limit INTEGER DEFAULT 25000
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings (id, budget_limit) VALUES (1, 25000)")
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT budget_limit FROM settings WHERE id = 1")
    row = cursor.fetchone()
    
    if row:
        budget_limit = row[0]
    else:
        budget_limit = 25000
        cursor.execute(
            "INSERT INTO settings (id, budget_limit) VALUES (1, ?)",
            (budget_limit,)
        )
        conn.commit()
        
    cursor.execute("SELECT SUM(amount), COUNT(id) FROM transactions")
    stats = cursor.fetchone()
    total_spent = stats[0] if stats[0] else 0.0
    
    if total_spent > budget_limit:
        budget_status = 'exceeded'
    elif total_spent >= (budget_limit * 0.8):
        budget_status = 'warning'
    else:
        budget_status = 'safe'
        
    cursor.execute("SELECT category, SUM(amount) FROM transactions GROUP BY category")
    pie_data = cursor.fetchall()
    
    cursor.execute("SELECT strftime('%Y-%m', date) as month, SUM(amount) FROM transactions GROUP BY month ORDER BY month ASC")
    bar_data = cursor.fetchall()
    
    conn.close()
    
    return render_template(
        'index.html',
        total_spent=total_spent,
        stats=stats,
        budget_limit=budget_limit,
        budget_status=budget_status,
        pie_data=pie_data,
        bar_data=bar_data
    )

@app.route('/upload', methods=['POST'])
def upload_file():
    budget_limit = int(request.form.get('budget_limit', 25000))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET budget_limit = ? WHERE id = 1", (budget_limit,))
    conn.commit()
    
    if 'file' not in request.files:
        conn.close()
        flash('No file uploaded', 'danger')
        return redirect(url_for('home'))
        
    file = request.files['file']
    if file.filename == '':
        conn.close()
        flash('No file selected', 'danger')
        return redirect(url_for('home'))
        
    if file and file.filename.endswith('.csv'):
        os.makedirs("uploads", exist_ok=True)
        file_path = os.path.join("uploads", file.filename)
        file.save(file_path)
        
        try:
            df = pd.read_csv(file_path)
            df.columns = [c.strip().lower() for c in df.columns]
            
            for _, row in df.iterrows():
                raw_date = row.get('date', '')
                parsed_date = pd.to_datetime(str(raw_date), errors='coerce').strftime('%Y-%m-%d')
                description = str(row.get('description', '')).strip()
                category = get_category(description)
                
                raw_amount = row.get('amount', 0)
                amount = abs(float(str(raw_amount).replace(',', '').strip()))
                
                cursor.execute(
                    "INSERT INTO transactions (date, description, category, amount) VALUES (?, ?, ?, ?)",
                    (parsed_date, description, category, amount)
                )
            
            conn.commit()
            flash('Uploaded!', 'success')
        except Exception as e:
            print(e)
            flash('Error processing file', 'danger')
        finally:
            conn.close()
            if os.path.exists(file_path):
                os.remove(file_path)
    else:
        conn.close()
        flash('Invalid file format', 'danger')
        
    return redirect(url_for('home'))

@app.route('/export-pdf')
def export_pdf():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT date, description, category, amount FROM transactions ORDER BY date DESC")
    rows = cursor.fetchall()
    
    cursor.execute("SELECT SUM(amount) FROM transactions")
    total_spent = cursor.fetchone()[0] or 0.0
    conn.close()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=15, textColor=colors.HexColor('#dc3545'))
    normal_style = styles['Normal']
    
    story.append(Paragraph("UPI Spending Report", title_style))
    story.append(Paragraph(f"Total Spent: ₹{total_spent:,.2f}", normal_style))
    story.append(Spacer(1, 15))
    
    table_data = [["Date", "Description", "Category", "Amount"]]
    for r in rows:
        table_data.append([r[0], r[1][:30], r[2], f"₹{r[3]:,.2f}"])
        
    t = Table(table_data, colWidths=[85, 215, 100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#dc3545')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F7F9FC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
    ]))
    
    story.append(t)
    doc.build(story)
    
    buffer.seek(0)
    pdf_bytes = buffer.read()
    buffer.close()
    
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=Report.pdf'
    return response

@app.route('/clear-data', methods=['POST'])
def clear_data():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()
    flash('Cleared.', 'success')
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )