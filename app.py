from flask import Flask, request, jsonify
import pandas as pd
import zipfile
import os
import re
import json
import requests
import fitz  # PyMuPDF for PDFs
import subprocess
import sqlite3
import openai
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def query_llm(question):
    """Use GPT-4 to answer questions that are not handled by predefined rules."""
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI tutor answering data science assignment questions."},
            {"role": "user", "content": question}
        ],
        api_key=OPENAI_API_KEY
    )
    return response["choices"][0]["message"]["content"]

app = Flask(__name__)
OPENAI_API_KEY = "your-proxy-token"

def handle_question(question, file):
    """Identify the question type and return the correct answer. If unknown, use LLM."""
    if "unzip" in question and "CSV" in question:
        return handle_csv_extraction(file)
    if "Sort this JSON array" in question:
        return sort_json(question)
    if "How many Wednesdays" in question:
        return count_wednesdays(question)
    if "hidden input" in question:
        return extract_hidden_value(question)
    if "SQL" in question or "SQLite" in question:
        return execute_sql(question)
    if "npx" in question or "uv run" in question:
        return execute_shell_command(question)
    if "PDF" in question:
        return process_pdf(file)
    if "Google Sheets" in question:
        return google_sheets_api(question)
    if "IMDb" in question:
        return scrape_imdb()
    if "Hacker News" in question:
        return scrape_hacker_news()
    if "log file" in question:
        return process_logs(file)
    if "GitHub Actions" in question:
        return check_github_workflow(question)
    if "Excel" in question:
        return process_excel(file)
    if "JSON" in question:
        return process_json(file)
    return query_llm(question)


def google_sheets_api(question):
    """Fetch data from Google Sheets API."""
    API_URL = "https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/{range}?key={API_KEY}"
    spreadsheet_id = "your_spreadsheet_id"
    sheet_range = "Sheet1!A1:B10"
    API_KEY = "your_google_api_key"
    response = requests.get(API_URL.format(spreadsheetId=spreadsheet_id, range=sheet_range, API_KEY=API_KEY))
    if response.status_code == 200:
        return response.json()
    return "Failed to fetch Google Sheets data."

def scrape_imdb():
    """Scrape IMDb for top movies."""
    url = "https://www.imdb.com/chart/top/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        movies = [movie.text.strip() for movie in soup.select(".titleColumn a")[:10]]
        return movies
    return "Failed to fetch IMDb data."

def scrape_hacker_news():
    """Scrape Hacker News for top stories."""
    url = "https://news.ycombinator.com/"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        stories = [story.text for story in soup.select(".storylink")[:10]]
        return stories
    return "Failed to fetch Hacker News data."

# Extract CSV from ZIP
def handle_csv_extraction(file):
    if file and file.filename.endswith('.zip'):
        zip_path = "uploaded.zip"
        file.save(zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("extracted")
        csv_files = [f for f in os.listdir("extracted") if f.endswith('.csv')]
        if csv_files:
            df = pd.read_csv(f"extracted/{csv_files[0]}")
            if "answer" in df.columns:
                return str(df["answer"].iloc[0])
    return "Invalid file or missing 'answer' column."

# Sort JSON
def sort_json(question):
    json_match = re.search(r'\[.*\]', question, re.DOTALL)
    if not json_match:
        return "Invalid JSON format."
    json_data = json.loads(json_match.group(0))
    sorted_json = sorted(json_data, key=lambda x: (x["age"], x["name"]))
    return json.dumps(sorted_json, separators=(',', ':'))

# Count Wednesdays
def count_wednesdays(question):
    match = re.search(r'(\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2})', question)
    if not match:
        return "Invalid date format."
    start_date = datetime.strptime(match.group(1), "%Y-%m-%d")
    end_date = datetime.strptime(match.group(2), "%Y-%m-%d")
    count = sum(1 for d in range((end_date - start_date).days + 1)
                if (start_date + timedelta(days=d)).weekday() == 2)
    return str(count)

# Extract Hidden Input
def extract_hidden_value(question):
    match = re.search(r'value="([a-zA-Z0-9]+)"', question)
    return match.group(1) if match else "No hidden value found."

# Execute SQL Query
def execute_sql(question):
    query_match = re.search(r'SELECT .* FROM .*', question, re.IGNORECASE)
    if not query_match:
        return "Invalid SQL query."
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id INTEGER, name TEXT)")
    cursor.execute("INSERT INTO test VALUES (1, 'Alice'), (2, 'Bob')")
    cursor.execute(query_match.group(0))
    result = cursor.fetchall()
    conn.close()
    return str(result)

# Process PDF
def process_pdf(file):
    if file and file.filename.endswith('.pdf'):
        doc = fitz.open(stream=file.read(), filetype="pdf")
        text = "\n".join([page.get_text("text") for page in doc])
        return text[:500]  # Return first 500 chars
    return "Invalid PDF file."

# Execute Shell Command
def execute_shell_command(question):
    try:
        result = subprocess.check_output(question, shell=True, stderr=subprocess.STDOUT, text=True)
        return result.strip()
    except subprocess.CalledProcessError as e:
        return str(e)

# Process JSON
def process_json(file):
    try:
        data = json.load(file)
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"Invalid JSON file: {str(e)}"

# Process Excel
def process_excel(file):
    try:
        df = pd.read_excel(file)
        return df.to_json()
    except Exception as e:
        return f"Invalid Excel file: {str(e)}"

# Process Logs
def process_logs(file):
    try:
        logs = file.read().decode("utf-8").split("\n")
        return json.dumps(logs[:10])  # Return first 10 lines
    except Exception as e:
        return f"Invalid log file: {str(e)}"

# Check GitHub Actions Workflow
def check_github_workflow(question):
    return "GitHub Actions processing is not yet implemented."

@app.route('/api/', methods=['POST'])
def api():
    question = request.form.get("question")
    file = request.files.get("file")
    if not question:
        return jsonify({"answer": "No question provided"}), 400
    answer = handle_question(question, file)
    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(debug=True)