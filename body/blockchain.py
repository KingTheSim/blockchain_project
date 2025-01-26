import datetime
import hashlib
import json
import time
from typing import Dict, List

import psycopg2
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor


class Block:
    def __init__(
        self,
        index: int,
        timestamp,
        proof: int,
        previous_hash: str,
        mined_difficulty: int,
    ) -> None:
        self.index: int = index
        self.timestamp: datetime.datetime = timestamp
        self.proof: int = proof
        self.previous_hash: str = previous_hash
        self.mined_difficulty: int = mined_difficulty
        self.hash: str = self.hash_block()

    def hash_block(self) -> str:
        block = json.dumps(self.to_dict_without_hash(), sort_keys=True).encode()
        return hashlib.sha256(block).hexdigest()

    def to_dict_without_hash(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp.isoformat(),
            "proof": self.proof,
            "previous_hash": self.previous_hash,
            "mined_difficulty": self.mined_difficulty,
        }

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp.isoformat(),
            "proof": self.proof,
            "previous_hash": self.previous_hash,
            "mined_difficulty": self.mined_difficulty,
            "hash": self.hash,
        }

    def __str__(self) -> str:
        return f"Block index: {self.index}, timestamp: {self.timestamp}, proof: {self.proof}, previous_hash: {self.previous_hash}, mined_difficulty: {self.mined_difficulty}, hash: {self.hash}"


class Blockchain:
    def __init__(self, db_config: Dict[str, str | None]) -> None:
        self.db_config = db_config
        self.height: int = 0
        self.chain: List[Block] = []

        self.target_time = 3
        self.adjust_interval = 10
        self.difficulty = 6
        self.mining_times = []

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
                    proof INTEGER NOT NULL,
                    previous_hash VARCHAR(64) NOT NULL,
                    mined_difficulty INTEGER NOT NULL,
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
                            proof=row["proof"],
                            previous_hash=row["previous_hash"],
                            mined_difficulty=row["mined_difficulty"],
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
            proof=1,
            previous_hash="0",
            mined_difficulty=0,
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
                                    INSERT INTO blockchain (timestamp, proof, previous_hash, mined_difficulty, hash)
                                    VALUES (%s, %s, %s, %s, %s)
                                """,
                    (
                        block.timestamp,
                        block.proof,
                        block.previous_hash,
                        block.mined_difficulty,
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
            if block.proof != 1:
                print(f"Invalid genesis block: expected 1, got {block.proof}")
                return False
            if block.mined_difficulty != 0:
                print(
                    f"Invalid genesis block: expected 0, got {block.mined_difficulty}"
                )
                return False
            if block.hash != block.hash_block():
                print("Invalid genesis block: hash mismatch")
                return False

            return True

        if block.hash != block.hash_block():
            print(f"Block {block.index} has an invalid hash.")
            return False

        last_block = self.chain[-1]
        timestamp_str = block.timestamp.strftime("%Y%m%d%H%M%S")
        target_prefix = timestamp_str[-block.mined_difficulty :]
        expected_hash = hashlib.sha256(
            f"{block.proof**2 - last_block.proof**2}".encode()
        ).hexdigest()

        if target_prefix not in expected_hash:
            print(f"Block {block.index} has an invalid proof.")
            return False

        if block.previous_hash != last_block.hash:
            print(f"Block {block.index} has an invalid previous hash.")
            return False

        return True

    def validate_chain(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            if i == 1:
                if current_block.index == 1:
                    if current_block.previous_hash != "0":
                        print(
                            f"Invalid genesis block: expected '0', got {current_block.previous_hash}"
                        )
                        return False
                    if current_block.proof != 1:
                        print(
                            f"Invalid genesis block: expected 1, got {current_block.proof}"
                        )
                        return False
                    if current_block.mined_difficulty != 0:
                        print(
                            f"Invalid genesis block: expected 0, got {current_block.mined_difficulty}"
                        )
                        return False
                    if current_block.hash != current_block.hash_block():
                        print("Invalid genesis block: hash mismatch")
                        return False

            last_block = self.chain[i - 1]

            if current_block.hash != current_block.hash_block():
                print(f"Invalid hash at block {i}.")
                return False

            timestamp_str = current_block.timestamp.strftime("%Y%m%d%H%M%S")
            target_prefix = timestamp_str[-current_block.mined_difficulty :]
            if (
                target_prefix
                not in hashlib.sha256(
                    f"{current_block.proof**2 - last_block.proof**2}".encode()
                ).hexdigest()
            ):
                print(f"Invalid proof of work at block {i}.")
                return False

            if current_block.previous_hash != last_block.hash:
                print(f"Invalid previous hash at block {i}.")
                return False

        return True

    def proof_of_work(self, previous_proof: int, timestamp: str) -> int:
        """
        Perform a proof-of-work where the hash contains the timestamp.
        """
        new_proof = 1
        check_proof = False

        max_symbols = len(timestamp)
        difficulty = min(self.difficulty, max_symbols)
        target_prefix = timestamp[-difficulty:]

        while not check_proof:
            potential_hash = hashlib.sha256(
                f"{new_proof**2 - previous_proof**2}".encode()
            ).hexdigest()

            if target_prefix in potential_hash:
                check_proof = True
            else:
                new_proof += 1

        return new_proof

    def adjust_difficulty(self) -> None:
        if len(self.mining_times) < self.adjust_interval:
            return None

        average_time = (
            sum(self.mining_times[-self.adjust_interval :]) / self.adjust_interval
        )

        if average_time < self.target_time - 1:
            self.difficulty = min(self.difficulty + 1, 14)
            print(f"Increasing difficulty to {self.difficulty}.")
        elif average_time > self.target_time + 1 and self.difficulty > 4:
            self.difficulty = max(self.difficulty - 1, 4)
            print(f"Decreasing difficulty to {self.difficulty}")

    def mine_block(self) -> Block:
        """
        Mines a new block by completing the PoW algorithm and appends it to the chain.
        """
        if not self.chain:
            raise Exception("Blockchain is empty. Initialize it first.")

        last_block = self.chain[-1]
        previous_proof = last_block.proof
        previous_hash = last_block.hash

        current_timestamp = datetime.datetime.now()
        timestamp_str = current_timestamp.strftime("%Y%m%d%H%M%S")

        print(f"Mining block with timestamp {timestamp_str}...")
        start_time = time.time()

        proof = self.proof_of_work(
            previous_proof=previous_proof, timestamp=timestamp_str
        )

        end_time = time.time()
        self.mining_times.append(end_time - start_time)
        print(f"Block mined! Time taken: {end_time - start_time:.2f} seconds")

        new_block = Block(
            index=last_block.index + 1,
            timestamp=current_timestamp,
            proof=proof,
            previous_hash=previous_hash,
            mined_difficulty=self.difficulty,
        )

        if len(self.chain) % self.adjust_interval == 0:
            self.adjust_difficulty()

        self.add_block_to_db(new_block)
        self.chain.append(new_block)
        self.height += 1

        return new_block

    def close_connection(self) -> None:
        self.conn.close()
