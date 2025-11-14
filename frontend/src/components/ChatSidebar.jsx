// frontend/src/components/ChatSidebar.jsx
/**
 * Production-Ready Chat Sidebar Component
 * 
 * FIXED (v2):
 * - Uses ES6 imports (not require)
 * - No process.env issues
 * - Safe async handling
 * - Proper error recovery
 */

import React, { useState, useRef, useEffect } from 'react'
import { analyzeLogs } from '../services/api'

function ChatSidebar({ isOpen, onClose, onSuggestedQuery }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '👋 Hi! I\'m your LogWatch AI assistant.\n\nTry asking:\n- "Show me errors from last hour"\n- "What\'s causing warnings?"\n- "Analyze database issues"'
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input when sidebar opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!input.trim()) {
      return
    }

    const userMessage = input.trim()
    setInput('')
    setError(null)
    setLoading(true)

    try {
      console.log('💬 User message:', userMessage)

      // Add user message to chat immediately
      setMessages(prev => [...prev, { role: 'user', content: userMessage }])

      // Call API
      console.log('📤 Sending to API...')
      const result = await analyzeLogs({
        natural_language_query: userMessage,
        time_window_minutes: 60
      })

      console.log('✅ API Response:', result)

      // Add assistant response
      const assistantMessage = result.analysis || 'No analysis available'
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: assistantMessage 
      }])

      // Show suggested queries
      if (result.suggested_queries && result.suggested_queries.length > 0) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: '📌 Try these queries:',
          type: 'separator'
        }])

        result.suggested_queries.slice(0, 3).forEach((query) => {
          setMessages(prev => [...prev, {
            role: 'suggestion',
            content: query,
            type: 'query'
          }])
        })
      }

    } catch (err) {
      console.error('❌ Error:', err)
      const errorMsg = err.message || 'Failed to analyze logs'
      setError(errorMsg)
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ Error: ${errorMsg}\n\nTroubleshooting:\n1. Is backend running? http://localhost:8000\n2. Do logs exist in time range?\n3. Is /api/chat/analyze endpoint available?`
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleSuggestedQueryClick = (query) => {
    console.log('🔍 Using suggested query:', query)
    if (onSuggestedQuery) {
      onSuggestedQuery(query)
    }
  }

  const handleClear = () => {
    console.log('🗑️ Clearing chat')
    setMessages([{
      role: 'assistant',
      content: '👋 Chat cleared! Ask me about your logs.'
    }])
    setInput('')
    setError(null)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-40 lg:hidden">
      {/* Overlay */}
      <div 
        className="absolute inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Sidebar */}
      <div className="absolute right-0 top-0 bottom-0 w-full sm:w-96 bg-white shadow-2xl flex flex-col overflow-hidden rounded-l-lg">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-blue-700 flex-shrink-0">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <span>🤖</span> AI Assistant
          </h2>
          <button
            onClick={onClose}
            className="text-white hover:bg-white hover:bg-opacity-20 p-2 rounded transition"
            title="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
          {messages.map((message, idx) => {
            // Separator
            if (message.type === 'separator') {
              return (
                <div key={idx} className="flex justify-center">
                  <p className="text-xs text-gray-500 font-medium">{message.content}</p>
                </div>
              )
            }

            // Suggested query
            if (message.type === 'query') {
              return (
                <div key={idx} className="flex justify-center">
                  <button
                    onClick={() => handleSuggestedQueryClick(message.content)}
                    className="max-w-xs px-3 py-2 bg-blue-100 hover:bg-blue-200 text-blue-900 rounded-lg text-xs font-mono border border-blue-300 transition truncate"
                    title={message.content}
                  >
                    → {message.content}
                  </button>
                </div>
              )
            }

            // Regular message
            return (
              <div 
                key={idx} 
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-xs px-4 py-3 rounded-lg text-sm leading-relaxed whitespace-pre-wrap break-words ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-none'
                      : 'bg-white text-gray-900 border border-gray-200 rounded-bl-none'
                  }`}
                >
                  {message.content}
                </div>
              </div>
            )
          })}

          {/* Loading */}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 px-4 py-3 rounded-lg rounded-bl-none">
                <div className="flex items-center gap-2 text-sm">
                  <div className="animate-spin">⏳</div>
                  <span className="text-gray-600">Analyzing...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Error Alert */}
        {error && (
          <div className="px-4 py-2 bg-red-50 border-t border-red-200 flex-shrink-0">
            <p className="text-xs text-red-700">⚠️ {error}</p>
          </div>
        )}

        {/* Input */}
        <form 
          onSubmit={handleSubmit} 
          className="border-t border-gray-200 p-4 bg-white space-y-2 flex-shrink-0"
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSubmit(e)
              }
            }}
            placeholder="Ask about your logs... (Shift+Enter for new line)"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 outline-none text-sm"
            rows="3"
            disabled={loading}
          />
          
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition text-sm font-medium"
            >
              {loading ? '⏳ Sending...' : '📤 Send'}
            </button>
            
            <button
              type="button"
              onClick={handleClear}
              disabled={loading}
              className="px-3 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:bg-gray-100 transition text-sm"
              title="Clear"
            >
              🗑️
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default ChatSidebar
