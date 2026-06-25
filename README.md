# UPI Spending Analyzer

I built this to track my own UPI spending — my bank app shows 
transactions but never tells me where my money is actually going.

Upload your bank statement CSV and it shows you a breakdown.

## What it does
- Upload your CSV bank statement
- Auto-categorizes transactions into Food, Travel, Shopping, Bills, Others
- Set your own monthly budget limit (customizable — not hardcoded)
- Shows category-wise pie chart and monthly bar chart
- 3-state budget alert — Safe, Warning, Exceeded
- Download PDF report with full transaction table
- Clear data option to start fresh

## Tech used
Python, Flask, SQLite, Pandas, Bootstrap, Chart.js, ReportLab

## Run it locally
pip install flask pandas reportlab
python app.py
Open: http://localhost:5000

## CSV format needed
Your file should have these columns: date, description, amount

## Note
Nothing is sent to any server — all data stays on your machine.

## Live Demo
https://upi-spending-analyzer.onrender.com
