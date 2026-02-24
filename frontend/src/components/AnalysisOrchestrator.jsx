import React, { useState, useEffect } from 'react'
import axios from 'axios'

function AnalysisOrchestrator() {
  const [loading, setLoading] = useState(false)
  const [aggregationData, setAggregationData] = useState(null)
  const [chunks, setChunks] = useState([])
  const [timeRange, setTimeRange] = useState({
    start: new Date(Date.now() - 3600000),
    end: new Date()
  })

  const runAggregationAnalysis = async () => {
    setLoading(true)
    try {
      const response = await axios.post(
        'http://localhost:8000/api/orchestration/analyze-aggregated',
        {
          start_time: timeRange.start.toISOString(),
          end_time: timeRange.end.toISOString(),
          top_k: 10
        }
      )

      setAggregationData(response.data)
      console.log('Aggregation complete:', response.data)

      // Optionally create chunks from priority queries
      if (response.data.priority_queries.length > 0) {
        await createChunks(response.data.priority_queries)
      }
    } catch (error) {
      console.error('Aggregation failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const createChunks = async (priorityQueries) => {
    try {
      const chunkPromises = priorityQueries.slice(0, 3).map(query =>
        axios.post(
          'http://localhost:8000/api/orchestration/summarize-chunk',
          {
            query_filter: query,
            start_time: timeRange.start.toISOString(),
            end_time: timeRange.end.toISOString()
          }
        )
      )

      const results = await Promise.all(chunkPromises)
      setChunks(results.map(r => r.data))
    } catch (error) {
      console.error('Chunk summarization failed:', error)
    }
  }

  const retrieveSummaries = async (userQuery) => {
    try {
      const response = await axios.post(
        'http://localhost:8000/api/orchestration/retrieve-summaries',
        {
          query: userQuery,
          top_k: 5,
          start_time: timeRange.start.toISOString(),
          end_time: timeRange.end.toISOString()
        }
      )

      console.log('Retrieved summaries:', response.data)
      return response.data.summaries
    } catch (error) {
      console.error('Summary retrieval failed:', error)
      return []
    }
  }

  return (
    <div className="space-y-6 p-6">
      <h2 className="text-2xl font-bold">Orchestrated Analysis</h2>

      {/* Time Range Selection */}
      <div className="bg-white rounded-lg shadow p-4">
        <label className="block text-sm font-medium mb-2">Time Range</label>
        <div className="flex gap-4">
          <input
            type="datetime-local"
            value={timeRange.start.toISOString().slice(0, 16)}
            onChange={(e) => setTimeRange({
              ...timeRange,
              start: new Date(e.target.value)
            })}
            className="px-3 py-2 border rounded"
          />
          <input
            type="datetime-local"
            value={timeRange.end.toISOString().slice(0, 16)}
            onChange={(e) => setTimeRange({
              ...timeRange,
              end: new Date(e.target.value)
            })}
            className="px-3 py-2 border rounded"
          />
          <button
            onClick={runAggregationAnalysis}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Analyzing...' : 'Run Analysis'}
          </button>
        </div>
      </div>

      {/* Aggregation Results */}
      {aggregationData && (
        <div className="bg-white rounded-lg shadow p-4 space-y-4">
          <h3 className="text-lg font-semibold">Aggregation Results</h3>

          <div className="grid grid-cols-3 gap-4">
            <div className="bg-gray-50 p-3 rounded">
              <p className="text-sm text-gray-600">Total Logs</p>
              <p className="text-2xl font-bold">{aggregationData.total_logs}</p>
            </div>
            <div className="bg-red-50 p-3 rounded">
              <p className="text-sm text-gray-600">Error Rate</p>
              <p className="text-2xl font-bold text-red-600">{(aggregationData.error_rate * 100).toFixed(1)}%</p>
            </div>
            <div className="bg-yellow-50 p-3 rounded">
              <p className="text-sm text-gray-600">Warning Rate</p>
              <p className="text-2xl font-bold text-yellow-600">{(aggregationData.warning_rate * 100).toFixed(1)}%</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="font-semibold mb-2">Top Services</h4>
              <ul className="space-y-1">
                {aggregationData.top_services.slice(0, 5).map(([service, count]) => (
                  <li key={service} className="text-sm">
                    {service}: <span className="font-mono">{count}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-2">Priority Queries</h4>
              <ul className="space-y-1">
                {aggregationData.priority_queries.map((query, i) => (
                  <li key={i} className="text-sm bg-gray-100 p-2 rounded font-mono break-words">
                    {query.substring(0, 50)}...
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Chunk Summaries */}
      {chunks.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4 space-y-4">
          <h3 className="text-lg font-semibold">Chunk Summaries</h3>
          {chunks.map((chunk) => (
            <div key={chunk.chunk_id} className="border rounded p-3 bg-gray-50">
              <p className="font-mono text-xs text-gray-600">{chunk.chunk_id}</p>
              <p className="text-sm mt-1">{chunk.summary_text}</p>
              <div className="mt-2 flex gap-2 text-xs">
                <span className="bg-red-200 text-red-800 px-2 py-1 rounded">
                  Errors: {chunk.error_count}
                </span>
                <span className="bg-yellow-200 text-yellow-800 px-2 py-1 rounded">
                  Warnings: {chunk.warning_count}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default AnalysisOrchestrator