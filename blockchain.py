import base64
import datetime
import hashlib
import json
import os.path
import pickle
import random
import torch
import sqlite3
from flask import Flask, jsonify


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
        file_existence = os.path.isfile(filename)
        with open(filename, "a") as f:
            if file_existence:
                f.write(",")
            f.write(json.dumps(block))

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

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

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


class FederatedDataset:
    def __init__(self, sentences, labels, transform=None):
        self.sentences = sentences
        self.labels = labels
        self.transform = transform

    def __getitem__(self, index):
        sentence, label = self.sentences[index], self.labels[index]

        if self.transform:
            sentence = self.transform(sentence)
            label = self.transform(label)

        return sentence, label

    def __len__(self):
        return len(self.sentences)


class FederatedDataLoader:
    def __init__(self, hf_dataset, batch_size=1, shuffle=False):
        self.dataset = FederatedDataset(hf_dataset[0], hf_dataset[1])
        self.batch_size = batch_size
        self.shuffle = shuffle

    def __iter__(self):
        if self.shuffle:
            indices = torch.randperm(len(self.dataset))
        else:
            indices = torch.arange(len(self.dataset))

        for start_idx in range(0, len(self.dataset), self.batch_size):
            end_idx = min(start_idx + self.batch_size, len(self.dataset))
            batch_indices = indices[start_idx:end_idx]
            batch = [(x, y) for (x, y) in [self.dataset[i] for i in batch_indices]]
            x, y = zip(*batch)
            yield torch.stack(x), torch.stack(y)

    def __len__(self):
        return len(self.dataset)


def create_model():
    model = torch.nn.Sequential(
        torch.nn.Linear(1, 32),
        torch.nn.ReLU(),
        torch.nn.Linear(32, 32),
        torch.nn.ReLU(),
        torch.nn.Linear(32, 1),
        torch.nn.Sigmoid()
    )
    return model


def hasher(text):
    salt = str(random.random()).encode()
    salted_text = salt + text.encode()
    hash_object = hashlib.sha256(salted_text)
    hash_value = int(hash_object.hexdigest(), 16)
    hash_float = float(hash_value) / float(2 ** 32 - 1)
    tensor_value = torch.clamp(torch.tensor([hash_float], dtype=torch.float32), 0, 1)
    return tensor_value


def train_model(model, federated_dataloader):
    # Define model
    loss_fn = torch.nn.BCELoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)

    # Train model
    num_epochs = 10  # Can be changed later on. For now, it's hard-coded
    for epoch in range(num_epochs):
        for x, y in federated_dataloader:
            y_predict = model(x)
            loss = loss_fn(y_predict, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    return model.state_dict()


# Web app creation
app = Flask(__name__)

# Creates object of the class blockchain.
blockchain = Blockchain()


# Mining a new block
@app.route("/mine_block", methods=["GET"])
def mine_block():
    previous_block = blockchain.print_previous_block()
    previous_proof = previous_block["proof"]
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)

    # Creating a model
    model = create_model()

    # Connecting to a dataset
    conn = sqlite3.connect("current_database.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS current_database (sentence TEXT, label TEXT)")

    # Extracting the data
    cursor.execute("SELECT sentence, label FROM current_database")
    rows = cursor.fetchall()
    sentences, labels = zip(*rows)
    hashed_sentences = [hasher(sentence) for sentence in sentences]
    hashed_labels = [hasher(label) for label in labels]

    # Using the data
    federated_dataset = FederatedDataset(hashed_sentences, hashed_labels)
    federated_dataloader = FederatedDataLoader(federated_dataset, batch_size=1, shuffle=True)

    # Model training
    trained_model_state_dict = train_model(model, federated_dataloader)

    # Serialization
    serialized_model = pickle.dumps(trained_model_state_dict)

    # Encoding
    encoded_model = base64.b64encode(serialized_model).decode("utf-8")

    # Block building
    block = blockchain.create_block(proof, previous_hash, encoded_model)

    response = {"message": "A block is mined",
                "index": block["index"],
                "timestamp": block["timestamp"],
                "proof": block["proof"],
                "previous_hash": block["previous_hash"],
                "encoded_model": block["encoded_model"]}

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
    validity = blockchain.chain_valid(blockchain.chain)

    if validity:
        response = {"message": "The blockchain is valid."}
    else:
        response = {"message": "The blockchain is invalid"}
    return jsonify(response), 200


# Run flask server locally
app.run(host="127.0.0.1", port=5000)
