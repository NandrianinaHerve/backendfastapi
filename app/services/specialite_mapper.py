from typing import List, Dict


class SpecialiteMapper:
    """
    Mappe une maladie (issue de l'IA) vers une ou plusieurs spécialités médicales.
    Utilise des mots-clés pour être robuste face aux variations de nommage.
    """

    MALADIE_TO_SPECIALITES: Dict[str, List[str]] = {
        # ========== INFECTIEUX / TROPICAL ==========
        "paludisme": ["Médecine générale", "Infectiologie", "Médecine interne"],
        "tuberculose": ["Pneumologie", "Infectiologie", "Médecine interne"],
        "dengue": ["Infectiologie", "Médecine générale"],
        "typhoïde": ["Infectiologie", "Médecine générale"],
        "grippe": ["Médecine générale", "ORL"],
        "covid": ["Médecine générale", "Pneumologie"],
        "hépatite": ["Gastro-entérologie", "Hépatologie", "Infectiologie"],
        "méningite": ["Neurologie", "Infectiologie", "Urgences"],

        # ========== DIGESTIF ==========
        "gastro-entérite": ["Gastro-entérologie", "Médecine générale"],
        "gastro": ["Gastro-entérologie", "Médecine générale"],
        "diarrhée": ["Gastro-entérologie", "Médecine générale"],
        "ulcère": ["Gastro-entérologie"],
        "reflux": ["Gastro-entérologie"],
        "appendicite": ["Chirurgie générale", "Gastro-entérologie"],
        "intoxication alimentaire": ["Gastro-entérologie", "Médecine générale"],
        "colite": ["Gastro-entérologie"],

        # ========== CARDIO / SANG ==========
        "anémie": ["Hématologie", "Médecine interne", "Médecine générale"],
        "hypertension": ["Cardiologie", "Médecine générale"],
        "infarctus": ["Cardiologie", "Urgences"],
        "arythmie": ["Cardiologie"],
        "palpitations": ["Cardiologie", "Médecine générale"],
        "insuffisance cardiaque": ["Cardiologie"],
        "thrombose": ["Hématologie", "Cardiologie", "Vasculaire"],

        # ========== NEURO / PSY ==========
        "anxiété": ["Psychiatrie", "Psychologie"],
        "panique": ["Psychiatrie", "Psychologie"],
        "dépression": ["Psychiatrie", "Psychologie"],
        "migraine": ["Neurologie", "Médecine générale"],
        "épilepsie": ["Neurologie"],
        "avc": ["Neurologie", "Urgences"],
        "parkinson": ["Neurologie"],
        "alzheimer": ["Neurologie", "Gériatrie"],

        # ========== RESPIRATOIRE ==========
        "pneumonie": ["Pneumologie", "Médecine générale"],
        "asthme": ["Pneumologie", "Allergologie"],
        "bronchite": ["Pneumologie", "Médecine générale"],
        "angine": ["ORL", "Médecine générale"],
        "sinusite": ["ORL"],
        "rhinite": ["ORL", "Allergologie"],
        "apnée du sommeil": ["Pneumologie", "ORL"],

        # ========== ENDOCRINO ==========
        "diabète": ["Endocrinologie", "Médecine générale"],
        "thyroïde": ["Endocrinologie"],
        "obésité": ["Endocrinologie", "Nutrition"],
        "cholestérol": ["Cardiologie", "Endocrinologie", "Médecine générale"],

        # ========== DERMATO / ALLERGIE ==========
        "allergie": ["Allergologie", "Dermatologie"],
        "eczéma": ["Dermatologie"],
        "acné": ["Dermatologie"],
        "psoriasis": ["Dermatologie"],
        "urticaire": ["Dermatologie", "Allergologie"],
        "mycose": ["Dermatologie"],

        # ========== OSTÉO / RHUMATO ==========
        "fracture": ["Orthopédie", "Traumatologie"],
        "entorse": ["Orthopédie", "Traumatologie"],
        "arthrose": ["Rhumatologie", "Orthopédie"],
        "arthrite": ["Rhumatologie"],
        "lombalgie": ["Rhumatologie", "Orthopédie"],
        "scoliose": ["Orthopédie"],

        # ========== URO / NÉPHRO ==========
        "infection urinaire": ["Urologie", "Médecine générale"],
        "calcul rénal": ["Urologie", "Néphrologie"],
        "prostate": ["Urologie"],
        "insuffisance rénale": ["Néphrologie"],

        # ========== GYNÉCO ==========
        "grossesse": ["Gynécologie", "Obstétrique"],
        "règles douloureuses": ["Gynécologie"],
        "endométriose": ["Gynécologie"],
        "ménopause": ["Gynécologie", "Endocrinologie"],

        # ========== OPHTALMO ==========
        "conjonctivite": ["Ophtalmologie"],
        "glaucome": ["Ophtalmologie"],
        "cataracte": ["Ophtalmologie"],
        "vision trouble": ["Ophtalmologie"],
    }

    DEFAULT_SPECIALITES = ["Médecine générale", "Médecine interne"]

    @classmethod
    def get_specialites_for_maladie(cls, maladie: str) -> List[str]:
        """Retourne la liste des spécialités pour une maladie donnée."""
        if not maladie:
            return cls.DEFAULT_SPECIALITES

        maladie_lower = maladie.lower().strip()

        # 1. Correspondance exacte
        if maladie_lower in cls.MALADIE_TO_SPECIALITES:
            return cls.MALADIE_TO_SPECIALITES[maladie_lower]

        # 2. Correspondance partielle
        for key, specialites in cls.MALADIE_TO_SPECIALITES.items():
            if key in maladie_lower or maladie_lower in key:
                return specialites

        # 3. Correspondance par mots individuels
        mots_maladie = set(maladie_lower.split())
        for key, specialites in cls.MALADIE_TO_SPECIALITES.items():
            mots_key = set(key.split())
            if mots_maladie & mots_key:
                return specialites

        # 4. Fallback
        return cls.DEFAULT_SPECIALITES