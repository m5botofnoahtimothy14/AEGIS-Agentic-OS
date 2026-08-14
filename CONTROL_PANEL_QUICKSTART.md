# S.A.T.U.R.D.A.Y Control Panel - Quick Start Guide

## ⚡ 5-Minute Setup

### Step 1: Start Backend Server
```bash
cd /workspaces/S.A.T.U.R.D.A.Y
python -m core.main
```

Wait for message: `Uvicorn running on http://0.0.0.0:8000`

### Step 2: Start Frontend Development Server
```bash
cd /workspaces/S.A.T.U.R.D.A.Y/core/saturday-control-panel
npm install  # Only on first run
npm run dev
```

### Step 3: Open in Browser
```
http://localhost:5173
```

---

## 🎯 Main Features at a Glance

| Feature | Location | Description |
|---------|----------|-------------|
| **AI Status** | Top Cards | Real-time CPU, Memory, Module status |
| **Quick Actions** | Command Panel | Wake/Sleep/Pause/Resume |
| **Send Commands** | Text Input | Custom commands to AI |
| **Monitor Performance** | Charts | Live CPU/Memory graphs |
| **Manage Tasks** | Task Manager | Create/Delete tasks |
| **View Events** | Event Log | Real-time system events |
| **Switch AI** | Sidebar | Toggle between Saturday/Edith |

---

## 🔧 Environment Setup

### Create `.env` in `core/saturday-control-panel/`:
```env
VITE_API_URL=http://localhost:8000
VITE_AEGIS_GATEWAY_URL=http://localhost:8000
```

### For Production:
```env
VITE_API_URL=https://yourdomain.com
VITE_AEGIS_GATEWAY_URL=https://yourdomain.com
```

---

## 📱 UI Layout

```
┌─────────────────────────────────────────────────────────┐
│  S.A.T.U.R.D.A.Y Control Panel          ⚙️ Settings    │ ← Header
├──────────┬──────────────────────────────────────────────┤
│ Saturday │                                              │
│ EDITH    │          Status Cards (2 AI Systems)        │
│ Settings │          ┌──────────────┬──────────────────┐ │
│          │          │ AI Status    │ AI Status        │ │
│          │          │ Saturday     │ EDITH            │ │
│          │          └──────────────┴──────────────────┘ │
│ Sidebar  │  ┌─ Control Section ────────────────────────┐ │
│          │  │ Command Panel    │ Monitoring Dashboard │ │
│          │  │ Quick Actions    │ CPU/Memory Charts    │ │
│          │  └──────────────────┴──────────────────────┘ │
│          │  ┌─ Info Section ───────────────────────────┐ │
│          │  │ Task Manager         │ Event Log        │ │
│          │  │ Create/Delete Tasks  │ Real-time Events │ │
│          │  └──────────────────────┴──────────────────┘ │
└──────────┴──────────────────────────────────────────────┘
```

---

## 🚀 Common Tasks

### 1. **Wake Up an AI System**
```
1. Click "SATURDAY" or "EDITH" in sidebar
2. Click "WAKE" button in Command Panel
3. Status changes to "ACTIVE"
```

### 2. **Send a Command**
```
1. Select AI system
2. Type command in text input: "restart voice_service"
3. Click Send
4. See confirmation in Event Log
```

### 3. **Monitor Performance**
```
1. Select AI system  
2. Watch real-time charts update
3. CPU/Memory shown in Status Card
```

### 4. **Create a Task**
```
1. Click "Add Task" button
2. Enter task title
3. Add description (optional)
4. Select priority (Low/Normal/High/Critical)
5. Click Save
```

### 5. **Check Events**
```
1. View Event Log at bottom-right
2. Color-coded by type:
   - Red = Error
   - Yellow = Warning
   - Green = Success
   - Blue = Info
```

---

## 🔗 API Endpoints Reference

### Get AI Status
```bash
curl http://localhost:8000/v1/ai/saturday/status
curl http://localhost:8000/v1/ai/edith/status
```

### Send Command
```bash
curl -X POST http://localhost:8000/v1/control/command \
  -H "Content-Type: application/json" \
  -d '{"command": "restart voice_service", "ai": "saturday"}'
```

