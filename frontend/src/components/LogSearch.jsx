import React from 'react'

function LogSearch({ value, onChange }) {
  const handleClear = () => {
    onChange('')
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h2 className="text-lg font-semibold mb-3">Search Logs</h2>
      
      <div className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Search logs by keywords, tokens, or fields..."
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        
        {value && (
          <button
            onClick={handleClear}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
          >
            Clear
          </button>
        )}
      </div>
      
      <p className="text-xs text-gray-500 mt-2">
        Examples: "error", "status:500", "user_login", "Database timeout"
      </p>
    </div>
  )
}

export default LogSearch
