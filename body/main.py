import base64
import pickle
import sqlite3
from flask import Flask, jsonify
from body.blockchain import Blockchain
from body.federated_learning import FederatedDataset, FederatedDataLoader, create_model, hasher, train_model
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
