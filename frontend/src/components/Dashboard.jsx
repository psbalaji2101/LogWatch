import React, { useState, useEffect } from 'react'
import TimeRangePicker from './TimeRangePicker'
import LogViewer from './LogViewer'
import LogSearch from './LogSearch'
import Charts from './Charts'
import { fetchLogs, fetchAggregations } from '../services/api'

function Dashboard() {
  const [timeRange, setTimeRange] = useState({
    start: new Date(Date.now() - 3600000), // 1 hour ago
    end: new Date()
  })
  const [logs, setLogs] = useState([])
  const [aggregations, setAggregations] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    loadData()
  }, [timeRange, page, searchQuery])

  const loadData = async () => {
    setLoading(true)
    try {
      // Fetch logs
      const logsData = await fetchLogs({
        start_time: timeRange.start.toISOString(),
        end_time: timeRange.end.toISOString(),
        query: searchQuery || undefined,
        page,
        page_size: 50
      })
      
      setLogs(logsData.logs)
      setTotal(logsData.total)

      // Fetch aggregations
      const aggsData = await fetchAggregations({
        start_time: timeRange.start.toISOString(),
        end_time: timeRange.end.toISOString(),
        interval: '1h'
      })
      
      setAggregations(aggsData)
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleTimeClick = (timestamp) => {
    // When clicking a chart point, narrow time range
    const clickedTime = new Date(timestamp)
    setTimeRange({
      start: new Date(clickedTime.getTime() - 300000), // 5 min before
      end: new Date(clickedTime.getTime() + 300000)   // 5 min after
    })
    setPage(1)
  }

  return (
    <div className="space-y-6">
      {/* Time Range Picker */}
      <TimeRangePicker timeRange={timeRange} onChange={setTimeRange} />

      {/* Search */}
      <LogSearch value={searchQuery} onChange={setSearchQuery} />

      {/* Charts */}
      {aggregations && (
        <Charts data={aggregations} onTimeClick={handleTimeClick} />
      )}

      {/* Log Viewer */}
      <LogViewer 
        logs={logs} 
        loading={loading} 
        page={page}
        total={total}
        onPageChange={setPage}
      />
    </div>
  )
}

export default Dashboard
