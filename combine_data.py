#!/usr/bin/env python
"""
Script pour combiner les données Kaggle nettoyées avec les good_data
et traduire les symptômes anglais en français avec équilibrage des classes
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

def balance_classes(data, max_per_class=4000, min_per_class=200):
    """
    Équilibrer les classes en échantillonnant
    
    Args:
        data: Liste des données
        max_per_class: Nombre maximum d'exemples par classe
        min_per_class: Nombre minimum d'exemples par classe (garde tout si moins)
    """
    
    # Compter les classes
    counts = Counter(item['specialite'] for item in data)
    
    print_info("\n📊 Distribution avant équilibrage:")
    for spec, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"   - {spec}: {count}")
    
    # Équilibrer
    balanced_data = []
    stats = {}
    
    for specialty in counts:
        items = [item for item in data if item['specialite'] == specialty]
        original_count = len(items)
        
        # Si la classe a plus que max_per_class, prendre un échantillon
        if len(items) > max_per_class:
            items = random.sample(items, max_per_class)
            stats[specialty] = f"{original_count} → {len(items)}"
        else:
            stats[specialty] = f"{original_count} (gardé)"
        
        balanced_data.extend(items)
    
    print_info("\n📊 Équilibrage effectué:")
    for spec, stat in sorted(stats.items(), key=lambda x: int(x[1].split()[0]) if x[1].split()[0].isdigit() else 0, reverse=True):
        print(f"   - {spec}: {stat}")
    
    return balanced_data

def create_base_good_data():
    """Créer des données de base si good_data n'existe pas"""
    print_info("Création de good_data de base...")
    
    base_data = []
    
    # 10 exemples par spécialité
    specialties = {
        'cardiologie': ['douleur thoracique serree', 'palpitations cardiaques fatigue', 'oppression thoracique sueurs'],
        'neurologie': ['migraine intense nausees', 'vertiges soudains perte equilibre', 'engourdissement main gauche'],
        'urologie': ['brulure en urinant', 'envie frequente d uriner', 'sang dans les urines'],
        'dermatologie': ['eruption cutanee demangeaison', 'boutons douloureux visage', 'plaques squameuses cuir chevelu'],
        'gastro-enterologie': ['douleur estomac apres repas', 'brulures estomac frequentes', 'nausees vomissements matinaux'],
        'psychiatrie': ['depression et anxiete', 'insomnie pensees suicidaires', 'panique soudaine en public'],
        'pneumologie': ['toux seche persistante', 'essoufflement effort', 'respiration sifflante'],
        'orthopedie': ['douleur genou raideur', 'douleur dos persistante', 'entorse cheville'],
        'ophtalmologie': ['vision floue', 'rougeur oculaire', 'douleur derriere oeil'],
        'orl': ['mal de gorge fievre', 'otite douleur', 'sinusite maux tete'],
        'gynecologie': ['douleurs menstruelles violentes', 'saignements irreguliers', 'infections vaginales recurrentes'],
        'pediatrie': ['fievre elevee enfant', 'eruption cutanee bebe', 'otite avec pleurs']
    }
    
    for specialty, symptoms in specialties.items():
        for symptom in symptoms:
            base_data.append({
                "symptomes": symptom,
                "specialite": specialty,
                "date": str(datetime.now())
            })
    
    save_json_file('app/models/ml_models/training_data_good.json', base_data)
    
    return base_data

def combine_data():
    """Combiner les données Kaggle nettoyées avec les good_data"""
    
    print_header("📊 COMBINAISON DES DONNÉES AVEC TRADUCTION ET ÉQUILIBRAGE")
    
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
    print_info("\n📊 Distribution des classes (Kaggle):")
    kaggle_counts = Counter(item['specialite'] for item in kaggle_data)
    for specialty, count in sorted(kaggle_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"   - {specialty}: {count}")
    
    print_info("\n📊 Distribution des classes (Good):")
    good_counts = Counter(item['specialite'] for item in good_data)
    for specialty, count in sorted(good_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"   - {specialty}: {count}")
    
    # 4. Échantillonner les données Kaggle (prendre un sous-ensemble équilibré)
    print_info("\n🔄 Échantillonnage des données Kaggle...")
    
    # Compter les classes
    counts = Counter(item['specialite'] for item in kaggle_data)
    
    # Définir le nombre maximum par classe (pour équilibrer)
    max_per_class = 3000
    
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
    print_info("\n🔄 Combinaison des données...")
    
    combined_data = good_data + sampled_kaggle
    
    print_success(f"{len(combined_data)} exemples combinés")
    
    # 6. Équilibrer les classes finales
    print_info("\n⚖️ Équilibrage final des classes...")
    
    balanced_data = balance_classes(combined_data, max_per_class=3000, min_per_class=200)
    
    # 7. Sauvegarder
    save_json_file('app/models/ml_models/training_data_combined.json', balanced_data)
    
    # 8. Afficher des exemples traduits
    print_info("\n📝 Exemples de données combinées (traduites):")
    random.shuffle(balanced_data)
    for i, item in enumerate(balanced_data[:10], 1):
        print(f"   {i}. {item['symptomes'][:60]}... → {item['specialite']}")
    
    # 9. Statistiques finales
    final_counts = Counter(item['specialite'] for item in balanced_data)
    
    print_header("✅ COMBINAISON AVEC TRADUCTION ET ÉQUILIBRAGE TERMINÉE")
    print_info(f"Total: {len(balanced_data)} exemples")
    print_info(f"Spécialités: {len(final_counts)}")
    
    print_info("\n📊 Distribution finale équilibrée:")
    for specialty, count in sorted(final_counts.items(), key=lambda x: -x[1]):
        print(f"   - {specialty}: {count}")
    
    return balanced_data

if __name__ == "__main__":
    combine_data()