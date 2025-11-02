import React, { useState, useEffect, useRef } from 'react'
import TimeRangePicker from './TimeRangePicker'
import LogViewer from './LogViewer'
import SearchBar from './SearchBar'
import Charts from './Charts'
import ChatSidebar from './ChatSidebar'
import { fetchLogs, searchLogs, fetchAggregations } from '../services/api'

function Dashboard() {
  const [timeRange, setTimeRange] = useState({
    start: new Date(Date.now() - 3600000),
    end: new Date()
  })
  const [logs, setLogs] = useState([])
  const [aggregations, setAggregations] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [chatOpen, setChatOpen] = useState(false)
  
  const searchTimeoutRef = useRef(null)

  // Load data when time range or page changes
  useEffect(() => {
    if (searchQuery) {
      loadSearchData()
    } else {
      loadDefaultData()
    }
  }, [timeRange, page]) // When page or time changes, reload

  // Debounced search when searchQuery changes
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    if (searchQuery) {
      // Debounce search
      searchTimeoutRef.current = setTimeout(() => {
        loadSearchData()
      }, 500)
    } else {
      // If search cleared, load default immediately
      loadDefaultData()
    }

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [searchQuery]) // Only when search query changes

  const loadDefaultData = async () => {
    setLoading(true)
    try {
      console.log('📥 Loading default (GET /api/logs):', { page, timeRange })
      
      const logsData = await fetchLogs({
        start_time: timeRange.start.toISOString(),
        end_time: timeRange.end.toISOString(),
        page,
        page_size: 50
      })
      
      setLogs(logsData.logs)
      setTotal(logsData.total)

      const aggsData = await fetchAggregations({
        start_time: timeRange.start.toISOString(),
        end_time: timeRange.end.toISOString(),
        interval: '1h'
      })
      
      setAggregations(aggsData)
    } catch (error) {
      console.error('❌ Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadSearchData = async () => {
    setLoading(true)
    try {
      console.log('🔍 Searching (POST /api/logs/search):', { query: searchQuery, page, timeRange })
      
      const logsData = await searchLogs({
        start_time: timeRange.start.toISOString(),
        end_time: timeRange.end.toISOString(),
        query: searchQuery,
        page,
        page_size: 50
      })
      
      setLogs(logsData.logs)
      setTotal(logsData.total)

      const aggsData = await fetchAggregations({
        start_time: timeRange.start.toISOString(),
        end_time: timeRange.end.toISOString(),
        interval: '1h'
      })
      
      setAggregations(aggsData)
    } catch (error) {
      console.error('❌ Error searching logs:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (query) => {
    setSearchQuery(query)
    setPage(1) // Reset to page 1 when search changes
  }

  const handleTimeClick = (timestamp) => {
    const clickedTime = new Date(timestamp)
    setTimeRange({
      start: new Date(clickedTime.getTime() - 300000),
      end: new Date(clickedTime.getTime() + 300000)
    })
    setPage(1)
  }

  const handleSuggestedQuery = (query) => {
    setSearchQuery(query)
    setChatOpen(false)
    setPage(1)
  }

  const handlePageChange = (newPage) => {
    console.log('📄 Page changed:', newPage)
    setPage(newPage)
  }

  return (
    <div className="space-y-6 relative">
      {/* AI Chat Button */}
      <button
        onClick={() => setChatOpen(!chatOpen)}
        className="fixed bottom-6 right-6 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition z-40"
        title="Open AI Assistant"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
      </button>

      {/* Chat Sidebar */}
      <ChatSidebar 
        isOpen={chatOpen} 
        onClose={() => setChatOpen(false)}
        onSuggestedQuery={handleSuggestedQuery}
      />

      <TimeRangePicker timeRange={timeRange} onChange={setTimeRange} />
      
      <SearchBar onSearch={handleSearch} loading={loading} />

      {aggregations && (
        <Charts data={aggregations} onTimeClick={handleTimeClick} />
      )}

      <LogViewer 
        logs={logs} 
        loading={loading} 
        page={page}
        total={total}
        onPageChange={handlePageChange}
      />
    </div>
  )
}

export default Dashboard
