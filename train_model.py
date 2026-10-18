import requests
import json
import random
from collections import Counter
import os

BASE_URL = "http://localhost:8000/api/v1"

def print_header(text):
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)

def print_success(text):
    print(f"✅ {text}")

def print_error(text):
    print(f"❌ {text}")

def print_info(text):
    print(f"ℹ️  {text}")

def balance_data(data, target_per_class=2000):
    """
    Équilibrer les données pour avoir target_per_class par classe
    """
    print("\n📊 Équilibrage des classes...")
    
    # Compter les classes
    counts = Counter(item['specialite'] for item in data)
    
    print_info("Distribution avant équilibrage:")
    for spec, count in sorted(counts.items(), key=lambda x: -x[1]):
        percentage = (count / len(data)) * 100
        bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))
        print(f"   {spec:20} {bar} {count} ({percentage:.1f}%)")
    
    # Équilibrer
    balanced_data = []
    stats = {}
    
    for specialty in counts:
        items = [item for item in data if item['specialite'] == specialty]
        original_count = len(items)
        
        if len(items) > target_per_class:
            items = random.sample(items, target_per_class)
            stats[specialty] = f"{original_count} → {len(items)} (réduit)"
        elif len(items) < target_per_class and len(items) > 0:
            # Dupliquer pour atteindre target_per_class
            original_items = items[:]
            while len(items) < target_per_class:
                needed = target_per_class - len(items)
                sample_size = min(needed, len(original_items))
                items.extend(random.sample(original_items, sample_size))
            stats[specialty] = f"{original_count} → {len(items)} (augmenté)"
        else:
            stats[specialty] = f"{original_count} (gardé)"
        
        balanced_data.extend(items)
    
    # Vérifier la nouvelle distribution
    new_counts = Counter(item['specialite'] for item in balanced_data)
    
    print_info("\nDistribution après équilibrage:")
    for spec, count in sorted(new_counts.items(), key=lambda x: -x[1]):
        percentage = (count / len(balanced_data)) * 100
        bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))
        print(f"   {spec:20} {bar} {count} ({percentage:.1f}%)")
    
    print_info(f"\nStatistiques d'équilibrage:")
    for spec, stat in stats.items():
        print(f"   {spec}: {stat}")
    
    return balanced_data

def train_balanced():
    """Entraîner le modèle avec des données équilibrées"""
    
    print_header("🚀 ENTRAÎNEMENT AVEC DONNÉES ÉQUILIBRÉES")
    
    # Se connecter
    print("\n🔑 Connexion admin...")
    try:
        login = requests.post(f"{BASE_URL}/auth/login", 
                              json={'email': 'admin@example.com', 'password': 'string'})
        if login.status_code != 200:
            print_error(f"Erreur de connexion: {login.status_code}")
            return
        
        token = login.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        print_success("Admin connecté")
        
    except Exception as e:
        print_error(f"Erreur de connexion: {e}")
        return
    
    # Charger les données
    print("\n📖 Chargement des données...")
    data_file = 'app/models/ml_models/training_data_combined.json'
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print_success(f"{len(data)} exemples chargés")
    except FileNotFoundError:
        print_error(f"Fichier non trouvé: {data_file}")
        return
    
    # Équilibrer les données
    balanced_data = balance_data(data, target_per_class=2000)
    
    # Sauvegarder les données équilibrées
    balanced_file = 'app/models/ml_models/training_data_balanced.json'
    with open(balanced_file, 'w', encoding='utf-8') as f:
        json.dump(balanced_data, f, indent=2, ensure_ascii=False)
    print_success(f"Données équilibrées sauvegardées: {balanced_file}")
    
    # Entraîner avec les données équilibrées
    print(f"\n🔄 Entraînement avec {len(balanced_data)} exemples équilibrés...")
    print_info("Cela peut prendre plusieurs minutes...")
    
    try:
        response = requests.post(f"{BASE_URL}/ia/train", headers=headers, json=balanced_data, timeout=600)
        
        if response.status_code == 200:
            result = response.json()
            print("\n" + "=" * 60)
            print(" ✅ MODÈLE ENTRAÎNÉ AVEC SUCCÈS")
            print("=" * 60)
            
            if 'result' in result:
                res = result['result']
                
                if 'accuracy' in res:
                    print(f"📊 Accuracy: {res['accuracy']:.2%}")
                if 'n_samples' in res:
                    print(f"📊 Exemples: {res['n_samples']}")
                if 'n_classes' in res:
                    print(f"📊 Classes: {res['n_classes']}")
                
                if 'report' in res:
                    print("\n📋 Rapport par classe:")
                    report = res['report']
                    for class_name, metrics in report.items():
                        if class_name not in ['accuracy', 'macro avg', 'weighted avg']:
                            if isinstance(metrics, dict):
                                precision = metrics.get('precision', 0)
                                recall = metrics.get('recall', 0)
                                f1 = metrics.get('f1-score', 0)
                                support = metrics.get('support', 0)
                                if support > 0:
                                    bar = "█" * int(f1 * 10) + "░" * (10 - int(f1 * 10))
                                    print(f"   {class_name:20} {bar} precision={precision:.2f}, recall={recall:.2f}, f1={f1:.2f}")
        else:
            print_error(f"Erreur: {response.status_code}")
            print(f"   {response.text}")
            
    except Exception as e:
        print_error(f"Erreur: {e}")

if __name__ == "__main__":
    train_balanced()