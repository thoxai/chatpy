# ChatPy

Lokales Streamlit-Portal für den Import offizieller ChatGPT-Datenexporte und die Aufbereitung als Markdown-Wissensarchiv. Optional werden Gespräche durch **Mistral Small** zusammengefasst, kategorisiert und mit Tags versehen.

## Start (Windows PowerShell)

```powershell
cd ChatPy
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# .env lokal öffnen und MISTRAL_API_KEY eintragen
streamlit run app.py
```

Danach die lokale Adresse im Browser öffnen (normalerweise http://localhost:8501).

## Ablauf
1. ZIP des offiziellen ChatGPT-Datenexports oder `conversations.json` auswählen.
2. Chats ansehen und optional nach Stichwort filtern.
3. Ausgabeverzeichnis wählen (Standard `./output`; nur lokale Pfade).
4. Optional Mistral Small für Metadaten und Zusammenfassung einschalten.
5. Verarbeitung starten. Pro Gespräch entsteht eine Markdown-Datei mit YAML-Frontmatter und Gesprächsverlauf. `manifest.json` und `index.csv` dienen als Index.

**Datenschutz:** Bei aktivierter KI-Analyse werden gekürzte Gesprächsausschnitte an die Mistral-API übertragen. Standardmäßig ist diese Funktion deaktiviert. Originale bleiben lokal. API-Schlüssel nie in Git einchecken.

## Grenzen
- Unterstützt das verbreitete offizielle `conversations.json`-Format mit `mapping`, einschließlich verzweigter Chats (es wird der aktuell ausgewählte Pfad rekonstruiert, sofern `current_node` verfügbar ist).
- Anhänge und multimodale Inhalte werden nicht exportiert; textuelle Nachrichten werden übernommen.
- Große Exporte werden im Arbeitsspeicher verarbeitet; Streamlit begrenzt Uploads standardmäßig auf 200 MB. Bei Bedarf in `.streamlit/config.toml` anpassen.
- Die KI-Analyse verarbeitet pro Gespräch nur einen begrenzten Textauszug; das vollständige Transkript bleibt im Markdown.
- Bei KI-Fehlern wird ohne KI-Metadaten exportiert.
- Keine Synchronisierung mit dem PHP-Portal in dieser Version.
