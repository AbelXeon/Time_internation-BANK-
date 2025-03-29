from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import os
import bcrypt

app = Flask(__name__)
app.secret_key = 'your_very_secure_secret_key_here'  # Change this for production

# Database connection function
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='abel tiruneh',  # Change to your MySQL username
            password='Ab1996@2468',  # Change to your MySQL password
            database='Time_Internation_BANK'
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Helper function for password hashing
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(hashed_password, user_password):
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password)

@app.route('/')
def home():
    # Clear any existing session
    session.clear()
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        # Validate input
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400

        try:
            conn = get_db_connection()
            if conn is None:
                return jsonify({'error': 'Database connection failed'}), 500
                
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT e.*, d.dep_name 
                FROM employee e
                JOIN department d ON e.dep_id = d.dep_id
                WHERE username = %s
            """, (username,))
            
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                # In production, use: if check_password(user['passwords'].encode('utf-8'), password):
                if user['passwords'] == password:  # Simple comparison for demo
                    # Store user info in session
                    session['user_id'] = user['emp_id']
                    session['username'] = user['username']
                    session['job_title'] = user['job_title']
                    session['name'] = user['emp_name']
                    session['emp_id'] = user['emp_id']
                    session['department'] = user['dep_name']
                    
                    return jsonify({
                        'success': True,
                        'job_title': user['job_title']
                    })
                else:
                    return jsonify({'error': 'Invalid username or password'}), 401
            else:
                return jsonify({'error': 'Invalid username or password'}), 401

        except Error as e:
            return jsonify({'error': 'Database error: ' + str(e)}), 500

# Dashboard routes
@app.route('/hr-dashboard')
def hr_dashboard():
    if 'user_id' not in session or 'HR Manager' not in session.get('job_title', ''):
        return redirect(url_for('home'))
    
    try:
        conn = get_db_connection()
        if conn is None:
            return "Database connection failed", 500
            
        cursor = conn.cursor(dictionary=True)
        
        # Get employee count by department
        cursor.execute("""
            SELECT d.dep_name, COUNT(e.emp_id) as employee_count
            FROM department d
            LEFT JOIN employee e ON d.dep_id = e.dep_id
            GROUP BY d.dep_name
        """)
        dept_counts = cursor.fetchall()
        
        # Get recent hires/fires
        cursor.execute("""
            SELECT ea.*, e.emp_name 
            FROM employee_actions ea
            JOIN employee e ON ea.emp_id = e.emp_id
            ORDER BY action_date DESC
            LIMIT 5
        """)
        recent_actions = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        user_info = {
            'name': session.get('name'),
            'emp_id': session.get('emp_id'),
            'role': session.get('job_title'),
            'department': session.get('department')
        }
        
        return render_template('hr_dashboard.html', 
                             user=user_info,
                             dept_counts=dept_counts,
                             recent_actions=recent_actions)
        
    except Error as e:
        return str(e), 500

@app.route('/accountant-dashboard')
def accountant_dashboard():
    if 'user_id' not in session or 'Accountant' not in session.get('job_title', ''):
        return redirect(url_for('home'))
    
    try:
        conn = get_db_connection()
        if conn is None:
            return "Database connection failed", 500
            
        cursor = conn.cursor(dictionary=True)
        
        # Get account balances summary
        cursor.execute("""
            SELECT 
                COUNT(*) as total_accounts,
                SUM(balance) as total_balance,
                AVG(balance) as avg_balance,
                MIN(balance) as min_balance,
                MAX(balance) as max_balance
            FROM accounts
            WHERE account_status = 'Active'
        """)
        account_summary = cursor.fetchone()
        
        # Get recent transactions
        cursor.execute("""
            SELECT t.*, a.cust_id, c.cust_name
            FROM transactions t
            JOIN accounts a ON t.account_no = a.account_no
            JOIN customer c ON a.cust_id = c.cust_id
            WHERE t.transaction_type IN ('Deposit', 'Withdrawal')
            ORDER BY transaction_date DESC
            LIMIT 5
        """)
        recent_transactions = cursor.fetchall()
        
        # Get pending transactions
        cursor.execute("""
            SELECT t.*, a.cust_id, c.cust_name
            FROM transactions t
            JOIN accounts a ON t.account_no = a.account_no
            JOIN customer c ON a.cust_id = c.cust_id
            WHERE t.transaction_status = 'Pending'
            ORDER BY transaction_date DESC
        """)
        pending_transactions = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        user_info = {
            'name': session.get('name'),
            'emp_id': session.get('emp_id'),
            'role': session.get('job_title'),
            'department': session.get('department')
        }
        
        return render_template('accountant_dashboard.html', 
                             user=user_info,
                             account_summary=account_summary,
                             recent_transactions=recent_transactions,
                             pending_transactions=pending_transactions)
        
    except Error as e:
        return str(e), 500
@app.route('/employee-dashboard')
def employee_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    try:
        conn = get_db_connection()
        if conn is None:
            return "Database connection failed", 500
            
        cursor = conn.cursor(dictionary=True)
        
        # Get employee notifications
        cursor.execute("""
            SELECT * FROM notifications
            WHERE emp_id = %s
            ORDER BY notification_date DESC
            LIMIT 5
        """, (session['user_id'],))
        notifications = cursor.fetchall()
        
        # Get employee info
        cursor.execute("""
            SELECT e.*, d.dep_name, b.branch_name
            FROM employee e
            JOIN department d ON e.dep_id = d.dep_id
            JOIN employee_branch eb ON e.emp_id = eb.emp_id
            JOIN branch b ON eb.branch_id = b.branch_id
            WHERE e.emp_id = %s
        """, (session['user_id'],))
        employee_info = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        user_info = {
            'name': session.get('name'),
            'emp_id': session.get('emp_id'),
            'role': session.get('job_title'),
            'department': session.get('department')
        }
        
        # Changed from employee_dashboard.html to Manager.html
        return render_template('Manager.html', 
                             user=user_info,
                             notifications=notifications,
                             employee_info=employee_info)
        
    except Error as e:
        return str(e), 500


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# API endpoints for dashboard functionality
@app.route('/api/transactions', methods=['POST'])
def create_transaction():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    account_no = data.get('account_no')
    transaction_type = data.get('transaction_type')
    amount = data.get('amount')
    description = data.get('description', '')
    
    if not all([account_no, transaction_type, amount]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400
            
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        # Check account exists and get current balance
        cursor.execute("SELECT * FROM accounts WHERE account_no = %s", (account_no,))
        account = cursor.fetchone()
        
        if not account:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Account not found'}), 404
            
        # Process transaction based on type
        if transaction_type == 'Withdrawal':
            if account['balance'] < amount:
                cursor.close()
                conn.close()
                return jsonify({'error': 'Insufficient funds'}), 400
            new_balance = account['balance'] - amount
        elif transaction_type == 'Deposit':
            new_balance = account['balance'] + amount
        else:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Invalid transaction type'}), 400
        
        # Update account balance
        cursor.execute("""
            UPDATE accounts 
            SET balance = %s 
            WHERE account_no = %s
        """, (new_balance, account_no))
        
        # Record transaction
        cursor.execute("""
            INSERT INTO transactions (
                account_no, transaction_type, 
                transaction_amount, transaction_description
            ) VALUES (%s, %s, %s, %s)
        """, (account_no, transaction_type, amount, description))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'new_balance': new_balance,
            'message': f'{transaction_type} successful'
        })
        
    except Error as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)
