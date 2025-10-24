import React, { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
// import { analyzeLogschatFeedback } from '../services/api'
import { analyzeLogs, chatFeedback } from '../services/api'

import ChatTimeline from './ChatTimeline'

function ChatSidebar({ isOpen, onClose, onSuggestedQuery }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(scrollToBottom, [messages])

  const handleQuickAction = async (action) => {
    const prompts = {
      'last-30min': { keywords: '', timeWindow: 30 },
      'errors': { keywords: 'ERROR', timeWindow: 60 },
      'warnings': { keywords: 'WARNING', timeWindow: 60 },
      'critical': { keywords: 'CRITICAL OR FATAL', timeWindow: 120 }
    }

    const config = prompts[action]
    if (config) {
      await analyzeWithConfig(config.keywords, config.timeWindow)
    }
  }

  const analyzeWithConfig = async (keywords, timeWindow) => {
    const userMessage = {
      role: 'user',
      content: keywords 
        ? `Analyze logs with keywords: "${keywords}" from last ${timeWindow} minutes`
        : `Analyze logs from last ${timeWindow} minutes`,
      timestamp: new Date().toISOString(),
      id: Date.now()
    }

    setMessages(prev => [...prev, userMessage])
    setLoading(true)

    try {
      // Build chat history for context
      const chatHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }))

      const response = await analyzeLogs({
        keywords: keywords || undefined,
        time_window_minutes: timeWindow,
        chat_history: chatHistory
      })

      const assistantMessage = {
        role: 'assistant',
        content: response.analysis,
        timestamp: response.timestamp,
        summary: response.summary,
        suggested_queries: response.suggested_queries,
        chart_data: response.chart_data,
        id: Date.now() + 1
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Analysis error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error.message}`,
        timestamp: new Date().toISOString(),
        id: Date.now() + 1,
        error: true
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    // Parse natural language for keywords and time
    const timeMatch = input.match(/(\d+)\s*(min|minutes|hour|hours|h)/i)
    const timeWindow = timeMatch 
      ? (timeMatch[2].startsWith('h') ? parseInt(timeMatch[1]) * 60 : parseInt(timeMatch[1]))
      : 30

    await analyzeWithConfig(input, timeWindow)
    setInput('')
  }

  const handleFeedback = async (messageId, rating) => {
    try {
      await chatFeedback({ message_id: messageId.toString(), rating })
      
      // Update message with feedback
      setMessages(prev => prev.map(msg => 
        msg.id === messageId ? { ...msg, userFeedback: rating } : msg
      ))
    } catch (error) {
      console.error('Feedback error:', error)
    }
  }

  const handleQueryClick = (query) => {
    if (onSuggestedQuery) {
      onSuggestedQuery(query)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-2xl z-50 flex flex-col">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 flex justify-between items-center">
        <div>
          <h2 className="text-lg font-bold">AI Log Assistant</h2>
          <p className="text-xs opacity-90">Powered by Llama 3</p>
        </div>
        <button
          onClick={onClose}
          className="text-white hover:bg-blue-800 rounded-full p-2 transition"
        >
          ✕
        </button>
      </div>

      {/* Quick Actions */}
      <div className="p-3 border-b bg-gray-50">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => handleQuickAction('last-30min')}
            className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm hover:bg-blue-200 transition"
            disabled={loading}
          >
            Last 30 min
          </button>
          <button
            onClick={() => handleQuickAction('errors')}
            className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm hover:bg-red-200 transition"
            disabled={loading}
          >
            Find Errors
          </button>
          <button
            onClick={() => handleQuickAction('warnings')}
            className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full text-sm hover:bg-yellow-200 transition"
            disabled={loading}
          >
            Warnings
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <div className="text-4xl mb-2">💬</div>
            <p className="text-sm">Ask me to analyze your logs!</p>
            <p className="text-xs mt-2">Try: "Analyze logs from last hour"</p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-lg p-3 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : message.error
                  ? 'bg-red-50 border border-red-200'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              {message.role === 'assistant' ? (
                <>
                  {/* AI Response */}
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                  </div>

                  {/* Chart */}
                  {message.chart_data && (
                    <div className="mt-3 pt-3 border-t">
                      <ChatTimeline data={message.chart_data.timeline} />
                    </div>
                  )}

                  {/* Suggested Queries */}
                  {message.suggested_queries && message.suggested_queries.length > 0 && (
                    <div className="mt-3 pt-3 border-t">
                      <p className="text-xs font-semibold mb-2 text-gray-600">Suggested Queries:</p>
                      <div className="space-y-1">
                        {message.suggested_queries.map((query, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleQueryClick(query)}
                            className="block w-full text-left px-2 py-1 bg-white border border-gray-300 rounded text-xs hover:bg-blue-50 hover:border-blue-400 transition font-mono"
                          >
                            {query}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Feedback */}
                  {!message.error && (
                    <div className="mt-3 pt-3 border-t flex justify-end gap-2">
                      <button
                        onClick={() => handleFeedback(message.id, 1)}
                        className={`text-sm ${message.userFeedback === 1 ? 'text-green-600' : 'text-gray-400'} hover:text-green-600 transition`}
                        disabled={message.userFeedback !== undefined}
                      >
                        👍
                      </button>
                      <button
                        onClick={() => handleFeedback(message.id, -1)}
                        className={`text-sm ${message.userFeedback === -1 ? 'text-red-600' : 'text-gray-400'} hover:text-red-600 transition`}
                        disabled={message.userFeedback !== undefined}
                      >
                        👎
                      </button>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm">{message.content}</p>
              )}

              <p className={`text-xs mt-1 ${message.role === 'user' ? 'text-blue-200' : 'text-gray-500'}`}>
                {new Date(message.timestamp).toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-3">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t bg-gray-50">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your logs..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}

export default ChatSidebar
