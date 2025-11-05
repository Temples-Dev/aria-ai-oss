"""
Bible RAG (Retrieval-Augmented Generation) service for intelligent Bible study.
"""

import logging
from typing import Dict, List, Any, Optional
import asyncio
import httpx

from app.services.bible_data_service import BibleDataService
from app.services.vector_service import VectorService
from app.core.config import settings

logger = logging.getLogger(__name__)


class BibleRAGService:
    """Core service for Bible RAG functionality."""
    
    def __init__(self):
        self.bible_data_service = BibleDataService()
        self.vector_service = VectorService()
        self.client = httpx.AsyncClient(timeout=30.0)
        self._initialized = False
    
    async def initialize(self):
        """Initialize the Bible RAG service."""
        if self._initialized:
            return
        
        try:
            logger.info("Initializing Bible RAG service...")
            
            # Initialize vector service
            await self.vector_service.initialize()
            
            # Check if embeddings exist, create if needed
            await self._ensure_embeddings_exist()
            
            self._initialized = True
            logger.info("Bible RAG service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Bible RAG service: {e}")
            raise
    
    async def _ensure_embeddings_exist(self):
        """Ensure that embeddings exist for Bible data."""
        try:
            # Check existing collections
            collection_info = await self.vector_service.get_collection_info()
            
            # Check for verse embeddings
            for translation in ['BSB', 'KJV']:
                collection_name = f"bible_verses_{translation.lower()}"
                if collection_name not in collection_info:
                    logger.info(f"Creating embeddings for {translation}...")
                    verses_df = await self.bible_data_service.load_bible_verses(translation)
                    await self.vector_service.create_verse_embeddings(verses_df, translation)
            
            # Check for commentary embeddings
            if "bible_commentary" not in collection_info:
                logger.info("Creating commentary embeddings...")
                commentary_df = await self.bible_data_service.load_commentary_data()
                await self.vector_service.create_commentary_embeddings(commentary_df)
            
        except Exception as e:
            logger.error(f"Error ensuring embeddings exist: {e}")
            # Continue without embeddings - service can still work with basic text search
    
    async def ask_bible_question(self, question: str, translation: str = "BSB", include_commentary: bool = True) -> Dict[str, Any]:
        """
        Answer a Bible question using RAG.
        
        Args:
            question: User's Bible question
            translation: Bible translation to use
            include_commentary: Whether to include commentary in the response
            
        Returns:
            Dictionary with answer and supporting information
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            logger.info(f"Processing Bible question: '{question}'")
            
            # Search for relevant verses
            relevant_verses = await self.vector_service.search_verses(
                query=question,
                translation=translation,
                limit=5
            )
            
            # Search for relevant commentary if requested
            relevant_commentary = []
            if include_commentary:
                relevant_commentary = await self.vector_service.search_commentary(
                    query=question,
                    limit=3
                )
            
            # Build context for AI response
            context = self._build_bible_context(question, relevant_verses, relevant_commentary)
            
            # Generate AI response
            ai_response = await self._generate_bible_response(context)
            
            # Format final response
            response = {
                'question': question,
                'answer': ai_response,
                'supporting_verses': relevant_verses,
                'commentary': relevant_commentary if include_commentary else [],
                'translation': translation,
                'sources_count': len(relevant_verses) + len(relevant_commentary)
            }
            
            logger.info(f"Generated Bible answer with {response['sources_count']} sources")
            return response
            
        except Exception as e:
            logger.error(f"Error answering Bible question: {e}")
            return {
                'question': question,
                'answer': "I apologize, but I encountered an error while searching for an answer to your Bible question. Please try again.",
                'supporting_verses': [],
                'commentary': [],
                'translation': translation,
                'error': str(e)
            }
    
    async def get_verse_with_context(self, reference: str, translation: str = "BSB") -> Dict[str, Any]:
        """
        Get a specific verse with surrounding context and commentary.
        
        Args:
            reference: Bible reference (e.g., "John 3:16")
            translation: Bible translation
            
        Returns:
            Dictionary with verse and context information
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # Get the specific verse
            verse = await self.bible_data_service.get_verse_by_reference(reference, translation)
            if not verse:
                return {
                    'reference': reference,
                    'error': 'Verse not found',
                    'translation': translation
                }
            
            # Get surrounding verses for context
            book = verse['Book']
            chapter = verse['Chapter']
            verse_num = verse['Verse']
            
            # Get a few verses before and after for context
            context_verses = await self.bible_data_service.get_chapter(book, chapter, translation)
            
            # Filter to get surrounding context (±2 verses)
            surrounding_verses = [
                v for v in context_verses
                if abs(v['Verse'] - verse_num) <= 2
            ]
            
            # Search for related commentary
            commentary_query = f"{reference} {verse['Text'][:100]}"
            related_commentary = await self.vector_service.search_commentary(
                query=commentary_query,
                limit=2
            )
            
            return {
                'reference': reference,
                'verse': verse,
                'surrounding_verses': surrounding_verses,
                'commentary': related_commentary,
                'translation': translation
            }
            
        except Exception as e:
            logger.error(f"Error getting verse with context: {e}")
            return {
                'reference': reference,
                'error': str(e),
                'translation': translation
            }
    
    async def explore_topic(self, topic: str, translation: str = "BSB", limit: int = 10) -> Dict[str, Any]:
        """
        Explore a biblical topic with relevant verses and commentary.
        
        Args:
            topic: Topic to explore (e.g., "love", "forgiveness", "faith")
            translation: Bible translation
            limit: Maximum number of verses to return
            
        Returns:
            Dictionary with topic exploration results
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            logger.info(f"Exploring biblical topic: '{topic}'")
            
            # Search for verses related to the topic
            topic_verses = await self.vector_service.search_verses(
                query=topic,
                translation=translation,
                limit=limit
            )
            
            # Search for commentary on the topic
            topic_commentary = await self.vector_service.search_commentary(
                query=topic,
                limit=5
            )
            
            # Generate AI summary of the topic
            context = self._build_topic_context(topic, topic_verses, topic_commentary)
            topic_summary = await self._generate_topic_summary(context)
            
            return {
                'topic': topic,
                'summary': topic_summary,
                'verses': topic_verses,
                'commentary': topic_commentary,
                'translation': translation,
                'total_sources': len(topic_verses) + len(topic_commentary)
            }
            
        except Exception as e:
            logger.error(f"Error exploring topic: {e}")
            return {
                'topic': topic,
                'error': str(e),
                'translation': translation
            }
    
    async def get_daily_verse(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get a daily verse with AI-generated reflection.
        
        Args:
            context: Optional context (time, user preferences, etc.)
            
        Returns:
            Dictionary with daily verse and reflection
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            # For now, use a simple approach - could be enhanced with user preferences
            import random
            
            # Get a random encouraging verse (this could be improved with better selection logic)
            encouraging_topics = ["hope", "peace", "strength", "love", "faith", "joy", "comfort"]
            topic = random.choice(encouraging_topics)
            
            verses = await self.vector_service.search_verses(
                query=topic,
                translation="BSB",
                limit=3
            )
            
            if not verses:
                # Fallback to a well-known verse
                verse = await self.bible_data_service.get_verse_by_reference("Jeremiah 29:11", "BSB")
                verses = [verse] if verse else []
            
            if verses:
                selected_verse = verses[0]
                
                # Generate AI reflection
                reflection_context = f"""
                Daily verse: {selected_verse['reference']} - "{selected_verse['text']}"
                Topic focus: {topic}
                Context: Daily devotional reflection
                """
                
                reflection = await self._generate_daily_reflection(reflection_context)
                
                return {
                    'verse': selected_verse,
                    'reflection': reflection,
                    'topic': topic,
                    'date': context.get('date') if context else None
                }
            
            return {
                'error': 'Could not retrieve daily verse',
                'topic': topic
            }
            
        except Exception as e:
            logger.error(f"Error getting daily verse: {e}")
            return {'error': str(e)}
    
    def _build_bible_context(self, question: str, verses: List[Dict], commentary: List[Dict]) -> str:
        """Build context string for Bible question answering."""
        context = f"Bible Question: {question}\n\n"
        
        if verses:
            context += "Relevant Bible Verses:\n"
            for verse in verses:
                context += f"- {verse['reference']}: \"{verse['text']}\"\n"
            context += "\n"
        
        if commentary:
            context += "Relevant Commentary:\n"
            for comm in commentary:
                preview = comm.get('preview', comm.get('text', ''))[:200]
                context += f"- {preview}...\n"
            context += "\n"
        
        return context
    
    def _build_topic_context(self, topic: str, verses: List[Dict], commentary: List[Dict]) -> str:
        """Build context string for topic exploration."""
        context = f"Biblical Topic: {topic}\n\n"
        
        if verses:
            context += "Related Verses:\n"
            for verse in verses[:5]:  # Limit for context length
                context += f"- {verse['reference']}: \"{verse['text']}\"\n"
            context += "\n"
        
        if commentary:
            context += "Commentary Insights:\n"
            for comm in commentary[:3]:  # Limit for context length
                preview = comm.get('preview', comm.get('text', ''))[:150]
                context += f"- {preview}...\n"
            context += "\n"
        
        return context
    
    async def _generate_bible_response(self, context: str) -> str:
        """Generate AI response for Bible questions."""
        prompt = f"""You are a knowledgeable Bible study assistant. Answer the user's question based on the provided biblical context.

