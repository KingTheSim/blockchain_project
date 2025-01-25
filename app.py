import os
from typing import List
from flask import Flask, jsonify, redirect
from dotenv import load_dotenv
from body.blockchain import Blockchain

load_dotenv()

db_config = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

# Web app creation
app = Flask(__name__)
app.config["SECRET_KEY"] = "test_key"

# Creates object of the class blockchain.
blockchain = Blockchain(db_config=db_config)

@app.route("/get_chain", methods=["GET"])
def get_chain():
    chain_data = [block.to_dict() for block in blockchain.chain]
    return jsonify(chain=chain_data, height=blockchain.height), 200

@app.route("/mine", methods=["GET"])
def mine():
    try:
        block = blockchain.mine_block()
        return jsonify({
            "message": "Block mined successfully",
            "block": block.to_dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/", methods=["GET"])
def index():
    return redirect("/get_chain")

# Run flask server locally
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
