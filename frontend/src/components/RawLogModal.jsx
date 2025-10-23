import React from 'react'
import { formatDate } from '../utils/formatters'

function RawLogModal({ log, onClose }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] overflow-hidden">
        <div className="p-4 border-b flex justify-between items-center">
          <h3 className="text-lg font-semibold">Log Details</h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
          <div className="space-y-4">
            <div>
              <label className="text-sm font-semibold text-gray-700">Timestamp</label>
              <div className="mt-1 text-sm">{formatDate(new Date(log.timestamp))}</div>
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-700">Source File</label>
              <div className="mt-1 text-sm">{log.source_file}</div>
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-700">Line Number</label>
              <div className="mt-1 text-sm">{log.line_number}</div>
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-700">Raw Log Line</label>
              <pre className="mt-1 p-3 bg-gray-100 rounded text-sm overflow-x-auto">
                {log.raw_line}
              </pre>
            </div>

            {Object.keys(log.fields).length > 0 && (
              <div>
                <label className="text-sm font-semibold text-gray-700">Parsed Fields</label>
                <div className="mt-1 bg-gray-50 p-3 rounded">
                  <table className="w-full text-sm">
                    <tbody>
                      {Object.entries(log.fields).map(([key, value]) => (
                        <tr key={key} className="border-b last:border-0">
                          <td className="py-2 pr-4 font-semibold text-gray-600">{key}</td>
                          <td className="py-2">{String(value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {log.tokens && log.tokens.length > 0 && (
              <div>
                <label className="text-sm font-semibold text-gray-700">Tokens</label>
                <div className="mt-1 flex flex-wrap gap-2">
                  {log.tokens.map((token, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs"
                    >
                      {token}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default RawLogModal
