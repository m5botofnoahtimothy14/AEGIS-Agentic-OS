import { useState } from 'react';
import { Send, Loader } from 'lucide-react';

export default function CommandPanel({ ai = 'saturday', onCommand, onAction }) {
  const [command, setCommand] = useState('');
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState('');

  const handleSendCommand = async () => {
    if (!command.trim()) return;
    
    setLoading(true);
    setFeedback('');
    
    try {
      await onCommand?.(ai, command);
      setFeedback('✓ Command sent');
      setCommand('');
      setTimeout(() => setFeedback(''), 2000);
    } catch (err) {
      setFeedback('✗ Command failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const quickActions = [
    { label: 'Wake', action: 'wake' },
    { label: 'Sleep', action: 'sleep' },
    { label: 'Pause', action: 'pause' },
    { label: 'Resume', action: 'resume' },
  ];

  return (
    <div className="command-panel glass-panel">
      <h3 className="section-title">Control Panel</h3>

      <div className="quick-actions">
        {quickActions.map(({ label, action }) => (
          <button
            key={action}
            className="action-btn"
            onClick={() => onAction?.(ai, action)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="command-input-group">
        <input
          type="text"
          className="command-input"
          placeholder="Enter command..."
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSendCommand()}
          disabled={loading}
        />
        <button
          className="cmd-send-btn"
          onClick={handleSendCommand}
          disabled={!command.trim() || loading}
        >
          {loading ? <Loader size={18} className="spinner" /> : <Send size={18} />}
        </button>
      </div>

      {feedback && (
        <div className={`feedback ${feedback.startsWith('✓') ? 'success' : 'error'}`}>
          {feedback}
        </div>
      )}
    </div>
  );
}
