import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_URL = process.env.REACT_APP_API_URL || '/api';

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_URL}/tasks`);
      setTasks(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch tasks');
      console.error('Error fetching tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  const addTask = async (e) => {
    e.preventDefault();
    if (!newTask.trim()) return;

    try {
      const response = await axios.post(`${API_URL}/tasks`, {
        title: newTask,
        completed: false
      });
      setTasks([...tasks, response.data]);
      setNewTask('');
      setError(null);
    } catch (err) {
      setError('Failed to add task');
      console.error('Error adding task:', err);
    }
  };

  const toggleTask = async (id, completed) => {
    try {
      const response = await axios.put(`${API_URL}/tasks/${id}`, {
        completed: !completed
      });
      setTasks(tasks.map(task => 
        task.id === id ? response.data : task
      ));
      setError(null);
    } catch (err) {
      setError('Failed to update task');
      console.error('Error updating task:', err);
    }
  };

  const deleteTask = async (id) => {
    try {
      await axios.delete(`${API_URL}/tasks/${id}`);
      setTasks(tasks.filter(task => task.id !== id));
      setError(null);
    } catch (err) {
      setError('Failed to delete task');
      console.error('Error deleting task:', err);
    }
  };

  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <h1>📋 Task Manager</h1>
          <p className="subtitle">Kubernetes Microservices Demo</p>
        </header>

        {error && (
          <div className="error-banner">
            ⚠️ {error}
          </div>
        )}

        <form onSubmit={addTask} className="task-form">
          <input
            type="text"
            value={newTask}
            onChange={(e) => setNewTask(e.target.value)}
            placeholder="Add a new task..."
            className="task-input"
          />
          <button type="submit" className="add-button">
            ➕ Add Task
          </button>
        </form>

        {loading ? (
          <div className="loading">Loading tasks...</div>
        ) : (
          <div className="task-list">
            {tasks.length === 0 ? (
              <div className="empty-state">
                <p>🎉 No tasks yet! Add one to get started.</p>
              </div>
            ) : (
              tasks.map(task => (
                <div key={task.id} className={`task-item ${task.completed ? 'completed' : ''}`}>
                  <input
                    type="checkbox"
                    checked={task.completed}
                    onChange={() => toggleTask(task.id, task.completed)}
                    className="task-checkbox"
                  />
                  <span className="task-title">{task.title}</span>
                  <button
                    onClick={() => deleteTask(task.id)}
                    className="delete-button"
                  >
                    🗑️
                  </button>
                </div>
              ))
            )}
          </div>
        )}

        <footer className="footer">
          <div className="stats">
            <span>Total: {tasks.length}</span>
            <span>Completed: {tasks.filter(t => t.completed).length}</span>
            <span>Pending: {tasks.filter(t => !t.completed).length}</span>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default App;
