import React from 'react'

function LogSearch({ value, onChange }) {
  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h2 className="text-lg font-semibold mb-3">Search Logs</h2>
      
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search logs by keywords, tokens, or fields..."
        className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      
      <p className="mt-2 text-sm text-gray-500">
        Examples: "error", "status:500", "user_login"
      </p>
    </div>
  )
}

export default LogSearch
