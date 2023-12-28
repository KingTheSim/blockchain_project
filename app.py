import base64
import pickle
import nltk
import io
# import cv2
# import numpy
from nltk.tokenize import word_tokenize
from PIL import Image
from flask import Flask, jsonify, redirect, flash, g, render_template, url_for
from flask_wtf import FlaskForm
from wtforms import FileField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired
from body.blockchain import Blockchain
from body.federated_learning import FederatedDataset, create_model, hasher, train_model
from body.utils import allowed_file

nltk.download("punkt")

# Web app creation
app = Flask(__name__)
app.config["SECRET_KEY"] = "test_key"

# Creates object of the class blockchain.
blockchain = Blockchain()


def process_data(data, data_type):
    if data_type == "text":
        text = data.decode("utf-8")
        words = word_tokenize(text)
        words = [word.lower() for word in words if word.isalpha()]
        return " ".join(words)
    elif data_type == "image":
        image = Image.open(io.BytesIO(data))
        image = image.resize((64, 64)).convert("L")
        return image
    elif data_type == "video":
        pass
    #     frames = []
    #     file_bytes = numpy.array(bytearray(data), dtype=numpy.uint8)
    #     video = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
    #
    #     while video.isOpened():
    #         ret, frame = video.read()
    #         if not ret:
    #             break
    #         image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    #         image = image.resize((64, 64)).convert("L")
    #         frames.append(image)
    #
    #     video.release()
    #     return frames1

    else:
        raise ValueError(f"Invalid data type: {data_type}")


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
            return redirect(url_for("upload_data"))

        g.data = data_file.read()
        g.label = label
        g.processed_data = process_data(g.data, data_type)

        response, status_code = mine_block(data_type)
        return jsonify(response), status_code

    return render_template("upload.html", form=form)


# Mining a new block
@app.route("/api/v1/blocks/mine/<data_type>", methods=["POST"])
def mine_block(data_type):
    previous_block = blockchain.print_previous_block()
    previous_proof = previous_block["proof"]
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)

    # Creating a model
    model = create_model(data_type)

    data = hasher(g.processed_data)
    label = hasher(g.label)

    # Using the data
    federated_dataset = FederatedDataset(data, label)

    # Model training
    trained_model_state_dict = train_model(model, federated_dataset)

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


# Default route. Redirects to the blockchain
@app.route("/", methods=["GET"])
def index():
    return redirect("/api/v1/blocks")


# Run flask server locally
app.run(host="127.0.0.1", port=5000)
