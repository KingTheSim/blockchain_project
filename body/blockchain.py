import datetime
import hashlib
import json
import os.path


class Blockchain:
    # First block creation function
    def __init__(self):
        self.chain = []
        self.chain_loader()
        if not self.chain:
            self.create_block(proof=1, previous_hash="0", encoded_model=None)

    # Block generator
    def create_block(self, proof, previous_hash, encoded_model):
        block = {"index": len(self.chain) + 1,
                 "timestamp": str(datetime.datetime.now()),
                 "proof": proof,
                 "previous_hash": previous_hash,
                 "encoded_model": encoded_model}
        self.chain.append(block)
        self.block_saver(block)
        return block

    def block_saver(self, block):
        filename = "blockchain.json"
        if not os.path.isfile(filename):
            with open(filename, "w") as f:
                json.dump([block], f)

        else:
            with open(filename, "r") as f:
                chain = json.load(f)
            chain.append(block)
            with open(filename, "w") as f:
                json.dump(chain, f)

    def _file_reader(self, filename):
        with open(filename, "r") as f:
            content = f.read().strip()
        return content

    def chain_loader(self):
        filename = "blockchain.json"
        if not os.path.isfile(filename):
            return

        content = self._file_reader(filename)
        if not content:
            return
        blocks = f"[{content}]"
        self.chain = json.loads(blocks)

    # Previous block viewer
    def print_previous_block(self):
        return self.chain[-1]

    # Proof-of-work miner
    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False
        fail_limit = 100000

        while not check_proof and new_proof < fail_limit:
            hash_operation = hashlib.sha256(
                f"{(new_proof ** 2 - previous_proof ** 2)}".encode()).hexdigest()
            if hash_operation[:5] == "00000":
                check_proof = True
            else:
                new_proof += 1

        return new_proof if check_proof else None

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def chain_valid(self, chain):
        if len(self.chain) < 2:
            return True

        last, second_last = self.chain[-1], self.chain[-2]
        if last["previous_hash"] != self.hash(second_last):
            return False

        previous_proof = second_last["proof"]
        proof = last["proof"]

        hashing = hashlib.sha256(f"{proof ** 2 - previous_proof ** 2}".encode()).hexdigest()

        return True
