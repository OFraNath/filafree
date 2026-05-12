from flask import Flask, redirect, send_file, abort
import os
import requests

app = Flask(__name__)

# ============================================================
# CONFIGURAÇÃO DA FONTE DO DOWNLOAD
# ============================================================
# Escolha UM dos dois modos abaixo e deixe o outro como None.
#
# MODO 1 — URL externa (ex: GitHub Releases, Google Drive, etc.)
#   O servidor redireciona o usuário para essa URL.
#   Exemplo: "https://github.com/seu-user/seu-repo/releases/latest/download/app-release.apk"
#
# MODO 2 — Arquivo local no servidor (ex: arquivo enviado junto com o deploy)
#   O servidor serve o arquivo diretamente do disco.
#   Coloque o app-release.apk na raiz do projeto e use o caminho abaixo.
#   Exemplo: "/app-release.apk"  ou  "static/app-release.apk"

APK_EXTERNAL_URL = "https://exemplo.com/caminho/para/app-release.apk"  # <- MODO 1
APK_LOCAL_PATH   = None  # <- MODO 2  ex: "/app-release.apk"

# Nome do arquivo que aparecerá no navegador do usuário ao baixar
APK_DOWNLOAD_NAME = "app-release.apk"
# ============================================================

@app.route("/")
@app.route("/download")
def download_apk():
    # Modo 2 tem prioridade se ambos estiverem preenchidos
    if APK_LOCAL_PATH:
        # Caminho absoluto: aceita tanto "/app-release.apk" quanto "static/app-release.apk"
        path = APK_LOCAL_PATH.lstrip("/")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, path)

        if not os.path.isfile(full_path):
            abort(404, description=f"Arquivo não encontrado no servidor: {full_path}")

        return send_file(
            full_path,
            mimetype="application/vnd.android.package-archive",
            as_attachment=True,
            download_name=APK_DOWNLOAD_NAME,
        )

    if APK_EXTERNAL_URL:
        return redirect(APK_EXTERNAL_URL, code=302)

    abort(500, description="Nenhuma fonte de APK configurada. Defina APK_EXTERNAL_URL ou APK_LOCAL_PATH no main.py.")

if __name__ == "__main__":
    app.run(debug=True, port=8000)
