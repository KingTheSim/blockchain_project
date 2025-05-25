import datetime
import hashlib
import json
import time
from typing import Dict

import psycopg2
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor


class Block:
    def __init__(
        self,
        index: int,
        timestamp: datetime.datetime,
        previous_hash: str,
    ) -> None:
        self.index: int = index
        self.timestamp: datetime.datetime = timestamp
        self.previous_hash: str = previous_hash
        self.hash: str = self.hash_block()

    def hash_block(self) -> str:
        block = json.dumps(self.to_dict_without_hash(), sort_keys=True).encode()
        return hashlib.sha256(block).hexdigest()

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

    def __str__(self) -> str:
        return f"Block index: {self.index}, timestamp: {self.timestamp}, previous_hash: {self.previous_hash}, hash: {self.hash}"


class Blockchain:
    def __init__(self, db_config: dict[str, str]) -> None:
        self.db_config = db_config
        self.height: int = 0
        self.chain: list[Block] = []

        self.conn = self.connect_to_db()
        self.create_table()
        self.load_chain()

    def connect_to_db(self) -> connection:
        try:
            conn = psycopg2.connect(**self.db_config)
            print("Connected to the database successfully!")
            return conn
        except Exception as e:
            raise Exception(f"Error connecting to database: {e}")

    def create_table(self) -> None:
        create_table_query = """
                CREATE TABLE IF NOT EXISTS blockchain (
                    index SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    previous_hash VARCHAR(64) NOT NULL,
                    hash VARCHAR(64) NOT NULL UNIQUE,
                    CONSTRAINT unique_index UNIQUE (index),
                    CONSTRAINT unique_previous_hash UNIQUE (previous_hash)
                );
            """

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(create_table_query)
                self.conn.commit()
        except Exception as e:
            raise Exception(f"Error creating blockchain table: {e}")

    def load_chain(self) -> None:
        """
        Load the blockchain from the database into memory.
        If it's the chain's start, initialize it with a genesis block.
        """
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM blockchain ORDER BY index ASC;")
                rows = cursor.fetchall()

                if rows:
                    for row in rows:
                        block = Block(
                            index=row["index"],
                            timestamp=row["timestamp"],
                            previous_hash=row["previous_hash"],
                        )
                        self.chain.append(block)
                    self.height = rows[-1]["index"]

                    if not self.validate_chain():
                        raise Exception("Blockchain validation failed.")
                else:
                    self.create_genesis_block()
        except Exception as e:
            raise Exception(f"Error loading blockchain: {e}")

    def create_genesis_block(self) -> None:
        """Create the genesis block"""
        genesis_block = Block(
            index=1,
            timestamp=datetime.datetime.now(),
            previous_hash="0",
        )
        self.add_block_to_db(genesis_block)
        self.chain.append(genesis_block)
        self.height = 1

    def add_block_to_db(self, block: Block) -> None:
        if not self.validate_block(block):
            raise Exception(f"Invalid block {block.index} detected. Aborting addition.")

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                                    INSERT INTO blockchain (timestamp, previous_hash, hash)
                                    VALUES (%s, %s, %s)
                                """,
                    (
                        block.timestamp,
                        block.previous_hash,
                        block.hash,
                    ),
                )
                self.conn.commit()
        except Exception as e:
            raise Exception(f"Error adding block to blockchain: {e}")

    def validate_block(self, block: Block) -> bool:
        if block.index == 1:
            if block.previous_hash != "0":
                print(f"Invalid genesis block: expected '0', got {block.previous_hash}")
                return False
            if block.hash != block.hash_block():
                print("Invalid genesis block: hash mismatch")
                return False

            return True

        if block.hash != block.hash_block():
            print(f"Block {block.index} has an invalid hash.")
            return False
        if block.index != self.chain[-1].index + 1:
            print(f"Block {block.index} has an invalid index.")
            return False

        return True

    def validate_chain(self) -> bool:
        for index, block in enumerate(self.chain):
            if not self.validate_block(block):
                print(f"Validation failed at block {index}.")
                return False
        return True

    def close_connection(self) -> None:
        self.conn.close()
