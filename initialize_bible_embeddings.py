#!/usr/bin/env python3
"""
Initialize Bible embeddings for the RAG system.
This script processes all Bible verses and commentary data to create vector embeddings.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.bible_data_service import BibleDataService
from app.services.vector_service import VectorService
from app.services.bible_rag_service import BibleRAGService

async def initialize_bsb_embeddings():
    """Initialize BSB (Berean Study Bible) embeddings."""
    print("📖 Initializing BSB embeddings...")
    
    try:
        bible_data_service = BibleDataService()
        vector_service = VectorService()
        
        # Initialize vector service
        await vector_service.initialize()
        
        # Load BSB verses
        print("   Loading BSB verses...")
        bsb_df = await bible_data_service.load_bible_verses("BSB")
        print(f"   Loaded {len(bsb_df)} BSB verses")
        
        # Create embeddings
        print("   Creating embeddings (this may take several minutes)...")
        start_time = datetime.now()
        
        success = await vector_service.create_verse_embeddings(bsb_df, "BSB")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if success:
            print(f"   ✅ BSB embeddings created successfully in {duration:.1f} seconds")
            
            # Test search
            test_results = await vector_service.search_verses("love", translation="BSB", limit=3)
            print(f"   🔍 Test search found {len(test_results)} results")
            
            return True
        else:
            print("   ❌ Failed to create BSB embeddings")
            return False
            
    except Exception as e:
        print(f"   ❌ Error creating BSB embeddings: {e}")
        import traceback
        traceback.print_exc()
        return False

async def initialize_kjv_embeddings():
    """Initialize KJV (King James Version) embeddings."""
    print("\n📖 Initializing KJV embeddings...")
    
    try:
        bible_data_service = BibleDataService()
        vector_service = VectorService()
        
        # Load KJV verses
        print("   Loading KJV verses...")
        kjv_df = await bible_data_service.load_bible_verses("KJV")
        print(f"   Loaded {len(kjv_df)} KJV verses")
        
        # Create embeddings
        print("   Creating embeddings (this may take several minutes)...")
        start_time = datetime.now()
        
        success = await vector_service.create_verse_embeddings(kjv_df, "KJV")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if success:
            print(f"   ✅ KJV embeddings created successfully in {duration:.1f} seconds")
            
            # Test search
            test_results = await vector_service.search_verses("faith", translation="KJV", limit=3)
            print(f"   🔍 Test search found {len(test_results)} results")
            
            return True
        else:
            print("   ❌ Failed to create KJV embeddings")
            return False
            
    except Exception as e:
        print(f"   ❌ Error creating KJV embeddings: {e}")
        import traceback
        traceback.print_exc()
        return False

async def initialize_commentary_embeddings():
    """Initialize commentary embeddings."""
    print("\n📚 Initializing commentary embeddings...")
    
    try:
        bible_data_service = BibleDataService()
        vector_service = VectorService()
        
        # Load commentary data
        print("   Loading commentary data...")
        commentary_df = await bible_data_service.get_commentary_data()
        print(f"   Loaded {len(commentary_df)} commentary entries")
        
        if len(commentary_df) == 0:
            print("   ⚠️  No commentary data found, skipping...")
            return True
        
        # Create embeddings
        print("   Creating commentary embeddings (this may take several minutes)...")
        start_time = datetime.now()
        
        success = await vector_service.create_commentary_embeddings(commentary_df)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if success:
            print(f"   ✅ Commentary embeddings created successfully in {duration:.1f} seconds")
            
            # Test search
            test_results = await vector_service.search_commentary("salvation", limit=3)
            print(f"   🔍 Test search found {len(test_results)} results")
            
            return True
        else:
            print("   ❌ Failed to create commentary embeddings")
            return False
            
    except Exception as e:
        print(f"   ❌ Error creating commentary embeddings: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_bible_rag_integration():
    """Test the complete Bible RAG system."""
    print("\n🧪 Testing Bible RAG integration...")
    
    try:
        bible_rag_service = BibleRAGService()
        
        # Initialize the service
        await bible_rag_service.initialize()
        print("   ✅ Bible RAG service initialized")
        
        # Test Bible question
        print("   Testing Bible question...")
        question = "What does the Bible say about love?"
        result = await bible_rag_service.ask_bible_question(question, translation="BSB")
        
        if result and not result.get('error'):
            print(f"   ✅ Question answered successfully")
            print(f"   📝 Answer preview: {result.get('answer', '')[:100]}...")
            print(f"   📚 Found {len(result.get('sources', []))} relevant verses")
            
            # Show top sources
            for i, source in enumerate(result.get('sources', [])[:2]):
                print(f"      {i+1}. {source.get('reference', 'Unknown')}")
        else:
            print(f"   ⚠️  Question answered with limited results: {result.get('error', 'Unknown error')}")
        
        # Test verse lookup
        print("   Testing verse lookup...")
        verse_result = await bible_rag_service.get_verse_with_context("John 3:16", translation="BSB")
        
        if verse_result and not verse_result.get('error'):
            print("   ✅ Verse lookup successful")
            verse_text = verse_result.get('verse', {}).get('text', '')
            print(f"   📖 John 3:16: {verse_text[:80]}...")
        else:
            print(f"   ❌ Verse lookup failed: {verse_result.get('error', 'Unknown error')}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error testing Bible RAG integration: {e}")
        import traceback
        traceback.print_exc()
        return False

async def show_collection_info():
    """Show information about created collections."""
    print("\n📊 Collection Information:")
    
    try:
        vector_service = VectorService()
        await vector_service.initialize()
        
        info = await vector_service.get_collection_info()
        
        if info:
            for collection_name, details in info.items():
                print(f"   📁 {collection_name}: {details.get('count', 0)} items")
        else:
            print("   ⚠️  No collections found")
            
    except Exception as e:
        print(f"   ❌ Error getting collection info: {e}")

async def main():
    """Main initialization function."""
    print("🚀 ARIA Bible RAG Embedding Initialization")
    print("=" * 50)
    
    start_time = datetime.now()
    
    # Check if we're using Docker configuration
    database_url = os.getenv("DATABASE_URL", "")
    if "postgresql" in database_url:
        print("🐳 Using Docker PostgreSQL configuration")
    else:
        print("💾 Using local SQLite configuration")
    
    print()
    
    tasks = [
        ("BSB Embeddings", initialize_bsb_embeddings),
        ("KJV Embeddings", initialize_kjv_embeddings),
        ("Commentary Embeddings", initialize_commentary_embeddings),
        ("Bible RAG Integration Test", test_bible_rag_integration)
    ]
    
    results = []
    
    for task_name, task_func in tasks:
        try:
            success = await task_func()
            results.append((task_name, success))
        except Exception as e:
            print(f"❌ {task_name} failed with exception: {e}")
            results.append((task_name, False))
    
    # Show collection information
    await show_collection_info()
    
    # Summary
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 50)
    print("📊 INITIALIZATION RESULTS")
    print("=" * 50)
    
    passed = 0
    for task_name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status} {task_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tasks completed successfully")
    print(f"⏱️  Total time: {total_duration:.1f} seconds")
    
    if passed == len(results):
        print("🎉 Bible RAG system fully initialized and ready!")
        print("\n🚀 Next steps:")
        print("   1. Test API endpoints: python3 -m uvicorn app.main:app --reload")
        print("   2. Try Bible queries through the API")
        print("   3. Integrate with ARIA's main conversation flow")
    else:
        print("⚠️  Some initialization tasks failed. Check the errors above.")
        print("\n💡 Troubleshooting:")
        print("   1. Ensure Docker containers are running")
        print("   2. Check database connections")
        print("   3. Verify Bible data files exist in bible-data/ directory")

if __name__ == "__main__":
    asyncio.run(main())
