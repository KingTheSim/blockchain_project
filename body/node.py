import asyncio
import uuid
from typing import Any, Optional
import datetime

from blockchain import Blockchain, Block

class Message:
    POSSIBLE_MESSAGES = (
        "NOMINATION",
        "BALLOT",
        "COMMIT",
        "EXTERNALIZE",
    )

    def __init__(self, msg_type: str, sender_id: uuid.UUID, data: dict[str, Any]) -> None:
        self._msg_type = msg_type
        self.sender_id = sender_id
        self.data = data

    @property
    def msg_type(self) -> str:
        return self._msg_type

    @msg_type.setter
    def msg_type(self, value: str) -> None:
        if value not in self.POSSIBLE_MESSAGES:
            raise ValueError(f"Invalid message type: {self.msg_type}. Allowed types: {self.POSSIBLE_MESSAGES}")
        self._msg_type = value

class Ballot:
    def __init__(self, block: Block, counter: int = 1) -> None:
        self.block = block
        self.counter = counter

class Node:
    POSSIBLE_STATES = (
        "IDLE",
        "NOMINATING",
        "PREPARING",
        "COMMITTING",
        "EXTERNALIZING",
    )

    def __init__(self, trusted_nodes: set["Node"], blockchain: Blockchain) -> None:
        self.node_id = uuid.uuid4()
        self.trusted_nodes = trusted_nodes
        self.blockchain = blockchain

        self.latest_block_hash: Optional[str] = None
        self.current_ballot: Optional[Ballot] = None
        self.voting_history = set()

        self.inbox = asyncio.Queue()
        self.outbox = asyncio.Queue()

        self._state = "IDLE"

        self.quorum_threshold = max(1, int(len(trusted_nodes) / 0.67))

    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, value: str) -> None:
        if value not in self.POSSIBLE_STATES:
            raise ValueError(f"Invalid state: {value}. Allowed states: {self.POSSIBLE_STATES}.")
        self._state = value

    async def process_message(self) -> None:
        while True:
            message: Message = await self.inbox.get()
            print(f"Node {self.node_id} received messsage: {message.msg_type} from {message.sender_id}")
            await self.handle_message(message)
            self.inbox.task_done()

    async def handle_message(self, message: Message) -> None:
        if message.msg_type == "NOMINATION":
            await self.handle_nomination(message)
        elif message.msg_type == "BALLOT":
            await self.handle_ballot(message)
        elif message.msg_type == "COMMIT":
            await self.handle_commit(message)
        elif message.msg_type == "EXTERNALIZE":
            await self.handle_externalize(message)

    async def handle_nomination(self, message: Message) -> None:
        proposed_block: Block = message.data["block"]

        if self.state == "IDLE":
            print(f"Node {self.node_id} starts nominating {proposed_block}.")
            self.state = "NOMINATING"
            self.current_ballot = Ballot(proposed_block)
            await self.broadcast("BALLOT", {"block": proposed_block, "counter": 1})

    async def handle_ballot(self, message: Message) -> None:
        ballot_block: Block = message.data["block"]
        counter = message.data["counter"]
        sender_id = message.sender_id

        self.voting_history.add(("BALLOT", ballot_block.hash, sender_id, counter))
        if self.check_quorum(ballot_block):
            print(f"Node {self.node_id} reached quorum for {ballot_block}.")
            self.state = "COMMITTING"
            await self.broadcast("COMMIT", {"block": ballot_block})

    async def handle_commit(self, message: Message) -> None:
        commit_block: Block = message.data["block"]
        if self.state != "EXTERNALIZING":
            if self.blockchain.validate_block(commit_block):
                self.blockchain.add_block_to_db(commit_block)
                self.blockchain.chain.append(commit_block)
                print(f"Node {self.node_id} commits to {commit_block}.")
                self.latest_block_hash = commit_block.hash
                self.state = "EXTERNALIZING"
                await self.broadcast("EXTERNALIZE", {"block": commit_block})
            else:
                print(f"Node {self.node_id} received invalid block {commit_block.hash}.")

    async def handle_externalize(self, message: Message) -> None:
        externalize_block: Block = message.data["block"]
        print(f"Node {self.node_id} externalized {externalize_block}.")
        self.latest_block_hash = externalize_block.hash
        self.state = "IDLE"

    async def propose_value(self) -> None:
        last_block = self.blockchain.chain[-1]
        new_block = Block(
            index=last_block.index + 1,
            timestamp=datetime.datetime.now(),
            previous_hash=last_block.hash,
        )
        print(f"Node {self.node_id} proposes {new_block.hash}.")
        await self.broadcast("NOMINATING", {"block": new_block})

    async def broadcast(self, msg_type: str, data: dict[str, Any]) -> None:
        for node in self.trusted_nodes:
            await node.inbox.put(Message(msg_type, self.node_id, data))

    def check_quorum(self, block: Block) -> bool:
        """
            Since it is unclear what self.voting_history will be in the future, as I
            can decide to keep all the messages for later analisis, the list
            comprehention needs to stay and to filter by msg_type.
        """
        unique_voters = {sender_id for msg_type, block_hash, sender_id, _ in
            self.voting_history if msg_type == "BALLOT" and block_hash == block.hash}
        return len(unique_voters) >= self.quorum_threshold

import os

from dotenv import load_dotenv



async def run_scp_simulation():
    # Setup: create a shared Blockchain instance for simplicity
    load_dotenv()

    db_config = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
    }
    blockchain = Blockchain(db_config)

    # Create 5 nodes, each trusting the others
    node_a = Node(set(), blockchain)
    node_b = Node(set(), blockchain)
    node_c = Node(set(), blockchain)
    node_d = Node(set(), blockchain)
    node_e = Node(set(), blockchain)

    # Define trust relationships (all-to-all for simplicity)
    all_nodes = {node_a, node_b, node_c, node_d, node_e}
    for node in all_nodes:
        node.trusted_nodes.update(all_nodes - {node})  # Trust everyone except self

    # Start message processing loops
    for node in all_nodes:
        asyncio.create_task(node.process_message())

    # Choose one node to propose a new block
    print("\nStarting SCP simulation with 5 nodes...\n")
    await node_a.propose_value()

    # Allow time for consensus to happen
    await asyncio.sleep(5)

    # Print blockchain state for each node
    for node in all_nodes:
        print(f"\nNode {node.node_id} Blockchain State:")
        for block in node.blockchain.chain:
            print(f" - Block {block.index}: {block.hash}")
        print(f"Latest block hash: {node.latest_block_hash}")

    # Close the database connection (optional)
    blockchain.close_connection()

# Run the simulation
asyncio.run(run_scp_simulation())
