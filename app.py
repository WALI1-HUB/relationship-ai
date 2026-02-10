from flask import Flask, render_template, request, jsonify
import os
from groq import Groq
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Setup Flask with proper static/template paths for Netlify
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, 
            static_folder=os.path.join(BASE_DIR, 'static'),
            template_folder=os.path.join(BASE_DIR, 'templates'))

# Initialize Groq client
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = None

def get_groq_client():
    global client
    if client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        client = Groq(api_key=api_key)
    return client

# Database Setup
# Use /tmp for Netlify (serverless environment), otherwise use local path
if os.environ.get('APP_ENV') == 'production':
    DB_NAME = "/tmp/relationship_ai.db"
else:
    DB_NAME = os.path.join(BASE_DIR, "relationship_ai.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB on startup
try:
    init_db()
except Exception as e:
    print(f"Warning: Database initialization failed: {e}")

# Store conversation history in memory (for context)
# In a real production app, we would load this from the DB for the specific session.
conversation_history = [
    {
        "role": "system",
        "content": (
            "You are a warm, empathetic, and insightful relationship advisor AI. "
            "Your client is the girlfriend of a man named Wali. "
            "Your goal is to have a meaningful conversation with her about their relationship. "
            "You must ask her specific questions to understand her feelings and the dynamics of their relationship. "
            "Key questions to ask (weave these naturally into the conversation, don't ask all at once): "
            "1. Why do you like Wali? "
            "2. When did you realize you were in love with him? "
            "3. What are his bad habits or things that annoy you? "
            "4. What makes you feel most connected to him? "
            "Based on her answers, provide constructive, actionable, and personalized advice to help make their relationship even more successful and fulfilling. "
            "Be a good listener. Validate her feelings. offer gentle guidance. "
            "Keep your responses concise and engaging."
        )
    }
]

def save_message(role, content):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving message: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM messages ORDER BY timestamp DESC")
        messages = c.fetchall()
        conn.close()
        return render_template('admin.html', messages=messages)
    except Exception as e:
        return f"Error accessing admin panel: {e}"

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Save user message to DB
    save_message("user", user_message)

    # Add user message to history
    conversation_history.append({"role": "user", "content": user_message})

    try:
        groq_client = get_groq_client()
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=conversation_history,
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )

        ai_response = completion.choices[0].message.content
        
        # Save AI response to DB
        save_message("assistant", ai_response)
        
        # Add AI response to history
        conversation_history.append({"role": "assistant", "content": ai_response})

        return jsonify({"response": ai_response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False)
