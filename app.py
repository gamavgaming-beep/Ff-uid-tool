from flask import Flask, request, render_template_string, send_file, session
import bytes_pb2
import meta_pb2
import io
import os
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24)

_store: dict = {}

def remove_uid_sequence(data: bytes, uid: int, pb2_class) -> bytes:
    msg = pb2_class()
    msg.uid = uid
    encoded = msg.SerializeToString()
    return data.replace(encoded, b'')

def file_ext(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    return ext or ""

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>UID Changer</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', sans-serif;
      background: #0f1117;
      color: #e2e8f0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
    }
    .container {
      background: #1a1d27;
      border: 1px solid #2d3148;
      border-radius: 16px;
      padding: 2.5rem;
      width: 100%;
      max-width: 580px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }
    h1 {
      font-size: 1.4rem;
      font-weight: 700;
      color: #a78bfa;
      margin-bottom: 0.4rem;
      letter-spacing: 0.02em;
    }
    .subtitle {
      font-size: 0.85rem;
      color: #64748b;
      margin-bottom: 2rem;
    }
    .upload-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    .upload-card {
      background: #12141e;
      border: 1.5px dashed #2d3148;
      border-radius: 12px;
      padding: 1.25rem 1rem;
      text-align: center;
      transition: border-color 0.2s;
    }
    .upload-card:hover { border-color: #7c3aed; }
    .upload-card label {
      display: block;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #94a3b8;
      margin-bottom: 0.75rem;
    }
    .upload-card .icon { font-size: 1.8rem; margin-bottom: 0.5rem; }
    .file-name {
      font-size: 0.72rem;
      color: #64748b;
      margin-top: 0.5rem;
      word-break: break-all;
    }
    input[type="file"] { display: none; }
    .pick-btn {
      background: #1e2035;
      border: 1px solid #3d4268;
      color: #c4b5fd;
      padding: 0.4rem 1rem;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.8rem;
      transition: background 0.2s;
    }
    .pick-btn:hover { background: #2a2d4a; }
    .submit-btn {
      width: 100%;
      padding: 0.85rem;
      background: linear-gradient(135deg, #7c3aed, #6d28d9);
      color: white;
      border: none;
      border-radius: 10px;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.2s;
      letter-spacing: 0.02em;
    }
    .submit-btn:hover { opacity: 0.88; }
    .results {
      margin-top: 1.75rem;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }
    .result-card {
      background: #12141e;
      border: 1px solid #2d3148;
      border-radius: 12px;
      padding: 1.1rem 1rem;
    }
    .result-card .r-label {
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #64748b;
      margin-bottom: 0.4rem;
    }
    .result-card .r-value {
      font-size: 1.25rem;
      font-weight: 700;
      color: #a78bfa;
      word-break: break-all;
    }
    .result-card .r-value.none {
      color: #3d4268;
      font-size: 0.9rem;
      font-weight: 400;
      font-style: italic;
    }
    .download-section {
      margin-top: 1.25rem;
      background: #12141e;
      border: 1px solid #2d3148;
      border-radius: 12px;
      padding: 1.1rem 1.25rem;
    }
    .download-section .ds-label {
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #64748b;
      margin-bottom: 0.85rem;
    }
    .download-btns { display: flex; gap: 0.75rem; flex-wrap: wrap; }
    .dl-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      background: #1e2035;
      border: 1px solid #3d4268;
      color: #c4b5fd;
      padding: 0.5rem 1.1rem;
      border-radius: 8px;
      text-decoration: none;
      font-size: 0.82rem;
      font-weight: 500;
      transition: background 0.2s, border-color 0.2s;
    }
    .dl-btn:hover { background: #2a2d4a; border-color: #7c3aed; color: #e9d5ff; }
    .error {
      margin-top: 1rem;
      background: #2d1515;
      border: 1px solid #7f1d1d;
      color: #fca5a5;
      padding: 0.8rem 1rem;
      border-radius: 8px;
      font-size: 0.82rem;
    }
  </style>
</head>
<body>
<div class="container">
  <h1>&#x2B21; UID Changer</h1>
  <p class="subtitle">Upload binary files to extract UIDs and strip them from the data.</p>

  <form method="POST" enctype="multipart/form-data">
    <div class="upload-grid">
      <div class="upload-card">
        <div class="icon">&#x1F4E6;</div>
        <label for="bytes_file">Bytes File</label>
        <label class="pick-btn" for="bytes_file">Choose file</label>
        <input type="file" id="bytes_file" name="bytes_file" onchange="showName(this,'bytes-name')">
        <div class="file-name" id="bytes-name">No file selected</div>
      </div>
      <div class="upload-card">
        <div class="icon">&#x1F5C2;</div>
        <label for="meta_file">Meta File</label>
        <label class="pick-btn" for="meta_file">Choose file</label>
        <input type="file" id="meta_file" name="meta_file" onchange="showName(this,'meta-name')">
        <div class="file-name" id="meta-name">No file selected</div>
      </div>
    </div>
    <button type="submit" class="submit-btn">Decode, Strip UIDs &amp; Prepare Downloads</button>
  </form>

  {% if error %}
  <div class="error">&#x26A0; {{ error }}</div>
  {% endif %}

  {% if bytes_uid is not none or meta_uid is not none %}
  <div class="results">
    <div class="result-card">
      <div class="r-label">Bytes UID</div>
      {% if bytes_uid is not none %}
        <div class="r-value">{{ bytes_uid }}</div>
      {% else %}
        <div class="r-value none">not provided</div>
      {% endif %}
    </div>
    <div class="result-card">
      <div class="r-label">Meta UID</div>
      {% if meta_uid is not none %}
        <div class="r-value">{{ meta_uid }}</div>
      {% else %}
        <div class="r-value none">not provided</div>
      {% endif %}
    </div>
  </div>

  <div class="download-section">
    <div class="ds-label">&#x2B07; Download modified files (UID sequence removed)</div>
    <div class="download-btns">
      {% if bytes_uid is not none %}
      <a class="dl-btn" href="/download/bytes">
        &#x1F4E6; bytes_modified{{ bytes_ext }}
      </a>
      {% endif %}
      {% if meta_uid is not none %}
      <a class="dl-btn" href="/download/meta">
        &#x1F5C2; meta_modified{{ meta_ext }}
      </a>
      {% endif %}
    </div>
  </div>
  {% endif %}
</div>

<script>
  function showName(input, targetId) {
    document.getElementById(targetId).textContent =
      input.files.length ? input.files[0].name : 'No file selected';
  }
</script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    bytes_uid = None
    meta_uid = None
    error = None
    bytes_ext = ""
    meta_ext = ""

    if request.method == "POST":
        bytes_file = request.files.get("bytes_file")
        meta_file = request.files.get("meta_file")

        if not (bytes_file and bytes_file.filename) and not (meta_file and meta_file.filename):
            error = "Please upload at least one file."
        else:
            try:
                sid = str(uuid.uuid4())
                store_entry = {}

                if bytes_file and bytes_file.filename:
                    raw = bytes_file.read()
                    msg = bytes_pb2.bytes()
                    msg.ParseFromString(raw)
                    bytes_uid = msg.uid
                    modified = remove_uid_sequence(raw, bytes_uid, bytes_pb2.bytes)
                    ext = file_ext(bytes_file.filename)
                    store_entry["bytes"] = modified
                    store_entry["bytes_name"] = "bytes_modified" + ext
                    bytes_ext = ext

                if meta_file and meta_file.filename:
                    raw = meta_file.read()
                    msg = meta_pb2.meta()
                    msg.ParseFromString(raw)
                    meta_uid = msg.uid
                    modified = remove_uid_sequence(raw, meta_uid, meta_pb2.meta)
                    ext = file_ext(meta_file.filename)
                    store_entry["meta"] = modified
                    store_entry["meta_name"] = "meta_modified" + ext
                    meta_ext = ext

                session["sid"] = sid
                _store[sid] = store_entry

            except Exception as e:
                error = f"Failed to decode protobuf: {str(e)}"

    return render_template_string(
        HTML,
        bytes_uid=bytes_uid,
        meta_uid=meta_uid,
        error=error,
        bytes_ext=bytes_ext,
        meta_ext=meta_ext,
    )

@app.route("/download/<kind>")
def download(kind):
    sid = session.get("sid")
    if not sid or sid not in _store:
        return "No file available. Please upload and decode first.", 404

    entry = _store[sid]
    if kind not in entry:
        return "File not found for this type.", 404

    data = entry[kind]
    filename = entry.get(kind + "_name", f"{kind}_modified.bin")
    return send_file(
        io.BytesIO(data),
        as_attachment=True,
        download_name=filename,
        mimetype="application/octet-stream",
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)