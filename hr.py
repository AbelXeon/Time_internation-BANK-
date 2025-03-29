from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
import random
import bcrypt
import os
from datetime import datetime

app = Flask(__name__, static_folder='templates')
app.secret_key = 'your_secure_secret_key'
CORS(app)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'abel tiruneh',
    'password': 'Ab1996@2468',
    'database': 'Time_Internation_BANK'
}

# Department mapping based on your current table structure
DEPARTMENT_MAPPING = {
    'Accountant': 101,
    'Manager': 102,
    'Finance': 103,
    'Security': 104,
    'Cleaner': 105,
    'HR': 107
}

def get_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

def generate_employee_id():
    return random.randint(1000, 9999)

def generate_password():
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(random.choices(chars, k=8))

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def initialize_database():
    conn = None
    cursor = None
    try:
        conn = get_db()
        if not conn:
            return False

        cursor = conn.cursor(dictionary=True)

        # Ensure all required departments exist with current IDs
        for dep_id, dep_name in [
            (101, 'Accountant'),
            (102, 'Manager'),
            (103, 'Finance'),
            (104, 'Security'),
            (105, 'Cleaner'),
            (107, 'HR')
        ]:
            cursor.execute("""
                INSERT INTO department (dep_id, dep_name)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE dep_name = %s
            """, (dep_id, dep_name, dep_name))

        # Ensure we have at least one branch
        cursor.execute("SELECT COUNT(*) FROM branch")
        if cursor.fetchone()['COUNT(*)'] == 0:
            cursor.execute("""
                INSERT INTO branch (branch_id, branch_name, city, address)
                VALUES 
                (1, 'Main Branch', 'Addis Ababa', 'Bole Road'),
                (2, 'North Branch', 'Addis Ababa', 'Megenagna'),
                (3, 'South Branch', 'Addis Ababa', 'Mexico')
            """)
            print("Added default branches")

        conn.commit()
        return True
    except Exception as e:
        print(f"Database initialization failed: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/')
def serve_dashboard():
    return send_from_directory('templates', 'HR_Dashboard.html')

@app.route('/api/departments', methods=['GET'])
def get_departments():
    conn = None
    cursor = None
    try:
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT dep_id, dep_name FROM department ORDER BY dep_id")
        departments = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'departments': departments
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
@app.route('/api/hire', methods=['POST'])
def hire_employee():
    conn = None
    cursor = None
    try:
        data = request.json
        required_fields = ['name', 'phone', 'email', 'salary', 'role', 'dob', 'gender']
        
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # Get department ID from mapping
        dep_id = DEPARTMENT_MAPPING.get(data['role'])
        if dep_id is None:
            return jsonify({'success': False, 'error': f'Invalid role: {data["role"]}'}), 400

        # Generate employee details
        emp_id = generate_employee_id()
        
        # For all employees, we'll generate credentials but only show them for specific roles
        temp_password = generate_password()
        username = f"{data['name'].split()[0].lower()}.{data['name'].split()[-1].lower() if len(data['name'].split()) > 1 else ''}"
        hashed_password = hash_password(temp_password)

        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        # Ensure unique employee ID
        while True:
            cursor.execute("SELECT emp_id FROM employee WHERE emp_id = %s", (emp_id,))
            if not cursor.fetchone():
                break
            emp_id = generate_employee_id()

        # Insert employee with credentials (all employees get them, but we only expose for certain roles)
        cursor.execute("""
            INSERT INTO employee (
                emp_id, emp_name, gender, dep_id, job_title, salary, dbo, phone, 
                email, username, passwords
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            emp_id, data['name'], data['gender'], dep_id, data['role'],
            float(data['salary']), datetime.strptime(data['dob'], '%Y-%m-%d').date(),
            data['phone'], data['email'], username, hashed_password
        ))

        # Assign to random branch
        cursor.execute("SELECT branch_id FROM branch ORDER BY RAND() LIMIT 1")
        if branch := cursor.fetchone():
            cursor.execute("INSERT INTO employee_branch (emp_id, branch_id) VALUES (%s, %s)", 
                         (emp_id, branch['branch_id']))

        # Log hiring action with employee name
        cursor.execute("""
            INSERT INTO employee_actions (emp_id, action_type, details)
            VALUES (%s, 'Hire', %s)
        """, (emp_id, f"Hired {data['name']} as {data['role']} with salary {data['salary']}"))

        conn.commit()
        
        response_data = {
            'success': True,
            'emp_id': emp_id,
            'message': 'Employee hired successfully'
        }
        
        # Only return credentials for specific roles
        if data['role'] in ['Manager', 'Accountant', 'HR']:
            response_data['username'] = username
            response_data['temp_password'] = temp_password
        
        return jsonify(response_data)

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/current-user', methods=['GET'])
def get_current_user():
    conn = None
    cursor = None
    try:
        # In a real app, you would get this from the session
        # For now, we'll just return the first HR user
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM employee 
            WHERE job_title = 'HR' 
            LIMIT 1
        """)
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'success': False, 'error': 'No HR user found'}), 404
            
        return jsonify({
            'success': True,
            'user': {
                'name': user['emp_name'],
                'emp_id': user['emp_id'],
                'role': user['job_title']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/department-stats', methods=['GET'])
def get_department_stats():
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT d.dep_name, COUNT(e.emp_id) as employee_count
            FROM department d
            LEFT JOIN employee e ON d.dep_id = e.dep_id
            GROUP BY d.dep_name
            ORDER BY d.dep_name
        """)
        stats = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/recent-actions', methods=['GET'])
def get_recent_actions():
    conn = None
    cursor = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT ea.*, e.emp_name 
            FROM employee_actions ea
            LEFT JOIN employee e ON ea.emp_id = e.emp_id
            ORDER BY ea.action_date DESC
            LIMIT 5
        """)
        actions = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'actions': actions
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/fire', methods=['POST'])
def fire_employee():
    conn = None
    cursor = None
    try:
        data = request.json
        required_fields = ['empId', 'name']
        
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Verify employee exists
        cursor.execute("SELECT * FROM employee WHERE emp_id = %s AND emp_name = %s", 
                      (data['empId'], data['name']))
        employee = cursor.fetchone()
        
        if not employee:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404

        # Log firing action
        cursor.execute("""
            INSERT INTO employee_actions (emp_id, action_type, details)
            VALUES (%s, 'Fire', %s)
        """, (data['empId'], f"Terminated employee {data['name']} (ID: {data['empId']})"))

        # Remove employee (or mark as inactive based on your schema)
        cursor.execute("UPDATE employee SET job_title = NULL WHERE emp_id = %s", (data['empId'],))

        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Employee terminated successfully'
        })

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/update-credentials', methods=['POST'])
def update_credentials():
    conn = None
    cursor = None
    try:
        data = request.json
        required_fields = ['currentUsername', 'newUsername', 'currentPassword', 'newPassword']
        
        if not all(field in data for field in required_fields):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Verify current credentials
        cursor.execute("""
            SELECT * FROM employee 
            WHERE username = %s AND passwords = %s
        """, (data['currentUsername'], hash_password(data['currentPassword'])))
        
        employee = cursor.fetchone()
        if not employee:
            return jsonify({'success': False, 'error': 'Invalid current credentials'}), 401

        # Update credentials
        cursor.execute("""
            UPDATE employee 
            SET username = %s, passwords = %s
            WHERE emp_id = %s
        """, (data['newUsername'], hash_password(data['newPassword']), employee['emp_id']))

        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Credentials updated successfully'
        })

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    if not os.path.exists('templates/HR_Dashboard.html'):
        with open('templates/HR_Dashboard.html', 'w') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>HR Dashboard</title>
</head>
<body>
    <h1>HR Dashboard</h1>
    <p>Employee management system</p>
</body>
</html>""")
    
    if initialize_database():
        print("Database initialized successfully")
    else:
        print("Database initialization failed - some features may not work")
    
    app.run(host='0.0.0.0', port=8000, debug=True)
