import datetime
import hashlib
import json
import os.path
import requests
from flask import Flask, jsonify


class Node:

    def __init__(self):
        self.blockchain = Blockchain()
        self.neighbours = []

    def add_neighbour(self, neighbour):
        self.neighbours.append(neighbour)


    def broadcast_block(self, block):
        # Broadcasts a new block to the network neighbours
        for neighbour in self.neighbours:
            neighbour.receive_block(block)

    def resolver(self):
        neighbours = []  # This is supposed to be a list of neighbouring nodes, from which to fetch the blockchain.
        max_length = len(self.blockchain.chain)
        new_chain = None

        # Fetches and verifies the chains from all neighbouring nodes
        for node in neighbours:
            response = requests.get(f"{node}/get_chain")
            if response.status_code == "200":
                length = response.json()["len"]
                chain = response.json()["chain"]

                # Checks if the chain is longer and valid
                if length > max_length and self.blockchain.chain_valid(chain):
                    max_length = length
                    new_chain = chain

        # Replaces our chain if a longer valid is found
        if new_chain:
            self.blockchain.chain = new_chain
            return True

        return False


class Blockchain:
    # First block creation function
    def __init__(self):
        self.chain = []
        self.node = Node()
        self.chain_loader()
        if not self.chain:
            self.create_block(proof=1, previous_hash="0")

    # Block generator
    def create_block(self, proof, previous_hash):
        block = {"index": len(self.chain) + 1,
                 "timestamp": str(datetime.datetime.now()),
                 "proof": proof,
                 "previous_hash": previous_hash}
        self.chain.append(block)
        self.block_saver(block)
        self.node.broadcast_block(block)
        return block

    # Saves the chain
    def block_saver(self, block):
        filename = "blockchain.json"
        file_existence = os.path.isfile(filename)
        with open(filename, "a") as f:
            if file_existence:
                f.write(",")
            f.write(json.dumps(block))

    # Loads the chain
    def chain_loader(self):
        filename = "blockchain.json"
        if not os.path.isfile(filename):
            return

        with open(filename, "r") as f:
            contents = f.read().strip()
            if not contents:
                return
            blocks = f"[{contents}]"
        self.chain = json.loads(blocks)

        if not self.chain_valid(self.chain):
            if self.node.resolver():
                print("The conflicts have been resolved by replacing the chain.")
            else:
                print("The chain is invalid and could not be resolved.")

    # Previous block viewer
    def print_previous_block(self):
        return self.chain[-1]

    # Proof-of-work miner
    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False

        while not check_proof:
            hash_operation = hashlib.sha256(
                str(new_proof ** 2 - previous_proof ** 2).encode()).hexdigest()
            if hash_operation[:5] == "00000":
                check_proof = True
            else:
                new_proof += 1

        return new_proof

    # Creates the hash for the block
    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    # Checks the validity of the chain
    def chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1

        while block_index < len(chain):
            block = chain[block_index]
            if block["previous_hash"] != self.hash(previous_block):
                return False

            previous_proof = previous_block["proof"]
            proof = block["proof"]
            hash_operation = hashlib.sha256(str(proof ** 2 - previous_proof ** 2).encode()).hexdigest()

            if hash_operation[:5] != "00000":
                return False
            previous_block = block
            block_index += 1

        return True


# Web app creation
app = Flask(__name__)

# Creates objects of the different classes.
# It's used to connect a class to a class and use different methods from each other
blockchain = Blockchain()
node = Node()


# Mining a new block
@app.route("/mine_block", methods=["GET"])
def mine_block():
    previous_block = blockchain.print_previous_block()
    previous_proof = previous_block["proof"]
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    block = blockchain.create_block(proof, previous_hash)

    response = {"message": "A block is mined",
                "index": block["index"],
                "timestamp": block["timestamp"],
                "proof": block["proof"],
                "previous_hash": block["previous_hash"]}

    return jsonify(response), 200


# Displaying blockchain
@app.route("/get_chain", methods=["GET"])
def display_chain():
    response = {"chain": blockchain.chain,
                "len": len(blockchain.chain)}
    return jsonify(response), 200


# Validity checker
@app.route("/valid", methods=["GET"])
def valid():
    valid = blockchain.chain_valid(blockchain.chain)

    if valid:
        response = {"message": "The blockchain is valid."}
    else:
        response = {"message": "The blockchain is invalid"}
        # If the chain is invalid, try to resolve the conflicts
        if node.resolver():
            response["message"] += " But the conflict has been resolved by replacing the chain."
        else:
            response["message"] += " The chain is still invalid."

    return jsonify(response), 200


# Run flask server locally
app.run(host="127.0.0.1", port=5000)
