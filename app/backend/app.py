import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'taskdb'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def init_db():
    """Initialize database tables with retry logic"""
    import time
    max_retries = 10
    retry_delay = 3
    
    for attempt in range(max_retries):
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    completed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            cur.close()
            conn.close()
            logger.info("Database initialized successfully")
            return True
        except Exception as e:
            logger.warning(f"Database init attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error("Database initialization failed after all retries")
                return False

# Track if DB is initialized
db_initialized = False

@app.before_request
def ensure_db():
    """Ensure database is initialized before handling requests"""
    global db_initialized
    if not db_initialized:
        db_initialized = init_db()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

@app.route('/ready', methods=['GET'])
def ready():
    """Readiness check endpoint"""
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({'status': 'ready'}), 200
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({'status': 'not ready', 'error': str(e)}), 503

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM tasks ORDER BY created_at DESC')
        tasks = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(tasks), 200
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        return jsonify({'error': 'Failed to fetch tasks'}), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    try:
        data = request.get_json()
        title = data.get('title')
        completed = data.get('completed', False)
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO tasks (title, completed) VALUES (%s, %s) RETURNING *',
            (title, completed)
        )
        task = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Task created: {task['id']}")
        return jsonify(task), 201
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({'error': 'Failed to create task'}), 500

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """Get a specific task"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM tasks WHERE id = %s', (task_id,))
        task = cur.fetchone()
        cur.close()
        conn.close()
        
        if task is None:
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify(task), 200
    except Exception as e:
        logger.error(f"Error fetching task: {e}")
        return jsonify({'error': 'Failed to fetch task'}), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Update a task"""
    try:
        data = request.get_json()
        title = data.get('title')
        completed = data.get('completed')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Build update query dynamically
        updates = []
        params = []
        
        if title is not None:
            updates.append('title = %s')
            params.append(title)
        
        if completed is not None:
            updates.append('completed = %s')
            params.append(completed)
        
        if not updates:
            return jsonify({'error': 'No fields to update'}), 400
        
        params.append(task_id)
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = %s RETURNING *"
        
        cur.execute(query, params)
        task = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if task is None:
            return jsonify({'error': 'Task not found'}), 404
        
        logger.info(f"Task updated: {task_id}")
        return jsonify(task), 200
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        return jsonify({'error': 'Failed to update task'}), 500

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM tasks WHERE id = %s RETURNING id', (task_id,))
        deleted = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if deleted is None:
            return jsonify({'error': 'Task not found'}), 404
        
        logger.info(f"Task deleted: {task_id}")
        return jsonify({'message': 'Task deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return jsonify({'error': 'Failed to delete task'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
