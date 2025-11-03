"""
Vector service for generating embeddings and performing semantic search.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import uuid

logger = logging.getLogger(__name__)


class VectorService:
    """Service for generating embeddings and performing semantic search on Bible data."""
    
    def __init__(self, data_dir: str = "vector_data", model_name: str = "all-MiniLM-L6-v2"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.model_name = model_name
        self.model = None
        self.chroma_client = None
        self.collections = {}
        
    async def initialize(self):
        """Initialize the vector service."""
        try:
            logger.info("Initializing vector service...")
            
            # Initialize sentence transformer model
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            
            # Initialize ChromaDB
            logger.info("Initializing ChromaDB...")
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.data_dir / "chroma_db"),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            logger.info("Vector service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing vector service: {e}")
            raise
    
    async def create_verse_embeddings(self, verses_df: pd.DataFrame, translation: str) -> bool:
        """
        Create embeddings for Bible verses and store in vector database.
        
        Args:
            verses_df: DataFrame with Bible verses
            translation: Bible translation (BSB, KJV)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.model is None:
                await self.initialize()
            
            collection_name = f"bible_verses_{translation.lower()}"
            logger.info(f"Creating embeddings for {len(verses_df)} verses ({translation})")
            
            # Get or create collection
            try:
                collection = self.chroma_client.get_collection(collection_name)
                logger.info(f"Using existing collection: {collection_name}")
            except Exception:
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"translation": translation, "type": "verses"}
                )
                logger.info(f"Created new collection: {collection_name}")
            
            # Prepare texts for embedding
            texts = []
            metadatas = []
            ids = []
            
            for _, row in verses_df.iterrows():
                # Combine verse reference and text for better context
                text = f"{row['Reference']}: {row['Text']}"
                texts.append(text)
                
                metadata = {
                    "book": row['Book'],
                    "chapter": int(row['Chapter']),
                    "verse": int(row['Verse']),
                    "reference": row['Reference'],
                    "translation": translation,
                    "text": row['Text']
                }
                metadatas.append(metadata)
                
                # Use verse ID as unique identifier
                ids.append(f"{translation}_{row['VerseId']}")
            
            # Generate embeddings in batches to avoid memory issues
            batch_size = 100
            total_batches = (len(texts) + batch_size - 1) // batch_size
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size]
                batch_ids = ids[i:i + batch_size]
                
                logger.info(f"Processing batch {i//batch_size + 1}/{total_batches}")
                
                # Generate embeddings
                embeddings = self.model.encode(batch_texts, convert_to_numpy=True)
                
                # Add to collection
                collection.add(
                    embeddings=embeddings.tolist(),
                    metadatas=batch_metadatas,
                    documents=batch_texts,
                    ids=batch_ids
                )
                
                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)
            
            self.collections[collection_name] = collection
            logger.info(f"Successfully created embeddings for {translation}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating verse embeddings for {translation}: {e}")
            return False
    
    async def create_commentary_embeddings(self, commentary_df: pd.DataFrame) -> bool:
        """
        Create embeddings for Bible commentary data.
        
        Args:
            commentary_df: DataFrame with commentary data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.model is None:
                await self.initialize()
            
            collection_name = "bible_commentary"
            logger.info(f"Creating embeddings for {len(commentary_df)} commentary entries")
            
            # Get or create collection
            try:
                collection = self.chroma_client.get_collection(collection_name)
                logger.info(f"Using existing collection: {collection_name}")
            except Exception:
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"type": "commentary"}
                )
                logger.info(f"Created new collection: {collection_name}")
            
            # Prepare texts for embedding
            texts = []
            metadatas = []
            ids = []
            
            for _, row in commentary_df.iterrows():
                # Use commentary text
                text = row['txt']
                texts.append(text)
                
                metadata = {
                    "book": row.get('book', ''),
                    "father_name": row.get('father_name', ''),
                    "source_title": row.get('source_title', ''),
                    "text": text[:500]  # Truncate for metadata
                }
                metadatas.append(metadata)
                
                # Use row ID or generate one
                row_id = row.get('id', str(uuid.uuid4()))
                ids.append(f"commentary_{row_id}")
            
            # Generate embeddings in batches
            batch_size = 50  # Smaller batches for commentary (longer texts)
            total_batches = (len(texts) + batch_size - 1) // batch_size
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size]
                batch_ids = ids[i:i + batch_size]
                
                logger.info(f"Processing commentary batch {i//batch_size + 1}/{total_batches}")
                
                # Generate embeddings
                embeddings = self.model.encode(batch_texts, convert_to_numpy=True)
                
                # Add to collection
                collection.add(
                    embeddings=embeddings.tolist(),
                    metadatas=batch_metadatas,
                    documents=batch_texts,
                    ids=batch_ids
                )
                
                await asyncio.sleep(0.1)
            
            self.collections[collection_name] = collection
            logger.info("Successfully created commentary embeddings")
            return True
            
        except Exception as e:
            logger.error(f"Error creating commentary embeddings: {e}")
            return False
    
    async def search_verses(self, query: str, translation: str = "BSB", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for verses using semantic similarity.
        
        Args:
            query: Search query
            translation: Bible translation
            limit: Maximum number of results
            
        Returns:
            List of matching verses with similarity scores
        """
        try:
            if self.model is None:
                await self.initialize()
            
            collection_name = f"bible_verses_{translation.lower()}"
            
            # Get collection
            if collection_name not in self.collections:
                try:
                    self.collections[collection_name] = self.chroma_client.get_collection(collection_name)
                except Exception:
                    logger.error(f"Collection {collection_name} not found. Please create embeddings first.")
                    return []
            
            collection = self.collections[collection_name]
            
            # Generate query embedding
            query_embedding = self.model.encode([query], convert_to_numpy=True)
            
            # Search for similar verses
            results = collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=limit,
                include=['metadatas', 'documents', 'distances']
            )
            
            # Format results
            formatted_results = []
            if results['metadatas'] and results['metadatas'][0]:
                for i, metadata in enumerate(results['metadatas'][0]):
                    result = {
                        'book': metadata['book'],
                        'chapter': metadata['chapter'],
                        'verse': metadata['verse'],
                        'reference': metadata['reference'],
                        'text': metadata['text'],
                        'translation': metadata['translation'],
                        'similarity_score': 1 - results['distances'][0][i],  # Convert distance to similarity
                        'full_document': results['documents'][0][i]
                    }
                    formatted_results.append(result)
            
            logger.info(f"Found {len(formatted_results)} verses for query: '{query}'")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching verses: {e}")
            return []
    
    async def search_commentary(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Search for commentary using semantic similarity.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching commentary entries with similarity scores
        """
        try:
            if self.model is None:
                await self.initialize()
            
            collection_name = "bible_commentary"
            
            # Get collection
            if collection_name not in self.collections:
                try:
                    self.collections[collection_name] = self.chroma_client.get_collection(collection_name)
                except Exception:
                    logger.error(f"Collection {collection_name} not found. Please create embeddings first.")
                    return []
            
            collection = self.collections[collection_name]
            
            # Generate query embedding
            query_embedding = self.model.encode([query], convert_to_numpy=True)
            
            # Search for similar commentary
            results = collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=limit,
                include=['metadatas', 'documents', 'distances']
            )
            
            # Format results
            formatted_results = []
            if results['metadatas'] and results['metadatas'][0]:
                for i, metadata in enumerate(results['metadatas'][0]):
                    result = {
                        'book': metadata.get('book', ''),
                        'father_name': metadata.get('father_name', ''),
                        'source_title': metadata.get('source_title', ''),
                        'text': results['documents'][0][i],
                        'similarity_score': 1 - results['distances'][0][i],
                        'preview': metadata.get('text', '')[:200] + '...'
                    }
                    formatted_results.append(result)
            
            logger.info(f"Found {len(formatted_results)} commentary entries for query: '{query}'")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching commentary: {e}")
            return []
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about available collections.
        
        Returns:
            Dictionary with collection information
        """
        try:
            if self.chroma_client is None:
                await self.initialize()
            
            collections = self.chroma_client.list_collections()
            
            info = {}
            for collection in collections:
                try:
                    count = collection.count()
                    info[collection.name] = {
                        'count': count,
                        'metadata': collection.metadata
                    }
                except Exception as e:
                    info[collection.name] = {'error': str(e)}
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {'error': str(e)}
    
    async def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection from the vector database.
        
        Args:
            collection_name: Name of collection to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.chroma_client is None:
                await self.initialize()
            
            self.chroma_client.delete_collection(collection_name)
            
            # Remove from cache
            if collection_name in self.collections:
                del self.collections[collection_name]
            
            logger.info(f"Deleted collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting collection {collection_name}: {e}")
            return False
