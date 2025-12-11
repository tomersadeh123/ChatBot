import time
import functools
from typing import Callable, Optional, Any
from utils.key_bank import get_keybank


def retry_with_key_rotation(max_attempts: int = 3, backoff: float = 1.5, penalize_seconds: float = 1.5):
    """Decorator for retrying API calls with key rotation on failures.

    Args:
        max_attempts: Maximum number of retry attempts
        backoff: Exponential backoff multiplier
        penalize_seconds: How long to penalize a failed key

    Usage:
        @retry_with_key_rotation(max_attempts=3)
        def call_api(key_index):
            # Make API call
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            keybank = get_keybank()

            for attempt in range(max_attempts):
                try:
                    # If the function needs a key_index, it should get it separately
                    result = func(*args, **kwargs)
                    return result

                except Exception as e:
                    last_exception = e
                    error_msg = str(e).lower()

                    # Determine if this is a retryable error
                    is_rate_limit = 'rate' in error_msg or 'quota' in error_msg or '429' in error_msg
                    is_timeout = 'timeout' in error_msg or 'timed out' in error_msg
                    is_connection = 'connection' in error_msg or 'network' in error_msg

                    is_retryable = is_rate_limit or is_timeout or is_connection

                    if not is_retryable or attempt == max_attempts - 1:
                        # Not retryable or last attempt - raise
                        raise

                    # Penalize the current key if we have a key_index in kwargs
                    if 'key_index' in kwargs:
                        key_idx = kwargs['key_index']
                        keybank.penalize_key(key_idx, seconds=penalize_seconds)

                    # Calculate wait time with exponential backoff
                    wait_time = backoff ** attempt

                    print(f"[RETRY] attempt={attempt+1}/{max_attempts} error={type(e).__name__} "
                          f"wait={wait_time:.2f}s retryable={is_retryable}", flush=True)

                    time.sleep(wait_time)

            # If we get here, all attempts failed
            raise last_exception

        return wrapper
    return decorator


def safe_call(fallback_value: Any = None, log_errors: bool = True):
    """Decorator for safe function calls with graceful degradation.

    Args:
        fallback_value: Value to return if function raises an exception
        log_errors: Whether to log errors

    Usage:
        @safe_call(fallback_value="")
        def risky_function():
            # Might fail
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    try:
                        print(f"[SAFE_CALL] {func.__name__} failed: {type(e).__name__}: {e}", flush=True)
                    except Exception:
                        pass
                return fallback_value
        return wrapper
    return decorator


class ErrorContext:
    """Context manager for error handling with logging."""

    def __init__(self, operation: str, raise_on_error: bool = False, log_prefix: str = "ERROR"):
        self.operation = operation
        self.raise_on_error = raise_on_error
        self.log_prefix = log_prefix

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            try:
                print(f"[{self.log_prefix}] operation={self.operation} "
                      f"error={exc_type.__name__}: {exc_val}", flush=True)
            except Exception:
                pass

            if self.raise_on_error:
                return False  # Re-raise the exception
            return True  # Suppress the exception
        return True


def log_errors(operation: str):
    """Decorator to log errors without suppressing them.

    Usage:
        @log_errors("groq_api_call")
        def call_groq():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                try:
                    print(f"[ERROR] operation={operation} function={func.__name__} "
                          f"error={type(e).__name__}: {e}", flush=True)
                except Exception:
                    pass
                raise  # Re-raise the original exception
        return wrapper
    return decorator
