import json
import random

# Charger les données existantes
with open('app/models/ml_models/training_data_balanced.json', 'r') as f:
    data = json.load(f)

# Ajouter des exemples pour médecine générale (symptômes plus spécifiques)
new_general = [
    {"symptomes": "fatigue chronique fievre", "specialite": "medecine generale"},
    {"symptomes": "perte de poids inexpliquee", "specialite": "medecine generale"},
    {"symptomes": "anemie fatigue", "specialite": "medecine generale"},
    {"symptomes": "hypertension arterielle", "specialite": "medecine generale"},
    {"symptomes": "hypercholesterolemie", "specialite": "medecine generale"},
    {"symptomes": "diabete equilibre", "specialite": "medecine generale"},
    {"symptomes": "infection urinaire", "specialite": "medecine generale"},
    {"symptomes": "grippe fievre", "specialite": "medecine generale"},
    {"symptomes": "angine fievre", "specialite": "medecine generale"},
    {"symptomes": "rhume fatigue", "specialite": "medecine generale"},
]

# Ajouter plus de données pour gastro-entérologie
new_gastro = [
    {"symptomes": "reflux gastro-oesophagien severe", "specialite": "gastro-enterologie"},
    {"symptomes": "douleur abdominale chronique", "specialite": "gastro-enterologie"},
    {"symptomes": "syndrome intestin irritable", "specialite": "gastro-enterologie"},
]

# Ajouter plus de données pour cardiologie
new_cardio = [
    {"symptomes": "insuffisance cardiaque essoufflement", "specialite": "cardiologie"},
    {"symptomes": "arythmie cardiaque", "specialite": "cardiologie"},
    {"symptomes": "valvulopathie cardiaque", "specialite": "cardiologie"},
]

# Ajouter plus de données pour neurologie
new_neuro = [
    {"symptomes": "neuropathie peripherique", "specialite": "neurologie"},
    {"symptomes": "sciatique douloureuse", "specialite": "neurologie"},
    {"symptomes": "epilepsie", "specialite": "neurologie"},
]

# Combiner
data.extend(new_general)
data.extend(new_gastro)
data.extend(new_cardio)
data.extend(new_neuro)

print(f"✅ {len(data)} exemples après ajout")

# Sauvegarder
with open('app/models/ml_models/training_data_improved.json', 'w') as f:
    json.dump(data, f, indent=2)

print("💾 Fichier sauvegardé: training_data_improved.json")