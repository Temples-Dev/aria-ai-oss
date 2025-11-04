#!/usr/bin/env python3
"""
Test script for Docker database and Redis connections.
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.services.context_memory_service import ContextMemoryService

async def test_redis_connection():
    """Test Redis connection."""
    print("🔍 Testing Redis connection...")
    
    try:
        context_memory = ContextMemoryService()
        
        if context_memory.redis_client:
            # Test basic Redis operations
            test_key = "test:connection"
            test_value = "Hello Redis!"
            
            context_memory.redis_client.set(test_key, test_value, ex=60)  # 60 second expiry
            retrieved_value = context_memory.redis_client.get(test_key)
            
            if retrieved_value == test_value:
                print("✅ Redis connection successful!")
                print(f"   - Set and retrieved test value: {retrieved_value}")
                
                # Clean up
                context_memory.redis_client.delete(test_key)
                print("   - Test key cleaned up")
                
                return True
            else:
                print(f"❌ Redis value mismatch. Expected: {test_value}, Got: {retrieved_value}")
                return False
        else:
            print("❌ Redis client not initialized")
            return False
            
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

async def test_database_connection():
    """Test database connection."""
    print("\n🔍 Testing database connection...")
    
    try:
        from app.database.database import engine, SessionLocal
        from sqlalchemy import text
        
        # Test database connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            
            if test_value == 1:
                print("✅ Database connection successful!")
                print(f"   - Database URL: {settings.DATABASE_URL}")
                
                # Test session creation
                db = SessionLocal()
                try:
                    # Test a simple query
                    result = db.execute(text("SELECT COUNT(*) FROM sessions"))
                    session_count = result.fetchone()[0]
                    print(f"   - Sessions table accessible, count: {session_count}")
                    
                    return True
                finally:
                    db.close()
            else:
                print(f"❌ Database test query failed. Expected: 1, Got: {test_value}")
                return False
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_context_memory_service():
    """Test the full context memory service."""
    print("\n🔍 Testing Context Memory Service...")
    
    try:
        context_memory = ContextMemoryService()
        
        # Test storing a conversation
        conversation_id = await context_memory.store_conversation(
            user_input="Test question about Docker connections",
            aria_response="Docker connections are working properly!",
            conversation_type="test"
        )
        
        print(f"✅ Stored test conversation with ID: {conversation_id}")
        
        # Test retrieving recent conversations
        recent_conversations = await context_memory.get_recent_conversations(limit=5)
        print(f"✅ Retrieved {len(recent_conversations)} recent conversations")
        
        # Test user context
        await context_memory.set_user_context(
            context_key="test_docker_setup",
            context_value={"status": "testing", "timestamp": "2025-11-03"},
            context_type="test"
        )
        
        retrieved_context = await context_memory.get_user_context("test_docker_setup")
        if retrieved_context:
            print("✅ User context storage and retrieval working")
            print(f"   - Retrieved: {retrieved_context}")
        else:
            print("❌ User context retrieval failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Context Memory Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all connection tests."""
    print("🚀 Testing Docker Connections for ARIA\n")
    print(f"📋 Current Configuration:")
    print(f"   - Database URL: {settings.DATABASE_URL}")
    print(f"   - Redis URL: {settings.REDIS_URL}")
    print()
    
    tests = [
        ("Redis Connection", test_redis_connection),
        ("Database Connection", test_database_connection),
        ("Context Memory Service", test_context_memory_service)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 DOCKER CONNECTION TEST RESULTS")
    print("="*50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All Docker connections working! Ready for integration.")
    else:
        print("⚠️  Some connections failed. Check Docker services and configuration.")
        print("\n💡 To fix connection issues:")
        print("   1. Make sure Docker containers are running: docker-compose up -d")
        print("   2. Update .env file with correct Docker URLs")
        print("   3. Check Docker container logs: docker-compose logs")

if __name__ == "__main__":
    asyncio.run(main())
