import os
import datetime
import markdown
import pandas as pd
import smtplib
import configparser
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from google import genai
from fpdf import FPDF

# --- LOAD CONFIGURATION ---
config = configparser.ConfigParser()
config.read('config.ini')

GEMINI_API_KEY = config.get('Credentials', 'GEMINI_API_KEY')
SENDER_EMAIL = config.get('Credentials', 'SENDER_EMAIL')
APP_PASSWORD = config.get('Credentials', 'APP_PASSWORD')
RECIPIENTS = [email.strip() for email in config.get('Settings', 'RECIPIENTS').split(',')]
WEIGHT_FILE = config.get('Settings', 'WEIGHT_FILE')
HISTORY_FILE = config.get('Settings', 'HISTORY_FILE')
TARGET_WEIGHT = config.getfloat('Settings', 'TARGET_WEIGHT')
# URL Inspiration
MENU_URL_LIST = ["https://alifeplus.com.au/collections/keto-diet-meal-plan-delivery-menu"] + \
                    [f"https://alifeplus.com.au/collections/keto-diet-meal-plan-delivery-menu?page={i}" for i in range(2,5,1)]

client = genai.Client(api_key=GEMINI_API_KEY)

def get_weight_stats():
    try:
        df = pd.read_csv(WEIGHT_FILE)
        current_w = df.iloc[-1]['weight']
        to_go = current_w - TARGET_WEIGHT
        return f"Current: {current_w}kg | Target: {TARGET_WEIGHT}kg | Distance: {to_go}kg"
    except:
        return f"Target: {TARGET_WEIGHT}kg. Tracking active."

def get_previous_context():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return f.read()[:2000]
    return "No previous plan found."

def save_current_plan(content):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

def create_styled_html(md_content):
    html_body = markdown.markdown(md_content, extensions=['extra', 'tables', 'sane_lists'])
    css = """
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: auto; padding: 20px; background-color: #f0f2f5; }
        .card { background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); border-top: 8px solid #2e7d32; }
        h1 { color: #1b5e20; text-align: center; border-bottom: 2px solid #a5d6a7; padding-bottom: 10px; }
        h2 { color: #2e7d32; margin-top: 30px; border-left: 5px solid #4caf50; padding-left: 10px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 0.9em; }
        th { background-color: #e8f5e9; color: #1b5e20; padding: 12px; border: 1px solid #c8e6c9; }
        td { padding: 10px; border: 1px solid #eee; }
        .footer { font-size: 0.8em; text-align: center; color: #999; margin-top: 40px; }
    </style>
    """
    return f"<html><head>{css}</head><body><div class='card'>{html_body}<div class='footer'>ZENITH OS | Weekly Biological Protocol</div></div></body></html>"

