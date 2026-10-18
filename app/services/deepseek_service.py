import json
import logging
from typing import Dict, List, Optional
from google import genai
from google.genai import types
from app.core.config import settings

logger = logging.getLogger(__name__)


class DeepSeekService:

    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.model = settings.DEEPSEEK_MODEL
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    # ============================================
    # APPEL GÉNÉRIQUE
    # ============================================
    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 3000,
        json_mode: bool = True,
    ) -> str:
        if self.client is None:
            raise RuntimeError(
                "Clé API IA non configurée. Définissez DEEPSEEK_API_KEY dans l'environnement."
            )

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt,
        )
        if json_mode:
            config.response_mime_type = "application/json"

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=config,
        )

        if not response.candidates or not response.candidates[0].content.parts:
            finish_reason = (
                response.candidates[0].finish_reason
                if response.candidates else "UNKNOWN"
            )
            raise RuntimeError(
                f"Réponse Gemini vide ou bloquée. Raison: {finish_reason}"
            )

        text = ""
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                text += part.text
        return text

    # ============================================
    # ÉTAPE 1 : PRÉDIRE + GÉNÉRER QUESTIONS
    # ============================================
    async def predire_et_questionner(
        self,
        symptomes: List[str],
        description_libre: Optional[str] = None,
        age: Optional[int] = None,
        sexe: Optional[str] = None,
        antecedents: Optional[List[str]] = None,
        duree_symptomes: Optional[str] = None,
    ) -> Dict:
        """
        ÉTAPE 1 :
        - Combine symptômes prédéfinis + description libre
        - Identifie 2-5 maladies candidates
        - Génère des questions différentielles
        """
        symptomes_str = ", ".join(symptomes) if symptomes else "(aucun coché)"

        system_prompt = """Tu es un assistant médical expert en diagnostic différentiel.

TA MISSION EN 3 PARTIES :

1. FUSIONNER les symptômes :
   - Le patient a coché des symptômes dans une liste prédéfinie
   - Le patient peut AUSSI ajouter une description libre
   - Tu dois COMBINER les deux sources pour créer une liste unifiée de symptômes
   - Standardise si possible les symptômes libres selon la liste officielle

2. IDENTIFIER 2 à 5 maladies CANDIDATES avec leur probabilité

3. GÉNÉRER 4 à 8 questions DIFFÉRENTIELLES pour départager ces maladies

RÈGLES IMPORTANTES :
- Ne donne JAMAIS de diagnostic définitif
- Si la description libre contient des symptômes déjà cochés, ne les duplique pas
- Si la description est floue, pose des questions de clarification
- Réponds UNIQUEMENT en JSON valide

FORMAT JSON ATTENDU :
{
  "symptomes_extraits": {
    "symptomes_finaux": ["Fièvre", "Frissons", "Maux de tête", "Vomissements", "Douleur abdominale"],
    "symptomes_ajoutes": ["Vomissements", "Douleur abdominale"],
    "description_utilisee": "j'ai aussi des vomissements depuis ce matin",
    "notes_extraction": "Vomissements et douleur abdominale ajoutés à partir de la description"
  },
  "maladies_probables": [
    {
      "nom": "Paludisme",
      "probabilite": 0.45,
      "symptomes_correspondants": ["Fièvre", "Frissons", "Maux de tête"],
      "description_courte": "Infection parasitaire transmise par les moustiques",
      "urgence": "élevée"
    }
  ],
  "questions_differentielles": [
    {
      "id": "q1",
      "question": "As-tu des selles liquides très abondantes ?",
      "type_reponse": "oui_non",
      "options": null,
      "aide": "Le choléra provoque une diarrhée aqueuse",
      "maladies_ciblees": ["Choléra"]
    }
  ],
  "message_introduction": "J'ai bien noté vos symptômes. Quelques questions vont aider à préciser le diagnostic.",
  "recommandation_generale": "Consultez un médecin rapidement.",
  "avertissement": "Ceci n'est pas un diagnostic médical."
}"""

        user_prompt = f"""SYMPTÔMES DU PATIENT :

1. Symptômes cochés dans la liste :
   {symptomes_str}
"""

        if description_libre and description_libre.strip():
            user_prompt += f"""
2. Description libre du patient :
   \"\"\"{description_libre.strip()}\"\"\"

⚠️ IMPORTANT : Combine les deux sources. Extrais tous les symptômes 
mentionnés dans la description et ajoute-les à la liste cochée.
"""
        else:
            user_prompt += """
2. Description libre : (aucune)
"""

        if age:
            user_prompt += f"\nÂge : {age} ans"
        if sexe:
            user_prompt += f"\nSexe : {sexe}"
        if antecedents:
            user_prompt += f"\nAntécédents : {', '.join(antecedents)}"
        if duree_symptomes:
            user_prompt += f"\nDurée des symptômes : {duree_symptomes}"

        user_prompt += """

Analyse ces informations, fais la fusion des symptômes,
identifie les maladies candidates et génère les questions. Réponds en JSON."""

        content = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            json_mode=True,
        )

        return json.loads(content)

    # ============================================
    # ÉTAPE 2 : ANALYSER RÉPONSES
    # ============================================
    async def analyser_reponses(
        self,
        symptomes: List[str],
        maladies_candidates: List[Dict],
        questions: List[Dict],
        reponses: Dict[str, str],
        age: Optional[int] = None,
        sexe: Optional[str] = None,
    ) -> Dict:
        """
        ÉTAPE 2 :
        - Analyse les réponses aux questions
        - DÉTERMINE la maladie finale
        - Ne propose JAMAIS de médicaments
        """
        candidats_str = "\n".join([
            f"- {m.get('nom')} (probabilité initiale : {m.get('probabilite', 0):.0%})"
            for m in maladies_candidates
        ])

        qr_str = ""
        for q in questions:
            qid = q.get("id", "?")
            qtext = q.get("question", "?")
            rep = reponses.get(qid, "(non répondu)")
            qr_str += f"[{qid}] {qtext}\n   → {rep}\n\n"

        system_prompt = """Tu es un assistant médical expert en diagnostic différentiel.

Tu as posé des questions pour distinguer plusieurs maladies candidates.
L'utilisateur a répondu.

TA MISSION :
- Analyser les réponses avec attention
- DÉTERMINER LA MALADIE LA PLUS PROBABLE parmi les candidates
- Si les réponses ne permettent PAS de trancher, indique-le clairement
- Donne un niveau de confiance (0.0 à 1.0)
- Ne propose JAMAIS de médicaments
- Fournis uniquement des recommandations générales (repos, hydratation)

RÈGLES :
- Réponds UNIQUEMENT en JSON valide
- "diagnostic_certain" : true seulement si les réponses sont sans ambiguïté
- Si incertain, propose une "maladie_alternative"
- "conseil_consultation" : conseil sur la conduite à tenir

FORMAT JSON ATTENDU :
{
  "maladie_confirmee": "Paludisme",
  "niveau_confiance": 0.85,
  "diagnostic_certain": true,
  "maladie_alternative": null,
  "justification": "Les réponses orientent clairement vers le paludisme.",
  "symptomes_cles": ["fièvre", "frissons", "sueurs nocturnes"],
  "niveau_urgence": "élevée",
  "recommandations": [
    "Consulter un médecin dans les 24h",
    "Se reposer et s'hydrater abondamment"
  ],
  "quand_consulter_urgence": [
    "Fièvre > 40°C",
    "Convulsions",
    "Confusion"
  ],
  "conseil_consultation": "Consultez rapidement un médecin pour un test de diagnostic rapide (TDR).",
  "avertissement": "Ceci n'est pas un diagnostic médical. Consultez un professionnel de santé."
}"""

        user_prompt = f"""Symptômes initiaux : {', '.join(symptomes)}
"""
        if age:
            user_prompt += f"Âge : {age} ans\n"
        if sexe:
            user_prompt += f"Sexe : {sexe}\n"

        user_prompt += f"""
MALADIES CANDIDATES IDENTIFIÉES :
{candidats_str}

QUESTIONS POSÉES ET RÉPONSES :
{qr_str}

Analyse ces réponses et détermine la maladie la plus probable.
Réponds en JSON."""

        content = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            json_mode=True,
        )

        return json.loads(content)


# Instance globale
deepseek_service = DeepSeekService()