### Execute Action
```bash
curl -X POST http://localhost:8000/v1/control/action \
  -H "Content-Type: application/json" \
  -d '{"action": "wake", "ai": "saturday"}'
```

### Get Tasks
```bash
curl http://localhost:8000/v1/tasks?ai=saturday
```

### Create Task
```bash
curl -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Backup Database",
    "description": "Daily database backup",
    "ai": "saturday",
    "priority": "normal"
  }'
```

---

## 🐛 Troubleshooting

### "Cannot connect to API"
```
✓ Check backend is running on http://localhost:8000
✓ Check frontend .env has correct VITE_API_URL
✓ Try visiting http://localhost:8000 in browser directly
```

### "Events not updating"
```
✓ Check WebSocket connection: Open DevTools → Network → ws://...
✓ Verify backend WebSocket endpoint is working
✓ Check for CORS errors in console
```

### "Commands not executing"
```
✓ Verify AI system status is ACTIVE
✓ Check command syntax is correct
✓ View Event Log for error details
✓ Check backend logs for execution errors
```

### "UI not styling properly"
```
✓ Clear browser cache (Ctrl+Shift+Del)
✓ Hard refresh page (Ctrl+Shift+R)
✓ Check styles.css is properly loaded in DevTools
```

---

## 📊 Status Indicators

### AI Status Badge
| Status | Color | Meaning |
|--------|-------|---------|
| **ACTIVE** | Green | System running |
| **STANDBY** | Yellow | System idle |
| **OFFLINE** | Red | System unreachable |
| **ERROR** | Red | System error state |

### Module Status
| Status | Indicator | Meaning |
|--------|-----------|---------|
| Enabled | Green dot | Module running |
| Disabled | Gray | Module stopped |
| Error | Red X | Module failed |

---

## 💡 Pro Tips

1. **Switch AI Quickly**: Click SATURDAY or EDITH in sidebar
2. **Monitor Multiple Systems**: Open two browser tabs (one per AI)
3. **Task Priority**: Use "critical" for urgent tasks
4. **Event Filtering**: Check Event Log for command results
5. **Auto-Refresh**: Data updates automatically every 5-10 seconds
6. **WebSocket**: Enables real-time updates without polling

---

## 📈 Performance Metrics

### What Gets Monitored
- **CPU Usage** - Percentage of CPU utilization
- **Memory** - MB of RAM in use
- **Response Time** - Milliseconds for commands
- **Uptime** - Hours/Minutes system running
- **Module Count** - Number of active modules

### Update Frequency
- Status: Every 5 seconds
- Tasks: Every 8 seconds
- Events: Every 8 seconds
- Performance: Every 10 seconds

---

## 🔒 Security Notes

1. **Never** share API tokens
2. **Use HTTPS** in production
3. **Restrict** admin access via RBAC
4. **Enable** Firebase authentication
5. **Monitor** audit logs for suspicious activity

---

## 🆘 Getting Help

### Check These First
1. Are both servers running? (Backend on 8000, Frontend on 5173)
2. Does http://localhost:8000/docs show Swagger UI?
3. Are there errors in browser Console (F12)?
4. Check backend logs for errors

### Backend Logs Location
```
/workspaces/S.A.T.U.R.D.A.Y/logs/
```

### Frontend Debugging
```
Open DevTools: F12
Check Console tab for errors
Check Network tab for API calls
Check Application tab for stored tokens
```

---

## 📝 Next Steps

1. **Configure**: Set up environment variables
2. **Authenticate**: Set up Firebase (optional)
3. **Deploy**: Follow production deployment guide
4. **Integrate**: Connect to other services
5. **Extend**: Add custom AI modules

---

## 📚 Full Documentation

For detailed information, see:
- [CONTROL_PANEL_DOCUMENTATION.md](./CONTROL_PANEL_DOCUMENTATION.md) - Complete reference
- [README.md](./README.md) - Project overview
- [PRODUCTION.md](./PRODUCTION.md) - Production deployment

---

**Status**: ✅ Ready to Use  
**Last Updated**: 2025-02-26  
**Supported Browsers**: Chrome, Firefox, Safari, Edge (latest versions)
