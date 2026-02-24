# backend/app/ai/analyzer.py
"""Log analysis service using aggregation-first approach with AI"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import json
import re
import asyncio

from app.ai.config import ai_settings
from app.ai.providers import get_ai_provider
from app.search.client import get_opensearch_client, search_logs

logger = logging.getLogger(__name__)


class LogAnalyzer:
    """Analyzes logs using aggregation-first orchestration + AI synthesis"""
    
    def __init__(self):
        # Get provider-specific settings
        provider_name = ai_settings.ai_provider
        
        if provider_name == "modelbroker":
            api_key = ai_settings.modelbroker_api_key
            model = ai_settings.modelbroker_model
            base_url = ai_settings.modelbroker_base_url
            self.provider = get_ai_provider(
                provider_name,
                api_key=api_key,
                model=model,
                base_url=base_url
            )
        elif provider_name == "groq":
            api_key = ai_settings.groq_api_key
            model = ai_settings.groq_model
            self.provider = get_ai_provider(
                provider_name,
                api_key=api_key,
                model=model
            )
        elif provider_name == "ollama":
            self.provider = get_ai_provider(
                provider_name,
                base_url=ai_settings.ollama_base_url,
                model=ai_settings.ollama_model
            )
        else:
            raise ValueError(f"Unsupported AI provider: {provider_name}")
        
        logger.info(f"Initialized LogAnalyzer with provider: {provider_name}")
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

Be concise but thorough. Focus on actionable insights based on the provided data."""
    
    def analyze(
        self,
        timestamp: Optional[datetime] = None,
        keywords: Optional[str] = None,
        time_window_minutes: int = 30,
        chat_history: Optional[List[Dict[str, str]]] = None,
        source_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze logs and return AI insights
        
        NOTE: This is a SYNCHRONOUS method (not async)
        All async operations inside must be handled properly
        
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
        
        logger.info(f"🔍 Starting analysis: {start_time} to {end_time}")
        logger.info(f"   Keywords: {keywords}, Source file: {source_file}")
        
        # Fetch logs from OpenSearch
        client = get_opensearch_client()
        
        try:
            # Fetch logs directly (synchronous)
            logger.info("📥 Fetching logs...")
            results = search_logs(
                client,
                start_time=start_time,
                end_time=end_time,
                query=keywords,
                source_file=source_file,
                page=1,
                page_size=ai_settings.max_logs_per_analysis
            )
            
            logs = results['logs']
            total_count = results['total']
            
            logger.info(f"✅ Fetched {len(logs)} logs (total: {total_count})")
            
            # If no logs found
            if not logs:
                logger.warning("⚠️  No logs found in range")
                return {
                    "analysis": "No logs found in the specified time range.",
                    "summary": {
                        "total_logs": total_count,
                        "errors": 0,
                        "warnings": 0,
                        "time_range": f"{start_time.isoformat()} to {end_time.isoformat()}",
                        "source_file": source_file,
                        "analysis_type": "standard"
                    },
                    "suggested_queries": [],
                    "chart_data": None,
                    "timestamp": datetime.utcnow().isoformat(),
                    "time_window_minutes": time_window_minutes,
                    "keywords": keywords
                }
            
            # Prepare context for AI
            logger.info("📝 Preparing log context...")
            log_context = self._prepare_log_context(logs, total_count)
            
            # Build messages for AI
            messages = [{"role": "system", "content": self.system_prompt}]

            file_context = ""
            if source_file:
                file_context = f"\n**IMPORTANT**: User specifically requested analysis of ONLY logs from file: {source_file}\n"
            
            user_prompt = f"""Analyze logs from {start_time.isoformat()} to {end_time.isoformat()}.
{file_context}
Keywords: {keywords or 'all'}
Total logs found: {len(logs)}

Logs:
{log_context}

Provide comprehensive analysis focused on these specific logs."""
            
            # Add chat history for context (last 10 messages = 5 Q&A pairs)
            if chat_history:
                for msg in chat_history[-10:]:
                    messages.append(msg)
            
            # Add current query
            messages.append({"role": "user", "content": user_prompt})
            
            # Generate AI response
            logger.info("🤖 Calling AI provider for analysis...")
            ai_response = self.provider.generate(
                messages,
                temperature=ai_settings.ai_temperature,
                max_tokens=ai_settings.ai_max_tokens
            )
            
            logger.info("✅ AI analysis complete")
            
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
                    "keywords": keywords,
                    "analysis_type": "standard"
                },
                "suggested_queries": parsed_response['suggested_queries'],
                "chart_data": chart_data,
                "timestamp": datetime.utcnow().isoformat(),
                "time_window_minutes": time_window_minutes,
                "keywords": keywords
            }
            
        except Exception as e:
            logger.error(f"❌ Analysis error: {e}", exc_info=True)
            raise
    
    def _prepare_log_context(self, logs: List[Dict], total_count: int) -> str:
        """Format logs for AI context"""
        
        context_lines = []
        context_lines.append(f"Total logs in range: {total_count}")
        context_lines.append(f"Showing {len(logs)} logs:\n")
        
        for i, log in enumerate(logs[:50], 1):
            try:
                timestamp = log.get('timestamp', 'N/A')
                level = log.get('fields', {}).get('level', 'INFO')
                #service = log.get('fields', {}).get('service', log.get('source_file', 'unknown').split('/')[-1])
                message = log.get('fields', {}).get('message', log.get('raw_line', ''))[:150]
                service = log.get('fields', {}).get('service')

                if not service or service == 'unknown':
                    raw_line = log.get('raw_line', '')
                    import re
                    match = re.search(r'\[([^\]]+)-service\]|\[([^\]]+)\]|service[:\s]*([^\s,\]]+)', raw_line, re.IGNORECASE)
                    if match:
                        service = match.group(1) or match.group(2) or match.group(3)
                        service = service.replace('-service', '').strip()
                    if not service or service == 'unknown':
                        service = log.get('source_file', 'unknown').split('/')[-1].split('.')

                context_lines.append(
                    f"{i}. [{timestamp}] {level} | {service} | {message}"
                )
            except Exception as e:
                logger.warning(f"Error formatting log {i}: {e}")
                continue
        
        if len(logs) > 50:
            context_lines.append(f"\n... and {len(logs) - 50} more logs")
        
        return "\n".join(context_lines)
    
    def _parse_ai_response(self, response: str, logs: List[Dict]) -> Dict[str, Any]:
        """Parse AI response to extract structured data"""
        
        # Count errors and warnings from logs
        error_count = sum(1 for log in logs if log.get('fields', {}).get('level') == 'ERROR')
        warning_count = sum(1 for log in logs if log.get('fields', {}).get('level') in ['WARN', 'WARNING'])
        
        # Extract suggested queries (look for code blocks or query patterns)
        suggested_queries = []
        
        # Pattern 1: Look for queries in code blocks
        code_blocks = re.findall(r'```(.*?)```', response, re.DOTALL)
        for block in code_blocks:
            queries = [q.strip() for q in block.split('\n') if q.strip() and not q.strip().startswith('#')]
            suggested_queries.extend(queries[:3])
        
        # Pattern 2: Look for inline queries
        inline_queries = re.findall(r'`([^`]+:.*?[^`]+)`', response)
        suggested_queries.extend(inline_queries[:5])
        
        # Deduplicate and limit to 5
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
            except Exception as e:
                logger.debug(f"Error processing log for chart: {e}")
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
