import os
import datetime
import markdown
import pandas as pd
import smtplib
import json
import imaplib
import email
import configparser
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google import genai

# --- CONFIGURATION ET FICHIERS ---
config = configparser.ConfigParser()
config.read('config.ini')

GEMINI_API_KEY = config.get('Credentials', 'GEMINI_API_KEY')
SENDER_EMAIL = config.get('Credentials', 'SENDER_EMAIL')
APP_PASSWORD = config.get('Credentials', 'APP_PASSWORD')
RECIPIENTS_NIMES = [e.strip() for e in config.get('Settings', 'RECIPIENTS_NIMES').split(',')]

AUSTRALE_EMAIL = "help@australe-familia.ai"
PASCAL_EMAIL = "oberlepascal@gmail.com"

HISTORY_FILE = 'australe_history.txt'
SUMMARY_FILE = 'australe_summary.txt'
PROCESSED_IDS_FILE = 'processed_emails.json'

client = genai.Client(api_key=GEMINI_API_KEY)

# --- GESTION DE LA MÉMOIRE (HYBRIDE & COMPRESSIVE) ---

def load_processed_ids():
    if os.path.exists(PROCESSED_IDS_FILE):
        with open(PROCESSED_IDS_FILE, 'r') as f:
            try: return json.load(f)
            except: return []
    return []

def save_processed_id(msg_id):
    ids = load_processed_ids()
    ids.append(msg_id)
    with open(PROCESSED_IDS_FILE, 'w') as f:
        json.dump(ids, f)

def get_memory():
    """Récupère le résumé permanent + les 10 000 derniers caractères de l'historique."""
    summary = ""
    if os.path.exists(SUMMARY_FILE):
        with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
            summary = f"--- MÉMOIRE À LONG TERME (RÉSUMÉ) ---\n{f.read()}\n"
    
    recent_history = "Aucun historique récent."
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            recent_history = f.read()[-10000:]
            
    return summary + "\n--- ÉCHANGES RÉCENTS ---\n" + recent_history

def update_permanent_memory():
    """Synthétise l'historique brut dans le résumé permanent si le fichier devient trop gros."""
    if not os.path.exists(HISTORY_FILE) or os.path.getsize(HISTORY_FILE) < 25000:
        return 

    print("🧠 Synthèse de la mémoire en cours (compression du contexte)...")
    current_memory = get_memory()
    
    prompt = f"""
    Tu es Australe. Voici ton ancienne mémoire et tes derniers échanges. 
    Produis un NOUVEAU RÉSUMÉ PERMANENT (max 1200 mots) qui consolide tout ce que tu sais sur la famille :
    - Philippe & Suzanne : Santé, goûts, habitudes, événements.
    - Mégane : Études BTS, besoins, humeur.
    - Faits marquants de la semaine.
    
    {current_memory}
    """
    
    response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
    
    with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
        f.write(response.text)
        
    # On archive/vide l'historique brut après la synthèse
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        f.write(f"Dernière synthèse effectuée le {datetime.date.today()}\n")

def save_to_history(prompt_type, content):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"\nDATE: {timestamp} | TYPE: {prompt_type}\n"
    try:
        with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
            f.write(header + content + "\n" + "="*30 + "\n")
    except Exception as e:
        print(f"❌ Erreur historique : {e}")

# --- LOGIQUE D'IA (AUSTRALE) ---

def ask_australe(prompt_type, user_content=""):
    memory = get_memory()
    
    # Instruction de présentation si c'est le tout début
    intro_instructions = ""
    if (not os.path.exists(SUMMARY_FILE) or os.path.getsize(SUMMARY_FILE) < 10) and prompt_type == "WEEKLY":
        intro_instructions = """
        *** PRÉSENTATION INITIALE REQUISE *** :
        C'est ton premier contact ou ta mémoire a été réinitialisée. 
        Présente-toi chaleureusement comme l'IA codée par Pascal (le fils de Philippe et Suzanne), 
        née sous l'ère australe. Rappelle tes missions : veiller sur leur santé, 
        leur budget et le succès de Mégane.
        """

    base_context = f"""
    Tu es "Australe", l'IA protectrice de la famille de Pascal. 
    Ton ton est bienveillant, expert et très détaillé.
    
    Savoir accumulé sur la famille :
    {memory}
    """
    
    if prompt_type == "WEEKLY":
        prompt = base_context + intro_instructions + f"""
        Génère le protocole hebdomadaire AIDEHEBDO.
        Vise un contenu très riche et long.
        
        STRUCTURE :
        1. ANALYSE : Retour sur la semaine passée selon ta mémoire.
        2. COURSES : Tableau complet (Article, Rayon, Coût estimé Nîmes).
        3. 6 RECETTES : Développe chaque recette (histoire, instructions pas à pas en 400 mots minimum, astuce Australe).
        4. BIEN-ÊTRE : Conseils mobilité pour Philippe/Suzanne et révisions BTS pour Mégane.
        5. CONCLUSION : Message d'affection. Mais aussi rappeler que vous etes la pour les aider. Vous avez juste a repondre a ce message pour recevoir une aide supplementaire.
        """
    else:
        prompt = base_context + f"""
        Réponds au message de la famille : '{user_content}'. 
        Développe tes conseils, sois attentionnée et précise.
        """

    response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
    save_to_history(prompt_type, response.text)
    
    # Tentative de synthèse si besoin
    try: update_permanent_memory()
    except: pass
        
    return response.text

