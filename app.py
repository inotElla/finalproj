import os
import base64
import requests
from flask import Flask, jsonify
from dotenv import load_dotenv

# 1. Fixed: Load from your custom token.env file
load_dotenv("token.env")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

app = Flask(__name__)

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "my-flask-app"
}

# 2. Fixed: Added a homepage route so 127.0.0.1:5000 doesn't show 404
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "Server is running!",
        "endpoints": [
            "/api/repos",
            "/api/data/<owner>/<repo>/<filepath>"
        ]
    })

# 3. Fixed: Pointed to ://github.com
@app.route("/api/repos", methods=["GET"])
def get_repos():
    url = "https://://github.com"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch repos", "details": response.json()}), response.status_code
        
    repos = [{"name": r["name"], "url": r["html_url"]} for r in response.json()]
    return jsonify(repos)

# 4. Fixed: Pointed to ://github.com...
@app.route("/api/data/<owner>/<repo>/<path:filepath>", methods=["GET"])
def get_repo_file(owner, repo, filepath):
    url = f"https://://github.com{owner}/{repo}/contents/{filepath}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code != 200:
        return jsonify({"error": "File not found", "details": response.json()}), response.status_code
        
    file_data = response.json()
    decoded_content = base64.b64decode(file_data["content"]).decode("utf-8")
    
    return decoded_content, 200, {"Content-Type": "application/json"}

if __name__ == "__main__":
    app.run(debug=True)