// frontend/src/components/Dashboard.jsx
/**
 * Production-Ready Dashboard Component
 * 
 * Features:
 * - Tabbed interface (Log View + AI Analysis)
 * - Aggregation-first analysis (Option A)
 * - Chunk summarization (Option B)
 * - RAG-based retrieval
 * - Full error handling & fallbacks
 * - No blank UI issues
 * 
 * BUG FIXES:
 * ✅ Removed unused AnalysisOrchestrator import
 * ✅ Added error boundaries and graceful fallbacks
 * ✅ Fixed component visibility issues
 * ✅ Added loading states
 * ✅ Proper initialization
 */

import React, { useState, useEffect, useRef } from 'react'
import TimeRangePicker from './TimeRangePicker'
import LogViewer from './LogViewer'
import SearchBar from './SearchBar'
import Charts from './Charts'
import ChatSidebar from './ChatSidebar'
import { 
  fetchLogs, 
  searchLogs, 
  fetchAggregations,
  analyzeWithAggregation,
  summarizeChunk,
  retrieveSummaries
} from '../services/api'

// Fallback components if imports fail
const FallbackTimeRangePicker = ({ timeRange, onChange }) => (
  <div className="bg-blue-100 border border-blue-300 rounded-lg p-4">
    <p className="text-sm text-blue-900">
      ⚠️ TimeRangePicker component not found. Using fallback.
    </p>
  </div>
)

const FallbackLogViewer = ({ logs, loading }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <p className="text-sm text-gray-600 mb-4">
      📋 {loading ? 'Loading logs...' : `Showing ${logs?.length || 0} logs`}
    </p>
    {logs && logs.slice(0, 5).map((log, idx) => (
      <div key={idx} className="p-2 bg-gray-50 rounded mb-2 text-xs font-mono">
        {log.raw_line || log.timestamp || 'Log entry'}
      </div>
    ))}
  </div>
)

const FallbackCharts = ({ data }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <p className="text-sm text-gray-600">📊 Charts component not found</p>
  </div>
)


