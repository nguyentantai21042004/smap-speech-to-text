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
    _providers: Dict[Type, Callable[[], Any]] = {}

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
        if interface in cls._instances:
            return cls._instances[interface]
        if interface in cls._providers:
            return cls._providers[interface]()
        raise KeyError(f"No provider registered for {interface.__name__}")

    @classmethod
    def clear(cls):
        """Clear all registrations (useful for testing)."""
        cls._instances.clear()
        cls._factories.clear()
        cls._providers.clear()


def bootstrap_container():
    """
    Initialize the dependency injection container.
    Register all dependencies here.
    """
    # Currently no dependencies to register for stateless service
    # as TranscribeService is self-contained or instantiated directly.
    pass
