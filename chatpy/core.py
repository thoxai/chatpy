import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

def load_export(raw: bytes, filename: str):
    if filename.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            candidates = [n for n in z.namelist() if n.endswith("conversations.json") and not n.startswith("__MACOSX")]
            if not candidates:
                raise ValueError("Keine conversations.json in der ZIP gefunden.")
            with z.open(sorted(candidates, key=len)[0]) as f:
                data = json.load(f)
    else:
        data = json.loads(raw)
    if isinstance(data, dict) and "conversations" in data:
        data = data["conversations"]
    if not isinstance(data, list):
        raise ValueError("Erwartet wird eine Liste von Gesprächen.")
    return data

def timestamp(value):
    if value is None:
        return ""
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError):
        return ""

def text_from_message(msg):
    content = msg.get("content") or {}
    if isinstance(content, str):
        return content.strip()
    parts = content.get("parts") or []
    text = []
    for p in parts:
        if isinstance(p, str):
            text.append(p)
        elif isinstance(p, dict) and isinstance(p.get("text"), str):
            text.append(p["text"])
    return "\n\n".join(text).strip()

def extract_messages(conv):
    mapping = conv.get("mapping") or {}
    if not mapping:
        return [{"role": m.get("role", "unknown"), "text": str(m.get("text", "")),
                 "created_at": timestamp(m.get("create_time"))}
                for m in conv.get("messages", []) if m.get("text")]
    node_id = conv.get("current_node")
    chain = []
    if node_id and node_id in mapping:
        seen = set()
        while node_id and node_id in mapping and node_id not in seen:
            seen.add(node_id)
            node = mapping[node_id]
            chain.append(node)
            node_id = node.get("parent")
        chain.reverse()
    else:
        chain = sorted(mapping.values(), key=lambda n: (
            (n.get("message") or {}).get("create_time") or 0,
            n.get("id") or ""))
    result = []
    for node in chain:
        msg = node.get("message") or {}
        role = (msg.get("author") or {}).get("role", "unknown")
        if role not in ("user", "assistant", "system", "developer"):
            continue
        body = text_from_message(msg)
        if body:
            result.append({"role": role, "text": body, "created_at": timestamp(msg.get("create_time"))})
    return result

def slugify(value):
    s = re.sub(r"[^a-z0-9]+", "-", (value or "chat").lower(), flags=re.I).strip("-")
    return s[:65] or "chat"

def quote_yaml(value):
    return json.dumps(str(value), ensure_ascii=False)

def markdown_for(conv, messages, meta):
    title = conv.get("title") or "Ohne Titel"
    cid = str(conv.get("id") or conv.get("conversation_id") or "")
    lines = ["---", f"title: {quote_yaml(title)}", f"chat_id: {quote_yaml(cid)}",
             f"created_at: {quote_yaml(timestamp(conv.get('create_time')))}",
             f"updated_at: {quote_yaml(timestamp(conv.get('update_time')))}",
             f"category: {quote_yaml(meta.get('category', 'Unsortiert'))}",
             "tags: " + json.dumps(meta.get("tags", []), ensure_ascii=False),
             f"summary: {quote_yaml(meta.get('summary', ''))}", "---", "",
             f"# {title}", ""]
    if meta.get("summary"):
        lines += ["## KI-Zusammenfassung", "", meta["summary"], ""]
    lines += ["## Gespräch", ""]
    for i, m in enumerate(messages, 1):
        role = {"user": "Nutzer", "assistant": "Assistent", "system": "System", "developer": "Entwickler"}.get(m["role"], m["role"])
        lines += [f"### {i}. {role}", "", m["text"], ""]
    return "\n".join(lines)

def export_one(conv, messages, meta, directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    cid = str(conv.get("id") or conv.get("conversation_id") or "")
    if not cid:
        cid = hashlib.sha256(json.dumps(conv, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", cid)[:48] or "chat"
    name = f"{slugify(conv.get('title'))}-{safe_id}.md"
    content = markdown_for(conv, messages, meta)
    path = directory / name
    temp = path.with_suffix(".md.tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return {"id": cid, "title": conv.get("title") or "Ohne Titel",
            "filename": name, "sha256": digest, "size": len(content.encode("utf-8")),
            "messages": len(messages), "category": meta.get("category", "Unsortiert"),
            "tags": meta.get("tags", []), "updated_at": timestamp(conv.get("update_time"))}

def save_index(rows, directory: Path):
    manifest = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(), "files": rows}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    with (directory / "index.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "filename", "category", "messages", "updated_at", "sha256"])
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in writer.fieldnames})
