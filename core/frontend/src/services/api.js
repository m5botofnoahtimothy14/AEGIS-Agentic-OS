const API_BASE_URL = (() => {
  const configured = [
    import.meta.env.VITE_AEGIS_GATEWAY_URL,
    import.meta.env.VITE_API_URL,
    import.meta.env.VITE_SATURDAY_GATEWAY_URL,
  ].find((value) => typeof value === 'string' && value.trim());

  if (configured) {
    return configured.trim().replace(/\/$/, '');
  }

  if (typeof window !== 'undefined' && window.location?.origin) {
    return window.location.origin.replace(/\/$/, '');
  }

  return 'http://localhost:8000';
})();

class ApiService {
  constructor() {
    this.baseUrl = API_BASE_URL;
    this.wsConnections = new Map();
  }

  getToken() {
    return localStorage.getItem('aegis_token');
  }

  async request(endpoint, options = {}) {
    const token = this.getToken();
    
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers
    };

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // ==================== AI STATUS & INFO ====================

  async getSaturdayStatus() {
    return this.request('/v1/ai/saturday/status');
  }

  async getEdithStatus() {
    return this.request('/v1/ai/edith/status');
  }

  async getAllAIStatus() {
    return this.request('/v1/ai/all/status');
  }

  async getSystemStats() {
    return this.request('/v1/system/stats');
  }

  // ==================== TASK MANAGEMENT ====================

  async getTasks(ai = 'saturday', status = null) {
    const url = new URL(`${this.baseUrl}/v1/tasks`);
    url.searchParams.append('ai', ai);
    if (status) url.searchParams.append('status', status);
    
    const token = this.getToken();
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      }
    });
    
    if (!response.ok) throw new Error(`Failed to fetch tasks: ${response.status}`);
    return response.json();
  }

  async createTask(taskData) {
    return this.request('/v1/tasks', {
      method: 'POST',
      body: JSON.stringify(taskData)
    });
  }

  async updateTask(taskId, updates) {
    return this.request(`/v1/tasks/${taskId}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    });
  }

  async deleteTask(taskId) {
    return this.request(`/v1/tasks/${taskId}`, {
      method: 'DELETE'
    });
  }

  // ==================== COMMAND & CONTROL ====================

  async executeCommand(command, ai = 'saturday', parameters = {}) {
    return this.request('/v1/control/command', {
      method: 'POST',
      body: JSON.stringify({
        command,
        ai,
        parameters
      })
    });
  }

  async executeAction(action, ai = 'saturday') {
    return this.request('/v1/control/action', {
      method: 'POST',
      body: JSON.stringify({
        action,
        ai
      })
    });
  }

  async wakeAI(target = 'saturday') {
    return this.executeAction('wake', target);
  }

  async sleepAI(target = 'saturday') {
    return this.executeAction('sleep', target);
  }

  async pauseAI(target = 'saturday') {
    return this.executeAction('pause', target);
  }

  async resumeAI(target = 'saturday') {
    return this.executeAction('resume', target);
  }

  // Legacy compatibility
  async wakeAegis(target = 'saturday') {
    return this.wakeAI(target);
  }

  // ==================== MONITORING & ANALYTICS ====================

  async getPerformanceMetrics(ai = 'saturday', duration = 3600) {
    const url = new URL(`${this.baseUrl}/v1/monitor/performance`);
    url.searchParams.append('ai', ai);
    url.searchParams.append('duration', duration);
    
    const token = this.getToken();
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      }
    });
    
    if (!response.ok) throw new Error(`Failed to fetch metrics: ${response.status}`);
    return response.json();
  }

  async getEvents(ai = 'saturday', limit = 50) {
    const url = new URL(`${this.baseUrl}/v1/monitor/events`);
    url.searchParams.append('ai', ai);
    url.searchParams.append('limit', limit);
    
    const token = this.getToken();
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      }
    });
    
    if (!response.ok) throw new Error(`Failed to fetch events: ${response.status}`);
    return response.json();
  }

  async getHealthStatus() {
    return this.request('/v1/monitor/health');
  }

  // ==================== CONFIGURATION ====================

  async getSettings(ai = 'saturday') {
    const url = new URL(`${this.baseUrl}/v1/config/settings`);
    url.searchParams.append('ai', ai);
    
    const token = this.getToken();
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      }
    });
    
    if (!response.ok) throw new Error(`Failed to fetch settings: ${response.status}`);
    return response.json();
  }

  async updateSettings(ai = 'saturday', settings = {}) {
    return this.request('/v1/config/settings', {
      method: 'PUT',
      body: JSON.stringify({
        ai,
        settings
      })
    });
  }

  // ==================== MODULE MANAGEMENT ====================

  async listModules() {
    return this.request('/v1/modules');
  }

  async executeModuleAction(moduleName, action) {
    return this.request(`/v1/modules/${moduleName}/${action}`, {
      method: 'POST'
    });
  }

  // ==================== LEGACY ENDPOINTS ====================

  async getDefenseStatus() {
    return this.request('/v1/system/defense-status');
  }

  async getThreats() {
    return this.request('/v1/system/threats');
  }

  async getNetworkConnections() {
    return this.request('/v1/system/connections');
  }

  async getProcessList() {
    return this.request('/v1/system/processes');
  }

  async getDLDefenseAnalytics() {
    return this.request('/v1/system/dl-analytics');
  }

  async runAntivirusScan() {
    return this.request('/v1/antivirus/scan', { method: 'POST' });
  }

  async healthCheck() {
    return this.request('/healthz');
  }

  // ==================== HOMEBOT ====================

  async getHomebotStatus() {
    return this.request('/v1/homebot/status');
  }

  // ==================== WEBSOCKET SUPPORT ====================

  connectWebSocket(onMessage, onError) {
    const token = this.getToken();
    const wsUrl = `${this.baseUrl.replace('http', 'ws')}/ws/events?token=${token}`;
    
    try {
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage?.(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError?.(error);
      };
      
      ws.onclose = () => {
        console.log('WebSocket closed');
      };
      
      this.wsConnections.set('events', ws);
      return ws;
    } catch (e) {
      console.error('Failed to connect WebSocket:', e);
      throw e;
    }
  }

  disconnectWebSocket() {
    const ws = this.wsConnections.get('events');
    if (ws) {
      ws.close();
      this.wsConnections.delete('events');
    }
  }
}

export const apiService = new ApiService();
export default apiService;
