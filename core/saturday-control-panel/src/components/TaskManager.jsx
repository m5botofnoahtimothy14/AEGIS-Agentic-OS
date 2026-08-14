import { useState } from 'react';
import { Plus, Trash2, CheckCircle, Clock, AlertCircle } from 'lucide-react';

export default function TaskManager({ ai = 'saturday', tasks = [], onCreateTask, onDeleteTask, onUpdateTask }) {
  const [newTask, setNewTask] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('normal');
  const [showForm, setShowForm] = useState(false);

  const handleCreateTask = async () => {
    if (!newTask.trim()) return;

    try {
      await onCreateTask?.({
        title: newTask,
        description,
        ai,
        priority
      });
      setNewTask('');
      setDescription('');
      setPriority('normal');
      setShowForm(false);
    } catch (err) {
      console.error('Task creation failed:', err);
    }
  };

  const statusIcon = {
    'pending': <Clock size={16} className="text-yellow-400" />,
    'running': <AlertCircle size={16} className="text-blue-400 animate-pulse" />,
    'completed': <CheckCircle size={16} className="text-green-400" />,
    'failed': <AlertCircle size={16} className="text-red-400" />
  };

  const priorityColor = {
    'low': 'priority-low',
    'normal': 'priority-normal',
    'high': 'priority-high',
    'critical': 'priority-critical'
  };

  return (
    <div className="task-manager glass-panel">
      <div className="section-header">
        <h3 className="section-title">Task Manager</h3>
        <button className="add-btn" onClick={() => setShowForm(!showForm)}>
          <Plus size={16} /> Add Task
        </button>
      </div>

      {showForm && (
        <div className="task-form">
          <input
            type="text"
            className="form-input"
            placeholder="Task title"
            value={newTask}
            onChange={(e) => setNewTask(e.target.value)}
          />
          <textarea
            className="form-input"
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows="3"
          />
          <select
            className="form-input"
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
          >
            <option value="low">Low Priority</option>
            <option value="normal">Normal Priority</option>
            <option value="high">High Priority</option>
            <option value="critical">Critical</option>
          </select>
          <div className="form-actions">
            <button className="btn btn-primary" onClick={handleCreateTask}>
              Create Task
            </button>
            <button className="btn btn-secondary" onClick={() => setShowForm(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="tasks-list">
        {tasks.length === 0 ? (
          <p className="empty-state">No tasks yet. Create one to get started!</p>
        ) : (
          tasks.map((task) => (
            <div key={task.id} className={`task-item ${priorityColor[task.priority]}`}>
              <div className="task-header">
                <div className="task-title">
                  {statusIcon[task.status] || statusIcon['pending']}
                  <span>{task.title}</span>
                </div>
                <button
                  className="delete-btn"
                  onClick={() => onDeleteTask?.(task.id)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
              {task.description && (
                <p className="task-description">{task.description}</p>
              )}
              <div className="task-meta">
                <span className={`status-label status-${task.status}`}>
                  {task.status || 'pending'}
                </span>
                <span className="task-priority">{task.priority}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
