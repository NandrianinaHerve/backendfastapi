import json
from datetime import datetime

# Données d'entraînement de qualité (symptômes clairs → spécialité correcte)
good_data = [
    # Cardiologie
    {"symptomes": "douleur thoracique serree essoufflement", "specialite": "cardiologie"},
    {"symptomes": "palpitations cardiaques fatigue", "specialite": "cardiologie"},
    {"symptomes": "oppression thoracique sueurs froides", "specialite": "cardiologie"},
    {"symptomes": "douleur bras gauche essoufflement", "specialite": "cardiologie"},
    {"symptomes": "battements coeur irreguliers vertiges", "specialite": "cardiologie"},
    {"symptomes": "hypertension arterielle severe", "specialite": "cardiologie"},
    {"symptomes": "douleur poitrine irradiant machoire", "specialite": "cardiologie"},
    {"symptomes": "essoufflement position allongee", "specialite": "cardiologie"},
    {"symptomes": "gonflement chevilles fatigue", "specialite": "cardiologie"},
    {"symptomes": "serrement poitrine stress", "specialite": "cardiologie"},
    
    # Neurologie
    {"symptomes": "migraine intense nausees", "specialite": "neurologie"},
    {"symptomes": "vertiges soudains perte equilibre", "specialite": "neurologie"},
    {"symptomes": "engourdissement main gauche", "specialite": "neurologie"},
    {"symptomes": "maux tete violents photophobie", "specialite": "neurologie"},
    {"symptomes": "perte connaissance breve", "specialite": "neurologie"},
    {"symptomes": "tremblements mains", "specialite": "neurologie"},
    {"symptomes": "trouble parole soudain", "specialite": "neurologie"},
    {"symptomes": "faiblesse membre inferieur", "specialite": "neurologie"},
    {"symptomes": "douleur faciale intense", "specialite": "neurologie"},
    {"symptomes": "confusion mentale soudaine", "specialite": "neurologie"},
    
    # Urologie
    {"symptomes": "brulure en urinant", "specialite": "urologie"},
    {"symptomes": "envie frequente d uriner", "specialite": "urologie"},
    {"symptomes": "sang dans les urines", "specialite": "urologie"},
    {"symptomes": "douleur lombaire unilaterale", "specialite": "urologie"},
    {"symptomes": "incontinence urinaire", "specialite": "urologie"},
    {"symptomes": "infection urinaire recurrente", "specialite": "urologie"},
    {"symptomes": "douleur testiculaire", "specialite": "urologie"},
    {"symptomes": "prostate volumineuse", "specialite": "urologie"},
    {"symptomes": "ejaculation douloureuse", "specialite": "urologie"},
    {"symptomes": "retenue urine aigue", "specialite": "urologie"},
    
    # Dermatologie
    {"symptomes": "eruption cutanee rouge demangeaisons", "specialite": "dermatologie"},
    {"symptomes": "boutons douloureux visage", "specialite": "dermatologie"},
    {"symptomes": "plaques squameuses cuir chevelu", "specialite": "dermatologie"},
    {"symptomes": "cloques bras", "specialite": "dermatologie"},
    {"symptomes": "taches blanches peau", "specialite": "dermatologie"},
    {"symptomes": "rougeur visage papules", "specialite": "dermatologie"},
    {"symptomes": "demangeaisons nocturnes", "specialite": "dermatologie"},
    {"symptomes": "peau seche craquele", "specialite": "dermatologie"},
    {"symptomes": "allergies cutanees", "specialite": "dermatologie"},
    {"symptomes": "eczema mains", "specialite": "dermatologie"},
    
    # Gastro-entérologie
    {"symptomes": "douleur abdominale apres repas", "specialite": "gastro-enterologie"},
    {"symptomes": "brulures estomac frequentes", "specialite": "gastro-enterologie"},
    {"symptomes": "nausees vomissements matinaux", "specialite": "gastro-enterologie"},
    {"symptomes": "diarrhee chronique douleur", "specialite": "gastro-enterologie"},
    {"symptomes": "constipation severe", "specialite": "gastro-enterologie"},
    {"symptomes": "reflux acide nocturne", "specialite": "gastro-enterologie"},
    {"symptomes": "ballonnements gaz excessifs", "specialite": "gastro-enterologie"},
    {"symptomes": "douleur haut ventre", "specialite": "gastro-enterologie"},
    {"symptomes": "saignement selles", "specialite": "gastro-enterologie"},
    {"symptomes": "perte appetit inexpliquee", "specialite": "gastro-enterologie"},
    
    # Psychiatrie
    {"symptomes": "anxiete constante palpitations", "specialite": "psychiatrie"},
    {"symptomes": "depression perte motivation", "specialite": "psychiatrie"},
    {"symptomes": "insomnie pensees suicidaires", "specialite": "psychiatrie"},
    {"symptomes": "panique soudaine public", "specialite": "psychiatrie"},
    {"symptomes": "humeur depressive chronique", "specialite": "psychiatrie"},
    {"symptomes": "troubles sommeil severes", "specialite": "psychiatrie"},
    {"symptomes": "angoisse nocturne", "specialite": "psychiatrie"},
    {"symptomes": "trouble humeur", "specialite": "psychiatrie"},
    {"symptomes": "crises angoisse repetees", "specialite": "psychiatrie"},
    {"symptomes": "depression post partum", "specialite": "psychiatrie"},
    
    # Pneumologie
    {"symptomes": "toux seche persistante", "specialite": "pneumologie"},
    {"symptomes": "essoufflement effort", "specialite": "pneumologie"},
    {"symptomes": "respiration sifflante", "specialite": "pneumologie"},
    {"symptomes": "douleur thoracique respirant", "specialite": "pneumologie"},
    {"symptomes": "crachats sanguinolents", "specialite": "pneumologie"},
    {"symptomes": "fievre difficulte respiratoire", "specialite": "pneumologie"},
    {"symptomes": "infections pulmonaires recurrentes", "specialite": "pneumologie"},
    {"symptomes": "asthme mal controle", "specialite": "pneumologie"},
    {"symptomes": "pneumonie fatigue", "specialite": "pneumologie"},
    {"symptomes": "bronchite chronique", "specialite": "pneumologie"},
    
    # Orthopédie
    {"symptomes": "douleur aigue genou", "specialite": "orthopedie"},
    {"symptomes": "raideur articulaire matinale", "specialite": "orthopedie"},
    {"symptomes": "douleur dos persistante", "specialite": "orthopedie"},
    {"symptomes": "entorse cheville", "specialite": "orthopedie"},
    {"symptomes": "fracture poignet", "specialite": "orthopedie"},
    {"symptomes": "sciatique intense", "specialite": "orthopedie"},
    {"symptomes": "arthrite mains", "specialite": "orthopedie"},
    {"symptomes": "douleur epaule levant bras", "specialite": "orthopedie"},
    {"symptomes": "luxation epaule", "specialite": "orthopedie"},
    {"symptomes": "gonalgie apres effort", "specialite": "orthopedie"},
    
    # Ophtalmologie
    {"symptomes": "vision floue soudaine", "specialite": "ophtalmologie"},
    {"symptomes": "rougeur demangeaison oculaire", "specialite": "ophtalmologie"},
    {"symptomes": "douleur derriere oeil", "specialite": "ophtalmologie"},
    {"symptomes": "eblouissement nocturne", "specialite": "ophtalmologie"},
    {"symptomes": "taches vision", "specialite": "ophtalmologie"},
    {"symptomes": "secheresse oculaire", "specialite": "ophtalmologie"},
    {"symptomes": "yeux larmoyants frequents", "specialite": "ophtalmologie"},
    {"symptomes": "vision double intermittente", "specialite": "ophtalmologie"},
    {"symptomes": "baisse vision progressive", "specialite": "ophtalmologie"},
    {"symptomes": "photophobie severe", "specialite": "ophtalmologie"},
    
    # ORL
    {"symptomes": "mal gorge persistant", "specialite": "orl"},
    {"symptomes": "otite douleur pulsatile", "specialite": "orl"},
    {"symptomes": "sinusite maux tete", "specialite": "orl"},
    {"symptomes": "vertiges acouphenes", "specialite": "orl"},
    {"symptomes": "perte audition soudaine", "specialite": "orl"},
    {"symptomes": "rhinite chronique", "specialite": "orl"},
    {"symptomes": "allergies saisonnieres", "specialite": "orl"},
    {"symptomes": "douleur faciale sinusienne", "specialite": "orl"},
    {"symptomes": "gorge rouge fievre", "specialite": "orl"},
    {"symptomes": "bourdonnement oreille", "specialite": "orl"},
]

