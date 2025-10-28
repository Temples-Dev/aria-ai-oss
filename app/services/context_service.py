"""
Context gathering service to collect system and environmental information.
"""

import logging
import os
import psutil
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ContextService:
    """Service for gathering contextual information for greeting generation."""
    
    def __init__(self):
        pass
    
    async def gather_context(self) -> Dict[str, Any]:
        """Gather all available context information."""
        context = {
            'time': self._get_time_context(),
            'system': self._get_system_context(),
            'weather': await self._get_weather_context(),
        }
        
        logger.debug(f"Gathered context: {context}")
        return context
    
    def _get_time_context(self) -> Dict[str, Any]:
        """Get current time and date information."""
        now = datetime.now()
        
        return {
            'hour': now.hour,
            'minute': now.minute,
            'day_name': now.strftime('%A'),
            'date': now.strftime('%Y-%m-%d'),
            'formatted_time': now.strftime('%H:%M'),
            'formatted_date': now.strftime('%B %d, %Y'),
            'is_weekend': now.weekday() >= 5,
            'is_morning': 5 <= now.hour < 12,
            'is_afternoon': 12 <= now.hour < 17,
            'is_evening': 17 <= now.hour < 22,
            'is_night': now.hour < 5 or now.hour >= 22,
        }
    
    def _get_system_context(self) -> Dict[str, Any]:
        """Get system information."""
        try:
            # Get username
            username = os.getenv('USER') or os.getenv('USERNAME') or 'user'
            
            # Get hostname
            hostname = os.uname().nodename if hasattr(os, 'uname') else 'unknown'
            
            # Get system stats
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get uptime
            boot_time = psutil.boot_time()
            uptime_seconds = datetime.now().timestamp() - boot_time
            uptime_minutes = int(uptime_seconds / 60)
            
            # Get load average (Linux specific)
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            return {
                'username': username,
                'hostname': hostname,
                'uptime_minutes': uptime_minutes,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 1),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 1),
                'load_average': round(load_avg[0], 2),
                'cpu_count': psutil.cpu_count(),
                'is_fresh_boot': uptime_minutes < 5,
            }
            
        except Exception as e:
            logger.error(f"Error gathering system context: {e}")
            return {
                'username': os.getenv('USER', 'user'),
                'hostname': 'unknown',
                'uptime_minutes': 0,
                'memory_percent': 0,
                'disk_percent': 0,
                'load_average': 0,
                'cpu_count': 1,
                'is_fresh_boot': True,
            }
    
    async def _get_weather_context(self) -> Dict[str, Any]:
        """Get weather information (placeholder for now)."""
        # TODO: Implement weather API integration
        # For now, return empty context
        return {
            'temperature': None,
            'description': None,
            'humidity': None,
            'available': False,
        }
    
    def _get_network_context(self) -> Dict[str, Any]:
        """Get network connectivity information."""
        try:
            # Check network interfaces
            interfaces = psutil.net_if_stats()
            active_interfaces = []
            
            for interface, stats in interfaces.items():
                if interface != "lo" and stats.isup:
                    active_interfaces.append(interface)
            
            # Get network IO stats
            net_io = psutil.net_io_counters()
            
            return {
                'active_interfaces': active_interfaces,
                'has_network': len(active_interfaces) > 0,
                'bytes_sent': net_io.bytes_sent if net_io else 0,
                'bytes_recv': net_io.bytes_recv if net_io else 0,
            }
            
        except Exception as e:
            logger.error(f"Error gathering network context: {e}")
            return {
                'active_interfaces': [],
                'has_network': False,
                'bytes_sent': 0,
                'bytes_recv': 0,
            }
    
    def _get_process_context(self) -> Dict[str, Any]:
        """Get information about running processes."""
        try:
            processes = list(psutil.process_iter(['pid', 'name', 'cpu_percent']))
            
            # Filter out system processes and get top CPU consumers
            user_processes = []
            for proc in processes:
                try:
                    if proc.info['name'] not in ['kernel', 'kthreadd', 'migration', 'rcu_']:
                        user_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage
            user_processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            return {
                'total_processes': len(processes),
                'user_processes': len(user_processes),
                'top_processes': user_processes[:5],  # Top 5 by CPU
            }
            
        except Exception as e:
            logger.error(f"Error gathering process context: {e}")
            return {
                'total_processes': 0,
                'user_processes': 0,
                'top_processes': [],
            }
