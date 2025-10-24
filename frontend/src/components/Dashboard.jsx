// import React, { useState, useEffect } from 'react'
// import TimeRangePicker from './TimeRangePicker'
// import LogViewer from './LogViewer'
// import LogSearch from './LogSearch'
// import Charts from './Charts'
// import { fetchLogs, fetchAggregations } from '../services/api'

// function Dashboard() {
//   const [timeRange, setTimeRange] = useState({
//     start: new Date(Date.now() - 3600000), // 1 hour ago
//     end: new Date()
//   })
//   const [logs, setLogs] = useState([])
//   const [aggregations, setAggregations] = useState(null)
//   const [loading, setLoading] = useState(false)
//   const [searchQuery, setSearchQuery] = useState('')
//   const [page, setPage] = useState(1)
//   const [total, setTotal] = useState(0)

//   useEffect(() => {
//     loadData()
//   }, [timeRange, page, searchQuery])

//   const loadData = async () => {
//     setLoading(true)
//     try {
//       // Fetch logs
//       const logsData = await fetchLogs({
//         start_time: timeRange.start.toISOString(),
//         end_time: timeRange.end.toISOString(),
//         query: searchQuery || undefined,
//         page,
//         page_size: 50
//       })
      
//       setLogs(logsData.logs)
//       setTotal(logsData.total)

//       // Fetch aggregations
//       const aggsData = await fetchAggregations({
//         start_time: timeRange.start.toISOString(),
//         end_time: timeRange.end.toISOString(),
//         interval: '1h'
//       })
      
//       setAggregations(aggsData)
//     } catch (error) {
//       console.error('Error loading data:', error)
//     } finally {
//       setLoading(false)
//     }
//   }

//   const handleTimeClick = (timestamp) => {
//     // When clicking a chart point, narrow time range
//     const clickedTime = new Date(timestamp)
//     setTimeRange({
//       start: new Date(clickedTime.getTime() - 300000), // 5 min before
//       end: new Date(clickedTime.getTime() + 300000)   // 5 min after
//     })
//     setPage(1)
//   }

//   return (
//     <div className="space-y-6">
//       {/* Time Range Picker */}
//       <TimeRangePicker timeRange={timeRange} onChange={setTimeRange} />

//       {/* Search */}
//       <LogSearch value={searchQuery} onChange={setSearchQuery} />

//       {/* Charts */}
//       {aggregations && (
//         <Charts data={aggregations} onTimeClick={handleTimeClick} />
//       )}

//       {/* Log Viewer */}
//       <LogViewer 
//         logs={logs} 
//         loading={loading} 
//         page={page}
//         total={total}
//         onPageChange={setPage}
//       />
//     </div>
//   )
// }

// export default Dashboard
import React, { useState, useEffect } from 'react'
import TimeRangePicker from './TimeRangePicker'
import LogViewer from './LogViewer'
import LogSearch from './LogSearch'
import Charts from './Charts'
import ChatSidebar from './ChatSidebar'
import { fetchLogs, fetchAggregations } from '../services/api'

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

  useEffect(() => {
    loadData()
  }, [timeRange, page, searchQuery])

  const loadData = async () => {
    setLoading(true)
    try {
      const logsData = await fetchLogs({
        start_time: timeRange.start.toISOString(),
        end_time: timeRange.end.toISOString(),
        query: searchQuery || undefined,
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
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
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
      <LogSearch value={searchQuery} onChange={setSearchQuery} />

      {aggregations && (
        <Charts data={aggregations} onTimeClick={handleTimeClick} />
      )}

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


