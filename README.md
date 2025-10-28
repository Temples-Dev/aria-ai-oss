# Smart AI Boot Greeter 🤖

A modular Linux boot greeting system that uses open-source AI models to deliver personalized, natural language greetings when your system finishes booting.

## Features

- **Boot Detection**: Automatically detects when Linux boot process completes
- **Natural Language Processing**: Uses open-source LLMs (via Ollama) for intelligent greeting generation
- **Text-to-Speech**: Delivers greetings via speech synthesis
- **Context Awareness**: Gathers system info, time, and environmental context
- **Modular Architecture**: Clean FastAPI-based architecture with separate services
- **No Interface**: Pure background service with optional API endpoints

## Quick Start

1. **Install the system**:
   ```bash
   ./install.sh
   ```

2. **Start the service**:
   ```bash
   systemctl --user start smart-greeter
   ```

3. **Test manually**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/greeting/deliver
   ```

## Architecture

```
├── main.py                 # FastAPI application entry point
├── app/
│   ├── core/
│   │   └── config.py       # Configuration settings
│   ├── services/
│   │   ├── boot_monitor.py     # Boot completion detection
│   │   ├── greeting_service.py # Main orchestration service
│   │   ├── ai_service.py       # LLM integration (Ollama)
│   │   ├── speech_service.py   # Text-to-speech
│   │   └── context_service.py  # System context gathering
│   └── api/
│       └── routes.py       # API endpoints
├── smart-greeter.service   # Systemd service file
└── install.sh             # Installation script
```

## Dependencies

- **Python 3.8+**
- **Ollama** (for AI model hosting)
- **FastAPI** (web framework)
- **pyttsx3** (text-to-speech)
- **psutil** (system information)

## Configuration

Edit `.env` file to customize:

```env
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

## API Endpoints

- `GET /` - Health check
- `POST /api/v1/greeting/deliver` - Trigger greeting
- `GET /api/v1/greeting/generate` - Generate greeting text only
- `GET /api/v1/context` - Get system context
- `GET /api/v1/services/test` - Test all services
- `POST /api/v1/speech/say` - Speak custom text

## How It Works

1. **Boot Monitoring**: Service monitors system indicators (load average, essential services, network) to detect boot completion
2. **Context Gathering**: Collects time, system info, user details
3. **AI Generation**: Sends context to local LLM to generate personalized greeting
4. **Speech Delivery**: Converts text to speech and plays through system audio

## Customization

### Change AI Model

```bash
# Pull a different model
ollama pull mistral:7b

# Update .env
MODEL_NAME=mistral:7b
```

### Disable Speech

```env
TTS_ENABLED=false
```

### Adjust Boot Detection

```env
BOOT_CHECK_INTERVAL=3    # Check every 3 seconds
BOOT_TIMEOUT=180         # Give up after 3 minutes
```

## Troubleshooting

### Check Service Status
```bash
systemctl --user status smart-greeter
```

### View Logs
```bash
journalctl --user -u smart-greeter -f
```

### Test Components
```bash
# Test all services
curl http://localhost:8000/api/v1/services/test

# Test speech
curl -X POST http://localhost:8000/api/v1/speech/test

# Check AI model
curl http://localhost:8000/api/v1/ai/models
```

### Common Issues

1. **No Speech Output**: Install espeak or festival
   ```bash
   sudo apt install espeak espeak-data
   ```

2. **Ollama Not Running**: Start Ollama service
   ```bash
   ollama serve
   ```

3. **Model Not Found**: Pull the model
   ```bash
   ollama pull llama2:7b
   ```

## Development

### Run in Development Mode
```bash
python main.py
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Test Individual Services
```python
from app.services.greeting_service import GreetingService

service = GreetingService()
result = await service.deliver_boot_greeting()
```

## Future Enhancements

- Weather integration
- Calendar awareness
- Voice interaction
- Cross-device synchronization
- Custom greeting templates
- Machine learning for personalization

## License

MIT License - Feel free to modify and distribute!

---

**Note**: This system is designed to be lightweight and run in the background. It only activates during boot completion and then remains dormant until the next boot cycle.
