import React, { useState } from 'react'
import RawLogModal from './RawLogModal'
import { formatDate } from '../utils/formatters'

function LogViewer({ logs, loading, page, total, onPageChange }) {
  const [selectedLog, setSelectedLog] = useState(null)

  const pageSize = 50
  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-4 border-b">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold">Log Events ({total.toLocaleString()})</h2>
          
          {totalPages > 1 && (
            <div className="flex gap-2">
              <button
                onClick={() => onPageChange(page - 1)}
                disabled={page === 1}
                className="px-3 py-1 bg-gray-200 rounded disabled:opacity-50"
              >
                Previous
              </button>
              
              <span className="px-3 py-1">
                Page {page} of {totalPages}
              </span>
              
              <button
                onClick={() => onPageChange(page + 1)}
                disabled={page >= totalPages}
                className="px-3 py-1 bg-gray-200 rounded disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>

      {loading ? (
        <div className="p-8 text-center text-gray-500">Loading logs...</div>
      ) : logs.length === 0 ? (
        <div className="p-8 text-center text-gray-500">No logs found</div>
      ) : (
        <div className="divide-y">
          {logs.map((log, index) => (
            <div
              key={index}
              onClick={() => setSelectedLog(log)}
              className="p-4 hover:bg-gray-50 cursor-pointer transition"
            >
              <div className="flex items-start gap-3">
                <div className="text-xs text-gray-500 min-w-[140px]">
                  {formatDate(new Date(log.timestamp))}
                </div>
                
                <div className="flex-1">
                  <div className="text-sm font-mono text-gray-800 truncate">
                    {log.raw_line}
                  </div>
                  
                  <div className="mt-1 flex gap-2 text-xs text-gray-500">
                    <span className="bg-gray-100 px-2 py-0.5 rounded">
                      {log.source_file.split('/').pop()}
                    </span>
                    
                    {log.fields.level && (
                      <span className={`px-2 py-0.5 rounded ${
                        log.fields.level === 'ERROR' ? 'bg-red-100 text-red-700' :
                        log.fields.level === 'WARN' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-green-100 text-green-700'
                      }`}>
                        {log.fields.level}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedLog && (
        <RawLogModal log={selectedLog} onClose={() => setSelectedLog(null)} />
      )}
    </div>
  )
}

export default LogViewer

