// frontend/src/services/api.js
/**
 * Complete API service layer for LogWatch
 * 
 * FIXED:
 * - Uses ES6 imports/exports (not CommonJS require)
 * - Handles process.env correctly
 * - Works in React environment
 */

import axios from 'axios'

// Safe environment variable access
const API_BASE_URL = (() => {
  if (typeof process !== 'undefined' && process.env?.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL
  }
  return 'http://localhost:8000'
})()

console.log('🔧 API Base URL:', API_BASE_URL)

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add auth token interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => {
  return Promise.reject(error)
})

// Add error handling interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('❌ API Error:', {
      status: error.response?.status,
      message: error.response?.data?.detail || error.message,
      endpoint: error.config?.url
    })
    return Promise.reject(error)
  }
)


// ============ LOG ENDPOINTS ============

export const fetchLogs = async (params) => {
  try {
    const response = await api.get('/api/logs', { params })
    return response.data
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to fetch logs')
  }
}

export const searchLogs = async (data) => {
  try {
    const response = await api.post('/api/logs/search', data)
    return response.data
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to search logs')
  }
}

export const fetchAggregations = async (params) => {
  try {
    const response = await api.get('/api/logs/aggregations', { params })
    return response.data
  } catch (error) {
    console.warn('⚠️ Aggregations not available:', error.message)
    return null
  }
}


// ============ CHAT & ANALYSIS ENDPOINTS ============

/**
 * Analyze logs with natural language query
 * POST /api/chat/analyze
 */
export const analyzeLogs = async (data) => {
  try {
    console.log('🚀 [API] POST /api/chat/analyze', data)
    const response = await api.post('/api/chat/analyze', data)
    return response.data
  } catch (error) {
    const message = error.response?.data?.detail || error.message || 'Analysis failed'
    console.error('❌ [API] Analysis failed:', message)
    throw new Error(message)
  }
}

export const sendChatMessage = async (message, chatHistory) => {
  try {
    console.log('🚀 [API] POST /api/chat')
    const response = await api.post('/api/chat', {
      message,
      chat_history: chatHistory
    })
    return response.data
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Chat failed')
  }
}

export const analyzeWithNaturalLanguage = async (query, timeWindowMinutes = 30) => {
  try {
    console.log('🚀 [API] POST /api/chat/analyze (natural language)')
    const response = await api.post('/api/chat/analyze', {
      natural_language_query: query,
      time_window_minutes: timeWindowMinutes
    })
    return response.data
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Analysis failed')
  }
}


// ============ AGGREGATION-FIRST ANALYSIS (Option A) ============

export const analyzeWithAggregation = async (data) => {
  try {
    console.log('🚀 [API] POST /api/orchestration/analyze-aggregated')
    const response = await api.post('/api/orchestration/analyze-aggregated', data)
    return response.data
  } catch (error) {
    const message = error.response?.data?.detail || error.message || 'Aggregation analysis failed'
    console.error('❌ [API] Aggregation failed:', message)
    throw new Error(message)
  }
}


// ============ CHUNK SUMMARIZATION (Option B) ============

export const summarizeChunk = async (data) => {
  try {
    console.log('🚀 [API] POST /api/orchestration/summarize-chunk')
    const response = await api.post('/api/orchestration/summarize-chunk', data)
    return response.data
  } catch (error) {
    const message = error.response?.data?.detail || error.message || 'Chunk summarization failed'
    console.error('❌ [API] Summarization failed:', message)
    throw new Error(message)
  }
}

export const getChunkStatus = async (chunkId) => {
  try {
    console.log(`🚀 [API] GET /api/orchestration/chunk-status/${chunkId}`)
    const response = await api.get(`/api/orchestration/chunk-status/${chunkId}`)
    return response.data
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to get chunk status')
  }
}


// ============ RAG RETRIEVAL ============

export const retrieveSummaries = async (data) => {
  try {
    console.log('🚀 [API] POST /api/orchestration/retrieve-summaries')
    const response = await api.post('/api/orchestration/retrieve-summaries', data)
    return response.data
  } catch (error) {
    const message = error.response?.data?.detail || error.message || 'Summary retrieval failed'
    console.error('❌ [API] Retrieval failed:', message)
    throw new Error(message)
  }
}


// ============ UTILITY FUNCTIONS ============

export const formatTimestamp = (iso) => {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

export const formatNumber = (num) => {
  return num.toLocaleString()
}

export const formatPercent = (decimal) => {
  return `${(decimal * 100).toFixed(1)}%`
}

export const truncate = (str, maxLen = 80) => {
  return str.length > maxLen ? str.substring(0, maxLen) + '...' : str
}