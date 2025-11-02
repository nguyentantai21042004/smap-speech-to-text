"""
Utilities for MongoDB ObjectId conversion.
Handles conversion between ObjectId and string formats.
"""

from typing import Union, Optional
from bson import ObjectId
from bson.errors import InvalidId


def objectid_to_str(obj_id: Union[ObjectId, str, None]) -> Optional[str]:
    """
    Convert ObjectId to string.
    
    Args:
        obj_id: ObjectId instance, string, or None
        
    Returns:
        String representation of ObjectId, or None if input is None
        
    Examples:
        >>> objectid_to_str(ObjectId("507f1f77bcf86cd799439011"))
        '507f1f77bcf86cd799439011'
        >>> objectid_to_str("507f1f77bcf86cd799439011")
        '507f1f77bcf86cd799439011'
        >>> objectid_to_str(None)
        None
    """
    if obj_id is None:
        return None
    
    if isinstance(obj_id, str):
        # Already a string, validate it's a valid ObjectId string
        try:
            ObjectId(obj_id)
            return obj_id
        except InvalidId:
            raise ValueError(f"Invalid ObjectId string: {obj_id}")
    
    if isinstance(obj_id, ObjectId):
        return str(obj_id)
    
    raise TypeError(f"Cannot convert {type(obj_id)} to ObjectId string")


def str_to_objectid(obj_id_str: Union[str, ObjectId, None]) -> Optional[ObjectId]:
    """
    Convert string to ObjectId.
    
    Args:
        obj_id_str: String representation of ObjectId, ObjectId instance, or None
        
    Returns:
        ObjectId instance, or None if input is None
        
    Raises:
        ValueError: If string is not a valid ObjectId format
        
    Examples:
        >>> str_to_objectid("507f1f77bcf86cd799439011")
        ObjectId('507f1f77bcf86cd799439011')
        >>> str_to_objectid(ObjectId("507f1f77bcf86cd799439011"))
        ObjectId('507f1f77bcf86cd799439011')
        >>> str_to_objectid(None)
        None
    """
    if obj_id_str is None:
        return None
    
    if isinstance(obj_id_str, ObjectId):
        return obj_id_str
    
    if isinstance(obj_id_str, str):
        try:
            return ObjectId(obj_id_str)
        except InvalidId:
            raise ValueError(f"Invalid ObjectId string: {obj_id_str}")
    
    raise TypeError(f"Cannot convert {type(obj_id_str)} to ObjectId")


def is_valid_objectid(obj_id_str: Union[str, ObjectId, None]) -> bool:
    """
    Check if string is a valid ObjectId format.
    
    Args:
        obj_id_str: String, ObjectId, or None to validate
        
    Returns:
        True if valid ObjectId, False otherwise
        
    Examples:
        >>> is_valid_objectid("507f1f77bcf86cd799439011")
        True
        >>> is_valid_objectid("invalid")
        False
        >>> is_valid_objectid(None)
        False
    """
    if obj_id_str is None:
        return False
    
    if isinstance(obj_id_str, ObjectId):
        return True
    
    if isinstance(obj_id_str, str):
        try:
            ObjectId(obj_id_str)
            return True
        except (InvalidId, TypeError):
            return False
    
    return False

