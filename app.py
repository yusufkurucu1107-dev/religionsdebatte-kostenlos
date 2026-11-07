from __future__ import annotations

import json
import csv
import io
from datetime import datetime
from pathlib import Path

import streamlit as st
from questions import QUESTIONS

st.set_page_config(
    page_title="Religionsdebatte – kostenlose Version",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.main .block-container {max-width: 920px; padding: 1rem 1rem 3rem;}
.hero {padding:1.15rem; border:1px solid rgba(128,128,128,.3); border-radius:18px; margin-bottom:1rem;}
.small-muted {opacity:.75; font-size:.9rem;}
div.stButton>button, div.stDownloadButton>button {width:100%; min-height:2.8rem; border-radius:12px;}
div[data-testid="stTextArea"] textarea, div[data-testid="stTextInput"] input {font-size:16px;}
@media(max-width:700px) {
 .main .block-container {padding:.55rem .65rem 2rem;}
 .hero {padding:.8rem;}
 .hero h1 {font-size:1.55rem !important;}
 div[data-testid="stHorizontalBlock"] {flex-wrap:wrap !important; gap:.5rem !important;}
 div[data-testid="stHorizontalBlock"]>div[data-testid="column"] {min-width:100% !important; flex:1 1 100% !important;}
 div.stButton>button, div.stDownloadButton>button {width:100%;}
 .stTabs [data-baseweb="tab-list"] {gap:.3rem; overflow-x:auto; flex-wrap:nowrap;}
 .stTabs [data-baseweb="tab"] {white-space:nowrap; padding:.4rem .6rem;}
}
</style>
""", unsafe_allow_html=True)

# The free version deliberately does not import or call any paid AI API.
if "debate_rounds" not in st.session_state:
    st.session_state.debate_rounds = []
if "selected_question" not in st.session_state:
    st.session_state.selected_question = 0
if "json_score_status" not in st.session_state:
    st.session_state.json_score_status = ""

ISLAM_ROLE = """Du bist ein hochqualifizierter islamischer Theologe und Religionswissenschaftler. Deine Fachgebiete umfassen Koran, Tafsir, Hadithwissenschaft, islamische Theologie (Aqidah), Tawhid, Kalām, islamische Philosophie, islamische Geschichte und vergleichende Religionswissenschaft.

Vertrete die islamische Position fachlich stark, aber fair. Beantworte die konkrete Frage direkt. Stelle christliche Lehren zuerst in ihrer stärksten plausiblen Form dar, bevor du sie kritisierst. Unterscheide bei Bedarf sunnitische, schiitische und andere Positionen. Nenne genaue Koranstellen (Sure und Vers), Hadith-Sammlungen und Nummern nur, wenn du sie verlässlich kennst. Unterscheide Glaubensaussagen, historische Rekonstruktion und akademischen Forschungsstand. Erfinde keine Quellen, Zitate oder Konsense. Weise auf Unsicherheiten hin. Antworte auf Deutsch, ausführlich, respektvoll und argumentativ präzise."""

CHRISTIAN_ROLE = """Du bist ein hochqualifizierter christlicher Theologe und Religionswissenschaftler. Deine Fachgebiete umfassen Altes und Neues Testament, Evangelien, Paulusbriefe, biblische Sprachen, Textkritik, frühes Christentum, Kirchenväter, Konzilien, Christologie, Trinitätslehre, Soteriologie und Kirchengeschichte.

Vertrete die klassische christliche Position fachlich stark, aber fair. Beantworte die konkrete Frage direkt. Stelle islamische Lehren zuerst in ihrer stärksten plausiblen Form dar, bevor du sie kritisierst. Unterscheide bei Bedarf katholische, orthodoxe, protestantische und andere Positionen. Nenne genaue Bibelstellen und berücksichtige Übersetzungs- und Textvarianten. Unterscheide Glaubensaussagen, historische Rekonstruktion und akademischen Forschungsstand. Erfinde keine Quellen, Zitate oder Konsense. Weise auf Unsicherheiten hin. Antworte auf Deutsch, ausführlich, respektvoll und argumentativ präzise."""

MODERATOR_ROLE = """Du bist ein vollständig neutraler akademischer Debattenmoderator. Du vertrittst weder Islam noch Christentum. Bewerte ausschließlich die Qualität der Argumentation, niemals welche Religion wahr oder falsch ist.

Prüfe direkte Beantwortung, logische Konsistenz, Belegqualität, historische Genauigkeit, Kontexttreue und Umgang mit Gegenargumenten. Gleiche Maßstäbe für beide Seiten. Eloquenz, Selbstsicherheit oder bloße Menge an Zitaten sind keine Belege. Ein religiöser Text ist eine Primärquelle für die Lehre der jeweiligen Tradition; seine historische Aussagekraft muss für jede historische Behauptung gesondert beurteilt werden. Unterscheide gesicherte Fakten, Forschungsmehrheiten, Minderheitenpositionen, theologische Deutungen und offene Fragen. Erfinde keine Belege. Beide Seiten dürfen hohe, niedrige oder gleiche Bewertungen bekommen.

Bewerte jede Seite in fünf Kriterien von 0 bis 20 Punkten: (1) logische Konsistenz, (2) Quellenqualität und Nachprüfbarkeit, (3) historische/textkritische Genauigkeit, (4) direkte Beantwortung und Umgang mit Einwänden, (5) Sachlichkeit und faire Darstellung. Begründe jeden Wert konkret. Ein Gleichstand ist möglich."""


def build_prompt(role: str, question: str, task: str, context: str = "") -> str:
    return f"{role}\n\nAKTUELLE DEBATTENFRAGE:\n{question}\n\nAUFGABE:\n{task}\n\nBISHERIGER DEBATTENKONTEXT:\n{context or 'Noch keine Antworten vorhanden.'}\n\nAntworte auf Deutsch. Nenne Quellen so genau wie verlässlich möglich und kennzeichne Unsicherheit."


def getv(key: str) -> str:
    return str(st.session_state.get(key, "")).strip()


def safe_total(scores: dict) -> int:
    return sum(int(scores.get(k, 0)) for k in ("logic", "sources", "history", "rebuttal", "fairness"))


def score_block(label: str, prefix: str) -> dict:
    st.markdown(f"#### {label}")
    labels = [
        ("logic", "Logische Konsistenz"),
        ("sources", "Quellenqualität"),
        ("history", "Historische / textkritische Genauigkeit"),
        ("rebuttal", "Beantwortung der Gegenargumente"),
        ("fairness", "Sachlichkeit und Fairness"),
    ]
    result = {}
    for key, name in labels:
        result[key] = st.number_input(
            f"{name} (0–20)", min_value=0, max_value=20,
            value=int(st.session_state.get(f"{prefix}_{key}", 0)),
            step=1, key=f"{prefix}_{key}"
        )
    st.metric(f"Punkte {label}", f"{safe_total(result)} / 100")
    return result


st.markdown("""
<div class="hero">
  <div class="small-muted">KOSTENLOSE DEBATTEN-PLATTFORM · OHNE API-SCHLÜSSEL</div>
  <h1>⚖️ Islam vs. Christentum</h1>
  <p>Drei getrennte ChatGPT-Rollen, alle 60 Pflichtfragen, manuelle Bewertung und laufender Punktestand.</p>
</div>
""", unsafe_allow_html=True)

st.info("Diese Version ruft keine kostenpflichtige API auf. Die drei KI-Rollen antworten nicht automatisch in dieser App: Du öffnest für jede Rolle einen eigenen ChatGPT-Chat, kopierst den jeweiligen Prompt hinein und fügst die Antworten hier ein. Die Punkte werden in der App addiert.")

# Scoreboard
rounds = st.session_state.debate_rounds
sum_islam = sum(r["islam_score"] for r in rounds)
sum_christian = sum(r["christian_score"] for r in rounds)
a, b, c = st.columns(3)
a.metric("☪️ Islam", sum_islam)
b.metric("✝️ Christentum", sum_christian)
if sum_islam > sum_christian:
    leader = "Islam führt"
elif sum_christian > sum_islam:
    leader = "Christentum führt"
else:
    leader = "Gleichstand"
c.metric("Zwischenstand", leader)
st.caption(f"Gespeicherte Runden: {len(rounds)} · Fragen aus dem festen Katalog abgeschlossen: {len(set(r['question_no'] for r in rounds if r['question_no']))}/60")

completed = {r["question_no"] for r in rounds if r["question_no"]}
with st.expander("📚 Fortschritt: alle 60 Pflichtfragen", expanded=False):
    for i, (cat, q) in enumerate(QUESTIONS, start=1):
        mark = "✅" if i in completed else "⬜"
        st.write(f"{mark} **{i}. {cat}:** {q}")

st.divider()
st.header("1. Debattenfrage auswählen")
question_options = [f"{i}. [{cat}] {q}" for i, (cat, q) in enumerate(QUESTIONS, start=1)]
choice = st.selectbox("Pflichtfrage", question_options, index=min(st.session_state.selected_question, 59), key="question_choice")
q_index = question_options.index(choice)
st.session_state.selected_question = q_index
question_no = q_index + 1
category, selected_question = QUESTIONS[q_index]
st.markdown(f"**Frage {question_no} von 60 · {category}**")
st.write(selected_question)
custom_question = st.text_input("Oder eigene Zusatzfrage (optional)", placeholder="Eigene Frage eingeben …")
if custom_question.strip():
    selected_question = custom_question.strip()
    question_no_for_save = None
else:
    question_no_for_save = question_no

st.divider()
st.header("2. Drei getrennte KI-Rollen")
st.caption("Öffne für jede Rolle einen eigenen ChatGPT-Chat. Die Prompts sind auf diese konkrete Debattenfrage zugeschnitten.")

prompt_tabs = st.tabs(["☪️ Islamischer Gelehrter", "✝️ Christlicher Gelehrter", "⚖️ Moderator"])
with prompt_tabs[0]:
    islam_prompt = build_prompt(ISLAM_ROLE, selected_question, "Gib dein Eröffnungsargument. Beantworte die Frage direkt und liefere die stärksten islamischen Argumente sowie passende Quellen.")
    st.code(islam_prompt, language="text")
    st.download_button("Prompt für Islam herunterladen", islam_prompt, file_name="prompt_islam.txt", mime="text/plain")
    st.link_button("ChatGPT öffnen – Islam", "https://chatgpt.com/")
with prompt_tabs[1]:
    christian_prompt = build_prompt(CHRISTIAN_ROLE, selected_question, "Gib dein Eröffnungsargument. Beantworte die Frage direkt und liefere die stärksten christlichen Argumente sowie passende Quellen.")
    st.code(christian_prompt, language="text")
    st.download_button("Prompt für Christentum herunterladen", christian_prompt, file_name="prompt_christentum.txt", mime="text/plain")
    st.link_button("ChatGPT öffnen – Christentum", "https://chatgpt.com/")
with prompt_tabs[2]:
    moderator_template = build_prompt(MODERATOR_ROLE, selected_question, "Stelle zunächst eine faire, präzise Nachfrage an jede Seite. Bewerte noch nicht, bevor beide Nachfragen beantwortet wurden.")
    st.code(moderator_template, language="text")
    st.download_button("Prompt für Moderator herunterladen", moderator_template, file_name="prompt_moderator.txt", mime="text/plain")
    st.link_button("Neuen Moderator-Chat öffnen", "https://chatgpt.com/")

st.divider()
st.header("3. Antworten der Gelehrten eintragen")
st.caption("Füge hier die Antworten aus den jeweiligen getrennten ChatGPT-Chats ein. Auf dem Handy kannst du zwischen den Tabs wechseln.")
ans_tabs = st.tabs(["☪️ Islam", "✝️ Christentum", "⚖️ Moderation"])
with ans_tabs[0]:
    st.text_area("Islamisches Eröffnungsargument", key="islam_opening", height=190)
    st.text_area("Islamische Erwiderung auf das Christentum", key="islam_rebuttal", height=160)
    st.text_area("Antwort auf die Nachfrage des Moderators", key="islam_followup", height=150)
with ans_tabs[1]:
    st.text_area("Christliches Eröffnungsargument", key="christian_opening", height=190)
    st.text_area("Christliche Erwiderung auf den Islam", key="christian_rebuttal", height=160)
    st.text_area("Antwort auf die Nachfrage des Moderators", key="christian_followup", height=150)
with ans_tabs[2]:
    st.text_area("Nachfrage des Moderators an den Islam", key="moderator_q_islam", height=100)
    st.text_area("Nachfrage des Moderators an das Christentum", key="moderator_q_christian", height=100)
    st.text_area("Neutrale Beobachtungen / offene Sachfragen", key="moderator_notes", height=130)

context = f"ISLAMISCHE ERÖFFNUNG:\n{getv('islam_opening')}\n\nCHRISTLICHE ERÖFFNUNG:\n{getv('christian_opening')}\n\nISLAMISCHE ERWIDERUNG:\n{getv('islam_rebuttal')}\n\nCHRISTLICHE ERWIDERUNG:\n{getv('christian_rebuttal')}"
mod_eval_prompt = build_prompt(
    MODERATOR_ROLE,
    selected_question,
    "Bewerte jetzt die Debatte anhand der fünf 0–20-Kriterien für beide Seiten. Begründe jeden Einzelwert konkret. Bevorzuge keine Religion. Wenn die Antworten noch nicht ausreichen, sage ausdrücklich, welche Rückfragen fehlen. Gib am Ende ausschließlich zusätzlich einen JSON-Block mit diesem Format aus: {\"islam\":{\"logic\":0,\"sources\":0,\"history\":0,\"rebuttal\":0,\"fairness\":0},\"christian\":{\"logic\":0,\"sources\":0,\"history\":0,\"rebuttal\":0,\"fairness\":0},\"comparison\":\"kurze Begründung\",\"factuality_notes\":[\"Prüfhinweis\"]}. Ersetze die Nullen durch ganzzahlige Werte von 0 bis 20.",
    context + f"\n\nMODERATOR-NACHFRAGEN UND NOTIZEN:\n{getv('moderator_q_islam')}\n{getv('moderator_q_christian')}\n{getv('moderator_notes')}\n\nANTWORT ISLAM AUF NACHFRAGE:\n{getv('islam_followup')}\n\nANTWORT CHRISTENTUM AUF NACHFRAGE:\n{getv('christian_followup')}"
)

st.divider()
st.header("4. Moderator bewertet die Runde")
st.markdown("**Schritt A:** Öffne einen frischen Moderator-Chat, kopiere diesen Prompt hinein und lasse beide Seiten unabhängig bewerten.")
st.code(mod_eval_prompt, language="text")
st.download_button("Bewertungs-Prompt herunterladen", mod_eval_prompt, file_name="moderator_bewertung.txt", mime="text/plain")
st.link_button("Moderator-ChatGPT öffnen", "https://chatgpt.com/")

st.markdown("**Schritt B:** Falls der Moderator den JSON-Block ausgegeben hat, füge ihn hier ein. Die App übernimmt dann die Punktzahlen.")
score_json = st.text_area("JSON-Punktzahlen des Moderators (optional)", key="score_json_input", height=150, placeholder='{"islam":{"logic":15,"sources":16,"history":14,"rebuttal":17,"fairness":18},"christian":{"logic":16,"sources":15,"history":15,"rebuttal":16,"fairness":18},"comparison":"...","factuality_notes":[]}')
if st.button("JSON-Punkte übernehmen"):
    try:
        raw = score_json.strip()
        if "```" in raw:
            raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        for side, prefix in (("islam", "islam_score"), ("christian", "christian_score")):
            vals = data[side]
            for field in ("logic", "sources", "history", "rebuttal", "fairness"):
                number = int(vals[field])
                if not 0 <= number <= 20:
                    raise ValueError(f"{side}.{field} muss zwischen 0 und 20 liegen")
                st.session_state[f"{prefix}_{field}"] = number
        st.session_state.json_score_status = "Punkte wurden übernommen. Bitte prüfe sie vor dem Speichern."
    except Exception as exc:
        st.session_state.json_score_status = f"JSON konnte nicht übernommen werden: {exc}"
if st.session_state.json_score_status:
    st.info(st.session_state.json_score_status)

st.markdown("**Schritt C:** Punkte prüfen oder manuell eintragen. Je Seite sind maximal 100 Punkte möglich.")
score_a, score_b = st.columns(2)
with score_a:
    islam_scores = score_block("☪️ Islamischer Gelehrter", "islam_score")
with score_b:
    christian_scores = score_block("✝️ Christlicher Gelehrter", "christian_score")

moderator_comparison = st.text_area("Begründung des Moderators / Vergleich", key="moderator_comparison", height=130)
factuality = st.text_area("Sachliche Prüfhinweise und offene Quellenfragen", key="factuality_notes", height=100)

if st.button("✅ Runde speichern und Punktestand aktualisieren", type="primary"):
    if not (getv("islam_opening") and getv("christian_opening")):
        st.error("Bitte mindestens beide Eröffnungsargumente eintragen, bevor du die Runde speicherst.")
    else:
        islam_total = safe_total(islam_scores)
        christian_total = safe_total(christian_scores)
        result = "Islam" if islam_total > christian_total else "Christentum" if christian_total > islam_total else "Gleichstand"
        record = {
            "round": len(st.session_state.debate_rounds) + 1,
            "question_no": question_no_for_save,
            "category": category if question_no_for_save else "Eigene Zusatzfrage",
            "question": selected_question,
            "islam_opening": getv("islam_opening"),
            "christian_opening": getv("christian_opening"),
            "islam_rebuttal": getv("islam_rebuttal"),
            "christian_rebuttal": getv("christian_rebuttal"),
            "islam_followup": getv("islam_followup"),
            "christian_followup": getv("christian_followup"),
            "moderator_q_islam": getv("moderator_q_islam"),
            "moderator_q_christian": getv("moderator_q_christian"),
            "moderator_notes": getv("moderator_notes"),
            "islam_scores": islam_scores,
            "christian_scores": christian_scores,
            "islam_score": islam_total,
            "christian_score": christian_total,
            "result": result,
            "comparison": moderator_comparison,
            "factuality_notes": factuality,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
        }
        st.session_state.debate_rounds.append(record)
        st.success(f"Runde gespeichert. Ergebnis: {result} ({islam_total} : {christian_total}).")
        st.rerun()

st.divider()
st.header("5. Debattenverlauf und Export")
if rounds:
    for record in reversed(rounds):
        label = f"Runde {record['round']} · {record['question']} · Islam {record['islam_score']} : Christentum {record['christian_score']}"
        with st.expander(label):
            st.write(f"**Ergebnis:** {record['result']}")
            st.write("**Islamisches Argument:**")
            st.write(record["islam_opening"])
            st.write("**Christliches Argument:**")
            st.write(record["christian_opening"])
            st.write("**Bewertung:**")
            st.write(record.get("comparison") or "Keine zusätzliche Begründung hinterlegt.")
    export_data = json.dumps(rounds, ensure_ascii=False, indent=2)
    st.download_button("📥 Gesamten Debattenverlauf als JSON sichern", export_data, file_name="religionsdebatte_backup.json", mime="application/json")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Runde", "Fragenummer", "Kategorie", "Frage", "Islam Punkte", "Christentum Punkte", "Ergebnis", "Gespeichert am"])
    for r in rounds:
        writer.writerow([r["round"], r["question_no"], r["category"], r["question"], r["islam_score"], r["christian_score"], r["result"], r["saved_at"]])
    st.download_button("📊 Punktetabelle als CSV sichern", output.getvalue(), file_name="religionsdebatte_punkte.csv", mime="text/csv")
else:
    st.caption("Noch keine Runden gespeichert.")

uploaded = st.file_uploader("Vorhandenes JSON-Backup wiederherstellen", type=["json"])
if uploaded is not None:
    if st.button("Backup importieren"):
        try:
            restored = json.loads(uploaded.getvalue().decode("utf-8"))
            if not isinstance(restored, list):
                raise ValueError("Das Backup muss eine Rundenliste enthalten.")
            st.session_state.debate_rounds = restored
            st.success(f"{len(restored)} Runden importiert.")
            st.rerun()
        except Exception as exc:
            st.error(f"Import fehlgeschlagen: {exc}")

st.caption("Kostenhinweis: Diese App selbst benötigt keinen API-Schlüssel und erzeugt keine API-Kosten. ChatGPT-Nutzung erfolgt separat über dein vorhandenes Konto und unterliegt dessen Nutzungslimits. Die App speichert Runden während der laufenden Sitzung; lade regelmäßig ein JSON-Backup herunter, da kostenlose Hosting-Umgebungen keine dauerhafte lokale Speicherung garantieren.")