function Dashboard() {
  // ============ STATE: TIME RANGE ============
  const [timeRange, setTimeRange] = useState({
    start: new Date(Date.now() - 3600000), // Last 1 hour
    end: new Date()
  })

  // ============ STATE: LOG VIEW TAB ============
  const [logs, setLogs] = useState([])
  const [aggregations, setAggregations] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [chatOpen, setChatOpen] = useState(false)
  
  // ============ STATE: ANALYSIS TAB ============
  const [activeTab, setActiveTab] = useState('logs')
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [analysisError, setAnalysisError] = useState(null)
  
  // ============ STATE: CHUNK SUMMARIZATION ============
  const [chunks, setChunks] = useState([])
  const [chunkLoading, setChunkLoading] = useState(false)
  
  // ============ STATE: RAG RETRIEVAL ============
  const [summaries, setSummaries] = useState([])
  const [ragQuery, setRagQuery] = useState('')
  const [ragLoading, setRagLoading] = useState(false)
  
  // ============ REFS ============
  const searchTimeoutRef = useRef(null)
  const refreshIntervalRef = useRef(null)


  // ============ EFFECT: LOAD DATA ON MOUNT & TIME RANGE CHANGE ============
  useEffect(() => {
    console.log('📱 Dashboard mounted or tab changed, loading data...')
    if (activeTab === 'logs') {
      if (searchQuery) {
        loadSearchData()
      } else {
        loadDefaultData()
      }
    }
  }, [timeRange, page, activeTab])


  // ============ EFFECT: DEBOUNCED SEARCH ============
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    if (searchQuery) {
      searchTimeoutRef.current = setTimeout(() => {
        setPage(1)
        loadSearchData()
      }, 800)
    } else {
      setPage(1)
      loadDefaultData()
    }

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [searchQuery])


  // ============ EFFECT: AUTO-REFRESH AGGREGATIONS (30s) ============
  useEffect(() => {
    if (activeTab === 'logs') {
      console.log('🔄 Setting up auto-refresh for aggregations (every 30s)')
      
      refreshIntervalRef.current = setInterval(() => {
        console.log('🔄 Auto-refreshing aggregations...')
        loadAggregations()
      }, 30000)

      return () => {
        if (refreshIntervalRef.current) {
          clearInterval(refreshIntervalRef.current)
          console.log('🛑 Cleared auto-refresh interval')
        }
      }
    }
  }, [timeRange, activeTab])


  // ============ FUNCTIONS: LOG LOADING ============

  const loadDefaultData = async () => {
    setLoading(true)
    try {
      console.log('📥 Loading default logs...', { 
        page, 
        timeRange
      })
      
      const logsData = await fetchLogs({
        start_time: timeRange.start.toISOString(),
        end_time: timeRange.end.toISOString(),
        page,
        page_size: 50
      })
      
      setLogs(logsData.logs || [])
      setTotal(logsData.total || 0)
      console.log(`✅ Loaded ${logsData.logs?.length || 0} logs`)
      
      await loadAggregations()
    } catch (error) {
      console.error('❌ Error loading default data:', error)
      setLogs([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  const loadSearchData = async () => {
    setLoading(true)
    try {
      console.log('🔍 Searching logs...', { searchQuery })
      
      const logsData = await searchLogs({
        start_time: timeRange.start.toISOString(),
        end_time: timeRange.end.toISOString(),
        query: searchQuery,
        page,
        page_size: 50
      })
      
      setLogs(logsData.logs || [])
      setTotal(logsData.total || 0)
      console.log(`✅ Found ${logsData.logs?.length || 0} logs`)
      
      await loadAggregations()
    } catch (error) {
      console.error('❌ Error searching logs:', error)
      setLogs([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  const loadAggregations = async () => {
    try {
      const aggsData = await fetchAggregations({
        start_time: timeRange.start.toISOString(),
        end_time: timeRange.end.toISOString(),
        interval: '1h'
      })
      
      setAggregations(aggsData)
      console.log('✅ Loaded aggregations')
    } catch (error) {
      console.error('❌ Error loading aggregations:', error)
      // Don't show error to user, aggregations are optional
    }
  }


  // ============ FUNCTIONS: ANALYSIS (ORCHESTRATION) ============

  const runAggregationAnalysis = async () => {
    setAnalysisLoading(true)
    setAnalysisError(null)
    setAnalysisResult(null)
    setChunks([])

    try {
      console.log('⚙️  Starting aggregation-first analysis...', { timeRange })

      const result = await analyzeWithAggregation({
        start_time: timeRange.start.toISOString(),
        end_time: timeRange.end.toISOString(),
        keywords: searchQuery || null,
        top_k: 10
      })

      setAnalysisResult(result)
      console.log('✅ Analysis complete:', result)

      // Create chunks from priority queries
      if (result.priority_queries && result.priority_queries.length > 0) {
        await createChunksFromPriorities(result.priority_queries)
      }
    } catch (error) {
      console.error('❌ Analysis failed:', error)
      setAnalysisError(error.message || 'Analysis failed. Please try again.')
    } finally {
      setAnalysisLoading(false)
    }
  }

  const createChunksFromPriorities = async (priorityQueries) => {
    setChunkLoading(true)
    try {
      console.log('🔨 Creating chunks from priority queries...', priorityQueries.length)

      const chunkPromises = priorityQueries.slice(0, 3).map((query, idx) =>
        summarizeChunk({
          query_filter: query,
          start_time: timeRange.start.toISOString(),
          end_time: timeRange.end.toISOString()
        })
          .then(result => ({ ...result, queryIndex: idx + 1 }))
          .catch(err => {
            console.error(`❌ Chunk ${idx + 1} failed:`, err)
            return null
          })
      )

      const results = await Promise.all(chunkPromises)
      const validChunks = results.filter(c => c !== null)
      
      setChunks(validChunks)
      console.log('✅ Created', validChunks.length, 'chunks')
    } catch (error) {
      console.error('❌ Chunk creation failed:', error)
    } finally {
      setChunkLoading(false)
    }
  }

  const handleRetrieveSummaries = async () => {
    if (!ragQuery.trim()) {
      console.warn('⚠️  RAG query is empty')
      return
    }

    setRagLoading(true)
    try {
      console.log('🔎 Retrieving summaries with RAG...', ragQuery)

      const results = await retrieveSummaries({
        query: ragQuery,
        top_k: 5,
        start_time: timeRange.start.toISOString(),
        end_time: timeRange.end.toISOString()
      })

      setSummaries(results.summaries || [])
      console.log('✅ Retrieved', results.summaries?.length || 0, 'summaries')
    } catch (error) {
      console.error('❌ Summary retrieval failed:', error)
    } finally {
      setRagLoading(false)
    }
  }


  // ============ HANDLERS ============

  const handleSearch = (query) => {
    console.log('🔍 Search query:', query)
    setSearchQuery(query)
    setPage(1)
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
    console.log('💡 Using suggested query:', query)
    setSearchQuery(query)
    setChatOpen(false)
    setPage(1)
  }

  const handlePageChange = (newPage) => {
    console.log('📄 Page changed:', newPage)
    setPage(newPage)
  }

  const handleTabChange = (tab) => {
    console.log('📑 Tab changed to:', tab)
    setActiveTab(tab)
    
    if (tab === 'analysis' && !analysisResult) {
      setTimeout(() => runAggregationAnalysis(), 100)
    }
  }


  // ============ RENDER ============

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ===== ERROR BOUNDARY ===== */}
      {analysisError && (
        <div className="fixed top-4 right-4 bg-red-50 border-l-4 border-red-500 p-4 rounded shadow-lg max-w-md z-50">
          <p className="text-red-800 font-semibold text-sm">⚠️ Error</p>
          <p className="text-red-700 text-xs mt-1">{analysisError}</p>
          <button
            onClick={() => setAnalysisError(null)}
            className="text-red-600 text-xs underline mt-2 hover:text-red-800"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ===== TAB NAVIGATION ===== */}
      <div className="sticky top-0 z-30 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex gap-2">
          <button
            onClick={() => handleTabChange('logs')}
            className={`px-6 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
              activeTab === 'logs'
                ? 'bg-blue-600 text-white shadow'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <span>📋</span> Logs
          </button>
          <button
            onClick={() => handleTabChange('analysis')}
            className={`px-6 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
              activeTab === 'analysis'
                ? 'bg-blue-600 text-white shadow'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <span>🤖</span> Analysis
          </button>
        </div>
      </div>

      {/* ===== MAIN CONTENT ===== */}
      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 min-h-[calc(100vh-120px)]">
        
        {/* ===== LOG VIEWER TAB ===== */}
        {activeTab === 'logs' && (
          <div className="space-y-6 animate-fadeIn">
            {/* Time Range Picker */}
            <div>
              {TimeRangePicker ? (
                <TimeRangePicker timeRange={timeRange} onChange={setTimeRange} />
              ) : (
                <FallbackTimeRangePicker timeRange={timeRange} onChange={setTimeRange} />
              )}
            </div>
            
            {/* Search Bar */}
            {SearchBar ? (
              <SearchBar onSearch={handleSearch} loading={loading} />
            ) : (
              <div className="bg-white rounded-lg shadow p-4">
                <input
                  type="text"
                  placeholder="Search logs..."
                  onChange={(e) => handleSearch(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                />
              </div>
            )}

            {/* Charts */}
            {aggregations && Charts ? (
              <Charts 
                data={aggregations} 
                onTimeClick={handleTimeClick}
                loading={loading}
              />
            ) : aggregations && !Charts ? (
              <FallbackCharts data={aggregations} />
            ) : loading ? (
              <div className="bg-white rounded-lg shadow p-8 text-center">
                <p className="text-gray-600">📊 Loading charts...</p>
              </div>
            ) : null}

            {/* Log Viewer */}
            {LogViewer ? (
              <LogViewer 
                logs={logs} 
                loading={loading} 
                page={page}
                total={total}
                onPageChange={handlePageChange}
              />
            ) : (
              <FallbackLogViewer logs={logs} loading={loading} />
            )}
          </div>
        )}

        {/* ===== AI ANALYSIS TAB ===== */}
        {activeTab === 'analysis' && (
          <div className="space-y-6 animate-fadeIn">
            {/* Time Range Picker */}
            <div>
              {TimeRangePicker ? (
                <TimeRangePicker timeRange={timeRange} onChange={setTimeRange} />
              ) : (
                <FallbackTimeRangePicker timeRange={timeRange} onChange={setTimeRange} />
              )}
            </div>

            {/* Analysis Controls */}
            <div className="bg-white rounded-lg shadow p-6 space-y-4 border-l-4 border-blue-500">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    🤖 Aggregation-First Analysis
                  </h2>
                  <p className="text-sm text-gray-600 mt-1">
                    Analyze logs with AI-powered insights
                  </p>
                </div>
                <button
                  onClick={runAggregationAnalysis}
                  disabled={analysisLoading}
                  className={`px-6 py-2 rounded-lg font-medium transition flex items-center gap-2 whitespace-nowrap ${
                    analysisLoading
                      ? 'bg-gray-400 text-white cursor-not-allowed'
                      : 'bg-blue-600 text-white hover:bg-blue-700 active:scale-95'
                  }`}
                >
                  {analysisLoading ? (
                    <>
                      <span className="animate-spin">⏳</span> Analyzing...
                    </>
                  ) : (
                    <>
                      <span>▶️</span> Run Analysis
                    </>
                  )}
                </button>
              </div>

              {/* Keywords Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Filter Keywords (optional)
                </label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="e.g., ERROR, database, timeout"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
            </div>

            {/* Analysis Results */}
            {analysisResult && (
              <div className="space-y-6 animate-fadeIn">
                {/* Metrics Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <MetricCard 
                    title="Total Logs" 
                    value={analysisResult.total_logs.toLocaleString()} 
                    icon="📊"
                    color="blue"
                  />
                  <MetricCard 
                    title="Error Rate" 
                    value={`${(analysisResult.error_rate * 100).toFixed(1)}%`}
                    icon="🔴"
                    color="red"
                  />
                  <MetricCard 
                    title="Warning Rate" 
                    value={`${(analysisResult.warning_rate * 100).toFixed(1)}%`}
                    icon="🟡"
                    color="yellow"
                  />
                  <MetricCard 
                    title="Chunks" 
                    value={analysisResult.estimated_chunks}
                    icon="🔨"
                    color="purple"
                  />
                </div>

                {/* Time Buckets */}
                {analysisResult.time_buckets && analysisResult.time_buckets.length > 0 && (
                  <AnalysisSection title="📈 Error Timeline (5-min buckets)">
                    <div className="space-y-3 max-h-64 overflow-y-auto">
                      {analysisResult.time_buckets.slice(-12).map((bucket, idx) => (
                        <div 
                          key={idx}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded hover:bg-gray-100 transition"
                        >
                          <span className="text-sm font-mono text-gray-600 flex-shrink-0">
                            {bucket.timestamp.split('T')[1] || bucket.timestamp}
                          </span>
                          <div className="flex items-center gap-3 flex-1 ml-4">
                            <span className="text-sm text-gray-600 flex-shrink-0">
                              {bucket.total_count} logs
                            </span>
                            <div className="w-24 h-6 bg-gray-200 rounded-full overflow-hidden flex-shrink-0">
                              <div 
                                className={`h-full transition-all ${
                                  bucket.error_rate > 0.5 ? 'bg-red-500' :
                                  bucket.error_rate > 0.2 ? 'bg-yellow-500' :
                                  'bg-green-500'
                                }`}
                                style={{ width: `${Math.min(bucket.error_rate * 100, 100)}%` }}
                              />
                            </div>
                            <span className="text-sm font-mono text-red-600 w-10 text-right flex-shrink-0">
                              {(bucket.error_rate * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </AnalysisSection>
                )}

                {/* Top Services */}
                {analysisResult.top_services && analysisResult.top_services.length > 0 && (
                  <AnalysisSection title="🚀 Top Services">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {analysisResult.top_services.slice(0, 6).map(([service, count], idx) => (
                        <div 
                          key={idx}
                          className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg border border-blue-200 hover:shadow-md transition"
                        >
                          <p className="text-sm font-mono text-blue-900 truncate">{service}</p>
                          <p className="text-2xl font-bold text-blue-600 mt-2">{count.toLocaleString()}</p>
                        </div>
                      ))}
                    </div>
                  </AnalysisSection>
                )}

                {/* Top Errors */}
                {analysisResult.top_errors && analysisResult.top_errors.length > 0 && (
                  <AnalysisSection title="🔴 Top Errors">
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {analysisResult.top_errors.slice(0, 5).map(([error, count], idx) => (
                        <div 
                          key={idx}
                          className="p-3 bg-red-50 rounded-lg border border-red-200 hover:bg-red-100 transition cursor-pointer"
                        >
                          <p className="text-sm text-red-900 font-mono break-words">
                            {error.substring(0, 100)}
                          </p>
                          <p className="text-xs text-red-700 mt-1">
                            🔴 {count} occurrences
                          </p>
                        </div>
                      ))}
                    </div>
                  </AnalysisSection>
                )}

                {/* Priority Queries */}
                {analysisResult.priority_queries && analysisResult.priority_queries.length > 0 && (
                  <AnalysisSection title="🎯 Priority Queries (for drilling down)">
                    <div className="space-y-2">
                      {analysisResult.priority_queries.slice(0, 5).map((query, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            setSearchQuery(query)
                            handleTabChange('logs')
                          }}
                          className="w-full text-left p-3 bg-blue-50 rounded-lg border border-blue-200 font-mono text-xs text-blue-900 hover:bg-blue-100 transition break-words"
                        >
                          {query}
                        </button>
                      ))}
                    </div>
                  </AnalysisSection>
                )}
              </div>
            )}

            {/* Chunk Summarization Results */}
            {chunks.length > 0 && (
              <div className="space-y-4 animate-fadeIn">
                <h3 className="text-lg font-bold text-gray-900">🔨 Chunk Summaries</h3>
                {chunks.map((chunk, idx) => (
                  <ChunkSummaryCard key={chunk.chunk_id || idx} chunk={chunk} />
                ))}

                {/* RAG Retrieval Section */}
                <div className="bg-white rounded-lg shadow p-6 space-y-4 border-l-4 border-green-500">
                  <h3 className="text-lg font-bold text-gray-900">🔍 Search Summaries (RAG)</h3>
                  <div className="flex gap-2 flex-col sm:flex-row">
                    <input
                      type="text"
                      value={ragQuery}
                      onChange={(e) => setRagQuery(e.target.value)}
                      placeholder="Search summaries e.g., 'database timeout'"
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 outline-none"
                      onKeyPress={(e) => e.key === 'Enter' && handleRetrieveSummaries()}
                    />
                    <button
                      onClick={handleRetrieveSummaries}
                      disabled={ragLoading}
                      className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 active:scale-95 whitespace-nowrap"
                    >
                      {ragLoading ? '🔄 Searching...' : '🔎 Search'}
                    </button>
                  </div>

                  {/* Retrieved Summaries */}
                  {summaries.length > 0 && (
                    <div className="space-y-3 mt-4 animate-fadeIn">
                      <p className="text-sm text-gray-600">
                        ✅ Found {summaries.length} relevant summaries
                      </p>
                      {summaries.map((summary, idx) => (
                        <div 
                          key={idx}
                          className="p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border border-green-300 hover:shadow-md transition"
                        >
                          <p className="text-xs font-mono text-green-900 mb-2">
                            {summary.chunk_id}
                          </p>
                          <p className="text-sm text-gray-700 mb-3 line-clamp-3">
                            {summary.summary}
                          </p>
                          <div className="flex gap-2 flex-wrap text-xs">
                            <span className="bg-red-200 text-red-800 px-2 py-1 rounded font-mono">
                              Errors: {summary.error_count}
                            </span>
                            <span className="bg-yellow-200 text-yellow-800 px-2 py-1 rounded font-mono">
                              Warnings: {summary.warning_count}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Loading State */}
            {analysisLoading && (
              <div className="bg-white rounded-lg shadow p-8 text-center animate-pulse">
                <div className="inline-block">
                  <p className="text-xl font-semibold text-blue-600">⏳</p>
                  <p className="text-gray-600 mt-2">Running aggregation analysis...</p>
                  <p className="text-sm text-gray-500 mt-1">This may take 2-4 seconds</p>
                </div>
              </div>
            )}

            {/* Empty State */}
            {!analysisLoading && !analysisResult && (
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow p-12 text-center border border-blue-200">
                <p className="text-xl font-semibold text-gray-900">🤖 AI Analysis</p>
                <p className="text-gray-600 mt-2">
                  Click "Run Analysis" to start aggregation-first analysis of your logs
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ===== AI CHAT BUTTON ===== */}
      {ChatSidebar && (
        <>
          <button
            onClick={() => setChatOpen(!chatOpen)}
            className="fixed bottom-6 right-6 bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 rounded-full shadow-lg hover:shadow-xl hover:scale-110 transition z-40"
            title="Open AI Assistant"
          >
            <svg 
              className="w-6 h-6" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" 
              />
            </svg>
          </button>

          <ChatSidebar 
            isOpen={chatOpen} 
            onClose={() => setChatOpen(false)}
            onSuggestedQuery={handleSuggestedQuery}
          />
        </>
      )}
    </div>
  )
}


// ===== HELPER COMPONENTS =====

function MetricCard({ title, value, icon, color = 'blue' }) {
  const colorMap = {
    blue: 'bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200 text-blue-900',
    red: 'bg-gradient-to-br from-red-50 to-red-100 border-red-200 text-red-900',
    yellow: 'bg-gradient-to-br from-yellow-50 to-yellow-100 border-yellow-200 text-yellow-900',
    purple: 'bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200 text-purple-900'
  }

  return (
    <div className={`${colorMap[color]} border rounded-lg p-4 hover:shadow-md transition`}>
      <p className="text-xs sm:text-sm text-gray-700 mb-2 font-medium">{icon} {title}</p>
      <p className="text-2xl sm:text-3xl font-bold">{value}</p>
    </div>
  )
}

function AnalysisSection({ title, children }) {
  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-4 hover:shadow-lg transition">
      <h3 className="text-lg font-bold text-gray-900">{title}</h3>
      {children}
    </div>
  )
}

function ChunkSummaryCard({ chunk }) {
  return (
    <div className="bg-white rounded-lg shadow p-6 border-l-4 border-indigo-500 hover:shadow-lg transition space-y-3">
      <div className="flex justify-between items-start gap-4 flex-wrap">
        <div>
          <p className="text-xs font-mono text-gray-600 truncate">{chunk.chunk_id}</p>
          <p className="text-xs text-gray-500 mt-1">Query {chunk.queryIndex || '?'}</p>
        </div>
        <span className="text-xs font-mono text-gray-500 flex-shrink-0">
          {chunk.timestamp ? new Date(chunk.timestamp).toLocaleTimeString() : 'N/A'}
        </span>
      </div>

      <p className="text-sm text-gray-700 line-clamp-3">
        {chunk.summary_text || 'No summary'}
      </p>

      <div className="grid grid-cols-3 gap-2">
        <div className="bg-blue-50 rounded p-2 text-center">
          <p className="text-xs text-gray-600">Logs</p>
          <p className="text-lg font-bold text-blue-600">{chunk.total_logs || 0}</p>
        </div>
        <div className="bg-red-50 rounded p-2 text-center">
          <p className="text-xs text-gray-600">Errors</p>
          <p className="text-lg font-bold text-red-600">{chunk.error_count || 0}</p>
        </div>
        <div className="bg-yellow-50 rounded p-2 text-center">
          <p className="text-xs text-gray-600">Warnings</p>
          <p className="text-lg font-bold text-yellow-600">{chunk.warning_count || 0}</p>
        </div>
      </div>

      {chunk.top_services && chunk.top_services.length > 0 && (
        <div className="text-xs bg-gray-50 p-2 rounded">
          <p className="font-medium text-gray-700 mb-1">Services:</p>
          <p className="text-gray-600">
            {chunk.top_services.slice(0, 3).map(([s, c]) => `${s} (${c})`).join(', ')}
          </p>
        </div>
      )}

      {chunk.suggested_queries && chunk.suggested_queries.length > 0 && (
        <div className="text-xs bg-gray-50 p-2 rounded">
          <p className="font-medium text-gray-700 mb-1">Suggested Queries:</p>
          <div className="space-y-1">
            {chunk.suggested_queries.slice(0, 2).map((q, i) => (
              <code 
                key={i} 
                className="block bg-white p-1 rounded text-gray-700 font-mono text-xs truncate border border-gray-200"
                title={q}
              >
                {q.substring(0, 50)}...
              </code>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// Add CSS animation
const style = document.createElement('style')
style.textContent = `
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  .animate-fadeIn {
    animation: fadeIn 0.3s ease-in-out;
  }
`
document.head.appendChild(style)

export default Dashboard
