from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "Bonjour depuis mon application Docker !"

@app.route("/api/status")
def status():
    return jsonify({"status": "ok", "message": "API Flask dans Docker"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
