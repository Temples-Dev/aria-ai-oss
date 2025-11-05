"""
Unlock detection service for monitoring laptop unlock events.
"""

import logging
import asyncio
import time
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta

from app.core.config import settings

# Try to import D-Bus for session monitoring
try:
    import pydbus
    from gi.repository import GLib
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False

logger = logging.getLogger(__name__)


class UnlockDetectionService:
    """Service for detecting laptop unlock events and triggering welcome messages."""
    
    def __init__(self):
        self.enabled = True
        self.monitoring = False
        self.last_unlock_time = None
        self.unlock_count = 0
        self.session_start_time = None
        self.unlock_callbacks = []
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required dependencies are available."""
        try:
            if not DBUS_AVAILABLE:
                logger.warning("D-Bus not available - using fallback unlock detection")
                # We'll implement a fallback method
            else:
                logger.info("D-Bus available for unlock detection")
            
            logger.info("Unlock detection service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize unlock detection service: {e}")
            self.enabled = False
    
    def add_unlock_callback(self, callback: Callable):
        """Add a callback function to be called when unlock is detected."""
        self.unlock_callbacks.append(callback)
        logger.info(f"Added unlock callback: {callback.__name__}")
    
    async def start_monitoring(self):
        """Start monitoring for unlock events."""
        if not self.enabled:
            logger.warning("Unlock detection service is not enabled")
            return
        
        if self.monitoring:
            logger.info("Unlock detection is already monitoring")
            return
        
        self.monitoring = True
        self.session_start_time = datetime.now()
        logger.info("Starting unlock detection monitoring...")
        
        if DBUS_AVAILABLE:
            # Start D-Bus monitoring in background
            asyncio.create_task(self._monitor_dbus_session())
        else:
            # Start fallback monitoring
            asyncio.create_task(self._monitor_fallback())
    
    async def stop_monitoring(self):
        """Stop monitoring for unlock events."""
        self.monitoring = False
        logger.info("Stopped unlock detection monitoring")
    
    async def _monitor_dbus_session(self):
        """Monitor D-Bus for session unlock events."""
        try:
            import concurrent.futures
            
            def setup_dbus_monitoring():
                try:
                    # Connect to session bus
                    bus = pydbus.SessionBus()
                    
                    # Monitor screen saver interface
                    try:
                        screensaver = bus.get('org.gnome.ScreenSaver', '/org/gnome/ScreenSaver')
                        screensaver.ActiveChanged.connect(self._on_screensaver_changed)
                        logger.info("Connected to GNOME ScreenSaver D-Bus interface")
                    except Exception as e:
                        logger.debug(f"GNOME ScreenSaver not available: {e}")
                    
                    # Monitor session manager
                    try:
                        session_manager = bus.get('org.gnome.SessionManager', '/org/gnome/SessionManager')
                        # Note: SessionManager doesn't have direct unlock events, but we can monitor presence
                        logger.info("Connected to GNOME SessionManager D-Bus interface")
                    except Exception as e:
                        logger.debug(f"GNOME SessionManager not available: {e}")
                    
                    # Monitor login manager (systemd-logind)
                    try:
                        login_manager = bus.get('org.freedesktop.login1', '/org/freedesktop/login1')
                        # Monitor session changes
                        logger.info("Connected to systemd-logind D-Bus interface")
                    except Exception as e:
                        logger.debug(f"systemd-logind not available: {e}")
                    
                    return True
                    
                except Exception as e:
                    logger.error(f"Failed to setup D-Bus monitoring: {e}")
                    return False
            
            # Setup D-Bus monitoring in thread
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                success = await loop.run_in_executor(executor, setup_dbus_monitoring)
            
            if success:
                logger.info("D-Bus unlock detection monitoring active")
                # Keep monitoring alive
                while self.monitoring:
                    await asyncio.sleep(1)
            else:
                logger.warning("D-Bus setup failed, falling back to alternative method")
                await self._monitor_fallback()
                
        except Exception as e:
            logger.error(f"Error in D-Bus monitoring: {e}")
            await self._monitor_fallback()
    
    def _on_screensaver_changed(self, active):
        """Callback for screensaver state changes."""
        if not active:  # Screen unlocked
            logger.info("Screen unlock detected via D-Bus screensaver")
            asyncio.create_task(self._handle_unlock_event())
    
    async def _monitor_fallback(self):
        """Fallback monitoring method using process and file system monitoring."""
        logger.info("Using fallback unlock detection method")
        
        last_activity_time = time.time()
        idle_threshold = 60  # Consider system idle after 60 seconds
        
        while self.monitoring:
            try:
                current_time = time.time()
                
                # Check for system activity indicators
                activity_detected = await self._check_system_activity()
                
                if activity_detected:
                    # Check if we were idle and now have activity (potential unlock)
                    if current_time - last_activity_time > idle_threshold:
                        logger.info("System activity detected after idle period - potential unlock")
                        await self._handle_unlock_event()
                    
                    last_activity_time = current_time
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in fallback monitoring: {e}")
                await asyncio.sleep(10)
    
    async def _check_system_activity(self) -> bool:
        """Check for system activity indicators."""
        try:
            import psutil
            
            # Check CPU usage (activity indicator)
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Check if there are active user processes
            user_processes = 0
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    if proc.info['username'] and proc.info['username'] != 'root':
                        user_processes += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Consider activity if CPU > 10% or many user processes
            return cpu_percent > 10 or user_processes > 20
            
        except Exception as e:
            logger.debug(f"Error checking system activity: {e}")
            return False
    
    async def _handle_unlock_event(self):
        """Handle detected unlock event."""
        try:
            current_time = datetime.now()
            
            # Avoid duplicate unlock events within short time window
            if (self.last_unlock_time and 
                current_time - self.last_unlock_time < timedelta(seconds=30)):
                logger.debug("Ignoring duplicate unlock event")
                return
            
            self.last_unlock_time = current_time
            self.unlock_count += 1
            
            logger.info(f"Unlock event #{self.unlock_count} detected at {current_time}")
            
            # Call all registered callbacks
            for callback in self.unlock_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(self._get_unlock_context())
                    else:
                        callback(self._get_unlock_context())
                except Exception as e:
                    logger.error(f"Error in unlock callback {callback.__name__}: {e}")
            
        except Exception as e:
            logger.error(f"Error handling unlock event: {e}")
    
    def _get_unlock_context(self) -> Dict[str, Any]:
        """Get context information about the unlock event."""
        current_time = datetime.now()
        session_duration = None
        
        if self.session_start_time:
            session_duration = current_time - self.session_start_time
        
        return {
            "unlock_time": current_time,
            "unlock_count": self.unlock_count,
            "session_start_time": self.session_start_time,
            "session_duration": session_duration,
            "time_since_last_unlock": (
                current_time - self.last_unlock_time if self.last_unlock_time else None
            )
        }
    
    async def trigger_welcome_message(self, context: Dict[str, Any]):
        """Trigger a welcome message based on unlock context."""
        try:
            # Import here to avoid circular imports
            from app.services.speech_service import SpeechService
            from app.services.ai_service import AIService
            from app.services.context_service import ContextService
            from app.services.context_memory_service import ContextMemoryService
            
            # Store unlock event in context memory
            context_memory = ContextMemoryService()
            await context_memory.store_system_event(
                event_type="unlock",
                event_data=context
            )
            
            # Get system context
            context_service = ContextService()
            system_context = await context_service.gather_context()
            
            # Add unlock-specific context
            system_context['unlock'] = context
            
            # Generate contextual welcome message
            ai_service = AIService()
            welcome_message = await ai_service.generate_unlock_welcome(system_context)
            
            # Store the welcome message in context memory
            await context_memory.store_system_event(
                event_type="unlock",
                event_data=context,
                response_text=welcome_message
            )
            
            # Speak the welcome message
            speech_service = SpeechService()
            await speech_service.speak_with_fallback(welcome_message)
            
            logger.info(f"Welcome message delivered: {welcome_message}")
            
        except Exception as e:
            logger.error(f"Error generating welcome message: {e}")
            # Fallback to simple welcome
            try:
                from app.services.speech_service import SpeechService
                speech_service = SpeechService()
                await speech_service.speak_with_fallback("Welcome back! ARIA is ready to assist you.")
            except Exception as e2:
                logger.error(f"Error with fallback welcome message: {e2}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get unlock detection service status."""
        return {
            "enabled": self.enabled,
            "monitoring": self.monitoring,
            "unlock_count": self.unlock_count,
            "last_unlock_time": self.last_unlock_time.isoformat() if self.last_unlock_time else None,
            "session_start_time": self.session_start_time.isoformat() if self.session_start_time else None,
            "dbus_available": DBUS_AVAILABLE,
            "callbacks_registered": len(self.unlock_callbacks)
        }
    
    async def test_unlock_detection(self) -> Dict[str, Any]:
        """Test unlock detection by simulating an unlock event."""
        try:
            logger.info("Testing unlock detection...")
            await self._handle_unlock_event()
            
            return {
                "success": True,
                "message": "Unlock detection test completed",
                "context": self._get_unlock_context()
            }
            
        except Exception as e:
            logger.error(f"Error testing unlock detection: {e}")
            return {
                "success": False,
                "message": f"Unlock detection test failed: {str(e)}"
            }
