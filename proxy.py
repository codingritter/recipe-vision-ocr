import base64
import io
import json
import os
from typing import Any

import requests
from flask import Flask, jsonify, request
from PIL import Image, ImageOps, UnidentifiedImageError


app = Flask(__name__)

# ---------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://127.0.0.1:11434/api/generate"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "rezept-ocr"
)

PROXY_HOST = os.getenv(
    "PROXY_HOST",
    "0.0.0.0"
)

PROXY_PORT = int(
    os.getenv(
        "PROXY_PORT",
        "11435"
    )
)

MAX_IMAGE_SIZE = int(
    os.getenv(
        "MAX_IMAGE_SIZE",
        "1400"
    )
)

JPEG_QUALITY = int(
    os.getenv(
        "JPEG_QUALITY",
        "78"
    )
)

OLLAMA_TIMEOUT = int(
    os.getenv(
        "OLLAMA_TIMEOUT",
        "600"
    )
)

MAX_UPLOAD_SIZE = 20 * 1024 * 1024

app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE


# ---------------------------------------------------------
# JSON-Schema für das Rezept
# ---------------------------------------------------------

RECIPE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": ["string", "null"]
        },
        "servings": {
            "type": ["string", "null"]
        },
        "time": {
            "type": ["string", "null"]
        },
        "ingredients": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "steps": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "notes": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "uncertain": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },
    "required": [
        "title",
        "servings",
        "time",
        "ingredients",
        "steps",
        "notes",
        "uncertain"
    ]
}


# ---------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------

def resize_and_compress_image(file_storage) -> bytes:
    """
    Liest das hochgeladene Bild,
    korrigiert die EXIF-Ausrichtung,
    verkleinert es und speichert es als JPEG.
    """

    try:
        image = Image.open(file_storage.stream)

    except UnidentifiedImageError as exc:
        raise ValueError(
            "Die Datei konnte nicht als Bild erkannt werden."
        ) from exc


    image = ImageOps.exif_transpose(image)

    image.thumbnail(
        (MAX_IMAGE_SIZE, MAX_IMAGE_SIZE),
        Image.Resampling.LANCZOS
    )

    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=JPEG_QUALITY,
        optimize=True
    )

    return buffer.getvalue()


def image_to_base64(image_bytes: bytes) -> str:
    """
    Wandelt Bilddaten in einen Base64-String um.
    """

    return base64.b64encode(
        image_bytes
    ).decode("utf-8")


def extract_json_from_response(response_text: str) -> dict[str, Any]:
    """
    Versucht, die Modellantwort als JSON zu interpretieren.

    Falls das Modell trotzdem Markdown-Codeblöcke zurückgibt,
    werden diese entfernt.
    """

    text = response_text.strip()

    # Markdown-Codeblock entfernen.
    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    try:
        result = json.loads(text)

    except json.JSONDecodeError as exc:
        raise ValueError(
            "Das Modell hat kein gültiges JSON zurückgegeben."
        ) from exc

    if not isinstance(result, dict):
        raise ValueError(
            "Die Modellantwort ist kein JSON-Objekt."
        )

    return result


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------

@app.get("/")
def health_check():
    return jsonify({
        "status": "ok",
        "service": "recipe-vision-ocr",
        "model": OLLAMA_MODEL,
        "ollama_url": OLLAMA_URL
    })


# ---------------------------------------------------------
# Rezept-Endpunkt
# ---------------------------------------------------------

