# backend/app/ai/analyzer.py
"""Log analysis service using aggregation-first approach with AI"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import json
import re

from app.ai.config import ai_settings
from app.ai.providers import get_ai_provider
from app.ai.aggregator import get_orchestrator
from app.search.client import get_opensearch_client, search_logs

logger = logging.getLogger(__name__)


class LogAnalyzer:
    """Analyzes logs using aggregation-first orchestration + AI synthesis"""
    
    def __init__(self):
        self.provider = get_ai_provider(
            ai_settings.ai_provider,
            api_key=ai_settings.groq_api_key,
            model=ai_settings.groq_model
        )
        self.orchestrator = get_orchestrator()
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for log analysis"""
        return """You are an expert log analysis assistant. Your job is to analyze application logs and provide:

1. **Summary**: Brief overview of log activity and key issues
2. **Issues Found**: List of errors, warnings, and anomalies with severity
3. **Root Cause Analysis**: Potential causes for each issue based on patterns
4. **Recommendations**: Actionable steps to resolve issues
5. **Suggested Queries**: OpenSearch query strings for drill-down (use Lucene query syntax)

Format your response as structured markdown with these sections.

When suggesting queries, use OpenSearch/Lucene syntax like:
- `level:ERROR AND service:api`
- `message:"database timeout" AND timestamp:[now-1h TO now]`
- `status:500 AND path:/api/users`

Be concise but thorough. Focus on actionable insights based on the aggregated data provided."""
    
    def analyze(
        self,
        timestamp: Optional[datetime] = None,
        keywords: Optional[str] = None,
        time_window_minutes: int = 30,
        chat_history: Optional[List[Dict[str, str]]] = None,
        source_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze logs using aggregation-first approach.
        
        FLOW:
        1. Run aggregation orchestration (100-300ms)
        2. Get priority queries from aggregation
        3. Fetch representative logs for top issues
        4. Build enhanced AI context (aggregation + sample logs)
        5. Call LLM for synthesis
        6. Parse and return results
        
        Args:
            timestamp: Reference timestamp (default: now)
            keywords: Search keywords to filter logs
            time_window_minutes: How far back to look (default: 30)
            chat_history: Previous conversation for context
            source_file: Specific log source file to filter
        
        Returns:
            Dictionary with analysis, suggestions, and metadata
        """

        # Determine time range
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        end_time = timestamp
        start_time = timestamp - timedelta(minutes=time_window_minutes)
        
        logger.info(f"🔍 Starting aggregation-first analysis: {start_time} to {end_time}")
        logger.info(f"   Keywords: {keywords}, Source file: {source_file}")
        
        client = get_opensearch_client()
        
        try:
            # ============ STAGE 1: AGGREGATION ORCHESTRATION ============
            logger.info("⚙️  Stage 1: Running aggregation orchestration...")

            agg_result = self.orchestrator.orchestrate_analysis(
                start_time=start_time,
                end_time=end_time,
                keywords=keywords,
                source_file=source_file,
                top_k=10
            )
            
            total_logs = agg_result['total_logs']
            logger.info(f"   ✅ Aggregation complete: {total_logs} logs analyzed")
            logger.info(f"   Error rate: {agg_result['error_rate']:.1%}")
            logger.info(f"   Top services: {agg_result['top_services'][:3]}")
            
            # If no logs, return early
            if total_logs == 0:
                return {
                    "analysis": "No logs found in the specified time range.",
                    "summary": {
                        "total_logs": 0,
                        "errors": 0,
                        "warnings": 0,
                        "time_range": f"{start_time.isoformat()} to {end_time.isoformat()}",
                        "source_file": source_file,
                        "analysis_type": "aggregation-first"
                    },
                    "suggested_queries": [],
                    "chart_data": None,
                    "timestamp": datetime.utcnow().isoformat(),
                    "time_window_minutes": time_window_minutes,
                    "keywords": keywords,
                    "aggregation_result": agg_result
                }
            
            # ============ STAGE 2: FETCH REPRESENTATIVE LOGS ============
            logger.info("⚙️  Stage 2: Fetching representative logs from priority queries...")
            
            all_representative_logs = []
            priority_queries = agg_result['priority_queries']
            
            # Fetch logs for top 3 priority queries (max 50 logs each for context)
            for i, query in enumerate(priority_queries[:3], 1):
                logger.info(f"   Query {i}/3: {query[:60]}...")
                
                try:
                    results = search_logs(
                        client,
                        start_time=start_time,
                        end_time=end_time,
                        query=query,
                        page_size=50
                    )
                    
                    logs_in_query = results['logs']
                    all_representative_logs.extend(logs_in_query)
                    logger.info(f"   ✅ Fetched {len(logs_in_query)} logs for query {i}")
                    
                except Exception as e:
                    logger.warning(f"   ⚠️  Failed to fetch logs for query {i}: {e}")
                    continue
            
            # Deduplicate by line_number + source_file
            unique_logs = {}
            for log in all_representative_logs:
                key = (log.get('source_file'), log.get('line_number'))
                if key not in unique_logs:
                    unique_logs[key] = log
            
            all_representative_logs = list(unique_logs.values())[:100]  # Max 100 logs for context
            logger.info(f"   ✅ Total unique logs: {len(all_representative_logs)}")
            
            # ============ STAGE 3: BUILD ENHANCED CONTEXT ============
            logger.info("⚙️  Stage 3: Building enhanced AI context...")
            
            enhanced_context = self._build_enhanced_context(
                agg_result, all_representative_logs, total_logs
            )
            
            # ============ STAGE 4: BUILD MESSAGES FOR LLM ============
            messages = [{"role": "system", "content": self.system_prompt}]
            
            file_context = ""
            if source_file:
                file_context = f"\n**IMPORTANT**: Analysis is filtered to file: {source_file}\n"
            
            user_prompt = f"""Analyze the following log summary and samples:

Time Range: {start_time.isoformat()} to {end_time.isoformat()}
{file_context}
Total Logs in Range: {total_logs}
Error Rate: {agg_result['error_rate']:.1%}
Warning Rate: {agg_result['warning_rate']:.1%}

{enhanced_context}

Provide comprehensive analysis based on the aggregated metrics and sample logs above."""
            
            # Add chat history for context (last 5 exchanges)
            if chat_history:
                for msg in chat_history[-10:]:  # Last 5 Q&A pairs
                    messages.append(msg)
            
            messages.append({"role": "user", "content": user_prompt})
            
            # ============ STAGE 5: CALL LLM ============
            logger.info("⚙️  Stage 5: Calling LLM for synthesis...")
            
            ai_response = self.provider.generate(
                messages,
                temperature=ai_settings.ai_temperature,
                max_tokens=ai_settings.ai_max_tokens
            )
            
            logger.info("✅ AI analysis complete")
            
            # ============ STAGE 6: PARSE RESPONSE ============
            parsed_response = self._parse_ai_response(ai_response, all_representative_logs)
            
            # Generate chart data from aggregation
            chart_data = self._generate_chart_data_from_aggregation(agg_result)
            
            # ============ RETURN RESULTS ============
            result = {
                "analysis": ai_response,
                "summary": {
                    "total_logs": total_logs,
                    "analyzed_logs": len(all_representative_logs),
                    "errors": parsed_response['error_count'],
                    "warnings": parsed_response['warning_count'],
                    "error_rate": agg_result['error_rate'],
                    "time_range": f"{start_time.isoformat()} to {end_time.isoformat()}",
                    "keywords": keywords,
                    "analysis_type": "aggregation-first"
                },
                "suggested_queries": parsed_response['suggested_queries'],
                "chart_data": chart_data,
                "timestamp": datetime.utcnow().isoformat(),
                "time_window_minutes": time_window_minutes,
                "keywords": keywords,
                "aggregation_result": agg_result  # Include for frontend use
            }
            
            logger.info(f"✅ Analysis complete: {result['summary']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Analysis error: {e}", exc_info=True)
            raise
    
    def _build_enhanced_context(
        self,
        agg_result: Dict[str, Any],
        logs: List[Dict[str, Any]],
        total_count: int
    ) -> str:
        """Build enhanced context combining aggregation + sample logs"""
        
        context_lines = []
        
        # === AGGREGATION SUMMARY ===
        context_lines.append("## AGGREGATION SUMMARY")
        context_lines.append(f"- Total Logs: {total_count}")
        context_lines.append(f"- Error Rate: {agg_result['error_rate']:.1%}")
        context_lines.append(f"- Warning Rate: {agg_result['warning_rate']:.1%}")
        context_lines.append("")
        
        # === TOP SERVICES ===
        if agg_result['top_services']:
            context_lines.append("### Top Services by Volume:")
            for service, count in agg_result['top_services'][:5]:
                pct = (count / max(total_count, 1)) * 100
                context_lines.append(f"- {service}: {count} logs ({pct:.1f}%)")
            context_lines.append("")
        
        # === TOP ERRORS ===
        if agg_result['top_errors']:
            context_lines.append("### Top Errors:")
            for error, count in agg_result['top_errors'][:5]:
                pct = (count / max(total_count, 1)) * 100
                context_lines.append(f"- {error[:80]}: {count} occurrences ({pct:.1f}%)")
            context_lines.append("")
        
        # === TIME BUCKETS ===
        if agg_result['time_buckets']:
            context_lines.append("### Error Timeline (5-min buckets):")
            for bucket in agg_result['time_buckets'][-6:]:  # Last 6 buckets
                error_rate = bucket['error_rate']
                context_lines.append(
                    f"- {bucket['timestamp']}: {bucket['total_count']} logs, "
                    f"{error_rate:.1%} errors"
                )
            context_lines.append("")
        
        # === SAMPLE LOGS ===
        context_lines.append("## REPRESENTATIVE LOG SAMPLES")
        context_lines.append(f"Showing {len(logs)} representative logs:\n")
        
        for i, log in enumerate(logs[:20], 1):  # Show first 20 samples
            timestamp = log.get('timestamp', 'N/A')
            level = log.get('fields', {}).get('level', 'INFO')
            service = log.get('fields', {}).get('service', log.get('source_file', 'unknown').split('/')[-1])
            message = log.get('fields', {}).get('message', log.get('raw_line', ''))[:150]
            
            context_lines.append(f"{i}. [{timestamp}] {level} | {service} | {message}")
        
        if len(logs) > 20:
            context_lines.append(f"\n... and {len(logs) - 20} more logs")
        
        return "\n".join(context_lines)
    
    def _parse_ai_response(self, response: str, logs: List[Dict]) -> Dict[str, Any]:
        """Parse AI response to extract structured data"""
        
        # Count errors and warnings from sample logs
        error_count = sum(1 for log in logs if log.get('fields', {}).get('level') == 'ERROR')
        warning_count = sum(1 for log in logs if log.get('fields', {}).get('level') in ['WARN', 'WARNING'])
        
        # Extract suggested queries (look for code blocks or query patterns)
        suggested_queries = []
        
        # Pattern 1: Look for queries in code blocks
        code_blocks = re.findall(r'```(.*?)```', response, re.DOTALL)
        for block in code_blocks:
            queries = [q.strip() for q in block.split('\n') if q.strip() and not q.strip().startswith('#')]
            suggested_queries.extend(queries[:3])  # Max 3 per block
        
        # Pattern 2: Look for inline queries (backtick-wrapped)
        inline_queries = re.findall(r'`([^`]+:.*?[^`]+)`', response)
        suggested_queries.extend(inline_queries[:5])
        
        # Deduplicate and limit to 5
        suggested_queries = list(dict.fromkeys(suggested_queries))[:5]
        
        return {
            "error_count": error_count,
            "warning_count": warning_count,
            "suggested_queries": suggested_queries
        }
    
    def _generate_chart_data_from_aggregation(
        self,
        agg_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate chart data from aggregation results"""
        
        timeline = []
        
        for bucket in agg_result.get('time_buckets', []):
            timeline.append({
                "time": bucket['timestamp'],
                "errors": bucket['error_count'],
                "warnings": bucket['warning_count'],
                "total": bucket['total_count']
            })
        
        return {
            "timeline": timeline,
            "bucket_minutes": 5,
            "error_rate": agg_result.get('error_rate', 0),
            "warning_rate": agg_result.get('warning_rate', 0)
        }


# Global analyzer instance
_analyzer = None

def get_analyzer() -> LogAnalyzer:
    """Get or create log analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = LogAnalyzer()
    return _analyzer


def parse_natural_language_query(query: str) -> dict:
    """
    Parse natural language query using regex patterns.
    
    Supports phrases like:
    - "last 5 hours"
    - "past 30 minutes"
    - "errors from database"
    - "in format1_2025-11-02.log"
    
    Args:
        query: User's natural language query
    
    Returns:
        {
            "keywords": "ERROR",
            "time_window_minutes": 300,
            "source_file": "/logs_in/format1_2025-11-02.log"
        }
    """
    
    query_lower = query.lower()
    logger.info(f"✅ [NL Parse] Query: {query_lower}")
    
    # Extract time window (in minutes)
    time_window = 30  # Default
    
    time_patterns = [
        (r'\b(\d+)\s*minute(s)?\b', 1),
        (r'\b(\d+)\s*min\b', 1),
        (r'\b(\d+)\s*hour(s)?\b', 60),
        (r'\b(\d+)\s*h\b', 60),
        (r'\b(\d+)\s*day(s)?\b', 1440),
        (r'\b(\d+)\s*week(s)?\b', 10080),
        (r'\blast\s+(\d+)\s*minute(s)?\b', 1),
        (r'\blast\s+(\d+)\s*hour(s)?\b', 60),
        (r'\blast\s+(\d+)\s*day(s)?\b', 1440),
        (r'\blast\s+(\d+)\s*week(s)?\b', 10080),
        (r'\bpast\s+(\d+)\s*minute(s)?\b', 1),
        (r'\bpast\s+(\d+)\s*hour(s)?\b', 60),
        (r'\bpast\s+(\d+)\s*day(s)?\b', 1440),
        (r'\bpast\s+(\d+)\s*week(s)?\b', 10080),
    ]
    
    for pattern, multiplier in time_patterns:
        match = re.search(pattern, query_lower)
        if match:
            amount = int(match.group(1))
            time_window = amount * multiplier
            logger.info(f"✅ [NL Parse] Detected time window: {time_window} minutes")
            break
    
    # Extract keywords
    keywords = None
    keyword_mapping = {
        'error': 'ERROR',
        'errors': 'ERROR',
        'warning': 'WARNING',
        'warnings': 'WARNING',
        'warn': 'WARN',
        'database': 'database',
        'db': 'database',
        'payment': 'payment',
        'timeout': 'timeout',
        'memory': 'memory',
        'fail': 'fail',
        'failure': 'fail',
        'crash': 'crash',
        'down': 'down',
    }
    
    for word, keyword in keyword_mapping.items():
        if word in query_lower:
            keywords = keyword
            logger.info(f"✅ [NL Parse] Detected keyword: {keyword}")
            break
    
    # Extract source file
    source_file = None
    for pattern in [
        r'file\s+(\S+\.log)',
        r'from\s+(\S+\.log)',
        r'in\s+(\S+\.log)',
        r'(format\d+_\w+\.log)',
    ]:
        match = re.search(pattern, query_lower)
        if match:
            source_file = match.group(1)
            if not source_file.startswith('/'):
                source_file = f"/logs_in/{source_file}"
            logger.info(f"✅ [NL Parse] Detected source file: {source_file}")
            break
    
    result = {
        "keywords": keywords,
        "time_window_minutes": time_window,
        "source_file": source_file
    }
    
    logger.info(f"✅ [NL Parse] Final result: {result}")
    
    return result
