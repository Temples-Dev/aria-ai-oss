"""
Boot monitoring service to detect when Linux boot process completes.
"""

import asyncio
import logging
import os
import time
import psutil
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.greeting_service import GreetingService

logger = logging.getLogger(__name__)


class BootMonitor:
    """Monitors system boot completion and triggers greeting."""
    
    def __init__(self):
        self.greeting_service = GreetingService()
        self.boot_complete = False
        self.boot_start_time = time.time()
        
    async def start_monitoring(self):
        """Start monitoring for boot completion."""
        logger.info("Starting boot monitoring...")
        
        # Check if we're actually in a boot scenario
        if not self._is_fresh_boot():
            logger.info("System appears to be already running, triggering greeting immediately")
            await self._trigger_greeting()
            return
            
        # Monitor boot completion
        timeout = time.time() + settings.BOOT_TIMEOUT
        
        while time.time() < timeout and not self.boot_complete:
            if await self._check_boot_complete():
                logger.info("Boot completion detected!")
                await self._trigger_greeting()
                break
                
            await asyncio.sleep(settings.BOOT_CHECK_INTERVAL)
            
        if not self.boot_complete:
            logger.warning("Boot monitoring timed out")
    
    def _is_fresh_boot(self) -> bool:
        """Check if this is a fresh boot (system uptime < 2 minutes)."""
        try:
            uptime = time.time() - psutil.boot_time()
            return uptime < 120  # Less than 2 minutes
        except Exception as e:
            logger.error(f"Error checking uptime: {e}")
            return False
    
    async def _check_boot_complete(self) -> bool:
        """Check various indicators that boot is complete."""
        try:
            # Check 1: System load has stabilized (load average < 1.0)
            load_avg = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
            if load_avg > 1.0:
                logger.debug(f"System load still high: {load_avg}")
                return False
            
            # Check 2: Essential services are running
            if not self._check_essential_services():
                logger.debug("Essential services not yet running")
                return False
            
            # Check 3: Desktop environment is ready (if applicable)
            if not self._check_desktop_ready():
                logger.debug("Desktop environment not ready")
                return False
            
            # Check 4: Network is available
            if not self._check_network_ready():
                logger.debug("Network not ready")
                return False
            
            logger.info("All boot completion checks passed")
            return True
            
        except Exception as e:
            logger.error(f"Error checking boot completion: {e}")
            return False
    
    def _check_essential_services(self) -> bool:
        """Check if essential system services are running."""
        try:
            # Check if systemd is fully operational
            systemd_ready = Path("/run/systemd/system").exists()
            
            # Check if basic services are running
            essential_processes = ["systemd", "dbus"]
            running_processes = [p.name() for p in psutil.process_iter(['name'])]
            
            for process in essential_processes:
                if process not in running_processes:
                    return False
            
            return systemd_ready
            
        except Exception as e:
            logger.error(f"Error checking essential services: {e}")
            return False
    
    def _check_desktop_ready(self) -> bool:
        """Check if desktop environment is ready."""
        try:
            # Check for X11 or Wayland session
            display_env = any([
                "DISPLAY" in os.environ,
                "WAYLAND_DISPLAY" in os.environ,
                "XDG_SESSION_TYPE" in os.environ
            ])
            
            # If no display environment, assume headless (ready)
            if not display_env:
                return True
            
            # Check if desktop processes are running
            desktop_processes = ["gnome-shell", "kde", "xfce", "i3", "sway"]
            running_processes = [p.name() for p in psutil.process_iter(['name'])]
            
            # If any desktop environment is detected, check if it's running
            for desktop in desktop_processes:
                if any(desktop.lower() in proc.lower() for proc in running_processes):
                    return True
            
            # If display env exists but no desktop detected, wait a bit more
            return False
            
        except Exception as e:
            logger.error(f"Error checking desktop readiness: {e}")
            return True  # Assume ready on error
    
    def _check_network_ready(self) -> bool:
        """Check if network connectivity is available."""
        try:
            # Check if any network interface is up (excluding loopback)
            interfaces = psutil.net_if_stats()
            for interface, stats in interfaces.items():
                if interface != "lo" and stats.isup:
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Error checking network readiness: {e}")
            return True  # Assume ready on error
    
    async def _trigger_greeting(self):
        """Trigger the greeting service."""
        try:
            self.boot_complete = True
            logger.info("Triggering boot greeting...")
            await self.greeting_service.deliver_boot_greeting()
            
        except Exception as e:
            logger.error(f"Error triggering greeting: {e}")


