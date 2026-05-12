from flask import Flask, redirect, send_file, abort, render_template
import os

app = Flask(__name__)

APK_FILES = {
    "universal": {
        "file": "app-release.apk",
        "gdrive_id": "1r1GBKtiRbolN-Y7eJvDwwmmEWUClRGj4",
    },
    "armeabi-v7a": {
        "file": "app-armeabi-v7a-release.apk",
        "gdrive_id": "1H8K5dqwwG1PZipwnsbOUKDvEs3Q3u3EC",
    },
    "arm64-v8a": {
        "file": "app-arm64-v8a-release.apk",
        "gdrive_id": "1q64eMGbOx-xgQVDskubTf8lROpaFKkKR",
    },
}

SOURCE_MODE = "gdrive"  # "gdrive" ou "local"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download/<arch>")
def download_apk(arch):
    apk = APK_FILES.get(arch)
    if not apk:
        abort(404)

    if SOURCE_MODE == "local":
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, apk["file"])
        if not os.path.isfile(full_path):
            abort(404)
        return send_file(
            full_path,
            mimetype="application/vnd.android.package-archive",
            as_attachment=True,
            download_name=apk["file"],
        )

    url = f"https://drive.google.com/uc?export=download&id={apk['gdrive_id']}"
    return redirect(url, code=302)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
