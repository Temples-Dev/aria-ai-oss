"""
Bible data service for loading and processing Bible text data.
"""

import logging
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import re

logger = logging.getLogger(__name__)


class BibleDataService:
    """Service for loading and processing Bible data from CSV files."""
    
    def __init__(self, data_dir: str = "bible-data"):
        self.data_dir = Path(data_dir)
        self._verses_cache = {}
        self._commentary_cache = {}
    
    async def load_bible_verses(self, translation: str = "BSB") -> pd.DataFrame:
        """
        Load Bible verses from CSV file.
        
        Args:
            translation: Bible translation (BSB or KJV)
            
        Returns:
            DataFrame with columns: Book, Chapter, Verse, Text
        """
        try:
            if translation in self._verses_cache:
                return self._verses_cache[translation]
            
            file_path = self.data_dir / f"{translation}.csv"
            if not file_path.exists():
                raise FileNotFoundError(f"Bible data file not found: {file_path}")
            
            logger.info(f"Loading {translation} Bible data from {file_path}")
            df = pd.read_csv(file_path)
            
            # Clean and standardize the data
            df = self._clean_verse_data(df, translation)
            
            # Cache the data
            self._verses_cache[translation] = df
            
            logger.info(f"Loaded {len(df)} verses from {translation}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading Bible verses for {translation}: {e}")
            raise
    
    async def load_commentary_data(self) -> pd.DataFrame:
        """
        Load Bible commentary data from CSV file.
        
        Returns:
            DataFrame with commentary data
        """
        try:
            if 'commentary' in self._commentary_cache:
                return self._commentary_cache['commentary']
            
            file_path = self.data_dir / "data-commentaries.csv"
            if not file_path.exists():
                raise FileNotFoundError(f"Commentary data file not found: {file_path}")
            
            logger.info(f"Loading commentary data from {file_path}")
            df = pd.read_csv(file_path)
            
            # Clean and process commentary data
            df = self._clean_commentary_data(df)
            
            # Cache the data
            self._commentary_cache['commentary'] = df
            
            logger.info(f"Loaded {len(df)} commentary entries")
            return df
            
        except Exception as e:
            logger.error(f"Error loading commentary data: {e}")
            raise
    
    def _clean_verse_data(self, df: pd.DataFrame, translation: str) -> pd.DataFrame:
        """Clean and standardize verse data."""
        # Remove any rows with missing essential data
        df = df.dropna(subset=['Book', 'Chapter', 'Verse', 'Text'])
        
        # Clean and standardize the data
        df = df.copy()  # Create explicit copy to avoid warnings
        df.loc[:, 'Text'] = df['Text'].str.strip()
        
        # Add translation info
        df.loc[:, 'Translation'] = translation
        
        # Create unique verse ID
        df.loc[:, 'VerseId'] = df['Book'] + '_' + df['Chapter'].astype(str) + '_' + df['Verse'].astype(str)
        
        # Create reference string
        df.loc[:, 'Reference'] = df['Book'] + ' ' + df['Chapter'].astype(str) + ':' + df['Verse'].astype(str)
        
        return df
    
    async def get_verses_by_translation(self, translation: str = "BSB") -> pd.DataFrame:
        """Get verses by translation as DataFrame."""
        return await self.load_bible_verses(translation)
    
    async def get_commentary_data(self) -> pd.DataFrame:
        """Get commentary data as DataFrame."""
        return await self.load_commentary_data_df()
    
    async def load_commentary_data_df(self) -> pd.DataFrame:
        """Load commentary data as DataFrame."""
        try:
            file_path = self.data_dir / "data-commentaries.csv"
            if not file_path.exists():
                logger.warning(f"Commentary file not found: {file_path}")
                return pd.DataFrame()
            
            df = pd.read_csv(file_path)
            return self._clean_commentary_data(df)
            
        except Exception as e:
            logger.error(f"Error loading commentary data: {e}")
            return pd.DataFrame()
    
    async def load_bible_data(self, translation: str = "BSB") -> List[Dict[str, Any]]:
        """Load Bible data and return as list of dictionaries."""
        try:
            verses_df = await self.get_verses_by_translation(translation)
            return verses_df.to_dict('records')
        except Exception as e:
            logger.error(f"Error loading Bible data for {translation}: {e}")
            return []
    
    async def load_commentary_data(self) -> List[Dict[str, Any]]:
        """Load commentary data and return as list of dictionaries."""
        try:
            commentary_df = await self.get_commentary_data()
            return commentary_df.to_dict('records')
        except Exception as e:
            logger.error(f"Error loading commentary data: {e}")
            return []
    
    def _clean_commentary_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and process commentary data."""
        # Remove rows with missing essential data
        df = df.dropna(subset=['txt'])
        
        # Clean commentary text
        df['txt'] = df['txt'].str.strip()
        
        # Parse location information if available
        if 'location_start' in df.columns and 'location_end' in df.columns:
            df['location_start'] = pd.to_numeric(df['location_start'], errors='coerce')
            df['location_end'] = pd.to_numeric(df['location_end'], errors='coerce')
        
        return df
    
    async def get_verse_by_reference(self, reference: str, translation: str = "BSB") -> Optional[Dict[str, Any]]:
        """
        Get a specific verse by reference (e.g., "Genesis 1:1").
        
        Args:
            reference: Bible reference string
            translation: Bible translation
            
        Returns:
            Dictionary with verse data or None if not found
        """
        try:
            df = await self.load_bible_verses(translation)
            
            # Parse reference
            book, chapter_verse = self._parse_reference(reference)
            if not book or not chapter_verse:
                return None
            
            chapter, verse = chapter_verse
            
            # Find the verse
            result = df[
                (df['Book'].str.lower() == book.lower()) &
                (df['Chapter'] == chapter) &
                (df['Verse'] == verse)
            ]
            
            if result.empty:
                return None
            
            return result.iloc[0].to_dict()
            
        except Exception as e:
            logger.error(f"Error getting verse by reference {reference}: {e}")
            return None
    
    async def search_verses_by_text(self, query: str, translation: str = "BSB", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search verses by text content (simple text search).
        
        Args:
            query: Search query
            translation: Bible translation
            limit: Maximum number of results
            
        Returns:
            List of matching verses
        """
        try:
            df = await self.load_bible_verses(translation)
            
            # Simple text search (case-insensitive)
            mask = df['Text'].str.contains(query, case=False, na=False)
            results = df[mask].head(limit)
            
            return results.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error searching verses by text: {e}")
            return []
    
    async def get_verses_by_book(self, book: str, translation: str = "BSB") -> List[Dict[str, Any]]:
        """
        Get all verses from a specific book.
        
        Args:
            book: Book name
            translation: Bible translation
            
        Returns:
            List of verses from the book
        """
        try:
            df = await self.load_bible_verses(translation)
            
            # Filter by book (case-insensitive)
            results = df[df['Book'].str.lower() == book.lower()]
            
            return results.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error getting verses by book {book}: {e}")
            return []
    
    async def get_chapter(self, book: str, chapter: int, translation: str = "BSB") -> List[Dict[str, Any]]:
        """
        Get all verses from a specific chapter.
        
        Args:
            book: Book name
            chapter: Chapter number
            translation: Bible translation
            
        Returns:
            List of verses from the chapter
        """
        try:
            df = await self.load_bible_verses(translation)
            
            # Filter by book and chapter
            results = df[
                (df['Book'].str.lower() == book.lower()) &
                (df['Chapter'] == chapter)
            ].sort_values('Verse')
            
            return results.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error getting chapter {book} {chapter}: {e}")
            return []
    
    def _parse_reference(self, reference: str) -> Tuple[Optional[str], Optional[Tuple[int, int]]]:
        """
        Parse a Bible reference string.
        
        Args:
            reference: Reference like "Genesis 1:1" or "John 3:16"
            
        Returns:
            Tuple of (book_name, (chapter, verse)) or (None, None) if invalid
        """
        try:
            # Pattern to match "Book Chapter:Verse"
            pattern = r'^(.+?)\s+(\d+):(\d+)$'
            match = re.match(pattern, reference.strip())
            
            if match:
                book = match.group(1).strip()
                chapter = int(match.group(2))
                verse = int(match.group(3))
                return book, (chapter, verse)
            
            return None, None
            
        except Exception as e:
            logger.error(f"Error parsing reference {reference}: {e}")
            return None, None
    
    async def get_available_books(self, translation: str = "BSB") -> List[str]:
        """
        Get list of available books in the Bible.
        
        Args:
            translation: Bible translation
            
        Returns:
            List of book names
        """
        try:
            df = await self.load_bible_verses(translation)
            return sorted(df['Book'].unique().tolist())
            
        except Exception as e:
            logger.error(f"Error getting available books: {e}")
            return []
    
    async def get_data_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the loaded Bible data.
        
        Returns:
            Dictionary with data statistics
        """
        try:
            stats = {}
            
            # Verse statistics
            for translation in ['BSB', 'KJV']:
                try:
                    df = await self.load_bible_verses(translation)
                    stats[translation] = {
                        'total_verses': len(df),
                        'total_books': df['Book'].nunique(),
                        'avg_verse_length': df['Text'].str.len().mean()
                    }
                except Exception:
                    stats[translation] = {'error': 'Failed to load'}
            
            # Commentary statistics
            try:
                commentary_df = await self.load_commentary_data()
                stats['commentary'] = {
                    'total_entries': len(commentary_df),
                    'avg_entry_length': commentary_df['txt'].str.len().mean()
                }
            except Exception:
                stats['commentary'] = {'error': 'Failed to load'}
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting data stats: {e}")
            return {'error': str(e)}
