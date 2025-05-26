import datetime
import hashlib
import json
import sqlite3

import psycopg2
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor
from genesis import Block, GENESIS_BLOCK

class Blockchain:
    def __init__(self, db_config: dict[str, str]|None, db_type: str = "postgresql", db_sqlite_in_memory: bool = False) -> None:
        self.db_type = db_type
        self.db_config = db_config
        self.db_sqlite_in_memory = db_sqlite_in_memory
        self.height: int = 0
        self.chain: list[Block] = []

        self.conn = self.connect_to_db()
        self.create_table()
        self.load_chain()

    def connect_to_db(self) -> connection:
        try:
            if self.db_type == "sqlite":
                if self.db_sqlite_in_memory:
                    conn = sqlite3.connect(":memory:")
                else:
                    conn = sqlite3.connect("blockchain.db")
                conn.row_factory = sqlite3.Row
                print("Connected to SQLite database successfully!")
            else:
                conn = psycopg2.connect(**self.db_config)
                print("Connected to PostgreSQL database successfully!")
            return conn
        except Exception as e:
            raise Exception(f"Error connecting to database: {e}")

    def create_table(self) -> None:
        if self.db_type == "sqlite":
            create_table_query = """
                CREATE TABLE IF NOT EXISTS blockchain (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    hash TEXT NOT NULL UNIQUE
                );
            """
        else:
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
            with self.conn:
                cursor = self.conn.cursor() if self.db_type == "postgresql" else self.conn
                cursor.execute(create_table_query)
                self.conn.commit() if self.db_type == "postgresql" else None
        except Exception as e:
            raise Exception(f"Error creating blockchain table: {e}")

    def load_chain(self):
        try:
            if self.db_type == "sqlite":
                cursor = self.conn.cursor()
                cursor.execute("SELECT * FROM blockchain ORDER BY id ASC;")
                rows = cursor.fetchall()
                for row in rows:
                    index = row["id"]
                    timestamp = datetime.datetime.fromisoformat(row["timestamp"])
                    previous_hash = row["previous_hash"]
                    # If this is the genesis block, use the shared one
                    block = GENESIS_BLOCK if index == 1 else Block(index, timestamp, previous_hash)
                    self.chain.append(block)
                self.height = rows[-1]["id"] if rows else 0

            else:
                cursor = self.conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT * FROM blockchain ORDER BY index ASC;")
                rows = cursor.fetchall()
                for row in rows:
                    index = row["index"]
                    timestamp = row["timestamp"]
                    previous_hash = row["previous_hash"]
                    # If this is the genesis block, use the shared one
                    block = GENESIS_BLOCK if index == 1 else Block(index, timestamp, previous_hash)
                    self.chain.append(block)
                self.height = rows[-1]["index"] if rows else 0

            if self.chain:
                if not self.validate_chain():
                    raise Exception("Blockchain validation failed.")
            else:
                # If no chain exists in DB, use predefined shared genesis block
                self.add_block_to_db(GENESIS_BLOCK)
                self.chain.append(GENESIS_BLOCK)
                self.height = 1

        except Exception as e:
            raise Exception(f"Error loading blockchain: {e}")

    def add_block_to_db(self, block: Block) -> None:
        if not self.validate_block(block):
            raise Exception(f"Invalid block {block.index} detected. Aborting addition.")

        try:
            if self.db_type == "sqlite":
                cursor = self.conn.cursor()
                query = """
                    INSERT INTO blockchain (timestamp, previous_hash, hash)
                    VALUES (?, ?, ?);
                """
                values = (block.timestamp.isoformat(), block.previous_hash, block.hash)
                cursor.execute(query, values)
                self.conn.commit()
            else:
                with self.conn.cursor() as cursor:
                    query = """
                        INSERT INTO blockchain (timestamp, previous_hash, hash)
                        VALUES (%s, %s, %s);
                    """
                    values = (block.timestamp, block.previous_hash, block.hash)
                    cursor.execute(query, values)
                    self.conn.commit()
        except Exception as e:
            raise Exception(f"Error adding block to blockchain: {e}")


    def validate_block(self, block: Block) -> bool:
        if block.index == 1:
            if block.previous_hash != "genesis":
                print(f"Invalid genesis block: expected genesis, got {block.previous_hash}")
                return False
            if block.hash != block.hash_block():
                print("Invalid genesis block: hash mismatch")
                return False

            return True

        if block.hash != block.hash_block():
            print(f"Block {block.index} has an invalid hash.")
            return False
        if block.index != self.chain[-1].index + 1:
            print(f"Block {block.index} has an invalid index. Expected: {self.chain[-1].index + 1}, received: {block.index}.")
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

