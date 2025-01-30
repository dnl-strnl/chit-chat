from flask import jsonify, Flask, render_template, request, Response, stream_with_context
from flask_cors import CORS
import json
from langchain_community.llms import Ollama
import os

from chit.database import Database


app = Flask(__name__)
CORS(app)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")
db = Database("./data/chat.db")
lm = Ollama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)

@app.route('/')
def home():
    return render_template('index.html')

def generate_tokens(question, session_id):
    for chunks in lm.stream(question):
        yield chunks

@app.route('/chat', methods=['POST'])
def chat():
    def generate_json(question, session_id):
        with app.app_context():
            full_content = ""
            for token in generate_tokens(question, session_id):
                full_content += token
                json_data = {
                    "model": OLLAMA_MODEL,
                    "content": token,
                    "done": False
                }
                yield json.dumps(json_data).encode('utf-8') + b'\n'

            # store messages in database.
            db.add_message(session_id, "user", question)
            db.add_message(session_id, "assistant", full_content)

            # update session title if it's the first message.
            session = db.get_session(session_id)

            # first user message + first LM response...
            is_first_message = len(session['messages']) == 2

            if is_first_message:
                title = question[:30] + ('...' if len(question) > 30 else '')
                db.update_session_title(session_id, title)

            # pack final output message.
            json_data = dict(model=OLLAMA_MODEL, full_content=full_content, done=True)
            yield json.dumps(json_data).encode('utf-8')

    try:

        data = request.json
        message = data.get('message')
        session_id = data.get('session_id')

        if not session_id:
            return jsonify(dict(error="No session ID provided.", success=False)), 400

        return Response(
            stream_with_context(generate_json(message, session_id)),
            mimetype='application/json'
        )

    except Exception as exception:
        return jsonify(dict(error=str(exception), success=False)), 500

@app.route('/sessions', methods=['GET'])
def list_sessions():
    sessions = db.get_all_sessions()
    return jsonify(sessions)

@app.route('/sessions', methods=['POST'])
def create_session():
    try:
        data = request.json
        session_id = data.get('session_id')
        title = data.get('title', 'New Chat')
        model = data.get('model', OLLAMA_MODEL)

        session = db.create_session(session_id, title, model)
        return jsonify(session)
    except Exception as exception:
        return jsonify(dict(error=str(exception), success=False)), 500

@app.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    session = db.get_session(session_id)
    if session:
        return jsonify(session)
    return jsonify(dict(error="Session not found.", success=False)), 404

@app.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    try:
        db.delete_session(session_id)
        return jsonify({"success": True})
    except Exception as exception:
        return jsonify(dict(error=str(exception), success=False)), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
