import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from chatpy.core import load_export, extract_messages, export_one, save_index
from chatpy.mistral import analyze

load_dotenv()
st.set_page_config(page_title="ChatPy", page_icon="🧠", layout="wide")
st.title("ChatPy")
st.caption("ChatGPT-Export lokal einlesen · Gespräche strukturieren · Markdown-Wissensarchiv erstellen")

with st.sidebar:
    st.header("Einstellungen")
    outdir = st.text_input("Lokaler Ausgabeordner", value=str(Path.cwd() / "output"))
    use_ai = st.toggle("Mit Mistral Small analysieren", value=False)
    model = st.text_input("Mistral-Modell", value=os.getenv("MISTRAL_MODEL", "mistral-small-latest"))
    api_key = st.text_input("Mistral API-Key", value=os.getenv("MISTRAL_API_KEY", ""), type="password") if use_ai else ""
    st.caption("Bei KI-Analyse werden Textauszüge an Mistral gesendet. Ohne KI bleibt alles lokal.")

uploaded = st.file_uploader("Offiziellen ChatGPT-Export hochladen", type=["zip", "json"])
if not uploaded:
    st.info("Bitte eine ChatGPT-Export-ZIP oder die Datei conversations.json auswählen.")
    st.stop()

try:
    conversations = load_export(uploaded.getvalue(), uploaded.name)
except Exception as e:
    st.error(f"Export konnte nicht gelesen werden: {e}")
    st.stop()

st.success(f"{len(conversations)} Gespräche gefunden.")
search = st.text_input("Titel filtern", placeholder="z. B. ChexU, KI38, Python")
filtered = [c for c in conversations if search.casefold() in (c.get("title") or "").casefold()]
max_count = len(filtered)
st.write(f"**{max_count}** Gespräche im aktuellen Filter")
if not max_count:
    st.stop()
limit = st.number_input("Maximal zu verarbeitende Gespräche", min_value=1, max_value=max_count,
                        value=min(max_count, 25), step=1)
selection = filtered[:int(limit)]
with st.expander("Vorschau"):
    for c in selection[:15]:
        st.write(f"• {c.get('title') or 'Ohne Titel'} — {len(extract_messages(c))} Nachrichten")

if use_ai and not api_key:
    st.warning("Bitte einen Mistral-API-Schlüssel eintragen oder KI-Analyse deaktivieren.")

if st.button("Markdown-Dateien lokal erstellen", type="primary", disabled=bool(use_ai and not api_key)):
    dest = Path(outdir).expanduser().resolve()
    if dest == Path(dest.anchor):
        st.error("Bitte einen Unterordner statt des Laufwerks-Stammverzeichnisses wählen.")
        st.stop()
    progress = st.progress(0)
    status = st.empty()
    rows, errors = [], []
    for i, conv in enumerate(selection):
        title = conv.get("title") or "Ohne Titel"
        status.write(f"Verarbeite {i+1}/{len(selection)}: {title}")
        try:
            messages = extract_messages(conv)
            meta = {"category": "Unsortiert", "tags": [], "summary": ""}
            if use_ai:
                try:
                    meta = analyze(messages, api_key, model)
                except Exception as e:
                    errors.append(f"{title}: KI-Analyse fehlgeschlagen ({type(e).__name__}); ohne KI-Metadaten exportiert")
            rows.append(export_one(conv, messages, meta, dest))
        except Exception as e:
            errors.append(f"{title}: Exportfehler ({type(e).__name__}: {e})")
        progress.progress((i + 1) / len(selection))
    if rows:
        save_index(rows, dest)
    status.empty()
    st.success(f"{len(rows)} Markdown-Dateien in {dest} gespeichert.")
    if errors:
        with st.expander(f"{len(errors)} Hinweise / Fehler"):
            for e in errors:
                st.warning(e)
    st.caption("Enthalten: Markdown-Dateien, manifest.json und index.csv. Bereits vorhandene Dateien gleicher Chat-ID werden aktualisiert.")
