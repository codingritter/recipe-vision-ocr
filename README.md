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

## Voraussetzungen

- Windows
- Python 3
- Ollama
- Qwen2.5-VL
- Android-Gerät im gleichen WLAN

## Installation

### 1. Python Umgebung

```bash
python -m venv venv
venv\Scripts\activate