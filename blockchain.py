import datetime
import hashlib
import json
import os.path
import requests
from flask import Flask, jsonify
import uuid


class Node:
    def __init__(self):
        self.nodes = {}
        self.removed = set()
        self.blocked = set()

    def add_node(self, node):
        un_id = str(uuid.uuid4())
        if un_id not in self.blocked:
            self.nodes[un_id] = {}
            return un_id
        else:
            print("Node is blocked and cannot be added.")

    def remove_node(self, node_id):
        if node_id in self.nodes:
            if node_id not in self.blocked and node_id not in self.removed:
                del self.nodes[node_id]
                self.removed.add(node_id)
                print("Node successfully removed.")
            else:
                print("Node is either blocked or already removed and cannot be removed again.")
        else:
            print("Node not found.")

    def block_node(self, node_id):
        if node_id in self.nodes:
            if node_id not in self.blocked:
                self.blocked.add(node_id)
                print("Node successfully blocked.")
            else:
                print("Node already blocked and cannot be blocked.")
        else:
            print("Node not found.")

    def get_nodes(self):
        return [node for node in self.nodes if node not in self.removed and node not in self.blocked]


class Blockchain:
    # First block creation function
    def __init__(self, nodes):
        self.chain = []
        self.chain_loader()
        self.nodes = nodes
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
            if self.resolver():
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

    def resolver(self):
        new_chain = None

        max_length = len(self.chain)

        for node in self.nodes:
            response = requests.get(f"http://{node}/chain")

            if response.status_code == 200:
                length = response.json()["length"]
                chain = response.json()["chain"]

                # Check for the validity and length:
                if length > max_length and self.chain_valid(chain):
                    max_length = length
                    new_chain = chain

            # Replace the chain if we discover new valid chain, longer than our
            if new_chain:
                self.chain = new_chain
                return True

        return False


# List of nodes
nodes = ["localhost:5000", "localhost:5001", "localhost:5002"]

# Web app creation
app = Flask(__name__)

# Creates objects of the different classes.
# It's used to connect a class to a class and use different methods from each other
blockchain = Blockchain(nodes)


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


# Adds nodes to the network
@app.route("/add_nodes/string:node", methods=["GET"])
def add_node(node):
    nodes.append(node)
    response = {"message": "New node is added.", "nodes": nodes}
    return jsonify(response), 200


# Removing nodes from the network
@app.route("/remove_node/string:node", methods=["GET"])
def remove_node(node):
    nodes.remove(node)
    response = {"message": "A node is removed.", "nodes": nodes}
    return jsonify(response), 200


# Displaying blockchain
@app.route("/get_chain", methods=["GET"])
def display_chain():
    response = {"chain": blockchain.chain,
                "len": len(blockchain.chain)}
    return jsonify(response), 200


# Returns the chains from all the nodes in the network
@app.route("/get_chains", methods=["GET"])
def get_chains():
    chains = [{"chain": blockchain.chain, "length": len(blockchain.chain)}]
    for node in nodes:
        if node != blockchain:
            response = requests.get(f"http://{node}/get_chain")
            if response.status_code == 200:
                length = response.json()["len"]
                chain = response.json()["chain"]
                chains.append({"chain": chain, "length": length})

    response = {"chains": chains}
    return jsonify(response), 200


# Validity checker
@app.route("/valid", methods=["GET"])
def valid():
    blockchain.resolver()
    if blockchain.chain_valid(blockchain.chain):
        response = {"message": "The blockchain is valid."}
    else:
        response = {"message": "The blockchain is not valid."}
    return jsonify(response), 200


@app.route("/resolve_conflicts", methods=["GET"])
def resolve_conflicts():
    if blockchain.resolver():
        response = {"message": "The conflicts have been resolved by replacing the chain."}
        status_code = 200
    else:
        response = {"message": "The chain is valid."}
        status_code = 200
    return jsonify(response), status_code


# Run flask server locally
app.run(host="127.0.0.1", port=5000)
