from flask import Flask, redirect, send_file, abort
import os

app = Flask(__name__)

APK_EXTERNAL_URL = "https://drive.google.com/uc?export=download&id=1q64eMGbOx-xgQVDskubTf8lROpaFKkKR"
APK_LOCAL_PATH   = None  # ex: "/app-release.apk"
APK_DOWNLOAD_NAME = "app-release.apk"


@app.route("/")
@app.route("/download")
def download_apk():
    if APK_LOCAL_PATH:
        path = APK_LOCAL_PATH.lstrip("/")
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
        if not os.path.isfile(full_path):
            abort(404)
        return send_file(
            full_path,
            mimetype="application/vnd.android.package-archive",
            as_attachment=True,
            download_name=APK_DOWNLOAD_NAME,
        )

    if APK_EXTERNAL_URL:
        return redirect(APK_EXTERNAL_URL, code=302)

    abort(500)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
