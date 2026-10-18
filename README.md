# Lancement avec Docker

Depuis le dossier `sante-fianarantsoa-backend`, démarrez l'API, PostgreSQL,
Redis et le frontend avec :

```sh
docker compose up --build
```

Le frontend est disponible sur `http://localhost:3000`. L'API est accessible
sur `http://localhost:8000` et sa documentation sur
`http://localhost:8000/api/docs`. Le frontend transmet les appels `/api/` à
l'API via le réseau Docker Compose.

Les variables de configuration sensibles doivent être fournies à l'exécution
et ne doivent pas être ajoutées aux images Docker.

Pour activer l'assistant IA, ajoutez votre clé à un fichier `.env` local
(ignoré par Git) :

```dotenv
DEEPSEEK_API_KEY=<votre-cle-api>
```

Compose transmet cette variable au backend. Sans clé, l'API et les autres
fonctionnalités démarrent normalement, mais les appels à l'assistant IA
renvoient une erreur de configuration explicite.
