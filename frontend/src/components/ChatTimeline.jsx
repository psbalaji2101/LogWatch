import React from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

function ChatTimeline({ data }) {
  if (!data || data.length === 0) return null

  return (
    <div>
      <p className="text-xs font-semibold mb-2 text-gray-600">Error Timeline:</p>
      <ResponsiveContainer width="100%" height={150}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="time" 
            tick={{ fontSize: 10 }}
            tickFormatter={(time) => time.split(' ')[1]}
          />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: '10px' }} />
          <Line type="monotone" dataKey="errors" stroke="#ef4444" strokeWidth={2} />
          <Line type="monotone" dataKey="warnings" stroke="#f59e0b" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default ChatTimeline