def generate_keto_plan():
    weight_context = get_weight_stats()
    supp_costs = dict(config.items('Costs_AUD'))
    stack = config.get('Supplements', 'STACK')
    weight_context = get_weight_stats()
    history_context = get_previous_context()
    
    # Récupération des données du config
    supp_costs = dict(config.items('Costs_AUD'))
    stack = config.get('Supplements', 'STACK')
    
   
    prompt = f"""
    Acting as Zenith, the personal AI Assistant and Keto-Alkaline Nutrition Expert. 
    Adopt a friendly, encouraging tone with a touch of fun (thermodynamic humor is welcome).
    
    [PASCAL PROGRESS]: {weight_context}
    [SUPPLEMENT STACK]: {stack}
    [SUPPLEMENT COSTS]: {supp_costs}
    [PREVIOUS WEEK CONTEXT - DO NOT REPEAT THESE RECIPES]: {history_context}
    
    DAILY STRUCTURE (2MAD for Pascal):
    - 06:00: Lemon Water + Gray Sea Salt.
    - 06:15: Tue/Thu/Sat: Strength | Mon/Wed/Fri: Z2 Cardio/Run+Swim.
    - 07:15: Cold Shower.
    - 07:30: BREAKFAST: Bacon, eggs, avocado + Keto Cloud Bread.
    - 09:00 - 16:00: Pascal Fasts (Zenith Sovereignty Window). 
    - 16:00: SNACK: 30g Macadamia&Almonds + 2 sq 90+% Dark Chocolate.
    - 19:00: DINNER (2x Fish, 2x Red Meat, 3x Other Chicken/Tofu etc). 
    Inspiration: {MENU_URL_LIST}
    Goal: 5 months reset for Pascal (strict Keto, Dr. Boz < 20) and Jennifer (53kg, flexible).
    

    CONSTRAINTS:
    - Budget: The TOTAL cost for the shopping list (groceries) MUST NOT exceed $180 AUD.
    - Diet: Strict Keto for Pascal, flexible for Jennifer.
    
    OUTPUT REQUIREMENTS:
    1. PROGRESS DASHBOARD: Acknowledge the path to 75kg.
    2. SHOPPING LIST: Provide a Markdown Table (Aisle | Item | Cost AUD). Include a TOTAL at the bottom. Start this section with '---SHOPPING_LIST_START---' and end it with '---SHOPPING_LIST_END---'.
    3. BUDGET TOTAL: Sum of Groceries + Supplements.
    4. SUPPLEMENT PROTOCOL:
        | Time | Supplement | Dosage | Zenith’s Rationale |
        | :--- | :--- | :--- | :--- |
        | 06:00 | ACV + Electrolytes | 1 tbsp + Mag Malate | The Primer: AMPK activation. |
        | 07:30 | Vit D3 + K2 | Standard | Absorption with healthy fats. |
        | 07:45 | Creatine | 5g | ATP recovery post-workout. |
        | 08:00 | Ashwagandha | 300mg | Cortisol Buffer for journaling. |
        | 10:00 | MCT Oil (C8) | 1-2 tsp | Ketone Turbo (Matcha). |
        | 16:00 | Spiruline | 3-5g | Alkaline bridge. + 30g Macadamia&Almonds + 2 sq 90+% Dark Chocolate|
        | 18:45 | Berberine | 500mg | Glucose Crusher pre-dinner. |
        | 19:00 | Keto Kimchi | 2 tbsp | Gut Firewall. |
        | 21:30 | Magnesium | Bisglycinate | Deep sleep & fat oxidation. |
    5. THE ZENITH PREP: Including 5-min Keto Kimchi and prep for the snacks.
    6. RECIPES: 7 varied recipes (2x Fish, 2x Red Meat, 3x Other). Be detailed and instructive (300 words each). 
    7. CLOSING: Remind Pascal of the Dr. Boz ratio. Encourage Jen to share her 'Best Self' vision.
    
    """
    response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
    return response.text

def create_shopping_list_pdf(text_content):
    # Extraction de la liste via les balises
    match = re.search(r'---SHOPPING_LIST_START---(.*?)---SHOPPING_LIST_END---', text_content, re.DOTALL)
    list_text = match.group(1).strip() if match else "Liste non générée."
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"ZENITH SHOPPING LIST - {datetime.date.today()}", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.ln(10)
    
    # Nettoyage rudimentaire du markdown pour le PDF
    lines = list_text.replace('|', ' ').split('\n')
    for line in lines:
        pdf.cell(200, 8, txt=line.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    
    pdf_path = "shopping_list.pdf"
    pdf.output(pdf_path)
    return pdf_path

def create_styled_html(md_content):
    # On retire les balises techniques avant d'afficher l'HTML
    clean_md = re.sub(r'---SHOPPING_LIST_.*?---', '', md_content)
    html_body = markdown.markdown(clean_md, extensions=['extra', 'tables', 'sane_lists'])
    return f"<html><body style='font-family: sans-serif; padding: 20px;'>{html_body}</body></html>"

def send_gmail(html_content, pdf_path):
    for recipient in RECIPIENTS:
        msg = MIMEMultipart()
        msg['Subject'] = f"🛡️ ZENITH AI ASSISTANT Protocol - {datetime.date.today().strftime('%d/%m')}"
        msg['To'] = recipient
        msg['From'] = SENDER_EMAIL
        msg.attach(MIMEText(html_content, 'html'))
        
        # Pièce jointe
        with open(pdf_path, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {pdf_path}")
            msg.attach(part)
            
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient, msg.as_string())
    print("✅ Emails envoyés avec PDF.")

if __name__ == "__main__":
    content = generate_keto_plan()
    save_current_plan(content)
    pdf_file = create_shopping_list_pdf(content)
    html = create_styled_html(content)
    send_gmail(html, pdf_file)
    print("🏁 Weekly update finalized.")
