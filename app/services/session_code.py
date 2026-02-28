import random
import string


def generate_session_code(length: int = 6) -> str:
    """Generate a random uppercase alphanumeric session code."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=length))
