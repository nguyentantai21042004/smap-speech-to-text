"""
Dependency Injection Container.
"""

from typing import Any, Dict, Type, TypeVar, Optional, Callable

T = TypeVar("T")


class Container:
    """
    Simple Dependency Injection Container.
    """

    _instances: Dict[Type, Any] = {}
    _factories: Dict[Type, Callable[[], Any]] = {}

    @classmethod
    def register(cls, interface: Type[T], instance: Any) -> None:
        """Register a singleton instance for an interface."""
        cls._instances[interface] = instance

    @classmethod
    def register_factory(cls, interface: Type[T], factory: Callable[[], T]) -> None:
        """Register a factory for an interface."""
        cls._providers[interface] = factory

    @classmethod
    def resolve(cls, interface: Type[T]) -> T:
        """Resolve an interface to its implementation."""
        if interface not in cls._providers:
            raise KeyError(f"No provider registered for {interface.__name__}")
        return cls._providers[interface]()

    @classmethod
    def clear(cls):
        """Clear all registrations (useful for testing)."""
        cls._instances.clear()
        cls._factories.clear()
