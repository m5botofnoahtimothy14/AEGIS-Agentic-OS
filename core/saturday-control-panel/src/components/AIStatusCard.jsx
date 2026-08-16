import { Power, Activity, AlertCircle } from 'lucide-react';

export default function AIStatusCard({ ai = 'saturday', status, onWake, onControl }) {
  const statusColor = {
    'ACTIVE': '#00ff41',
    'STANDBY': '#ffd700',
    'OFFLINE': '#ff0000',
    'ERROR': '#ff6b6b'
  };

  const statusIcon = {
    'ACTIVE': <Activity size={20} className="animate-pulse" style={{ color: statusColor[status] }} />,
    'STANDBY': <Power size={20} style={{ color: statusColor[status] }} />,
    'OFFLINE': <AlertCircle size={20} style={{ color: statusColor[status] }} />,
    'ERROR': <AlertCircle size={20} style={{ color: statusColor[status] }} />
  };

  const uptime = status?.uptime_seconds || 0;
  const hours = Math.floor(uptime / 3600);
  const minutes = Math.floor((uptime % 3600) / 60);
  const uptimeStr = `${hours}h ${minutes}m`;

  return (
    <div className="ai-status-card glass-panel">
      <div className="card-header">
        <div className="ai-title">
          {statusIcon[status?.status] || statusIcon['OFFLINE']}
          <div>
            <h3>{ai.toUpperCase()}</h3>
            <span className="ai-type">{status?.type || 'unknown'}</span>
          </div>
        </div>
        <span className={`status-badge status-${status?.status?.toLowerCase()}`}>
          {status?.status || 'UNKNOWN'}
        </span>
      </div>

      <div className="card-content">
        <div className="metric-row">
          <span>Uptime:</span>
          <strong>{uptimeStr}</strong>
        </div>
        
        <div className="metric-row">
          <span>CPU:</span>
          <strong>{status?.system?.cpu_percent?.toFixed(1)}%</strong>
        </div>

        <div className="metric-row">
          <span>Memory:</span>
          <strong>{status?.system?.memory_percent?.toFixed(1)}%</strong>
        </div>

        <div className="modules-grid">
          {status?.modules && Object.entries(status.modules).map(([module, enabled]) => (
            <div key={module} className={`module-badge ${enabled ? 'enabled' : 'disabled'}`}>
              {module}
            </div>
          ))}
        </div>
      </div>

      <div className="card-actions">
        <button 
          className="btn btn-primary" 
          onClick={() => onWake?.(ai)}
          disabled={status?.status === 'ACTIVE'}
        >
          Wake
        </button>
        <button 
          className="btn btn-secondary" 
          onClick={() => onControl?.(ai)}
        >
          Control
        </button>
      </div>
    </div>
  );
}