{context}

Provide a thoughtful, accurate answer that:
1. Directly addresses the question
2. References the relevant verses provided
3. Explains the biblical context and meaning
4. Is respectful of different interpretations
5. Is helpful for Bible study

Your response:"""
        
        try:
            # Use Ollama with custom prompt
            response = await self._call_ollama(prompt)
            return self._clean_response(response)
        except Exception as e:
            logger.error(f"Error generating Bible response: {e}")
            return "I apologize, but I'm having trouble generating a response right now. Please try again."
    
    async def _generate_topic_summary(self, context: str) -> str:
        """Generate AI summary for topic exploration."""
        prompt = f"""You are a Bible study assistant. Provide a comprehensive summary of the biblical topic based on the provided verses and commentary.

{context}

Create a summary that:
1. Explains what the Bible teaches about this topic
2. Highlights key themes and patterns
3. References specific verses when relevant
4. Is suitable for Bible study and reflection
5. Is encouraging and instructive

Your summary:"""
        
        try:
            response = await self._call_ollama(prompt)
            return self._clean_response(response)
        except Exception as e:
            logger.error(f"Error generating topic summary: {e}")
            return "I apologize, but I'm having trouble generating a summary right now. Please try again."
    
    async def _generate_daily_reflection(self, context: str) -> str:
        """Generate AI reflection for daily verse."""
        prompt = f"""You are a devotional writer. Create a brief, encouraging reflection based on the daily Bible verse.

