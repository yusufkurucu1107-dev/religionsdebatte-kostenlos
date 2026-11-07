# Religionsdebatte – kostenlose Smartphone- und PC-Version

Diese Version benötigt **keinen OpenAI-API-Key** und ruft keine kostenpflichtige API auf.

## Was die App kann

- Enthält den vollständigen Katalog mit 60 Fragen.
- Erstellt getrennte Rollen-Prompts für islamischen Gelehrten, christlichen Gelehrten und neutralen Moderator.
- Öffnet ChatGPT zum manuellen Einfügen der Prompts.
- Ermöglicht das Einfügen der drei Rollen-Antworten in die App.
- Erstellt einen Bewertungs-Prompt für den Moderator.
- Übernimmt Moderator-Punktzahlen aus JSON oder erlaubt manuelle Eingabe.
- Addiert Punkte, zeigt den Zwischenstand und exportiert den Debattenverlauf.
- Funktioniert auf PC und Smartphone im Browser.

## Wichtige kostenlose Nutzungsweise

Die drei KI-Rollen laufen **nicht automatisch innerhalb der App**. Ohne API-Verbindung kann die App keine KI-Anfragen selbst ausführen. Öffne drei getrennte ChatGPT-Chats, verwende jeweils den passenden Rollen-Prompt, kopiere die Antworten in die App und lasse den Moderator anhand des Moderator-Prompts bewerten.

## Online auf Streamlit Community Cloud bereitstellen

1. Entpacke die ZIP-Datei.
2. Lege ein privates oder öffentliches GitHub-Repository an.
3. Lade diese Dateien in das Repository: `app.py`, `questions.py`, `requirements.txt`, `README.md`.
4. Öffne https://share.streamlit.io/ und melde dich mit GitHub an.
5. Wähle **Create app**.
6. Wähle dein Repository und den Branch.
7. Als Main file path trägst du `app.py` ein.
8. Wähle **Deploy**.
9. Öffne die von Streamlit angezeigte Webadresse auf deinem Samsung-Handy oder PC.

Es werden keine Secrets und kein API-Key benötigt.

## Lokal starten

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Datensicherung

Runden bleiben während einer laufenden Browser-Sitzung in der App. Lade regelmäßig das JSON-Backup herunter. Kostenlose Hosting-Instanzen garantieren keine dauerhafte Speicherung lokaler Dateien oder Sitzungsdaten.
