import React from 'react'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'

function Charts({ data, onTimeClick }) {
  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Time Series Chart */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Events Over Time</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={data.time_series}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="timestamp" 
              tickFormatter={(ts) => new Date(ts).toLocaleTimeString()}
            />
            <YAxis />
            <Tooltip 
              labelFormatter={(ts) => new Date(ts).toLocaleString()}
            />
            <Line 
              type="monotone" 
              dataKey="count" 
              stroke="#3b82f6" 
              strokeWidth={2}
              onClick={(e) => onTimeClick && onTimeClick(e.timestamp)}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Top Tokens Chart */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Top Tokens</h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={data.top_tokens.slice(0, 10)}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="token" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#10b981" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Source Distribution */}
      <div className="bg-white p-4 rounded-lg shadow col-span-1 md:col-span-2">
        <h3 className="text-lg font-semibold mb-4">Distribution by Source File</h3>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={data.sources}
              dataKey="count"
              nameKey="source"
              cx="50%"
              cy="50%"
              outerRadius={80}
              label={(entry) => entry.source.split('/').pop()}
            >
              {data.sources.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default Charts
