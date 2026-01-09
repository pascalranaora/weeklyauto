import google.generativeai as genai
from pushbullet import Pushbullet
import datetime

# --- CONFIGURATION ---
GEMINI_API_KEY = "VOTRE_CLE_API_GEMINI"
PUSHBULLET_API_KEY = "VOTRE_CLE_API_PUSHBULLET"
MENU_URL = "https://alifeplus.com.au/collections/keto-diet-meal-plan-delivery-menu"

# Configuration de Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def generate_keto_plan():
    prompt = f"""
    Agis en tant qu'expert en nutrition Keto-Alcaline (Hosokawa). 
    Génère un programme hebdomadaire pour 2 personnes.
    
    STRUCTURE DE LA JOURNÉE (2MAD) :
    - 06h00 : Eau citronnée + Sel.
    - 07h00 : Routine Workout ou Cardio Z2.
    - 08h00 : Journaling / Lecture.
    - 09h00 : PETIT-DÉJEUNER FIXE : Bacon, œufs et avocat (avec Keto Cloud Bread).
    - 12h00 - 16h00 : JEÛNE (Lunch sauté).
    - 16h00 : SNACK : Mélange de noix (Macadamias/Amandes) + 2 carrés de chocolat noir 90%.
    - 19h00 : DÎNER (Inspiration : {MENU_URL}).
    
    RÉPARTITION DES DÎNERS :
    - 2x Poisson sauvage.
    - 2x Viande rouge (Bœuf/Agneau).
    - 3x Autres (Poulet, Tempeh, Tofu fermenté).
    
    CONTENU REQUIS DANS LA NOTIFICATION :
    1. LISTE DE COURSES détaillée pour 2 personnes (incluant ingrédients pour Keto Cloud Bread).
    2. GUIDE DE PRÉPARATION (Prep) du dimanche matin (90 min) pour tout préparer d'avance.
    3. RECETTES DÉTAILLÉES des dîners (70% légumes alcalins, 30% protéines).
    4. RAPPEL DES OBJECTIFS : Score Dr. Boz < 20, poids cible 75kg.
    """
    
    response = model.generate_content(prompt)
    return response.text

def send_to_pushbullet(content):
    pb = Pushbullet(PUSHBULLET_API_KEY)
    title = f"🍳 Prep & Plan Keto-Alcalin - {datetime.date.today().strftime('%d/%m')}"
    pb.push_note(title, content)

if __name__ == "__main__":
    plan_content = generate_keto_plan()
    send_to_pushbullet(plan_content)
    print("Succès : Le plan complet avec Prep Guide a été envoyé !")