# ARIA Troubleshooting Guide 🔧

This document covers common installation and runtime issues encountered with ARIA and their solutions.

## Installation Issues

### 1. Python 3.13 Compatibility & Rust Compilation Errors

**Problem**: 
```bash
error: Microsoft Visual C++ 14.0 is required
# OR
error: could not compile `pydantic-core`
# OR  
Building wheel for pydantic-core (pyproject.toml) ... error
```

**Cause**: 
- Python 3.13 is very new and some packages require Rust compilation
- Pydantic v2 requires Rust compiler for `pydantic-core`

**Solution**:
```bash
# Use flexible version ranges in requirements.txt
fastapi>=0.100.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
# Instead of pinned versions like pydantic==2.5.0
```

**Fixed in**: Commit `9a7cdda` - Updated requirements.txt with compatible versions

---

### 2. Systemd Service Permission Errors

**Problem**:
```bash
aria.service: Failed to determine supplementary groups: Operation not permitted
aria.service: Failed at step GROUP spawning: Operation not permitted
```

**Cause**: 
- User systemd services should not have `User=` and `Group=` directives
- These directives cause permission conflicts in user service context

**Solution**:
```bash
# Remove from aria.service file:
User=shelemiah     # ❌ Remove this
Group=shelemiah    # ❌ Remove this

# Keep only:
[Service]
Type=simple
WorkingDirectory=/home/shelemiah/Personal/aria_ai
```

**Fixed in**: Commit `e8e46cd` - Removed User/Group directives from service file

---

## Audio & Speech Issues

### 3. Text-to-Speech Not Working (No Audio Output)

**Problem**:
```bash
# In logs:
TTS engine initialized successfully
Greeting delivered successfully via speech
# But no audio is heard
```

**Cause**: Missing audio utilities and TTS engines

**Solutions**:

#### Install espeak-ng (Text-to-Speech Engine)
```bash
# Arch Linux / Manjaro
sudo pacman -S espeak-ng

# Ubuntu / Debian
sudo apt install espeak-ng espeak-ng-data

# Fedora / RHEL
sudo dnf install espeak-ng

# openSUSE
sudo zypper install espeak-ng
```

#### Install ALSA Audio Utilities
```bash
# Arch Linux / Manjaro  
sudo pacman -S alsa-utils

# Ubuntu / Debian
sudo apt install alsa-utils

# Fedora / RHEL
sudo dnf install alsa-utils

# openSUSE
sudo zypper install alsa-utils
```

**Verification**:
```bash
# Test if espeak works
espeak "Hello, this is a test"

# Test if aplay works  
aplay /usr/share/sounds/alsa/Front_Left.wav

# Test ARIA speech
curl -X POST http://localhost:8000/api/v1/speech/test
```

---

### 4. Audio Output Routing Issues

**Problem**:
```bash
# In logs:
sh: line 1: aplay: command not found
Exception ignored on calling ctypes callback function
```

**Cause**: 
- Missing `aplay` command (part of alsa-utils)
- Audio system not properly configured

**Solutions**:

1. **Install missing audio tools**:
   ```bash
   sudo pacman -S alsa-utils pulseaudio-alsa  # Arch
   sudo apt install alsa-utils pulseaudio     # Ubuntu
   ```

2. **Check audio devices**:
   ```bash
   aplay -l                    # List audio devices
   amixer                      # Check volume levels
   pulseaudio --check -v       # Check PulseAudio status
   ```

3. **Test audio output**:
   ```bash
   speaker-test -c 2           # Test speakers
   espeak "Audio test"         # Test TTS directly
   ```

---

## Service & Boot Issues

### 5. Boot Greeting Not Triggered

**Problem**: Service starts but no automatic greeting on boot

**Debugging Steps**:

1. **Check service status**:
   ```bash
   systemctl --user status aria
   journalctl --user -u aria -f
   ```

2. **Check boot detection logs**:
   ```bash
   journalctl --user -u aria --since "10 minutes ago" | grep -i boot
   ```

