#!/usr/bin/env python
"""
Script pour combiner les données Kaggle nettoyées avec les good_data
et traduire les symptômes anglais en français
"""

import json
import random
from collections import Counter
from datetime import datetime
import re

# Dictionnaire de traduction anglais → français pour les symptômes médicaux
TRANSLATION_DICT = {
    # Symptômes cardiologiques
    'chest pain': 'douleur thoracique',
    'chest': 'thoracique',
    'pain': 'douleur',
    'tight': 'serree',
    'tightness': 'serrement',
    'pressure': 'pression',
    'heart': 'cardiaque',
    'palpitations': 'palpitations',
    'cardiac': 'cardiaque',
    'angina': 'angine de poitrine',
    'shortness of breath': 'essoufflement',
    'shortness': 'essoufflement',
    'breath': 'respiration',
    'breathing': 'respiration',
    'difficulty breathing': 'difficulte respiratoire',
    
    # Symptômes neurologiques
    'headache': 'mal de tete',
    'migraine': 'migraine',
    'dizziness': 'vertiges',
    'vertigo': 'vertiges',
    'numbness': 'engourdissement',
    'tingling': 'fourmillements',
    'tremor': 'tremblements',
    'trembling': 'tremblements',
    'weakness': 'faiblesse',
    'confusion': 'confusion',
    'seizure': 'crise',
    'stroke': 'avc',
    'paralysis': 'paralysie',
    'speech': 'parole',
    'vision changes': 'changements visuels',
    
    # Symptômes gastro-intestinaux
    'abdominal pain': 'douleur abdominale',
    'abdominal': 'abdominale',
    'stomach': 'estomac',
    'nausea': 'nausees',
    'vomiting': 'vomissements',
    'vomit': 'vomissements',
    'diarrhea': 'diarrhee',
    'constipation': 'constipation',
    'reflux': 'reflux',
    'acid': 'acide',
    'heartburn': 'brulures d estomac',
    'bloating': 'ballonnements',
    'gas': 'gaz',
    'indigestion': 'indigestion',
    
    # Symptômes dermatologiques
    'skin rash': 'eruption cutanee',
    'rash': 'eruption',
    'itching': 'demangeaisons',
    'itchy': 'demangeaisons',
    'eczema': 'eczema',
    'psoriasis': 'psoriasis',
    'acne': 'acne',
    'pimples': 'boutons',
    'redness': 'rougeur',
    'swelling': 'gonflement',
    'blisters': 'cloques',
    'scaly': 'squameux',
    'dry skin': 'peau seche',
    
    # Symptômes pulmonaires
    'cough': 'toux',
    'dry cough': 'toux seche',
    'wheezing': 'respiration sifflante',
    'asthma': 'asthme',
    'pneumonia': 'pneumonie',
    'bronchitis': 'bronchite',
    'phlegm': 'crachats',
    'sputum': 'crachats',
    'hemoptysis': 'crachats sanguinolents',
    
    # Symptômes orthopédiques
    'joint pain': 'douleur articulaire',
    'joint': 'articulation',
    'arthritis': 'arthrite',
    'fracture': 'fracture',
    'sprain': 'entorse',
    'back pain': 'douleur dorsale',
    'back': 'dos',
    'knee': 'genou',
    'ankle': 'cheville',
    'shoulder': 'epaule',
    'stiffness': 'raideur',
    'muscle': 'musculaire',
    'bone': 'osseux',
    
    # Symptômes ophtalmologiques
    'eye': 'oeil',
    'blurry vision': 'vision floue',
    'vision': 'vision',
    'cataract': 'cataracte',
    'glaucoma': 'glaucome',
    'red eye': 'oeil rouge',
    'painful eye': 'douleur oculaire',
    
    # Symptômes psychiatriques
    'depression': 'depression',
    'anxiety': 'anxiete',
    'panic': 'panique',
    'insomnia': 'insomnie',
    'mood swings': 'changements d humeur',
    'bipolar': 'bipolaire',
    'psychosis': 'psychose',
    
    # Symptômes urologiques
    'urinary': 'urinaire',
    'urination': 'miction',
    'burning urination': 'brulure en urinant',
    'frequent urination': 'envie frequente d uriner',
    'blood in urine': 'sang dans les urines',
    'kidney': 'rein',
    'bladder': 'vessie',
    'prostate': 'prostate',
    'incontinence': 'incontinence',
    
    # Symptômes ORL
    'sore throat': 'mal de gorge',
    'throat': 'gorge',
    'ear': 'oreille',
    'hearing loss': 'perte auditive',
    'tinnitus': 'acouphenes',
    'sinus': 'sinus',
    'nose': 'nez',
    'runny nose': 'nez qui coule',
    
    # Symptômes gynécologiques
    'menstrual': 'menstruel',
    'pregnancy': 'grossesse',
    'uterine': 'uterin',
    'ovarian': 'ovarien',
    'cervical': 'cervical',
    'vaginal': 'vaginal',
    
    # Symptômes généraux
    'fever': 'fievre',
    'fatigue': 'fatigue',
    'weakness': 'faiblesse',
    'infection': 'infection',
    'inflammation': 'inflammation',
    'weight loss': 'perte de poids',
    'appetite loss': 'perte d appetit',
    'sweating': 'sueurs',
}