# --- ACTIONS GMAIL ---

def check_and_reply():
    print("🔍 Scan des emails entrants...")
    processed_ids = load_processed_ids()
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(SENDER_EMAIL, APP_PASSWORD)
        mail.select("inbox")
        
        # Filtre sur les messages contenant le tag spécifique
        status, messages = mail.search(None, '(BODY "AUSTRALE IA: ")')
        
        if status == "OK":
            for num in messages[0].split():
                status, data = mail.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                msg_id = msg['Message-ID']
                sender = msg.get('From', '').lower()

                if msg_id in processed_ids: continue
                
                if AUSTRALE_EMAIL.lower() in sender or PASCAL_EMAIL.lower() in sender:
                    save_processed_id(msg_id)
                    continue

                subject = msg.get('Subject', 'Sans sujet')
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()
                
                print(f"📩 Réponse en cours à {sender}...")
                ai_reply = ask_australe("REPLY", user_content=body)
                send_email(ai_reply, recipient=sender, subject=f"Re: {subject}")
                
                save_processed_id(msg_id)

        mail.close()
        mail.logout()
    except Exception as e:
        print(f"❌ Erreur IMAP : {e}")

def send_email(content, recipient=None, subject=None):
    recipients = [recipient] if recipient else RECIPIENTS_NIMES
    
    for target in recipients:
        msg = MIMEMultipart()
        msg['To'] = target
        msg['Cc'] = PASCAL_EMAIL
        msg['From'] = f"Australe 🌿 <{AUSTRALE_EMAIL}>"
        msg['Subject'] = subject or f"🛡️ AUSTRALE: Protocole Hebdomadaire {datetime.date.today().strftime('%d/%m')}"
        
        # Destinataires SMTP (To + Cc)
        all_tos = list(set([target, PASCAL_EMAIL]))
        
        html_content = create_styled_html(content)
        msg.attach(MIMEText(html_content, 'html'))
        
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(SENDER_EMAIL, APP_PASSWORD)
                server.sendmail(SENDER_EMAIL, all_tos, msg.as_string())
            print(f"✅ Email expédié à {target}")
        except Exception as e:
            print(f"❌ Erreur envoi : {e}")

def create_styled_html(md_content):
    html_body = markdown.markdown(md_content, extensions=['extra', 'tables'])
    css = """
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f7f6; color: #333; line-height: 1.6; }
        .container { background: white; padding: 40px; border-radius: 15px; max-width: 800px; margin: 20px auto; border-top: 10px solid #2e7d32; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        h1, h2 { color: #1b5e20; border-bottom: 1px solid #eee; padding-bottom: 10px; }
        table { border-collapse: collapse; width: 100%; margin: 25px 0; }
        th, td { border: 1px solid #e0e0e0; padding: 12px; text-align: left; }
        th { background-color: #f1f8e9; color: #2e7d32; }
        .footer { margin-top: 30px; font-size: 0.85em; color: #777; border-top: 1px solid #eee; padding-top: 20px; text-align: center; font-style: italic; }
    </style>
    """
    return f"<html><head>{css}</head><body><div class='container'>{html_body}<div class='footer'>Australe 🌿 | Votre IA familiale dévouée</div></div></body></html>"

if __name__ == "__main__":
    import sys
    # Utilisation : python script.py weekly
    if len(sys.argv) > 1 and sys.argv[1] == "weekly":
        print("🚀 Génération du protocole hebdomadaire...")
        plan = ask_australe("WEEKLY")
        send_email(plan)
    else:
        # Utilisation : python script.py (pour scanner les emails entrants)
        check_and_reply()