"""
Interface for Keyword Repository.
Defines the contract that all keyword repositories must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime


class IKeywordRepository(ABC):
    """Interface for keyword extraction repository operations."""

    @abstractmethod
    async def create(self, data: Dict) -> str:
        """
        Create a new keyword extraction record.
        
        Args:
            data: Dictionary containing extraction data
            
        Returns:
            str: ID of created record
        """
        pass

    @abstractmethod
    async def find_by_id(self, record_id: str) -> Optional[Dict]:
        """
        Find a keyword extraction record by ID.
        
        Args:
            record_id: ID of the record
            
        Returns:
            Optional[Dict]: Record data if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_text_hash(self, text_hash: str, method: str) -> Optional[Dict]:
        """
        Find a keyword extraction record by text hash and method.
        
        Args:
            text_hash: Hash of the input text
            method: Extraction method used
            
        Returns:
            Optional[Dict]: Record data if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_recent(
        self, 
        limit: int = 10, 
        method: Optional[str] = None
    ) -> List[Dict]:
        """
        Find recent keyword extraction records.
        
        Args:
            limit: Maximum number of records to return
            method: Optional filter by extraction method
            
        Returns:
            List[Dict]: List of recent records
        """
        pass

    @abstractmethod
    async def update(self, record_id: str, data: Dict) -> bool:
        """
        Update a keyword extraction record.
        
        Args:
            record_id: ID of the record
            data: Dictionary containing update data
            
        Returns:
            bool: True if update successful, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, record_id: str) -> bool:
        """
        Delete a keyword extraction record.
        
        Args:
            record_id: ID of the record
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_statistics(self) -> Dict:
        """
        Get statistics about keyword extractions.
        
        Returns:
            Dict: Statistics data
        """
        pass

    @abstractmethod
    async def count_by_method(self) -> Dict[str, int]:
        """
        Count records by extraction method.
        
        Returns:
            Dict[str, int]: Dictionary mapping method to count
        """
        pass

