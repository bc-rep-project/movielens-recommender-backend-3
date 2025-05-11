"""
Custom exception classes for the application.
These are used across different modules for consistent error handling.
"""

class BaseAppException(Exception):
    """Base class for all application exceptions"""
    pass


class MovieNotFoundError(BaseAppException):
    """Raised when a movie is not found in the database"""
    pass


class RecommendationServiceError(BaseAppException):
    """Raised when there is an error in the recommendation service"""
    pass


class InteractionServiceError(BaseAppException):
    """Raised when there is an error in the interaction service"""
    pass


class AuthenticationError(BaseAppException):
    """Raised when there is an authentication error"""
    pass


class DatabaseError(BaseAppException):
    """Raised when there is a database error"""
    pass


class ValidationError(BaseAppException):
    """Raised when there is a validation error"""
    pass 