{context}

Write a reflection that:
1. Explains the verse in practical terms
2. Offers encouragement and hope
3. Suggests how to apply it to daily life
4. Is warm and personal in tone
5. Is 2-3 sentences maximum

Your reflection:"""
        
        try:
            response = await self._call_ollama(prompt)
            return self._clean_response(response)
        except Exception as e:
            logger.error(f"Error generating daily reflection: {e}")
            return "May this verse bring you peace and encouragement today."
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get status of the Bible RAG service."""
        try:
            status = {
                'initialized': self._initialized,
                'bible_data': await self.bible_data_service.get_data_stats(),
                'vector_collections': await self.vector_service.get_collection_info() if self._initialized else {},
                'ai_service': 'available'  # Simplified status check
            }
            return status
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {'error': str(e)}
    
    async def _call_ollama(self, prompt: str) -> str:
        """Make API call to ARIA's AI generation endpoint."""
        try:
            payload = {
                "prompt": prompt,
                "model": settings.MODEL_NAME,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 300
                }
            }
            
            response = await self.client.post(
                f"http://{settings.HOST}:{settings.PORT}/api/v1/ai/generate",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "").strip()
            
        except Exception as e:
            logger.error(f"Error calling ARIA AI API: {e}")
            return ""
    
    def _clean_response(self, response: str) -> str:
        """Clean and format AI response."""
        if not response:
            return ""
        
        # Remove common AI prefixes/suffixes
        response = response.strip()
        
        # Remove quotes if the entire response is quoted
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        
        # Remove common AI response patterns
        patterns_to_remove = [
            "Here's my response:",
            "My response:",
            "Response:",
            "Answer:",
        ]
        
        for pattern in patterns_to_remove:
            if response.startswith(pattern):
                response = response[len(pattern):].strip()
        
        return response
