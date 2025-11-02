import React, { useState } from 'react'

function SearchBar({ onSearch, loading }) {
  const [query, setQuery] = useState('')

  const handleChange = (e) => {
    const value = e.target.value
    setQuery(value)
    // Trigger search through parent (will be debounced)
    onSearch(value)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    // Trigger immediate search
    onSearch(query)
  }

  const handleClear = () => {
    setQuery('')
    onSearch('')
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h2 className="text-lg font-semibold mb-3">Search Logs</h2>
      
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={handleChange}
          placeholder="Search logs by keywords, tokens, or fields..."
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={loading}
        />
        
        <button
          type="submit"
          disabled={loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition font-medium"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
        
        {query && (
          <button
            type="button"
            onClick={handleClear}
            disabled={loading}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:opacity-50 transition"
          >
            Clear
          </button>
        )}
      </form>
      
      <p className="text-xs text-gray-500 mt-2">
        Examples: "error", "status:500", "user_login", "Database timeout"
      </p>
    </div>
  )
}

export default SearchBar
