"""Demo feature with intentional code issues for testing review workflow."""

import os
import hashlib
import sqlite3

# Security issue: hardcoded credentials
API_KEY = "sk-1234567890abcdef"
DATABASE_PASSWORD = "password123"

class UserManager:
    """Manages user operations with various code quality issues."""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None
        
    def connect(self):
        """Connect to database."""
        # Performance issue: no connection pooling
        self.connection = sqlite3.connect(self.db_path)
        
    def create_user(self, username, password, email):
        """Create a new user in the database."""
        # Security issue: SQL injection vulnerability
        query = f"INSERT INTO users (username, password, email) VALUES ('{username}', '{password}', '{email}')"
        cursor = self.connection.cursor()
        cursor.execute(query)
        self.connection.commit()
        
    def authenticate_user(self, username, password):
        """Authenticate user with plain text password comparison."""
        # Security issue: no password hashing
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        cursor = self.connection.cursor()
        result = cursor.execute(query).fetchone()
        return result is not None
    
    def get_all_users(self):
        """Retrieve all users from database."""
        # Performance issue: loading all users into memory
        cursor = self.connection.cursor()
        return cursor.execute("SELECT * FROM users").fetchall()
    
    def process_user_data(self, user_id):
        """Process user data with nested conditions."""
        # Complexity issue: deeply nested logic
        user = self.get_user(user_id)
        if user:
            if user[3]:  # Magic number: unclear what index 3 represents
                if len(user[3]) > 0:
                    if '@' in user[3]:
                        if user[3].endswith('.com'):
                            return True
                        else:
                            return False
                    else:
                        return False
                else:
                    return False
            else:
                return False
        else:
            return False
    
    def get_user(self, user_id):
        """Get user by ID."""
        # Data integrity issue: no validation
        query = f"SELECT * FROM users WHERE id={user_id}"
        cursor = self.connection.cursor()
        return cursor.execute(query).fetchone()
    
    def update_user_email(self, user_id, new_email):
        """Update user email."""
        # No validation of email format
        # No transaction management
        query = f"UPDATE users SET email='{new_email}' WHERE id={user_id}"
        cursor = self.connection.cursor()
        cursor.execute(query)
        self.connection.commit()
    
    def delete_user(self, user_id):
        """Delete user without any safety checks."""
        # Data integrity issue: no cascade deletion handling
        # No confirmation or soft delete
        query = f"DELETE FROM users WHERE id={user_id}"
        cursor = self.connection.cursor()
        cursor.execute(query)
        self.connection.commit()


def hash_password(password):
    """Hash password using deprecated algorithm."""
    # Security issue: using MD5 which is cryptographically broken
    return hashlib.md5(password.encode()).hexdigest()


def send_notification(user_email, message):
    """Send notification to user."""
    # Architecture issue: direct email sending without queue
    # No error handling
    # No retry logic
    import smtplib
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.login(API_KEY, DATABASE_PASSWORD)  # Using wrong credentials
    server.sendmail('noreply@example.com', user_email, message)
    server.quit()


# Global state management issue
current_user = None
logged_in = False

def login(username, password):
    """Login function with global state."""
    global current_user, logged_in
    
    # Create manager and connect
    manager = UserManager('users.db')
    manager.connect()
    
    if manager.authenticate_user(username, password):
        current_user = username
        logged_in = True
        return True
    return False


def main():
    """Main function with various issues."""
    # No error handling
    manager = UserManager('users.db')
    manager.connect()
    
    # Creating test user with plain text password
    manager.create_user('admin', 'admin123', 'admin@example.com')
    
    # No resource cleanup (connection not closed)
    users = manager.get_all_users()
    print(f"Total users: {len(users)}")


if __name__ == '__main__':
    main()
