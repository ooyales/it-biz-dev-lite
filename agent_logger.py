#!/usr/bin/env python3
"""
Agent Activity Logger

Tracks all AI agent activity to a SQLite database for the Agent Dashboard.
Each agent call is logged with timestamp, agent name, action, status, and duration.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class AgentLogger:
    """Logs AI agent activity for monitoring and analytics"""
    
    def __init__(self, db_path: str = 'data/agent_logs.db'):
        self.db_path = db_path
        Path(db_path).parent.mkdir(exist_ok=True)
        self._initialize_db()
    
    def _initialize_db(self):
        """Create agent_logs table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                agent_name TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_seconds REAL,
                input_data TEXT,
                output_data TEXT,
                error_message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on timestamp for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_logs_timestamp 
            ON agent_logs(timestamp DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_logs_agent_id 
            ON agent_logs(agent_id, timestamp DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def log_agent_activity(
        self,
        agent_id: int,
        agent_name: str,
        action: str,
        status: str,
        duration_seconds: float = None,
        input_data: Dict = None,
        output_data: Dict = None,
        error_message: str = None
    ) -> int:
        """
        Log an agent activity
        
        Args:
            agent_id: Agent number (1-6)
            agent_name: Human-readable agent name
            action: What action was performed
            status: 'success', 'error', or 'running'
            duration_seconds: How long the action took
            input_data: Input parameters (will be JSON serialized)
            output_data: Output/results (will be JSON serialized)
            error_message: Error details if status='error'
        
        Returns:
            Log ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO agent_logs (
                agent_id, agent_name, action, status, duration_seconds,
                input_data, output_data, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_id,
            agent_name,
            action,
            status,
            duration_seconds,
            json.dumps(input_data) if input_data else None,
            json.dumps(output_data) if output_data else None,
            error_message
        ))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return log_id
    
    def get_recent_logs(self, agent_id: Optional[int] = None, limit: int = 100) -> List[Dict]:
        """
        Get recent agent logs
        
        Args:
            agent_id: Filter by specific agent (1-6), or None for all agents
            limit: Maximum number of logs to return
        
        Returns:
            List of log dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if agent_id:
            cursor.execute("""
                SELECT * FROM agent_logs 
                WHERE agent_id = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (agent_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM agent_logs 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            log = dict(row)
            # Parse JSON fields
            if log['input_data']:
                log['input_data'] = json.loads(log['input_data'])
            if log['output_data']:
                log['output_data'] = json.loads(log['output_data'])
            logs.append(log)
        
        return logs
    
    def get_agent_stats(self, agent_id: int, days: int = 7) -> Dict:
        """
        Get statistics for an agent over the last N days
        
        Args:
            agent_id: Agent number (1-6)
            days: Number of days to look back
        
        Returns:
            Dictionary with stats (total_runs, success_rate, avg_duration, etc.)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total runs in last N days
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successes,
                   AVG(duration_seconds) as avg_duration,
                   MAX(timestamp) as last_run
            FROM agent_logs
            WHERE agent_id = ? 
            AND timestamp >= datetime('now', '-' || ? || ' days')
        """, (agent_id, days))
        
        row = cursor.fetchone()
        conn.close()
        
        total = row[0] or 0
        successes = row[1] or 0
        
        return {
            'total_runs': total,
            'successes': successes,
            'failures': total - successes,
            'success_rate': (successes / total * 100) if total > 0 else 0,
            'avg_duration': row[2] or 0,
            'last_run': row[3]
        }


# Global logger instance
_logger = None

def get_logger() -> AgentLogger:
    """Get the global agent logger instance"""
    global _logger
    if _logger is None:
        _logger = AgentLogger()
    return _logger


if __name__ == '__main__':
    # Test the logger
    logger = AgentLogger()
    
    # Log some test activities
    logger.log_agent_activity(
        agent_id=1,
        agent_name='Opportunity Scout',
        action='Score opportunities',
        status='success',
        duration_seconds=2.5,
        input_data={'opportunity_count': 15},
        output_data={'scored': 15, 'high_priority': 3}
    )
    
    logger.log_agent_activity(
        agent_id=2,
        agent_name='Competitive Intelligence',
        action='Analyze incumbent',
        status='success',
        duration_seconds=5.2,
        input_data={'opportunity_id': 'ABC123'},
        output_data={'incumbent_found': True, 'teaming_partners': 2}
    )
    
    # Get recent logs
    logs = logger.get_recent_logs(limit=10)
    print(f"Total logs: {len(logs)}")
    for log in logs:
        print(f"  [{log['timestamp']}] Agent {log['agent_id']}: {log['action']} - {log['status']}")
    
    # Get stats
    stats = logger.get_agent_stats(agent_id=1, days=7)
    print(f"\nAgent 1 stats: {stats}")