def translate_symptoms(text):
    """
    Traduire les symptômes anglais en français
    """
    if not text:
        return ""
    
    text_lower = text.lower()
    
    # Traduire les symptômes un par un
    translated = text_lower
    for english, french in TRANSLATION_DICT.items():
        if english in translated:
            # Remplacer le terme anglais par le français
            translated = translated.replace(english, french)
    
    # Nettoyer le texte
    translated = re.sub(r'[^\w\s]', ' ', translated)
    translated = re.sub(r'\s+', ' ', translated)
    translated = translated.strip()
    
    return translated

def clean_symptom(text):
    """
    Nettoyer et traduire les symptômes
    """
    if not text:
        return ""
    
    # Enlever les instructions
    patterns = [
        r'You are a medical assistant\..*?symptoms[:\s]*',
        r'Patient symptoms[:\s]*',
        r'Symptoms[:\s]*',
        r'list the most relevant diseases grouped by confidence[:\s]*',
        r'list the most relevant diseases grouped confidence[:\s]*',
        r'Given the following patient symptoms[:\s]*',
        r'Please analyze the following symptoms[:\s]*',
        r'Based on the following symptoms[:\s]*',
        r'For the following symptoms[:\s]*',
        r'what is the diagnosis\??',
        r'what are the possible diseases\??',
        r'diagnose me\??',
        r'high_confidence[:\s]*',
        r'medium_confidence[:\s]*',
        r'low_confidence[:\s]*',
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Traduire en français
    text = translate_symptoms(text)
    
    # Nettoyer la ponctuation
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    # Garder les 10 premiers mots maximum
    words = text.split()
    if len(words) > 10:
        words = words[:10]
    
    return ' '.join(words)

def print_header(text):
    """Afficher un en-tête formaté"""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)

def print_success(text):
    print(f"✅ {text}")

def print_info(text):
    print(f"ℹ️  {text}")

def print_warning(text):
    print(f"⚠️  {text}")

def load_json_file(filepath):
    """Charger un fichier JSON"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print_warning(f"Fichier non trouvé: {filepath}")
        return None
    except Exception as e:
        print_warning(f"Erreur de chargement {filepath}: {e}")
        return None

def save_json_file(filepath, data):
    """Sauvegarder un fichier JSON"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print_success(f"Fichier sauvegardé: {filepath}")

def create_base_good_data():
    """Créer des données de base si good_data n'existe pas"""
    print_info("Création de good_data de base...")
    
    base_data = [
        # Cardiologie
        {"symptomes": "douleur thoracique serree", "specialite": "cardiologie"},
        {"symptomes": "palpitations cardiaques fatigue", "specialite": "cardiologie"},
        {"symptomes": "oppression thoracique sueurs", "specialite": "cardiologie"},
        
        # Neurologie
        {"symptomes": "migraine intense nausees", "specialite": "neurologie"},
        {"symptomes": "vertiges soudains perte equilibre", "specialite": "neurologie"},
        {"symptomes": "engourdissement main gauche", "specialite": "neurologie"},
        
        # Urologie
        {"symptomes": "brulure en urinant", "specialite": "urologie"},
        {"symptomes": "envie frequente d uriner", "specialite": "urologie"},
        {"symptomes": "sang dans les urines", "specialite": "urologie"},
        
        # Dermatologie
        {"symptomes": "eruption cutanee demangeaison", "specialite": "dermatologie"},
        {"symptomes": "boutons douloureux visage", "specialite": "dermatologie"},
        {"symptomes": "plaques squameuses cuir chevelu", "specialite": "dermatologie"},
        
        # Gastro-entérologie
        {"symptomes": "douleur estomac apres repas", "specialite": "gastro-enterologie"},
        {"symptomes": "brulures estomac frequentes", "specialite": "gastro-enterologie"},
        {"symptomes": "nausees vomissements matinaux", "specialite": "gastro-enterologie"},
        
        # Psychiatrie
        {"symptomes": "depression et anxiete", "specialite": "psychiatrie"},
        {"symptomes": "insomnie pensees suicidaires", "specialite": "psychiatrie"},
        {"symptomes": "panique soudaine en public", "specialite": "psychiatrie"},
        
        # Pneumologie
        {"symptomes": "toux seche persistante", "specialite": "pneumologie"},
        {"symptomes": "essoufflement effort", "specialite": "pneumologie"},
        {"symptomes": "respiration sifflante", "specialite": "pneumologie"},
        
        # Orthopédie
        {"symptomes": "douleur genou raideur", "specialite": "orthopedie"},
        {"symptomes": "douleur dos persistante", "specialite": "orthopedie"},
        {"symptomes": "entorse cheville", "specialite": "orthopedie"},
        
        # Ophtalmologie
        {"symptomes": "vision floue", "specialite": "ophtalmologie"},
        {"symptomes": "rougeur oculaire", "specialite": "ophtalmologie"},
        {"symptomes": "douleur derriere oeil", "specialite": "ophtalmologie"},
        
        # ORL
        {"symptomes": "mal de gorge fievre", "specialite": "orl"},
        {"symptomes": "otite douleur", "specialite": "orl"},
        {"symptomes": "sinusite maux tete", "specialite": "orl"},
    ]
    
    # Ajouter la date
    for item in base_data:
        item['date'] = str(datetime.now())
    
    save_json_file('app/models/ml_models/training_data_good.json', base_data)
    
    return base_data

