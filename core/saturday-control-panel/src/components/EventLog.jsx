import { useEffect, useRef } from 'react';
import { AlertCircle, Info, CheckCircle, AlertTriangle } from 'lucide-react';

export default function EventLog({ ai = 'saturday', events = [] }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const eventIcon = {
    'error': <AlertCircle size={14} className="text-red-400" />,
    'warning': <AlertTriangle size={14} className="text-yellow-400" />,
    'success': <CheckCircle size={14} className="text-green-400" />,
    'info': <Info size={14} className="text-blue-400" />
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp * 1000 || timestamp);
    return date.toLocaleTimeString();
  };

  return (
    <div className="event-log glass-panel">
      <h3 className="section-title">Event Log - {ai.toUpperCase()}</h3>
      
      <div className="events-container">
        {events.length === 0 ? (
          <p className="empty-state">No events recorded</p>
        ) : (
          events.map((event, idx) => (
            <div key={idx} className={`event-item event-${event.type || 'info'}`}>
              <div className="event-icon">
                {eventIcon[event.type] || eventIcon['info']}
              </div>
              <div className="event-content">
                <div className="event-message">{event.message}</div>
                <div className="event-time">{formatTime(event.timestamp)}</div>
              </div>
            </div>
          ))
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
