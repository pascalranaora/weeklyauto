import os
import datetime
import markdown
import pandas as pd
import smtplib
import configparser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google import genai

# --- LOAD CONFIGURATION ---
config = configparser.ConfigParser()
config.read('config.ini')

# Credentials
GEMINI_API_KEY = config.get('Credentials', 'GEMINI_API_KEY')
PUSH_API_KEY = config.get('Credentials', 'PUSH_API_KEY')
SENDER_EMAIL = config.get('Credentials', 'SENDER_EMAIL')
APP_PASSWORD = config.get('Credentials', 'APP_PASSWORD')

# Settings
RECIPIENTS = [email.strip() for email in config.get('Settings', 'RECIPIENTS').split(',')]
WEIGHT_FILE = config.get('Settings', 'WEIGHT_FILE')
HISTORY_FILE = config.get('Settings', 'HISTORY_FILE')
TARGET_WEIGHT = config.getfloat('Settings', 'TARGET_WEIGHT')

# --- REFRESH ZENITH LOGIC ---
MENU_URL_LIST = ["https://alifeplus.com.au/collections/keto-diet-meal-plan-delivery-menu"] + \
                [f"https://alifeplus.com.au/collections/keto-diet-meal-plan-delivery-menu?page={i}" for i in range(2,5,1)]

client = genai.Client(api_key=GEMINI_API_KEY)

def get_weight_stats():
    try:
        df = pd.read_csv(WEIGHT_FILE)
        start_w = df.iloc[0]['weight']
        current_w = df.iloc[-1]['weight']
        lost = start_w - current_w
        to_go = current_w - TARGET_WEIGHT
        return f"Start: {start_w}kg | Current: {current_w}kg | Lost: {lost}kg | Distance to {TARGET_WEIGHT}kg: {to_go}kg"
    except Exception:
        return f"Target: {TARGET_WEIGHT}kg. Tracking initiated."

def get_previous_context():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return f.read()[:2000]
    return "No previous plan found."

def save_current_plan(content):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

def generate_keto_plan():
    weight_context = get_weight_stats()
    history_context = get_previous_context()
    
    prompt = fweight_context = get_weight_stats()
    history_context = get_previous_context()
    
    prompt = f"""
    Acting as Zenith, the personal AI Assistant and Keto-Alkaline Nutrition Expert. Adopt a friendly tone and add some fun in your messages (but not too much)
    
    [PASCAL PROGRESS]: {weight_context}
    
    [PREVIOUS WEEK CONTEXT - DO NOT REPEAT THESE RECIPES]:
    {history_context}
    
    Goal: 5 months reset for Pascal (strict Keto, Dr. Boz < 20) and Jennifer (53kg, flexible).
    
    DAILY STRUCTURE (2MAD for Pascal mainly):
    - 06:00: Lemon Water + Gray Sea Salt.
    - 06:15: Tue/Thu/Sat: Strength | Mon/Wed/Fri: Z2 Cardio/Run+Swim.
    - 07:15: Cold Shower.
    - 07:30: BREAKFAST: Bacon, eggs, avocado + Keto Cloud Bread.
    - 09:00 - 16:00: Pascal Fasts. 
    - 16:00: SNACK: 30g Macadamia/Almonds + 2 sq 90% Dark Chocolate.
    - 19:00: DINNER (2x Fish, 2x Red Meat, 3x Other Chicken/Tofu etc). Inspirations: {MENU_URL_LIST}

    RITUALS: Tue 18:45 Gym | Sun 16:00 Yoga/Ping Pong | Sun 18:00 Shop | Sun 19:00 Zenith Prep.

    OUTPUT REQUIREMENTS:
    1. PROGRESS DASHBOARD (For Pascal): Acknowledge weight loss and thermodynamic efficiency.
    2. SHOPPING LIST: Markdown Table separated by aisle. 
       **NEW: Add an 'Estimated Cost (AUD)' column for each item and a TOTAL estimated budget at the bottom.**
    3. VARIETY CHECK: Based on the previous week's context provided, you MUST pick different recipes and flavors.
    4. THE ZENITH PREP: 45-min task list for Sunday 19:00 (Pascal & Jen tasks).
    5. RECIPES: 5-line min per recipe. Include Cloud Bread recipe.
    6. CLOSING: Remind Pascal of the Dr. Boz ratio. Encourage Jen to share her 'Best Self' vision.
    """
    
    response = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
    return response.text

def create_styled_html(md_content):
    # Rendering with tables enabled for the Shopping List
    html_body = markdown.markdown(md_content, extensions=['extra', 'tables', 'sane_lists'])
    css = """
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: auto; padding: 20px; background-color: #f9f9f9; }
        .card { background: white; padding: 40px; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
        h1 { color: #2e7d32; text-align: center; border-bottom: 2px solid #81c784; padding-bottom: 15px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th { background-color: #f1f8e9; padding: 12px; border: 1px solid #ddd; }
        td { padding: 10px; border: 1px solid #ddd; }
        .footer { font-size: 0.8em; text-align: center; color: #777; margin-top: 30px; }
    </style>
    """
    return f"<html><head>{css}</head><body><div class='card'>{html_body}<div class='footer'>ZENITH | Personal Optimization Engine</div></div></body></html>"

def send_gmail(html_content):
    for recipient in RECIPIENTS:
        message = MIMEMultipart()
        message['to'] = recipient
        message['from'] = f"Zenith Assistant <{SENDER_EMAIL}>"
        message['subject'] = f"🛡️ ZENITH: Jennifer and Pascal AI Assistant - Weekly Protocol {datetime.date.today().strftime('%d/%m')}"
        message.attach(MIMEText(html_content, 'html'))
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(SENDER_EMAIL, APP_PASSWORD)
                server.sendmail(SENDER_EMAIL, recipient, message.as_string())
            print(f"✅ Dispatched to {recipient}")
        except Exception as e:
            print(f"❌ Dispatch failed for {recipient}: {e}")

if __name__ == "__main__":
    print("Zenith is loading secure config and generating protocol...")
    content = generate_keto_plan()
    save_current_plan(content)
    html = create_styled_html(content)
    send_gmail(html)
    print("🏁 Weekly update finalized.")