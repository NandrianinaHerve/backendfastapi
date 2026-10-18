import json
import os
from datetime import datetime
import re

def clean_text(text):
    if not text:
        return ""
    text = str(text).replace('\n', ' ').replace('\r', '')
    text = ' '.join(text.split())
    return text

def extract_symptoms_from_user(content):
    """
    Extraire uniquement les symptômes (enlever le prompt système)
    """
    # Enlever le prompt système
    patterns = [
        r"You are a medical assistant\..*?symptoms[:\s]*",
        r"Patient symptoms[:\s]*",
        r"Symptoms[:\s]*",
        r"The patient has[:\s]*",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            content = content[match.end():]
            break
    
    # Nettoyer le texte
    content = clean_text(content)
    return content

def extract_diseases_from_assistant(content):
    """
    Extraire les maladies du message assistant
    """
    diseases = []
    
    # Chercher "high_confidence: ..."
    match = re.search(r'high_confidence:\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
    if match:
        diseases_text = match.group(1)
        # Séparer les maladies par virgule
        disease_list = [d.strip() for d in diseases_text.split(',') if d.strip()]
        diseases.extend(disease_list)
    
    # Si pas de high_confidence, chercher d'autres patterns
    if not diseases:
        patterns = [
            r'Diagnosis[:\s]+(.+?)(?:\n|$)',
            r'Disease[:\s]+(.+?)(?:\n|$)',
            r'Condition[:\s]+(.+?)(?:\n|$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                diseases_text = match.group(1)
                disease_list = [d.strip() for d in diseases_text.split(',') if d.strip()]
                diseases.extend(disease_list)
                break
    
    # Si toujours pas de maladies, prendre les premiers mots
    if not diseases:
        words = content.split()[:10]
        diseases = [' '.join(words)]
    
    # Nettoyer les noms de maladies
    cleaned_diseases = []
    for d in diseases:
        # Enlever les préfixes
        d = re.sub(r'^high_confidence:\s*', '', d)
        d = re.sub(r'^medium_confidence:\s*', '', d)
        d = re.sub(r'^low_confidence:\s*', '', d)
        d = d.strip()
        if d and len(d) > 2:
            cleaned_diseases.append(d)
    
    return cleaned_diseases

def map_disease_to_specialty(disease):
    """
    Mapper une maladie à une spécialité médicale
    """
    disease_lower = disease.lower()
    
    # Mapping maladie → spécialité
    mapping = {
        # Cardiologie
        'heart': 'cardiologie',
        'cardiac': 'cardiologie',
        'chest pain': 'cardiologie',
        'arrhythmia': 'cardiologie',
        
        # Neurologie
        'headache': 'neurologie',
        'migraine': 'neurologie',
        'stroke': 'neurologie',
        'seizure': 'neurologie',
        'parkinson': 'neurologie',
        'alzheimer': 'neurologie',
        
        # Gastro-entérologie
        'stomach': 'gastro-enterologie',
        'abdomen': 'gastro-enterologie',
        'ulcer': 'gastro-enterologie',
        'colitis': 'gastro-enterologie',
        'crohn': 'gastro-enterologie',
        
        # Dentisterie
        'tooth': 'dentisterie',
        'dental': 'dentisterie',
        'cavity': 'dentisterie',
        'gingivitis': 'dentisterie',
        
        # Dermatologie
        'skin': 'dermatologie',
        'eczema': 'dermatologie',
        'psoriasis': 'dermatologie',
        'acne': 'dermatologie',
        'rash': 'dermatologie',
        
        # Pneumologie
        'lung': 'pneumologie',
        'asthma': 'pneumologie',
        'pneumonia': 'pneumologie',
        'bronchitis': 'pneumologie',
        
        # Orthopédie
        'bone': 'orthopedie',
        'joint': 'orthopedie',
        'arthritis': 'orthopedie',
        'fracture': 'orthopedie',
        'spine': 'orthopedie',
        
        # Ophtalmologie
        'eye': 'ophtalmologie',
        'vision': 'ophtalmologie',
        'cataract': 'ophtalmologie',
        'glaucoma': 'ophtalmologie',
        
        # Psychiatrie
        'depression': 'psychiatrie',
        'anxiety': 'psychiatrie',
        'bipolar': 'psychiatrie',
        'schizophrenia': 'psychiatrie',
        
        # Urologie
        'urinary': 'urologie',
        'kidney': 'urologie',
        'bladder': 'urologie',
        'prostate': 'urologie',
        
        # Gynécologie
        'uterine': 'gynecologie',
        'ovarian': 'gynecologie',
        'menstrual': 'gynecologie',
        'pregnancy': 'gynecologie',
        
        # Pédiatrie
        'child': 'pediatrie',
        'infant': 'pediatrie',
        'adolescent': 'pediatrie',
        
        # ORL
        'ear': 'orl',
        'nose': 'orl',
        'throat': 'orl',
        'tonsil': 'orl',
        
        # Médecine générale
        'fever': 'medecine generale',
        'fatigue': 'medecine generale',
        'weakness': 'medecine generale',
    }
    
    for key, specialty in mapping.items():
        if key in disease_lower:
            return specialty
    
    # Si aucune correspondance, utiliser "medecine generale"
    return "medecine generale"

def convert_kaggle_to_training_data():
    """Convertir le fichier JSONL au format training_data.json"""
    
    input_file = "data/symptom-based-disease-prediction-v2.jsonl"
    output_file = "app/models/ml_models/training_data.json"
    
    if not os.path.exists(input_file):
        print(f"❌ Fichier non trouvé: {input_file}")
        return
    
    print(f"📖 Lecture du fichier: {input_file}")
    print("⏳ Patientez, le fichier peut être volumineux...")
    
    training_data = []
    specialites = set()
    total_lines = 0
    errors = 0
    no_symptoms = 0
    no_disease = 0
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            total_lines += 1
            if not line.strip():
                continue
            
            try:
                item = json.loads(line)
                messages = item.get("messages", [])
                
                if not messages:
                    errors += 1
                    continue
                
                # Extraire les messages
                user_content = ""
                assistant_content = ""
                
                for msg in messages:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    
                    if role == "user":
                        user_content = content
                    elif role == "assistant":
                        assistant_content = content
                
                if not user_content:
                    no_symptoms += 1
                    continue
                
                # Extraire les symptômes
                symptoms = extract_symptoms_from_user(user_content)
                
                if not symptoms:
                    no_symptoms += 1
                    continue
                
                # Extraire les maladies
                diseases = extract_diseases_from_assistant(assistant_content)
                
                if not diseases:
                    no_disease += 1
                    continue
                
                # Pour chaque maladie, créer un exemple
                for disease in diseases[:3]:  # Limiter à 3 maladies par ligne
                    # Mapper la maladie à une spécialité
                    specialty = map_disease_to_specialty(disease)
                    
                    training_data.append({
                        "symptomes": symptoms[:500],
                        "specialite": specialty,
                        "maladie_originale": disease[:100],
                        "date": str(datetime.now())
                    })
                    specialites.add(specialty)
                
            except json.JSONDecodeError as e:
                errors += 1
                continue
            except Exception as e:
                errors += 1
                continue
            
            if total_lines % 10000 == 0:
                print(f"   ... {total_lines} lignes traitées, {len(training_data)} exemples")
    
    # Créer le dossier de sortie
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Sauvegarder
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print("✅ CONVERSION TERMINÉE")
    print("=" * 60)
    print(f"📊 Total lignes lues: {total_lines}")
    print(f"✅ Exemples convertis: {len(training_data)}")
    print(f"⚠️ Erreurs: {errors}")
    print(f"📝 Aucun symptôme: {no_symptoms}")
    print(f"📝 Aucune maladie: {no_disease}")
    print(f"🏷️ Spécialités uniques: {len(specialites)}")
    print(f"📁 Fichier sauvegardé: {output_file}")
    
    if len(training_data) > 0:
        print("\n📝 Exemples:")
        for i, item in enumerate(training_data[:5], 1):
            print(f"  {i}. {item['symptomes'][:100]}...")
            print(f"     → {item['specialite']}")
            print()
        
        print(f"\n📋 Spécialités trouvées:")
        for s in sorted(specialites):
            count = sum(1 for item in training_data if item['specialite'] == s)
            print(f"  - {s}: {count} exemples")

if __name__ == "__main__":
    convert_kaggle_to_training_data()