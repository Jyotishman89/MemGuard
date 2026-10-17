import hashlib
import hmac
import os
 
_DEV_KEY = b"dev-insecure-key-change-me"
 
 
def get_key():
    k = os.environ.get("MEMGUARD_KEY")
    return k.encode() if k else _DEV_KEY
 
 
def sign(text: str) -> str:
    """Return the HMAC-SHA256 hex tag for this text under the secret key."""
    return hmac.new(get_key(), text.encode("utf-8"), hashlib.sha256).hexdigest()
 
 
def verify(text: str, signature: str) -> bool:
    """True only if `signature` is a valid tag for `text`. Constant-time compare."""
    if not signature:
        return False
    return hmac.compare_digest(sign(text), signature)
 