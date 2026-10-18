import pickle
import os
import re
import json
import numpy as np
from typing import List, Tuple, Dict, Optional
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import logging

logger = logging.getLogger(__name__)

class MLService:
    """Service de Machine Learning pour l'analyse des symptômes"""
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.model_path = "app/models/ml_models/symptom_classifier.pkl"
        self.vectorizer_path = "app/models/ml_models/vectorizer.pkl"
        self._load_model()
    
    def _load_model(self):
        """Charger le modèle entraîné"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.vectorizer_path):
                # Vérifier que les fichiers ne sont pas vides
                if os.path.getsize(self.model_path) > 0 and os.path.getsize(self.vectorizer_path) > 0:
                    with open(self.model_path, 'rb') as f:
                        self.model = pickle.load(f)
                    with open(self.vectorizer_path, 'rb') as f:
                        self.vectorizer = pickle.load(f)
                    logger.info("✅ Modèle ML chargé avec succès")
                    return
                else:
                    logger.warning("⚠️ Fichiers de modèle vides")
            else:
                logger.warning("⚠️ Modèle ML non trouvé")
        except Exception as e:
            logger.error(f"❌ Erreur de chargement du modèle: {e}")
        
        # Créer le modèle de fallback
        self._create_fallback_model()
    
    def _create_fallback_model(self):
        """Créer un modèle de fallback avec des données minimales"""
        logger.info("🔄 Création du modèle de fallback...")
        
        # Données d'entraînement minimales (à enrichir)
        training_data = [
            # Symptômes, Spécialité
            ("douleur poitrine essoufflement palpitations", "cardiologie"),
            ("maux tête vertiges perte connaissance", "neurologie"),
            ("douleur estomac nausée vomissement", "gastro-enterologie"),
            ("douleur os fracture entorse", "orthopedie"),
            ("fievre toux mal gorge", "pneumologie"),
            ("eruption cutanee demangeaison", "dermatologie"),
            ("douleur oeil vision trouble", "ophtalmologie"),
            ("depression anxiete", "psychiatrie"),
            ("douleur dent saignement", "dentisterie"),
            ("douleur articulaire", "rhumatologie"),
            ("infection urinaire", "urologie"),
            ("trouble sommeil fatigue", "medecine generale"),
            ("douleur abdominale", "gastro-enterologie"),
            ("toux seche", "pneumologie"),
            ("migraine", "neurologie"),
            ("douleur thoracique", "cardiologie"),
        ]
        
        X = [d[0] for d in training_data]
        y = [d[1] for d in training_data]
        
        # ✅ CORRECTION : stop_words=None
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            stop_words=None,  # ← Changé de 'french' à None
            lowercase=True
        )
        X_vectorized = self.vectorizer.fit_transform(X)
        
        # Créer et entraîner le modèle
        # self.model = RandomForestClassifier(
        #     n_estimators=100,
        #     random_state=42,
        #     class_weight='balanced'
        # )
        self.model = RandomForestClassifier(
             n_estimators=200,        # ← Augmenté de 150 à 200
             random_state=42,
             class_weight='balanced',
             max_depth=15,            # ← Augmenté de 10 à 15
             min_samples_split=5,     # ← Ajouté
             min_samples_leaf=2 
        )
        self.model.fit(X_vectorized, y)
        
        # Sauvegarder le modèle
        self._save_model()
        logger.info("✅ Modèle de fallback créé et sauvegardé")
    
    def _save_model(self):
        """Sauvegarder le modèle et le vectorizer"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            with open(self.vectorizer_path, 'wb') as f:
                pickle.dump(self.vectorizer, f)
            logger.info("✅ Modèle sauvegardé avec succès")
        except Exception as e:
            logger.error(f"❌ Erreur de sauvegarde: {e}")
    
    def train(self, data: List[Tuple[str, str]]) -> Dict:
        """Entraîner le modèle avec de nouvelles données"""
        if len(data) < 10:
            return {"error": "Besoin d'au moins 10 exemples pour l'entraînement"}
        
        X = [d[0] for d in data]
        y = [d[1] for d in data]
        
        # ✅ CORRECTION : stop_words=None
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            stop_words=None,  # ← Changé de 'french' à None
            lowercase=True
        )
        X_vectorized = self.vectorizer.fit_transform(X)
        
        # Division train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X_vectorized, y, test_size=0.2, random_state=42
        )
        
        # Entraînement
        # self.model = RandomForestClassifier(
        #     n_estimators=150,
        #     random_state=42,
        #     class_weight='balanced',
        #     max_depth=10
        # )
        self.model = RandomForestClassifier(
             n_estimators=200,        # ← Augmenté de 150 à 200
             random_state=42,
             class_weight='balanced',
             max_depth=15,            # ← Augmenté de 10 à 15
             min_samples_split=5,     # ← Ajouté
             min_samples_leaf=2       # ← Ajouté
)
        self.model.fit(X_train, y_train)
        
        # Évaluation
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        
        # Sauvegarder
        self._save_model()
        
        return {
            "accuracy": accuracy,
            "report": report,
            "n_samples": len(data),
            "n_features": X_vectorized.shape[1]
        }
    
    def predict(self, symptoms: str) -> Dict:
        """Prédire la spécialité à partir des symptômes"""
        if not self.model or not self.vectorizer:
            self._load_model()
        
        # Nettoyer et vectoriser
        symptoms_clean = self._clean_text(symptoms)
        X = self.vectorizer.transform([symptoms_clean])
        
        # Prédiction
        prediction = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]
        confidence = float(max(probabilities))
        
        # Top 3 spécialités
        top_indices = np.argsort(probabilities)[-3:][::-1]
        top_specialities = [
            {
                "specialite": self.model.classes_[i],
                "confiance": float(probabilities[i])
            }
            for i in top_indices
        ]
        
        return {
            "specialite": prediction,
            "confiance": confidence,
            "top_3": top_specialities,
            "symptomes_analyses": symptoms_clean
        }
    
    def _clean_text(self, text: str) -> str:
        """Nettoyer le texte des symptômes"""
        text = text.lower()
        # Supprimer les caractères spéciaux
        text = re.sub(r'[^a-z\s]', '', text)
        # Supprimer les espaces multiples
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def get_statistics(self) -> Dict:
        """Obtenir des statistiques sur le modèle"""
        if not self.model:
            return {"error": "Modèle non chargé"}
        
        return {
            "model_type": type(self.model).__name__,
            "n_classes": len(self.model.classes_),
            "classes": list(self.model.classes_),
            "n_features": self.model.n_features_in_ if hasattr(self.model, 'n_features_in_') else 0,
            "is_trained": True
        }
    
    def add_training_data(self, symptoms: str, specialite: str) -> Dict:
        """Ajouter des données d'entraînement (pour enrichir progressivement)"""
        data_file = "app/models/ml_models/training_data.json"
        
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
        except:
            data = []
        
        data.append({
            "symptomes": symptoms,
            "specialite": specialite,
            "date": str(datetime.now())
        })
        
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        training_data = [(d["symptomes"], d["specialite"]) for d in data]
        return self.train(training_data)

# Instance globale
ml_service = MLService()