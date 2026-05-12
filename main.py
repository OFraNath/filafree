from flask import Flask, redirect, send_file, abort, render_template
import os

app = Flask(__name__)

APK_FILES = {
    "universal": {
        "file": "app-release.apk",
        "url": "https://github.com/OFraNath/filafree/releases/download/all/app-release.apk",
    },
    "armeabi-v7a": {
        "file": "app-armeabi-v7a-release.apk",
        "url": "https://github.com/OFraNath/filafree/releases/download/all/app-armeabi-v7a-release.apk",
    },
    "arm64-v8a": {
        "file": "app-arm64-v8a-release.apk",
        "url": "https://github.com/OFraNath/filafree/releases/download/all/app-arm64-v8a-release.apk",
    },
}

SOURCE_MODE = "direct"

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

    return redirect(apk["url"], code=302)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
