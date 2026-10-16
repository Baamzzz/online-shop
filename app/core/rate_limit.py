"""Rate limiting, used to slow down brute-force password guessing."""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Limits are counted per client IP address
limiter = Limiter(key_func=get_remote_address)