@app.post("/rezept")
def rezept():

    print()
    print("=" * 60)
    print("Neuer Rezept-Request")
    print("=" * 60)

    # -----------------------------------------------------
    # Bild prüfen
    # -----------------------------------------------------

    if "image" not in request.files:
        return jsonify({
            "error": "Kein Bild erhalten.",
            "details": (
                "Das HTTP-Shortcuts-Dateifeld muss "
                "den Namen 'image' verwenden."
            )
        }), 400

    image_file = request.files["image"]

    if not image_file.filename:
        return jsonify({
            "error": "Keine Datei ausgewählt."
        }), 400

    print(f"Bild: {image_file.filename}")

    # -----------------------------------------------------
    # Prompt aus Request lesen
    # -----------------------------------------------------

    user_prompt = request.form.get(
        "prompt",
        (
            "Lies das Rezept aus dem Bild "
            "und gib es im vorgegebenen JSON-Format zurück."
        )
    )

    print(f"Prompt: {user_prompt}")

    # -----------------------------------------------------
    # Bild verkleinern
    # -----------------------------------------------------

    try:
        compressed_image = resize_and_compress_image(
            image_file
        )

    except ValueError as exc:
        return jsonify({
            "error": "Bildverarbeitung fehlgeschlagen.",
            "details": str(exc)
        }), 400

    print(
        f"Bildgröße nach Komprimierung: "
        f"{len(compressed_image) / 1024:.1f} KB"
    )

    # -----------------------------------------------------
    # Base64
    # -----------------------------------------------------

    image_base64 = image_to_base64(
        compressed_image
    )

    # -----------------------------------------------------
    # Anfrage an Ollama
    # -----------------------------------------------------

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": user_prompt,
        "images": [
            image_base64
        ],
        "stream": False,

        # Modell soll möglichst lange geladen bleiben.
        "keep_alive": "10m",

        # Wir verwenden Structured Output.
        "format": RECIPE_SCHEMA
    }

    print("Sende Anfrage an Ollama...")
    print(f"Modell: {OLLAMA_MODEL}")

    try:

        ollama_response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=OLLAMA_TIMEOUT
        )

    except requests.RequestException as exc:

        print(f"Ollama-Verbindungsfehler: {exc}")

        return jsonify({
            "error": "Ollama konnte nicht erreicht werden.",
            "details": str(exc)
        }), 502

    # -----------------------------------------------------
    # HTTP-Fehler von Ollama
    # -----------------------------------------------------

    if not ollama_response.ok:

        print(
            "Ollama HTTP-Fehler:",
            ollama_response.status_code
        )

        try:
            ollama_error = ollama_response.json()

        except ValueError:
            ollama_error = {
                "response": ollama_response.text
            }

        return jsonify({
            "error": "Ollama hat einen Fehler zurückgegeben.",
            "ollama_status": ollama_response.status_code,
            "ollama_response": ollama_error
        }), 502

    # -----------------------------------------------------
    # Ollama JSON lesen
    # -----------------------------------------------------

    try:
        ollama_data = ollama_response.json()

    except ValueError:

        return jsonify({
            "error": "Ollama hat kein gültiges JSON geliefert."
        }), 502

    model_response = ollama_data.get(
        "response",
        ""
    )

    if not model_response:

        return jsonify({
            "error": "Ollama hat keine Modellantwort geliefert."
        }), 502

    # -----------------------------------------------------
    # Modellantwort in JSON umwandeln
    # -----------------------------------------------------

    try:

        recipe = extract_json_from_response(
            model_response
        )

    except ValueError as exc:

        print("Ungültige Modellantwort:")
        print(model_response)

        return jsonify({
            "error": str(exc),
            "raw_response": model_response
        }), 502

    # -----------------------------------------------------
    # Antwort an Smartphone
    # -----------------------------------------------------

    print("Rezept erfolgreich erkannt.")
    print("=" * 60)

    return jsonify(recipe)


# ---------------------------------------------------------
# Fehlerbehandlung
# ---------------------------------------------------------

@app.errorhandler(413)
def request_too_large(error):

    return jsonify({
        "error": "Das Bild ist zu groß.",
        "max_size_mb": MAX_UPLOAD_SIZE / 1024 / 1024
    }), 413


@app.errorhandler(Exception)
def handle_unexpected_error(error):

    print("Unerwarteter Fehler:")
    print(repr(error))

    return jsonify({
        "error": "Interner Serverfehler.",
        "details": str(error)
    }), 500


# ---------------------------------------------------------
# Server starten
# ---------------------------------------------------------

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("Recipe Vision OCR")
    print("=" * 60)
    print(f"Server:      http://{PROXY_HOST}:{PROXY_PORT}")
    print(f"Ollama:      {OLLAMA_URL}")
    print(f"Modell:      {OLLAMA_MODEL}")
    print(f"Max. Bild:   {MAX_IMAGE_SIZE}px")
    print(f"JPEG Qualität: {JPEG_QUALITY}")
    print("=" * 60)
    print()

    app.run(
        host=PROXY_HOST,
        port=PROXY_PORT,
        debug=False
    )