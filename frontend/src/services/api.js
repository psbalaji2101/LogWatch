import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add auth token if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const fetchLogs = async (params) => {
  const response = await api.get('/api/logs', { params })
  return response.data
}

export const searchLogs = async (data) => {
  const response = await api.post('/api/logs/search', data)
  return response.data
}

export const fetchAggregations = async (params) => {
  const response = await api.get('/api/logs/aggregations', { params })
  return response.data
}

export const login = async (username, password) => {
  const formData = new FormData()
  formData.append('username', username)
  formData.append('password', password)
  
  const response = await api.post('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  })
  
  return response.data
}
