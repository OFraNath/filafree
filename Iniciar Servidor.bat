@echo off
:: Inicia o seu código Flask/SocketIO
start python main.py

:: Aguarda o servidor Flask subir (3 segundos para garantir)
timeout /t 1 /nobreak

:: Inicia o túnel da Cloudflare para a porta 8000
cloudflared tunnel --url http://localhost:8000