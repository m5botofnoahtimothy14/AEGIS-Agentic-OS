# S.A.T.U.R.D.A.Y Control Panel - Website Documentation

## Overview

The **S.A.T.U.R.D.A.Y Control Panel** is a comprehensive web-based interface for monitoring and controlling two AI systems:
- **SATURDAY** (Primary AI System)
- **EDITH** (Secondary AI System / Subdomain)

This document describes the complete implementation, features, and how to use the system.

---

## Architecture

### Backend (`core/main.py`)

The backend is a **FastAPI** application with the following enhancements:

#### Core Features:
1. **WebSocket Support** - Real-time event streaming
2. **Firebase Authentication** - Secure token-based access
3. **Event Bus Architecture** - Asynchronous command dispatch
4. **Comprehensive Logging** - Detailed audit trails

#### New API Endpoints (`/v1/*`)

##### AI Status & Monitoring
- `GET /v1/ai/saturday/status` - Get Saturday AI system status
- `GET /v1/ai/edith/status` - Get Edith AI system status  
- `GET /v1/ai/all/status` - Get all AI systems status

##### Task Management
- `GET /v1/tasks?ai=saturday` - List tasks for specific AI
- `POST /v1/tasks` - Create new task
- `PUT /v1/tasks/{task_id}` - Update task
- `DELETE /v1/tasks/{task_id}` - Delete task

##### Command & Control
- `POST /v1/control/command` - Execute command on AI
- `POST /v1/control/action` - Execute action (wake, sleep, pause, resume)

##### Monitoring & Analytics
- `GET /v1/monitor/performance` - Performance metrics
- `GET /v1/monitor/events` - System events
- `GET /v1/monitor/health` - System health status

##### Configuration
- `GET /v1/config/settings` - Get AI settings
- `PUT /v1/config/settings` - Update AI settings

##### WebSocket
- `WS /ws/events` - Real-time event stream

---

### Frontend (`core/saturday-control-panel/`)

#### Technology Stack
- **Framework**: React 18.3.1
- **Build Tool**: Vite
- **Styling**: Custom CSS with CSS Variables
- **Charts**: Recharts
- **UI Icons**: Lucide React
- **State Management**: React Hooks

#### Components

##### 1. **AIStatusCard** (`components/AIStatusCard.jsx`)
Displays comprehensive status for each AI system:
- System status (ACTIVE/STANDBY/OFFLINE)
- Resource usage (CPU, Memory)
- Module availability
- Uptime tracking
- Quick action buttons (Wake, Control)

##### 2. **CommandPanel** (`components/CommandPanel.jsx`)
Command and control interface:
- Quick action buttons (Wake, Sleep, Pause, Resume)
- Text command input
- Real-time feedback
- Loading states

##### 3. **MonitoringDashboard** (`components/MonitoringDashboard.jsx`)
Real-time performance monitoring:
- CPU & Memory usage charts
- Response time tracking
- Historical data visualization
- Live updates

##### 4. **TaskManager** (`components/TaskManager.jsx`)
Task management interface:
- Create new tasks
- View all tasks with status
- Delete tasks
- Priority levels
- Task descriptions

##### 5. **EventLog** (`components/EventLog.jsx`)
Real-time event monitoring:
- Event severity levels (error, warning, success, info)
- Timestamp tracking
- Auto-scrolling to latest events
- Color-coded by type

#### Main App Structure

```
App
├── Header (Navigation & Settings)
├── Sidebar (AI Selection)
├── Main Content
│   ├── Status Grid (Saturday + Edith Cards)
│   ├── Control Section
│   │   ├── Command Panel
│   │   └── Monitoring Dashboard
│   └── Info Section
│       ├── Task Manager
│       └── Event Log
└── Error/Loading States
```

---

## API Service (`core/frontend/src/services/api.js`)

The `ApiService` class provides comprehensive client-side API integration:

### AI Status Methods
```javascript
await apiService.getSaturdayStatus()    // Saturday status
await apiService.getEdithStatus()       // Edith status
await apiService.getAllAIStatus()       // Both systems
```

### Task Management
```javascript
await apiService.getTasks('saturday', status)
await apiService.createTask(taskData)
await apiService.updateTask(taskId, updates)
await apiService.deleteTask(taskId)
```

### Commands & Control
```javascript
await apiService.executeCommand(command, ai, parameters)
await apiService.executeAction(action, ai)  // wake, sleep, pause, resume
await apiService.wakeAI('saturday')
```

### Monitoring
```javascript
await apiService.getPerformanceMetrics('saturday', duration)
await apiService.getEvents('saturday', limit)
await apiService.getHealthStatus()
```

### Configuration
```javascript
await apiService.getSettings('saturday')
await apiService.updateSettings('saturday', settings)
```

### WebSocket
```javascript
apiService.connectWebSocket(
  (data) => console.log('Event:', data),
  (error) => console.error('WS Error:', error)
)
apiService.disconnectWebSocket()
```

---

## Features

### 1. **Dual AI System Support**
- Independent monitoring for Saturday and Edith
- Separate status pages and controls
- Distinct module management
- Isolated task queues

### 2. **Real-Time Monitoring**
- Live CPU and memory usage
- Response time tracking
- Event stream via WebSocket
- Health status monitoring

### 3. **Task Management**
- Create tasks with priority levels
- Track task status (pending, running, completed, failed)
- Delete tasks
- Real-time task updates

### 4. **Command & Control**
- Send text commands to AIs
- Quick actions (Wake, Sleep, Pause, Resume)
- Module start/stop/restart
- Feedback confirmation

### 5. **System Health**
- Component status monitoring
- Performance metrics
- Event logging
- Error tracking

---

## Configuration

### Environment Variables

Create `.env` file in `core/saturday-control-panel/`:

