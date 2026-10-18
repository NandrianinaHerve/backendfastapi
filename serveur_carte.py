#!/usr/bin/env python
"""
Serveur simple pour afficher la carte
"""
import http.server
import socketserver
import os

PORT = 8001
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"🌐 Carte disponible sur: http://localhost:{PORT}/carte_fianarantsoa.html")
    print(f"📊 Assurez-vous que l'API tourne sur http://localhost:8000")
    print("Appuyez sur Ctrl+C pour arrêter")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Serveur arrêté")