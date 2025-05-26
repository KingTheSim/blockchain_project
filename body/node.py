import asyncio
import datetime
import uuid
from typing import Any, Optional

from blockchain import Blockchain
from genesis import Block


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

        self.latest_block_hash: str = "genesis"
        self.current_ballot: Optional[Ballot] = None
        self.voting_history = set()

        self.inbox = asyncio.Queue()

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
            self.state = "NOMINATING"
            self.current_ballot = Ballot(proposed_block)
            await self.broadcast("BALLOT", {"block": proposed_block, "counter": 1})

    async def handle_ballot(self, message: Message) -> None:
        ballot_block: Block = message.data["block"]
        counter = message.data["counter"]
        sender_id = message.sender_id

        self.voting_history.add(("BALLOT", ballot_block.hash, sender_id, counter))
        if self.check_quorum(ballot_block):
            self.state = "COMMITTING"
            await self.broadcast("COMMIT", {"block": ballot_block})

    async def handle_commit(self, message: Message) -> None:
        commit_block: Block = message.data["block"]
        if self.state != "EXTERNALIZING":
            # If we've already committed this block, ignore further commits
            if self.latest_block_hash == commit_block.hash:
                return

            if self.blockchain.validate_block(commit_block):
                if commit_block.hash not in [b.hash for b in self.blockchain.chain]:
                    self.blockchain.add_block_to_db(commit_block)
                    self.blockchain.chain.append(commit_block)
                self.latest_block_hash = commit_block.hash
                self.state = "EXTERNALIZING"
                await self.broadcast("EXTERNALIZE", {"block": commit_block})
            else:
                print(f"Node {self.node_id} received invalid block {commit_block.hash}.")


    async def handle_externalize(self, message: Message) -> None:
        externalize_block = message.data["block"]
        if externalize_block.hash not in [b.hash for b in self.blockchain.chain]:
            self.blockchain.add_block_to_db(externalize_block)
            self.blockchain.chain.append(externalize_block)
        self.latest_block_hash = externalize_block.hash
        self.state = "IDLE"

    async def propose_value(self) -> None:
        if self.state != "IDLE":
            return
        last_block = self.blockchain.chain[-1]
        new_block = Block(
            index=last_block.index + 1,
            timestamp=datetime.datetime.now(),
            previous_hash=last_block.hash,
        )
        self.state = "NOMINATING"
        await self.broadcast("NOMINATION", {"block": new_block})

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

async def test_scp_consensus():
    print("🔬 Starting SCP Consensus Test with 5 Nodes 🔬")

    # Create separate blockchains for each node
    blockchains = [
        Blockchain(db_config=None, db_type="sqlite", db_sqlite_in_memory=True)
        for _ in range(5)
    ]

    # Create nodes with these blockchains
    nodes = [
        Node(trusted_nodes=set(), blockchain=blockchain)
        for blockchain in blockchains
    ]

    # Make nodes trust each other (full-mesh network)
    all_nodes = set(nodes)
    for node in nodes:
        node.trusted_nodes.update(all_nodes - {node})

    # Start message processors
    for node in nodes:
        asyncio.create_task(node.process_message())

    # Propose a block from the first node
    print("\n🚀 Node A proposing a block...")
    for _ in range(5):
        await asyncio.sleep(2)
        await nodes[0].propose_value()

    # Print blockchain state
    for i, node in enumerate(nodes):
        print(f"\n🔹 Node_{chr(65+i)} (ID: {node.node_id}):")
        for block in node.blockchain.chain:
            print(f"   - Block {block.index}: {block.hash}")
        print(f"   Latest Block Hash: {node.latest_block_hash}")

    # Verify that all nodes have the same latest block
    latest_hashes = {node.latest_block_hash for node in nodes}
    assert len(latest_hashes) == 1, "❌ Consensus failed: Nodes have different latest hashes"
    print("\n✅ SCP consensus reached: All nodes have the same latest block!")
    print(len(nodes[0].blockchain.chain))

async def run_all_tests():
    await test_scp_consensus()

if __name__ == "__main__":
    asyncio.run(run_all_tests())