```env
VITE_API_URL=http://localhost:8000
VITE_AEGIS_GATEWAY_URL=http://localhost:8000
```

For production:
```env
VITE_API_URL=https://your-domain.com/api
VITE_AEGIS_GATEWAY_URL=https://your-domain.com
```

### Backend Configuration

In `core/main.py`, set these environment variables:

```bash
# Authentication
SATURDAY_DISABLE_AUTH=false
SATURDAY_STRICT_PROD=false

# CORS
SATURDAY_CORE_ORIGINS=http://localhost:5173,http://localhost:5174

# Optional: Firebase
GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase-key.json
```

---

## Usage Guide

### Starting the System

1. **Backend**:
```bash
cd /workspaces/S.A.T.U.R.D.A.Y
python -m core.main
```
Server runs on `http://localhost:8000`

2. **Frontend**:
```bash
cd /workspaces/S.A.T.U.R.D.A.Y/core/saturday-control-panel
npm install
npm run dev
```
UI runs on `http://localhost:5173`

### Accessing the Control Panel

1. Open browser to `http://localhost:5173`
2. Authenticate (if Firebase enabled)
3. View dual AI status cards
4. Select AI (Saturday/Edith) from sidebar
5. Monitor, control, and manage tasks

### Key Workflows

#### Monitoring Saturday
1. Click "SATURDAY" in sidebar
2. View real-time status card
3. Monitor CPU/Memory in dashboard
4. Check recent events in log

#### Sending Commands
1. Select AI system
2. Type command in command panel
3. Click Send or press Enter
4. See confirmation feedback

#### Managing Tasks
1. Click "Add Task" button
2. Enter task details and priority
3. View task status updates
4. Delete completed/failed tasks

#### Quick Actions
1. Click action button (Wake/Sleep/Pause/Resume)
2. See immediate status update
3. View confirmation in event log

---

## Data Flow

### Real-Time Updates

1. **WebSocket Connection**
   - Established on component mount
   - Receives events from backend
   - Updates UI in real-time

2. **Polling**
   - Status: every 5 seconds
   - Tasks: every 8 seconds  
   - Events: every 8 seconds
   - Performance: every 10 seconds

3. **User Actions**
   - Command/action sent via HTTP POST
   - Event published to event bus
   - WebSocket broadcasts update
   - UI re-renders with new state

---

## Status Codes

### AI Status
- `ACTIVE` - System running and responsive
- `STANDBY` - System idle but available
- `OFFLINE` - System not reachable
- `ERROR` - System error state

### Task Status
- `pending` - Waiting to be executed
- `running` - Currently executing
- `completed` - Successfully finished
- `failed` - Execution failed

### Event Types
- `error` - Red indicator
- `warning` - Yellow indicator
- `success` - Green indicator
- `info` - Blue indicator

---

## Security

### Authentication
- Firebase Auth tokens required (if enabled)
- Bearer token in Authorization header
- Token stored in localStorage
- Auto-refresh on expiration

### CORS
- Whitelist specific origins
- Default: localhost:5173 and 5174
- Configurable via environment

### Rate Limiting
- Implement via API gateway
- WebSocket connection limits
- Task creation throttling

---

## Troubleshooting

### Connection Issues
```
Error: Failed to connect to API
→ Check backend is running on configured URL
→ Verify VITE_API_URL environment variable
→ Check CORS configuration
```

### WebSocket Errors
```
Error: WebSocket connection failed
→ Check WSS/WS protocol correct for HTTPS/HTTP
→ Verify firewall allows WebSocket
→ Check backend /ws/events endpoint
```

### Task Not Updating
```
→ Check task_manager module initialized
→ Verify database connection
→ Check polling intervals set correctly
```

### Authentication Failed
```
→ Verify Firebase credentials
→ Check token not expired
→ Clear localStorage and retry
```

---

## Performance Optimization

### Frontend
- Component lazy loading
- Memoization for status cards
- Efficient re-renders with hooks
- Virtualized event log for large lists

### Backend
- Async task dispatch
- Connection pooling
- Query optimization
- Caching for frequently accessed data

### Network
- WebSocket for real-time updates
- Compression for large responses
- Request batching where possible
- CDN for static assets

---

## Future Enhancements

### Planned Features
1. **Multi-user Support**
   - Role-based access control (RBAC)
   - User activity audit trail
   - Collaborative features

2. **Advanced Analytics**
   - Predictive performance analysis
   - Anomaly detection
   - Historical trend analysis

3. **Enhanced Controls**
   - Scheduled tasks
   - Conditional workflows
   - Macro recording

4. **Mobile App**
   - React Native implementation
   - Offline support
   - Push notifications

5. **Integration**
   - Webhook support
   - Third-party service connectors
   - Custom module API

---

## Support & Documentation

### Key Files
- Backend: [/workspaces/S.A.T.U.R.D.A.Y/core/main.py](../../core/main.py)
- Frontend: [/workspaces/S.A.T.U.R.D.A.Y/core/saturday-control-panel/src/App.jsx](../../core/saturday-control-panel/src/App.jsx)
- API Service: [/workspaces/S.A.T.U.R.D.A.Y/core/frontend/src/services/api.js](../../core/frontend/src/services/api.js)
- Styles: [/workspaces/S.A.T.U.R.D.A.Y/core/saturday-control-panel/src/styles.css](../../core/saturday-control-panel/src/styles.css)

### Getting Help
1. Check error messages and logs
2. Review configuration
3. Test API endpoints with curl
4. Check browser console for client errors
5. Review backend server logs

---

## License

SATURDAY Control Panel - All Rights Reserved

---

**Last Updated**: 2025-02-26
**Version**: 2.0.0
**Maintained By**: S.A.T.U.R.D.A.Y Development Team
