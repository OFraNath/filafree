from flask import Flask, redirect, send_file, abort
import os
import requests
import re

app = Flask(__name__)

# ============================================================
# CONFIGURAÇÃO DA FONTE DO DOWNLOAD
# ============================================================
APK_EXTERNAL_URL = "https://drive.google.com/uc?export=download&id=1q64eMGbOx-xgQVDskubTf8lROpaFKkKR"
APK_LOCAL_PATH   = None  # ex: "/app-release.apk"

APK_DOWNLOAD_NAME = "app-release.apk"
# ============================================================

GDRIVE_ID_REGEX = re.compile(r"[?&]id=([\w-]+)")


def get_gdrive_direct_url(file_id: str) -> str:
    """
    Faz a requisição inicial ao Google Drive, captura o cookie de confirmação
    de vírus/arquivo grande e retorna a URL direta de download.
    """
    base_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    session = requests.Session()

    response = session.get(base_url, stream=True, timeout=15)

    confirm_token = None

    # Tenta pelo cookie (arquivos grandes)
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            confirm_token = value
            break

    # Fallback: tenta achar o token no HTML da página de confirmação
    if not confirm_token:
        match = re.search(r'confirm=([0-9A-Za-z_\-]+)', response.text)
        if match:
            confirm_token = match.group(1)

    if confirm_token:
        return f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm_token}"
    
    return base_url


@app.route("/")
@app.route("/download")
def download_apk():
    # --- Modo 2: arquivo local ---
    if APK_LOCAL_PATH:
        path = APK_LOCAL_PATH.lstrip("/")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, path)

        if not os.path.isfile(full_path):
            abort(404, description=f"Arquivo não encontrado: {full_path}")

        return send_file(
            full_path,
            mimetype="application/vnd.android.package-archive",
            as_attachment=True,
            download_name=APK_DOWNLOAD_NAME,
        )

    # --- Modo 1: URL externa ---
    if APK_EXTERNAL_URL:
        match = GDRIVE_ID_REGEX.search(APK_EXTERNAL_URL)
        if match:
            file_id = match.group(1)
            try:
                direct_url = get_gdrive_direct_url(file_id)
                return redirect(direct_url, code=302)
            except Exception as e:
                abort(502, description=f"Erro ao resolver URL do Google Drive: {e}")

        return redirect(APK_EXTERNAL_URL, code=302)

    abort(500, description="Nenhuma fonte de APK configurada.")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
