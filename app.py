import base64
import pickle
from flask import Flask, jsonify, request, redirect, flash, g, render_template
from flask_wtf import FlaskForm
from wtforms import FileField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired
from body.blockchain import Blockchain
from body.federated_learning import FederatedDataset, FederatedDataLoader, create_model, hasher, train_model

# Web app creation
app = Flask(__name__)
app.config["SECRET_KEY"] = "test_key"  # To be researched

# Creates object of the class blockchain.
blockchain = Blockchain()

# File specifics
ALLOWED_EXTENSIONS = {"txt", "jpg", "jpeg", "png", "gif", "mp4", "mkv", "avi"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def process_data(data, data_type):
    if data_type == "text":
        pass
    elif data_type == "image":
        pass
    elif data_type == "video":
        pass
    else:
        raise ValueError("Invalid data type")

    return data


class DataUploadForm(FlaskForm):
    data_file = FileField("Data file", validators=[DataRequired()])
    data_type = SelectField("Data type", choices=[("image", "Image"), ("video", "Video"), ("text", "Text")])
    label = StringField("Label", validators=[DataRequired()])
    submit = SubmitField("Upload")


# Route for the data upload form
@app.route("/api/v1/upload", methods=["GET", "POST"])
def upload_data():
    form = DataUploadForm()

    if form.validate_on_submit():
        data_file = form.data_file.data
        data_type = form.data_type.data
        label = form.label.data

        if not allowed_file(data_file.filename):
            flash("Format not allowed")
            return redirect(request.url)

        g.data = data_file.read()
        g.label = label
        g.processed_data = process_data(g.data, data_type)

        response, status_code = mine_block()
        return jsonify(response), status_code

    return render_template("upload.html", form=form)


# Mining a new block
@app.route("/api/v1/blocks/mine", methods=["POST"])
def mine_block():
    previous_block = blockchain.print_previous_block()
    previous_proof = previous_block["proof"]
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)

    # Creating a model
    model = create_model()

    data = hasher(g.processed_data)
    label = hasher(g.label)

    # Using the data
    federated_dataset = FederatedDataset(data, label)
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
@app.route("/api/v1/blocks", methods=["GET"])
def display_chain():
    response = {"chain": blockchain.chain,
                "len": len(blockchain.chain)}
    return jsonify(response), 200


# Validity checker
@app.route("/api/v1/blocks/validity", methods=["GET"])
def valid():
    validity = blockchain.chain_valid(blockchain.chain)

    if validity:
        response = {"message": "The blockchain is valid."}
    else:
        response = {"message": "The blockchain is invalid"}
    return jsonify(response), 200


# Run flask server locally
app.run(host="127.0.0.1", port=5000)
