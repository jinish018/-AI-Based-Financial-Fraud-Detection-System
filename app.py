from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
import pandas as pd
import numpy as np
import pickle
import json
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'fraud_detection_secret_key'

# Load the ML model
MODEL_PATH = 'model/fraud_detection_model.pkl'

def load_model():
    try:
        with open(MODEL_PATH, 'rb') as file:
            model = pickle.load(file)
        return model
    except Exception as e:
        print(f"Error loading model: {e}")
        return None

# Initialize database
def init_db():
    conn = sqlite3.connect('instance/transactions.db')
    cursor = conn.cursor()
    
    # Create transactions table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id TEXT PRIMARY KEY,
        timestamp TEXT,
        amount REAL,
        merchant TEXT,
        category TEXT,
        description TEXT,
        location TEXT,
        user_id TEXT,
        card_type TEXT,
        is_fraud INTEGER,
        fraud_score REAL,
        fraud_reason TEXT
    )
    ''')
    
    # Create users table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        created_at TEXT
    )
    ''')
    
    # Add admin user if not exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (id, username, password, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), 'admin', 'admin123', 'admin', datetime.now().isoformat())
        )
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Helper function to get database connection
def get_db_connection():
    conn = sqlite3.connect('instance/transactions.db')
    conn.row_factory = sqlite3.Row
    return conn

# Preprocess transaction data for model input
def preprocess_transaction(transaction_data):
    # Extract features needed by the model
    # This should be customized based on your model's expected input
    features = {
        'amount': float(transaction_data['amount']),
        'hour_of_day': datetime.now().hour,
        'day_of_week': datetime.now().weekday(),
        'merchant_category': hash(transaction_data['category']) % 100,  # Simple encoding
        'location_hash': hash(transaction_data['location']) % 100,      # Simple encoding
        'card_type_hash': hash(transaction_data['card_type']) % 10      # Simple encoding
    }
    
    # Convert to DataFrame for model prediction
    df = pd.DataFrame([features])
    return df

# Analyze transaction with ML model
def analyze_transaction(transaction_data):
    model = load_model()
    if not model:
        return {'is_fraud': 0, 'fraud_score': 0.0, 'fraud_reason': 'Model not available'}
    
    # Preprocess data
    processed_data = preprocess_transaction(transaction_data)
    
    # Make prediction
    try:
        fraud_score = model.predict_proba(processed_data)[0][1]  # Probability of fraud
        is_fraud = 1 if fraud_score > 0.7 else 0  # Threshold can be adjusted
        
        # Generate reason based on features
        fraud_reason = ''
        if is_fraud:
            if transaction_data['amount'] > 1000:
                fraud_reason += 'Unusually high transaction amount. '
            if datetime.now().hour < 6 or datetime.now().hour > 22:
                fraud_reason += 'Unusual transaction time. '
            if 'foreign' in transaction_data['location'].lower():
                fraud_reason += 'Unusual location. '
            
            if not fraud_reason:
                fraud_reason = 'Multiple suspicious patterns detected.'
        
        return {
            'is_fraud': is_fraud,
            'fraud_score': float(fraud_score),
            'fraud_reason': fraud_reason
        }
    except Exception as e:
        print(f"Prediction error: {e}")
        # Fallback to rule-based detection
        is_fraud = 1 if transaction_data['amount'] > 2000 else 0
        return {
            'is_fraud': is_fraud,
            'fraud_score': 0.5 if is_fraud else 0.1,
            'fraud_reason': 'Fallback detection: High amount' if is_fraud else ''
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                        (username, password)).fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        return redirect(url_for('dashboard'))
    else:
        return render_template('index.html', error='Invalid credentials')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    is_admin = session.get('role') == 'admin'
    return render_template('dashboard.html', username=session.get('username'), is_admin=is_admin)

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    try:
        transaction_data = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'amount': float(request.form.get('amount')),
            'merchant': request.form.get('merchant'),
            'category': request.form.get('category'),
            'description': request.form.get('description'),
            'location': request.form.get('location'),
            'user_id': session.get('user_id'),
            'card_type': request.form.get('card_type')
        }
        
        # Analyze transaction
        analysis = analyze_transaction(transaction_data)
        transaction_data.update(analysis)
        
        # Save to database
        conn = get_db_connection()
        conn.execute('''
        INSERT INTO transactions 
        (id, timestamp, amount, merchant, category, description, location, user_id, card_type, is_fraud, fraud_score, fraud_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction_data['id'],
            transaction_data['timestamp'],
            transaction_data['amount'],
            transaction_data['merchant'],
            transaction_data['category'],
            transaction_data['description'],
            transaction_data['location'],
            transaction_data['user_id'],
            transaction_data['card_type'],
            transaction_data['is_fraud'],
            transaction_data['fraud_score'],
            transaction_data['fraud_reason']
        ))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'transaction': transaction_data,
            'message': 'Transaction added successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_transactions')
def get_transactions():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'})
    
    try:
        conn = get_db_connection()
        
        # Admin sees all transactions, regular users see only their own
        if session.get('role') == 'admin':
            transactions = conn.execute('SELECT * FROM transactions ORDER BY timestamp DESC').fetchall()
        else:
            transactions = conn.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY timestamp DESC', 
                                       (session.get('user_id'),)).fetchall()
        
        conn.close()
        
        # Convert to list of dicts
        result = []
        for t in transactions:
            transaction_dict = dict(t)
            result.append(transaction_dict)
        
        return jsonify({'success': True, 'transactions': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/analytics')
def analytics():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    try:
        conn = get_db_connection()
        
        # Get fraud statistics
        stats = {}
        stats['total_transactions'] = conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]
        stats['fraud_transactions'] = conn.execute('SELECT COUNT(*) FROM transactions WHERE is_fraud = 1').fetchone()[0]
        stats['fraud_percentage'] = round((stats['fraud_transactions'] / stats['total_transactions']) * 100, 2) if stats['total_transactions'] > 0 else 0
        
        # Get top merchants with fraud
        top_fraud_merchants = conn.execute('''
            SELECT merchant, COUNT(*) as count 
            FROM transactions 
            WHERE is_fraud = 1 
            GROUP BY merchant 
            ORDER BY count DESC 
            LIMIT 5
        ''').fetchall()
        
        # Get fraud by category
        fraud_by_category = conn.execute('''
            SELECT category, COUNT(*) as count 
            FROM transactions 
            WHERE is_fraud = 1 
            GROUP BY category 
            ORDER BY count DESC
        ''').fetchall()
        
        conn.close()
        
        return render_template('analytics.html', 
                              stats=stats, 
                              top_fraud_merchants=[dict(m) for m in top_fraud_merchants],
                              fraud_by_category=[dict(c) for c in fraud_by_category])
    except Exception as e:
        return render_template('analytics.html', error=str(e))

if __name__ == '__main__':
    # Make sure model directory exists
    os.makedirs('model', exist_ok=True)
    app.run(debug=True)