# Ajouter dans create_good_data.py

# Plus de cardiologie
plus_cardio = [
    {"symptomes": "douleur poitrine serree", "specialite": "cardiologie"},
    {"symptomes": "angine de poitrine effort", "specialite": "cardiologie"},
    {"symptomes": "infarctus douleur bras", "specialite": "cardiologie"},
    {"symptomes": "insuffisance cardiaque essoufflement", "specialite": "cardiologie"},
]

# Plus de neurologie
plus_neuro = [
    {"symptomes": "migraine avec aura visuelle", "specialite": "neurologie"},
    {"symptomes": "acouphene et vertige", "specialite": "neurologie"},
    {"symptomes": "neuropathie peripherique", "specialite": "neurologie"},
]

# Plus de dermatologie
plus_dermato = [
    {"symptomes": "acne severe", "specialite": "dermatologie"},
    {"symptomes": "herpes cutane", "specialite": "dermatologie"},
    {"symptomes": "verrue plantaire", "specialite": "dermatologie"},
]

# Ajouter aux données existantes
good_data.extend(plus_cardio)
good_data.extend(plus_neuro)
good_data.extend(plus_dermato)

print(f"✅ {len(good_data)} exemples de qualité créés")

# Ajouter la date
for item in good_data:
    item['date'] = str(datetime.now())

# Sauvegarder
with open('app/models/ml_models/training_data_good.json', 'w') as f:
    json.dump(good_data, f, indent=2)

print(f"💾 Fichier sauvegardé: app/models/ml_models/training_data_good.json")