3. **Manual greeting test**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/greeting/deliver
   ```

**Common Causes**:
- Boot detection logic considers system "already running" if uptime > 2 minutes
- Ollama service not running when ARIA starts
- Network connectivity issues during boot

**Solutions**:
- Ensure Ollama starts before ARIA: `systemctl --user enable ollama`
- Adjust boot detection timeout in `.env`: `BOOT_TIMEOUT=600`
- Check network connectivity: Service waits for `network.target`

---

### 6. Ollama Connection Issues

**Problem**:
```bash
Network error calling Ollama
Error generating greeting
```

**Solutions**:

1. **Start Ollama service**:
   ```bash
   ollama serve &
   # OR
   systemctl --user start ollama  # if service is installed
   ```

2. **Check Ollama status**:
   ```bash
   curl http://localhost:11434/api/tags
   ollama list
   ```

3. **Pull required model**:
   ```bash
   ollama pull llama2:7b
   ```

4. **Verify ARIA can connect**:
   ```bash
   curl http://localhost:8000/api/v1/ai/models
   ```

---

## Configuration Issues

### 7. Environment Variables Not Loading

**Problem**: ARIA uses default settings instead of `.env` file

**Solution**:
```bash
# Ensure .env file exists in project root
ls -la /home/shelemiah/Personal/aria_ai/.env

# Check file permissions
chmod 644 .env

# Verify service WorkingDirectory
systemctl --user cat aria | grep WorkingDirectory
```

**Sample .env file**:
```env
# ARIA Configuration
DEBUG=false
HOST=127.0.0.1
PORT=8000

# AI Model Settings
OLLAMA_HOST=http://localhost:11434
MODEL_NAME=llama2:7b

# Speech Settings
TTS_ENABLED=true
TTS_RATE=200

# Boot Monitoring
BOOT_CHECK_INTERVAL=5
BOOT_TIMEOUT=300
```

---

## Performance Issues

### 8. High CPU Usage During Greeting Generation

**Problem**: System becomes slow when generating greetings

**Solutions**:

1. **Use smaller AI model**:
   ```bash
   ollama pull llama2:7b-chat-q4_0  # Quantized version
   # Update .env: MODEL_NAME=llama2:7b-chat-q4_0
   ```

2. **Adjust generation parameters**:
   ```python
   # In ai_service.py, reduce max_tokens
   "options": {
       "temperature": 0.7,
       "top_p": 0.9,
       "max_tokens": 50  # Reduced from 100
   }
   ```

3. **Limit concurrent requests**:
   ```bash
   # Only one greeting at a time
   systemctl --user restart aria
   ```

---

## Diagnostic Commands

### Quick Health Check
```bash
# Service status
systemctl --user status aria

# API health
curl http://localhost:8000/api/v1/health

# Test all services  
curl http://localhost:8000/api/v1/services/test

# Manual greeting
curl -X POST http://localhost:8000/api/v1/greeting/deliver
```

### Log Analysis
```bash
# Recent logs
journalctl --user -u aria -n 50

# Follow logs in real-time
journalctl --user -u aria -f

# Filter for errors
journalctl --user -u aria | grep -i error

# Boot-related logs
journalctl --user -u aria --since "boot" | grep -i "boot\|greeting"
```

### Audio Debugging
```bash
# Test TTS engine
espeak "ARIA audio test"

# Test system audio
aplay /usr/share/sounds/alsa/Front_Left.wav

# Check audio devices
aplay -l
amixer scontrols

# Test ARIA speech
curl -X POST http://localhost:8000/api/v1/speech/test
```

---

## Getting Help

If you encounter issues not covered here:

1. **Check logs first**: `journalctl --user -u aria -f`
2. **Test components individually**: Use the diagnostic commands above
3. **Verify dependencies**: Ensure Ollama, espeak-ng, and alsa-utils are installed
4. **Check permissions**: Ensure service files have correct permissions
5. **Create GitHub issue**: Include logs and system information

### System Information Template
```bash
# Include this information when reporting issues:
uname -a                           # System info
python3 --version                  # Python version
systemctl --user status aria      # Service status
journalctl --user -u aria -n 20   # Recent logs
curl http://localhost:8000/api/v1/health  # API status
```

---

## Prevention

### Recommended Installation Order
1. Install system dependencies first (espeak-ng, alsa-utils)
2. Install and configure Ollama
3. Run ARIA installation script
4. Test each component before enabling auto-start

### Regular Maintenance
```bash
# Update AI model
ollama pull llama2:7b

# Check service health
curl http://localhost:8000/api/v1/services/test

# Review logs for issues
journalctl --user -u aria --since "1 week ago" | grep -i error
```
