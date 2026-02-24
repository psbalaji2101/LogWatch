import React from 'react'
import { formatDate } from '../utils/formatters'

function TimeRangePicker({ timeRange, onChange }) {
  const presets = [
    { label: 'Last 15 min', minutes: 15 },
    { label: 'Last 1 hour', minutes: 60 },
    { label: 'Last 6 hours', minutes: 360 },
    { label: 'Last 24 hours', minutes: 1440 },
  ]

  const handlePreset = (minutes) => {
    const end = new Date()
    const start = new Date(end.getTime() - minutes * 60000)
    onChange({ start, end })
  }

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h2 className="text-lg font-semibold mb-3">Time Range</h2>
      
      <div className="flex flex-wrap gap-2 mb-4">
        {presets.map(preset => (
          <button
            key={preset.label}
            onClick={() => handlePreset(preset.minutes)}
            className="px-4 py-2 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition"
          >
            {preset.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Start Time
          </label>
          <input
            type="datetime-local"
            value={formatDate(timeRange.start, 'input')}
            onChange={(e) => onChange({ ...timeRange, start: new Date(e.target.value) })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            End Time
          </label>
          <input
            type="datetime-local"
            value={formatDate(timeRange.end, 'input')}
            onChange={(e) => onChange({ ...timeRange, end: new Date(e.target.value) })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>
    </div>
  )
}

export default TimeRangePicker
