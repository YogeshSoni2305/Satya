
from flask import Flask, render_template, request, jsonify
import os
from flask_cors import CORS
import json
from werkzeug.utils import secure_filename
from fighter import ClaimFighter
from config import (
    FLASK_UPLOAD_FOLDER,
    FLASK_STATIC_FOLDER,
    OUTPUT_JSON_PATH,
    PROCESSED_JSON_PATH
)

app = Flask(__name__, static_folder=FLASK_STATIC_FOLDER)
CORS(app)
app.config['UPLOAD_FOLDER'] = FLASK_UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@app.route('/')
def index():
 return render_template('index.html')


@app.route('/explore')
def explore():
    return render_template('upload.html')


@app.route('/process', methods=['POST'])
def process_upload():
    results = {}

    # ---- Handle file uploads ----
    file_types = ['image', 'video', 'audio']
    for file_type in file_types:
        if file_type in request.files and request.files[file_type].filename:
            file = request.files[file_type]
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            results[file_type] = file_path
        else:
            results[file_type] = None

    # ---- Handle text and URL inputs ----
    results['text'] = request.form.get('user-text', '') or None
    results['url'] = request.form.get('url', '') or None

    print("Processing inputs:", results)

    # ---- Run ClaimFighter ----
    fighter = ClaimFighter()
    fighter.run(results)

    # ---- Extract Gemini + Tavily output ----
    try:
        with open(OUTPUT_JSON_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)

        claim_data = data.get("claim0", {})
        gemini_response = claim_data.get("gemini_response", {})
        tavily_sources = claim_data.get("tavily_sources", [])

        extracted = {
            "inputs": results,
            "gemini_response": gemini_response,
            "tavily_sources": tavily_sources
        }

        # ---- Save extracted info to new JSON file ----
        with open(PROCESSED_JSON_PATH, 'w', encoding='utf-8') as outfile:
            json.dump(extracted, outfile, indent=4, ensure_ascii=False)

        print(f"✅ Processed output saved to: {PROCESSED_JSON_PATH}")

        return jsonify({
            "status": "success",
            "message": "Processing complete",
            "data": extracted
        })

    except Exception as e:
        print(f"❌ Error extracting data: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/knowledge_graph')
def knowledge_graph():
    try:
        with open(OUTPUT_JSON_PATH, 'r', encoding='utf-8') as file:
            output = json.load(file)
    except Exception as e:
        print(f"Error loading output.json: {e}")
        return jsonify({"error": str(e)}), 500

    return render_template('knowledge_graph.html', output=output)


@app.route('/chat')
def chat():
    try:
        with open(OUTPUT_JSON_PATH, 'r', encoding='utf-8') as file:
            output = json.load(file)
    except Exception as e:
        print(f"Error loading output.json: {e}")
        return jsonify({"error": str(e)}), 500

    return render_template('chat.html', output=output)


if __name__ == '__main__':
    
    port = int(os.environ.get("PORT", 10000))  # Default to 10000 if not provided
    app.run(host="0.0.0.0", port=port, debug=False)



