# Recipe Vision OCR

Lokaler Vision-OCR-Dienst zur Erkennung und Strukturierung von Rezepten aus Bildern.

## Features

- Lokale Verarbeitung ohne Cloud
- Qwen2.5-VL über Ollama
- Bildverarbeitung und Komprimierung mit Pillow
- Flask REST API
- Strukturierte JSON-Ausgabe
- Android-Anbindung über HTTP Shortcuts

## Architektur

```
Android / HTTP Shortcuts
        |
        v
Flask Proxy :11435
        |
        v
Ollama :11434
        |
        v
Qwen2.5-VL
        |
        v
Structured JSON
```

## Voraussetzungen

- Windows
- Python 3
- Ollama
- Qwen2.5-VL
- Android-Gerät im gleichen WLAN

## Installation

### 1. Python-Umgebung

```bash
python -m venv venv
venv\Scripts\activate
```

### 2. Abhängigkeiten

```bash
pip install -r requirements.txt
```

### 3. Vision-Modell

```bash
ollama pull qwen2.5vl:7b
```

### 4. Eigenes Ollama-Modell erstellen

```bash
ollama create rezept-ocr -f Modelfile
```

### 5. Proxy starten

```bash
python proxy.py
```

Der Proxy läuft anschließend auf:

```
http://0.0.0.0:11435
```

## HTTP Shortcuts Konfiguration

| Einstellung | Wert |
|---|---|
| Methode | `POST` |
| URL | `http://PC-IP:11435/rezept` |
| Body | `form-data` |

**Parameter:**

| Name | Typ | Wert |
|---|---|---|
| `image` | Datei | Bild des Rezepts |
| `prompt` | Text | `Lies das Rezept aus dem Bild und gib es im vorgegebenen JSON-Format zurück.` |

## JSON-Ausgabe

Beispiel:

```json
{
  "title": "Spaghetti Carbonara",
  "servings": "2",
  "time": "20 Minuten",
  "ingredients": [
    "200 g Spaghetti",
    "2 Eier",
    "80 g Speck",
    "50 g Parmesan"
  ],
  "steps": [
    "Spaghetti in Salzwasser kochen.",
    "Speck anbraten.",
    "Eier mit Parmesan verrühren.",
    "Spaghetti mit den Zutaten vermischen."
  ],
  "notes": [],
  "uncertain": []
}
```


## Technologien

- Python
- Flask
- Pillow
- Requests
- Ollama
- Qwen2.5-VL
- REST
- JSON
- Android / HTTP Shortcuts

## Alles testen

Virtuelle Umgebung aktivieren:

```bat
cd C:\recipe-vision-ocr
venv\Scripts\activate
```

Proxy starten:

```bash
python proxy.py
```

Erwartete Ausgabe:

```
============================================================
Recipe Vision OCR
============================================================
Server:      http://0.0.0.0:11435
Ollama:      http://127.0.0.1:11434/api/generate
Modell:      rezept-ocr
Max. Bild:   1400px
JPEG Qualität: 78
============================================================
```