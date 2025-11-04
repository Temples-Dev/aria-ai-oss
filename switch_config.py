#!/usr/bin/env python3
"""
Script to switch between different environment configurations.
"""

import shutil
import os
import sys

def switch_to_docker():
    """Switch to Docker configuration."""
    try:
        if os.path.exists('.env.docker'):
            # Backup current .env
            if os.path.exists('.env'):
                shutil.copy('.env', '.env.backup')
                print("📋 Backed up current .env to .env.backup")
            
            # Copy Docker config to .env
            shutil.copy('.env.docker', '.env')
            print("✅ Switched to Docker configuration")
            print("🐳 Using PostgreSQL and Redis from Docker containers")
            return True
        else:
            print("❌ .env.docker file not found")
            return False
    except Exception as e:
        print(f"❌ Error switching to Docker config: {e}")
        return False

def switch_to_local():
    """Switch to local SQLite configuration."""
    try:
        if os.path.exists('.env.backup'):
            shutil.copy('.env.backup', '.env')
            print("✅ Restored local configuration from backup")
        else:
            # Create basic local config
            local_config = """# ARIA - Adaptive Responsive Intelligence Assistant Configuration
DEBUG=false
HOST=127.0.0.1
PORT=8000

# AI Model Settings
OLLAMA_HOST=http://localhost:11434
MODEL_NAME=llama2:7b

# Speech Settings
TTS_ENABLED=true
TTS_RATE=150
TTS_VOLUME=0.8
TTS_FESTIVAL_VOICE=cmu_us_slt_cg

# Boot Monitoring
BOOT_CHECK_INTERVAL=5
BOOT_TIMEOUT=300

# Database Configuration (Local SQLite)
DATABASE_URL=sqlite:///./aria.db

# Redis Configuration (Local)
REDIS_URL=redis://localhost:6379/0
"""
            with open('.env', 'w') as f:
                f.write(local_config)
            print("✅ Created local SQLite configuration")
        
        print("💾 Using local SQLite database and Redis")
        return True
    except Exception as e:
        print(f"❌ Error switching to local config: {e}")
        return False

def show_current_config():
    """Show current configuration."""
    try:
        if os.path.exists('.env'):
            print("📋 Current .env configuration:")
            with open('.env', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        print(f"   {line.strip()}")
        else:
            print("❌ No .env file found")
    except Exception as e:
        print(f"❌ Error reading config: {e}")

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("🔧 ARIA Configuration Switcher")
        print("Usage:")
        print("  python3 switch_config.py docker   # Switch to Docker (PostgreSQL + Redis)")
        print("  python3 switch_config.py local    # Switch to Local (SQLite + Redis)")
        print("  python3 switch_config.py show     # Show current configuration")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'docker':
        if switch_to_docker():
            print("\n🚀 Ready to test with Docker services!")
            print("   Run: python3 test_docker_connections.py")
    elif command == 'local':
        if switch_to_local():
            print("\n🚀 Ready to test with local services!")
            print("   Run: python3 test_bible_rag.py")
    elif command == 'show':
        show_current_config()
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: docker, local, show")

if __name__ == "__main__":
    main()
