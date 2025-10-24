"""Log analysis service using AI"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import json
import re

from app.ai.config import ai_settings
from app.ai.providers import get_ai_provider
from app.search.client import get_opensearch_client, search_logs

logger = logging.getLogger(__name__)


class LogAnalyzer:
    """Analyzes logs using AI"""
    
    def __init__(self):
        self.provider = get_ai_provider(
            ai_settings.ai_provider,
            api_key=ai_settings.groq_api_key,
            model=ai_settings.groq_model
        )
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for log analysis"""
        return """You are an expert log analysis assistant. Your job is to analyze application logs and provide:

1. **Summary**: Brief overview of log activity
2. **Issues Found**: List of errors, warnings, and anomalies with severity
3. **Root Cause Analysis**: Potential causes for each issue
4. **Recommendations**: Actionable steps to resolve issues
5. **Suggested Queries**: OpenSearch query strings for drill-down (use Lucene query syntax)

Format your response as structured markdown with these sections.

When suggesting queries, use OpenSearch/Lucene syntax like:
- `level:ERROR AND service:api`
- `message:"database timeout" AND timestamp:[now-1h TO now]`
- `status:500 AND path:/api/users`

Be concise but thorough. Focus on actionable insights."""
    
    def analyze(
        self,
        timestamp: Optional[datetime] = None,
        keywords: Optional[str] = None,
        time_window_minutes: int = 30,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze logs and return AI insights
        
        Args:
            timestamp: Reference timestamp (default: now)
            keywords: Search keywords to filter logs
            time_window_minutes: How far back to look (default: 30)
            chat_history: Previous conversation for context
        
        Returns:
            Dictionary with analysis, suggestions, and metadata
        """
        
        # Determine time range
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        end_time = timestamp
        start_time = timestamp - timedelta(minutes=time_window_minutes)
        
        logger.info(f"Analyzing logs from {start_time} to {end_time}")
        
        # Fetch logs from OpenSearch
        client = get_opensearch_client()
        
        try:
            results = search_logs(
                client,
                start_time=start_time,
                end_time=end_time,
                query=keywords,
                page=1,
                page_size=ai_settings.max_logs_per_analysis
            )
            
            logs = results['logs']
            total_count = results['total']
            
            logger.info(f"Fetched {len(logs)} logs (total: {total_count})")
            
            if not logs:
                return {
                    "analysis": "No logs found in the specified time range.",
                    "summary": {
                        "total_logs": 0,
                        "errors": 0,
                        "warnings": 0,
                        "time_range": f"{start_time.isoformat()} to {end_time.isoformat()}"
                    },
                    "suggested_queries": [],
                    "chart_data": None,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Prepare context for AI
            log_context = self._prepare_log_context(logs, total_count)
            
            # Build messages for AI
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add chat history for context (last 5 exchanges)
            if chat_history:
                for msg in chat_history[-10:]:  # Last 5 Q&A pairs
                    messages.append(msg)
            
            # Add current query
            user_query = self._build_user_query(
                start_time, end_time, keywords, time_window_minutes, log_context
            )
            messages.append({"role": "user", "content": user_query})
            
            # Generate AI response
            logger.info("Calling AI provider for analysis...")
            ai_response = self.provider.generate(
                messages,
                temperature=ai_settings.ai_temperature,
                max_tokens=ai_settings.ai_max_tokens
            )
            
            logger.info("AI analysis complete")
            
            # Parse response and extract structured data
            parsed_response = self._parse_ai_response(ai_response, logs)
            
            # Generate chart data
            chart_data = self._generate_chart_data(logs, start_time, end_time)
            
            return {
                "analysis": ai_response,
                "summary": {
                    "total_logs": total_count,
                    "analyzed_logs": len(logs),
                    "errors": parsed_response['error_count'],
                    "warnings": parsed_response['warning_count'],
                    "time_range": f"{start_time.isoformat()} to {end_time.isoformat()}",
                    "keywords": keywords
                },
                "suggested_queries": parsed_response['suggested_queries'],
                "chart_data": chart_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Analysis error: {e}", exc_info=True)
            raise
    
    def _prepare_log_context(self, logs: List[Dict], total_count: int) -> str:
        """Format logs for AI context"""
        
        context_lines = []
        context_lines.append(f"Total logs in range: {total_count}")
        context_lines.append(f"Sample of {len(logs)} logs:\n")
        
        for i, log in enumerate(logs[:50], 1):  # First 50 for detailed view
            timestamp = log.get('timestamp', 'N/A')
            level = log.get('fields', {}).get('level', 'INFO')
            source = log.get('source_file', 'unknown').split('/')[-1]
            raw_line = log.get('raw_line', '')[:200]  # Truncate long lines
            
            context_lines.append(
                f"{i}. [{timestamp}] {level} | {source} | {raw_line}"
            )
        
        if len(logs) > 50:
            context_lines.append(f"\n... and {len(logs) - 50} more logs")
        
        return "\n".join(context_lines)
    
    def _build_user_query(
        self,
        start_time: datetime,
        end_time: datetime,
        keywords: Optional[str],
        time_window: int,
        log_context: str
    ) -> str:
        """Build user query for AI"""
        
        query_parts = [
            f"Analyze the following logs from the past {time_window} minutes",
            f"(from {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')})."
        ]
        
        if keywords:
            query_parts.append(f"\nFiltered by keywords: '{keywords}'")
        
        query_parts.append(f"\n\n{log_context}")
        query_parts.append("\n\nProvide a comprehensive analysis with actionable insights.")
        
        return " ".join(query_parts)
    
    def _parse_ai_response(self, response: str, logs: List[Dict]) -> Dict[str, Any]:
        """Parse AI response to extract structured data"""
        
        # Count errors and warnings
        error_count = sum(1 for log in logs if log.get('fields', {}).get('level') == 'ERROR')
        warning_count = sum(1 for log in logs if log.get('fields', {}).get('level') in ['WARN', 'WARNING'])
        
        # Extract suggested queries (look for code blocks or query patterns)
        suggested_queries = []
        
        # Pattern 1: Look for queries in code blocks
        code_blocks = re.findall(r'``````', response, re.DOTALL)
        for block in code_blocks:
            queries = [q.strip() for q in block.split('\n') if q.strip() and not q.strip().startswith('#')]
            suggested_queries.extend(queries[:3])  # Max 3 per block
        
        # Pattern 2: Look for inline queries
        inline_queries = re.findall(r'`([^`]+:.*?)`', response)
        suggested_queries.extend(inline_queries[:5])
        
        # Deduplicate and limit
        suggested_queries = list(dict.fromkeys(suggested_queries))[:5]
        
        return {
            "error_count": error_count,
            "warning_count": warning_count,
            "suggested_queries": suggested_queries
        }
    
    def _generate_chart_data(
        self,
        logs: List[Dict],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Generate chart data for error timeline"""
        
        # Group logs by 5-minute buckets
        bucket_minutes = 5
        buckets = {}
        
        current = start_time
        while current <= end_time:
            bucket_key = current.strftime('%Y-%m-%d %H:%M')
            buckets[bucket_key] = {"errors": 0, "warnings": 0, "info": 0, "total": 0}
            current += timedelta(minutes=bucket_minutes)
        
        # Count logs per bucket
        for log in logs:
            try:
                log_time = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                bucket_key = log_time.replace(
                    minute=(log_time.minute // bucket_minutes) * bucket_minutes,
                    second=0, microsecond=0
                ).strftime('%Y-%m-%d %H:%M')
                
                if bucket_key in buckets:
                    level = log.get('fields', {}).get('level', 'INFO').upper()
                    buckets[bucket_key]['total'] += 1
                    
                    if level == 'ERROR':
                        buckets[bucket_key]['errors'] += 1
                    elif level in ['WARN', 'WARNING']:
                        buckets[bucket_key]['warnings'] += 1
                    else:
                        buckets[bucket_key]['info'] += 1
            except:
                continue
        
        # Convert to chart format
        timeline = [
            {
                "time": key,
                "errors": val['errors'],
                "warnings": val['warnings'],
                "info": val['info']
            }
            for key, val in sorted(buckets.items())
        ]
        
        return {
            "timeline": timeline,
            "bucket_minutes": bucket_minutes
        }


# Global analyzer instance
_analyzer = None

def get_analyzer() -> LogAnalyzer:
    """Get or create log analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = LogAnalyzer()
    return _analyzer
