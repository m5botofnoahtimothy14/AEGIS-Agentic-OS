import { useEffect, useState } from 'react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function MonitoringDashboard({ ai = 'saturday', performanceData = [] }) {
  const [chartData, setChartData] = useState(performanceData);

  useEffect(() => {
    setChartData(performanceData);
  }, [performanceData]);

  // Sample data if none provided
  const sampleData = Array.from({ length: 12 }, (_, i) => ({
    time: `${i * 5}m`,
    cpu: Math.random() * 100,
    memory: Math.random() * 100,
    response_time: Math.random() * 500
  }));

  const data = chartData.length > 0 ? chartData : sampleData;

  return (
    <div className="monitoring-dashboard glass-panel">
      <h3 className="section-title">System Performance - {ai.toUpperCase()}</h3>

      <div className="charts-container">
        <div className="chart-wrapper">
          <h4>CPU & Memory Usage</h4>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={data}>
              <defs>
                <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00ff41" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#00ff41" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorMemory" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ff0080" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#ff0080" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="time" stroke="rgba(255,255,255,0.5)" />
              <YAxis stroke="rgba(255,255,255,0.5)" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                  border: '1px solid #00ff41',
                  borderRadius: '4px'
                }}
              />
              <Legend />
              <Area type="monotone" dataKey="cpu" stroke="#00ff41" fillOpacity={1} fill="url(#colorCpu)" name="CPU %" />
              <Area type="monotone" dataKey="memory" stroke="#ff0080" fillOpacity={1} fill="url(#colorMemory)" name="Memory %" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-wrapper">
          <h4>Response Time</h4>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="time" stroke="rgba(255,255,255,0.5)" />
              <YAxis stroke="rgba(255,255,255,0.5)" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                  border: '1px solid #00d9ff',
                  borderRadius: '4px'
                }}
              />
              <Line type="monotone" dataKey="response_time" stroke="#00d9ff" dot={false} name="Response Time (ms)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