def combine_data():
    """Combiner les données Kaggle nettoyées avec les good_data"""
    
    print_header("📊 COMBINAISON DES DONNÉES AVEC TRADUCTION")
    
    # 1. Charger les données Kaggle nettoyées
    print_info("Chargement des données Kaggle nettoyées...")
    kaggle_data = load_json_file('app/models/ml_models/training_data_cleaned.json')
    
    if kaggle_data is None:
        print_warning("Données Kaggle non disponibles")
        return None
    
    print_success(f"{len(kaggle_data)} exemples Kaggle chargés")
    
    # Traduire les symptômes des données Kaggle
    print_info("Traduction des symptômes en français...")
    translated_count = 0
    for item in kaggle_data:
        if 'symptomes' in item:
            original = item['symptomes']
            translated = clean_symptom(original)
            if translated and translated != original:
                item['symptomes'] = translated
                translated_count += 1
    
    print_success(f"{translated_count} exemples traduits")
    
    # 2. Charger les good_data
    print_info("Chargement des good_data...")
    good_data = load_json_file('app/models/ml_models/training_data_good.json')
    
    if good_data is None:
        print_warning("good_data non trouvées, création de données de base")
        good_data = create_base_good_data()
    
    print_success(f"{len(good_data)} exemples good_data chargés")
    
    # 3. Afficher la distribution des classes
    print_info("Distribution des classes (Kaggle):")
    kaggle_counts = Counter(item['specialite'] for item in kaggle_data)
    for specialty, count in sorted(kaggle_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"   - {specialty}: {count}")
    
    print_info("Distribution des classes (Good):")
    good_counts = Counter(item['specialite'] for item in good_data)
    for specialty, count in sorted(good_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"   - {specialty}: {count}")
    
    # 4. Échantillonner les données Kaggle (prendre un sous-ensemble équilibré)
    print_info("Échantillonnage des données Kaggle...")
    
    # Compter les classes
    counts = Counter(item['specialite'] for item in kaggle_data)
    
    # Définir le nombre maximum par classe (pour équilibrer)
    max_per_class = 5000
    
    sampled_kaggle = []
    for specialty in counts:
        items = [item for item in kaggle_data if item['specialite'] == specialty]
        
        # Si la classe a trop d'exemples, prendre un échantillon
        if len(items) > max_per_class:
            items = random.sample(items, max_per_class)
        
        # Si la classe a trop peu d'exemples, prendre tout
        sampled_kaggle.extend(items)
    
    print_success(f"{len(sampled_kaggle)} exemples Kaggle sélectionnés")
    
    # 5. Combiner les données
    print_info("Combinaison des données...")
    
    combined_data = good_data + sampled_kaggle
    
    print_success(f"{len(combined_data)} exemples combinés")
    
    # 6. Équilibrer les classes finales
    print_info("Équilibrage final des classes...")
    
    final_counts = Counter(item['specialite'] for item in combined_data)
    
    print_info("Distribution finale:")
    for specialty, count in sorted(final_counts.items(), key=lambda x: -x[1]):
        print(f"   - {specialty}: {count}")
    
    # 7. Sauvegarder
    save_json_file('app/models/ml_models/training_data_combined.json', combined_data)
    
    # 8. Afficher des exemples traduits
    print_info("Exemples de données combinées (traduites):")
    random.shuffle(combined_data)
    for i, item in enumerate(combined_data[:10], 1):
        print(f"   {i}. {item['symptomes'][:60]}... → {item['specialite']}")
    
    print_header("✅ COMBINAISON AVEC TRADUCTION TERMINÉE")
    print_info(f"Total: {len(combined_data)} exemples")
    print_info(f"Spécialités: {len(final_counts)}")
    
    return combined_data

if __name__ == "__main__":
    combine_data()