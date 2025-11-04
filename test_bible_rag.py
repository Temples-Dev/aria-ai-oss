#!/usr/bin/env python3
"""
Test script for Bible RAG functionality.
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.bible_rag_service import BibleRAGService
from app.services.bible_data_service import BibleDataService
from app.services.vector_service import VectorService

async def test_bible_data_loading():
    """Test Bible data loading."""
    print("🔍 Testing Bible data loading...")
    
    bible_data_service = BibleDataService()
    
    try:
        # Test loading BSB data
        bsb_verses = await bible_data_service.load_bible_data("BSB")
        print(f"✅ Loaded {len(bsb_verses)} BSB verses")
        
        # Show a sample verse
        if bsb_verses:
            sample = bsb_verses[0]
            book = sample.get('Book', sample.get('book', 'Unknown'))
            chapter = sample.get('Chapter', sample.get('chapter', 0))
            verse = sample.get('Verse', sample.get('verse', 0))
            text = sample.get('Text', sample.get('text', ''))
            print(f"📖 Sample verse: {book} {chapter}:{verse}")
            print(f"   Text: {text[:100]}...")
        
        # Test loading KJV data
        kjv_verses = await bible_data_service.load_bible_data("KJV")
        print(f"✅ Loaded {len(kjv_verses)} KJV verses")
        
        # Test loading commentary data
        commentary = await bible_data_service.load_commentary_data()
        print(f"✅ Loaded {len(commentary)} commentary entries")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading Bible data: {e}")
        return False

async def test_vector_service():
    """Test vector embedding and search."""
    print("\n🔍 Testing vector service...")
    
    vector_service = VectorService()
    
    try:
        # Initialize the service
        await vector_service.initialize()
        print("✅ Vector service initialized")
        
        # Test creating embeddings for sample verses
        sample_verses = [
            {"id": "test1", "Book": "John", "Chapter": 3, "Verse": 16, 
             "Text": "For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life.", 
             "Translation": "BSB"},
            {"id": "test2", "Book": "Romans", "Chapter": 8, "Verse": 28, 
             "Text": "And we know that in all things God works for the good of those who love him, who have been called according to his purpose.", 
             "Translation": "BSB"},
            {"id": "test3", "Book": "Philippians", "Chapter": 4, "Verse": 13, 
             "Text": "I can do all this through him who gives me strength.", 
             "Translation": "BSB"}
        ]
        
        # Add verses to vector database
        await vector_service.add_verses(sample_verses)
        print(f"✅ Added {len(sample_verses)} sample verses to vector database")
        
        # Test semantic search
        search_results = await vector_service.search_verses("God's love", limit=2)
        print(f"✅ Search for 'God's love' returned {len(search_results)} results")
        
        for i, result in enumerate(search_results):
            score = result.get('score', 'N/A')
            score_str = f"{score:.3f}" if isinstance(score, (int, float)) else str(score)
            # Handle both uppercase and lowercase keys
            book = result.get('book', result.get('Book', 'Unknown'))
            chapter = result.get('chapter', result.get('Chapter', 0))
            verse = result.get('verse', result.get('Verse', 0))
            text = result.get('text', result.get('Text', result.get('document', '')))
            print(f"   {i+1}. {book} {chapter}:{verse} (score: {score_str})")
            print(f"      {text[:80]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing vector service: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_bible_rag_service():
    """Test the main Bible RAG service."""
    print("\n🔍 Testing Bible RAG service...")
    
    bible_rag_service = BibleRAGService()
    
    try:
        # Initialize the service
        await bible_rag_service.initialize()
        print("✅ Bible RAG service initialized")
        
        # Test asking a Bible question
        question = "What does the Bible say about love?"
        result = await bible_rag_service.ask_bible_question(question)
        
        print(f"✅ Asked question: '{question}'")
        print(f"📝 Answer: {result.get('answer', 'No answer')[:200]}...")
        print(f"📚 Found {len(result.get('sources', []))} relevant verses")
        
        # Show sources
        for i, source in enumerate(result.get('sources', [])[:3]):
            print(f"   {i+1}. {source['reference']}: {source['text'][:60]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Bible RAG service: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_verse_lookup():
    """Test verse lookup functionality."""
    print("\n🔍 Testing verse lookup...")
    
    bible_rag_service = BibleRAGService()
    
    try:
        # Test looking up a specific verse
        reference = "John 3:16"
        result = await bible_rag_service.get_verse_with_context(reference)
        
        if "error" not in result:
            print(f"✅ Found verse: {reference}")
            print(f"📖 Text: {result.get('verse', {}).get('text', 'No text')[:100]}...")
            print(f"🔗 Found {len(result.get('related_verses', []))} related verses")
        else:
            print(f"❌ Error looking up verse: {result['error']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing verse lookup: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("🚀 Starting Bible RAG Tests\n")
    
    tests = [
        ("Bible Data Loading", test_bible_data_loading),
        ("Vector Service", test_vector_service),
        ("Bible RAG Service", test_bible_rag_service),
        ("Verse Lookup", test_verse_lookup)
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
    print("📊 TEST RESULTS SUMMARY")
    print("="*50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Bible RAG is ready to use.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())
