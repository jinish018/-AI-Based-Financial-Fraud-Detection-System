import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import pickle
import os

# Create directory for the model if it doesn't exist
os.makedirs('model', exist_ok=True)

# Set random seed for reproducibility
np.random.seed(42)

# Generate synthetic transaction data
def generate_synthetic_data(n_samples=10000):
    # Features
    amount = np.concatenate([
        np.random.normal(100, 50, int(n_samples * 0.8)),  # Normal transactions
        np.random.normal(1000, 500, int(n_samples * 0.2))  # Some high-value transactions
    ])
    
    # Ensure no negative amounts
    amount = np.abs(amount)
    
    hour_of_day = np.random.randint(0, 24, n_samples)
    day_of_week = np.random.randint(0, 7, n_samples)
    merchant_category = np.random.randint(0, 100, n_samples)
    location_hash = np.random.randint(0, 100, n_samples)
    card_type_hash = np.random.randint(0, 10, n_samples)
    
    # Create fraud patterns
    is_fraud = np.zeros(n_samples, dtype=int)
    
    # Pattern 1: High amount transactions at unusual hours
    unusual_hour_mask = (hour_of_day < 6) | (hour_of_day > 22)
    high_amount_mask = amount > 800
    pattern1_mask = unusual_hour_mask & high_amount_mask
    is_fraud[pattern1_mask] = 1
    
    # Pattern 2: Specific merchant categories with unusual activity
    suspicious_merchants = [13, 42, 67, 89]
    for merchant in suspicious_merchants:
        merchant_mask = merchant_category == merchant
        high_value_mask = amount > 500
        pattern2_mask = merchant_mask & high_value_mask
        is_fraud[pattern2_mask] = 1
    
    # Pattern 3: Unusual locations
    suspicious_locations = [7, 23, 56, 78, 91]
    for location in suspicious_locations:
        location_mask = location_hash == location
        weekend_mask = day_of_week >= 5  # Weekend
        pattern3_mask = location_mask & weekend_mask
        is_fraud[pattern3_mask] = 1
    
    # Create DataFrame
    data = pd.DataFrame({
        'amount': amount,
        'hour_of_day': hour_of_day,
        'day_of_week': day_of_week,
        'merchant_category': merchant_category,
        'location_hash': location_hash,
        'card_type_hash': card_type_hash,
        'is_fraud': is_fraud
    })
    
    return data

# Generate data
print("Generating synthetic transaction data...")
data = generate_synthetic_data(10000)

# Check fraud distribution
fraud_count = data['is_fraud'].sum()
print(f"Generated {len(data)} transactions with {fraud_count} fraudulent cases ({fraud_count/len(data)*100:.2f}%)")

# Split features and target
X = data.drop('is_fraud', axis=1)
y = data['is_fraud']

# Split into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train a Random Forest model
print("Training fraud detection model...")
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate the model
train_accuracy = model.score(X_train, y_train)
test_accuracy = model.score(X_test, y_test)
print(f"Model training accuracy: {train_accuracy:.4f}")
print(f"Model testing accuracy: {test_accuracy:.4f}")

# Save the model
model_path = 'model/fraud_detection_model.pkl'
with open(model_path, 'wb') as file:
    pickle.dump(model, file)

print(f"Model saved to {model_path}")

# Feature importance
feature_importance = pd.DataFrame({
    'Feature': X.columns,
    'Importance': model.feature_importances_
}).sort_values('Importance', ascending=False)

print("\nFeature Importance:")
print(feature_importance)

print("\nModel is ready to use with the fraud detection system!")