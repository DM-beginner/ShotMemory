import hashlib


class TokenUtil:
    @classmethod
    def make_hash_token(cls, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
