import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Se connecter
print("🔑 Connexion...")
login = requests.post(f"{BASE_URL}/auth/login", 
                      json={'email': 'jean.patient@email.com', 'password': 'password123'})
token = login.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}
print("✅ Connecté")

# Tests
tests = {
    'douleur poitrine serre': 'cardiologie',
    'migraine intense et nausees': 'neurologie',
    'brulure en urinant': 'urologie',
    'eruption cutanee demangeaison': 'dermatologie',
    'douleur estomac apres repas': 'gastro-enterologie',
    'depression et anxiete': 'psychiatrie',
    'toux seche et essoufflement': 'pneumologie',
    'douleur genou et raideur': 'orthopedie',
    'vision floue et douleur oeil': 'ophtalmologie',
    'mal de gorge et fievre': 'orl'
}

print("\n" + "=" * 60)
print("🧪 TEST DU MODÈLE ML")
print("=" * 60)

results = []
for symptoms, expected in tests.items():
    data = {'symptomes': symptoms, 'patient_id': 2}
    response = requests.post(f"{BASE_URL}/ia/analyze", headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        ml = result.get('ml_details', {})
        predicted = ml.get('specialite', 'N/A')
        confidence = ml.get('confiance', 0)
        
        is_correct = predicted == expected
        status = "✅" if is_correct else "❌"
        results.append(is_correct)
        
        print(f"{status} {symptoms[:30]}...")
        print(f"   Prédit: {predicted} ({confidence:.2%}) | Attendu: {expected}")
    else:
        print(f"❌ Erreur pour '{symptoms}': {response.text}")

print("\n" + "=" * 60)
score = sum(results) / len(results) if results else 0
print(f"📊 Score: {sum(results)}/{len(results)} ({score*100:.1f}%)")
print("=" * 60)