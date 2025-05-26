import datetime
import hashlib
import json


class Block:
    def __init__(self, index: int, timestamp: datetime.datetime, previous_hash: str) -> None:
        self.index: int = index
        self.timestamp: datetime.datetime = timestamp
        self.previous_hash: str = previous_hash
        self.hash: str = self.hash_block()

    def to_dict_without_hash(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp.isoformat(),
            "previous_hash": self.previous_hash,
        }

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp.isoformat(),
            "previous_hash": self.previous_hash,
            "hash": self.hash,
        }

    def hash_block(self) -> str:
        block_data = json.dumps(self.to_dict_without_hash(), sort_keys=True).encode()
        return hashlib.sha256(block_data).hexdigest()

    def __str__(self) -> str:
        return f"Block index: {self.index}, timestamp: {self.timestamp}, previous_hash: {self.previous_hash}, hash: {self.hash}"

GENESIS_BLOCK = Block(
    index=1,
    timestamp=datetime.datetime(1970, 1, 1, 0, 0, 0),
    previous_hash="genesis",
)
