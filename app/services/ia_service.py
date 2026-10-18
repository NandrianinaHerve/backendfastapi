# class IAAnalyzer:
#     """Service d'analyse des symptômes par IA"""
    
#     # Mapping symptômes -> spécialités
#     SYMPTOME_SPECIALITE = {
#         # ... (défini plus haut)
#     }
    
#     @classmethod
#     def analyze(cls, symptomes: str) -> dict:
#         """Analyser les symptômes et retourner la spécialité recommandée"""
#         symptomes_lower = symptomes.lower()
#         scores = {}
        
#         for key, specialite in cls.SYMPTOME_SPECIALITE.items():
#             if key in symptomes_lower:
#                 scores[specialite] = scores.get(specialite, 0) + 1
        
#         if not scores:
#             return {
#                 "specialite": "médecine générale",
#                 "confiance": 0.3,
#                 "symptomes_trouves": []
#             }
        
#         # Trouver la spécialité avec le plus grand score
#         best_specialite = max(scores.items(), key=lambda x: x[1])
#         confidence = min(best_specialite[1] / 3, 0.95)
        
#         return {
#             "specialite": best_specialite[0],
#             "confiance": confidence,
#             "symptomes_trouves": [k for k in cls.SYMPTOME_SPECIALITE.keys() if k in symptomes_lower]
#         }

import random
from typing import Dict, List, Tuple

class IAAnalyzer:
    """Système expert à base de règles (fallback)"""
    
    # Mapping symptômes → spécialités
    SYMPTOME_SPECIALITE = {
        "douleur poitrine": "cardiologie",
        "essoufflement": "cardiologie",
        "palpitations": "cardiologie",
        "maux tête": "neurologie",
        "vertiges": "neurologie",
        "perte connaissance": "neurologie",
        "douleur estomac": "gastro-entérologie",
        "nausée": "gastro-entérologie",
        "vomissement": "gastro-entérologie",
        "douleur os": "orthopédie",
        "fracture": "orthopédie",
        "entorse": "orthopédie",
        "fièvre": "médecine générale",
        "toux": "pneumologie",
        "mal gorge": "ORL",
        "éruption cutanée": "dermatologie",
        "démangeaison": "dermatologie",
        "douleur oeil": "ophtalmologie",
        "vision trouble": "ophtalmologie",
        "dépression": "psychiatrie",
        "anxiété": "psychiatrie",
        "douleur dent": "dentisterie",
        "saignement": "dentisterie"
    }
    
    @classmethod
    def analyze(cls, symptomes: str) -> Dict:
        """Analyser les symptômes avec le système expert"""
        symptomes_lower = symptomes.lower()
        scores = {}
        
        for key, specialite in cls.SYMPTOME_SPECIALITE.items():
            if key in symptomes_lower:
                scores[specialite] = scores.get(specialite, 0) + 1
        
        if not scores:
            return {
                "specialite": "médecine générale",
                "confiance": 0.3,
                "symptomes_trouves": []
            }
        
        # Trouver la meilleure spécialité
        best_specialite = max(scores.items(), key=lambda x: x[1])
        confidence = min(best_specialite[1] / 3, 0.95)
        
        return {
            "specialite": best_specialite[0],
            "confiance": confidence,
            "symptomes_trouves": [k for k in cls.SYMPTOME_SPECIALITE.keys() if k in symptomes_lower],
            "scores": scores
        }