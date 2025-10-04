# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# OpenRouter GPT client
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key="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")

# SQLite database file
DB_FILE = "movies.db"

# Initialize SQLite table
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT,
            recommended_movies TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Save a recommendation
def save_recommendation(user_input, recommended_movies):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO recommendations (user_input, recommended_movies, timestamp)
        VALUES (?, ?, ?)
    """, (user_input, recommended_movies, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

# Fetch all past recommendations
def get_history():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, user_input, recommended_movies, timestamp FROM recommendations ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [
        {"id": r[0], "user_input": r[1], "recommended_movies": r[2], "timestamp": r[3]}
        for r in rows
    ]

@app.route("/recommend", methods=["POST"])
def recommend_movies():
    try:
        data = request.get_json()
        preference = data.get("preference", "")

        # GPT prompt
        messages = [
            {"role": "system", "content": "You are a helpful movie recommendation assistant."},
            {"role": "user", "content": f"Suggest 3–5 movies for this preference: {preference}. Return only the titles in a numbered list."}
        ]

        response = client.chat.completions.create(
            model="cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            messages=messages
        )

        raw_text = response.choices[0].message.content.strip()
        recommendations = [
            line.strip("0123456789). ").strip()
            for line in raw_text.split("\n") if line.strip()
        ]

        # Save to SQLite
        save_recommendation(preference, ", ".join(recommendations))

        return jsonify({"movies": recommendations, "raw": raw_text})

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/history", methods=["GET"])
def history():
    return jsonify(get_history())

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
