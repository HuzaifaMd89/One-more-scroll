"""Stage only game code, build using pygbag, and create an itch.io ZIP."""
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


def main():
    root = Path(__file__).resolve().parent
    stage = root / "build" / "web-src"
    stage.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "main.py", stage / "main.py")
    subprocess.run([sys.executable, "-m", "pygbag", "--build", "--title", "One More Scroll", "--width", "540", "--height", "820", str(stage)], check=True, cwd=root)
    web = stage / "build" / "web"
    if not (web / "index.html").is_file():
        raise RuntimeError("pygbag did not produce index.html; no release created")
    # The upstream template defaults to a landscape aspect ratio, even when
    # passed portrait framebuffer dimensions. Keep the loader portrait too.
    index = web / "index.html"
    html = index.read_text(encoding="utf-8")
    html = html.replace("fb_ar   :  1.77", "fb_ar   :  0.6585365854")
    html = html.replace('background = "#7f7f7f"', 'background = "#090f1f"')
    html = html.replace("</head>", """<style>
html, body { background: #090f1f; overflow: hidden; overscroll-behavior: none; }
canvas { touch-action: none; }
#infobox { background: #121d31; color: #6ff9ae; border: 1px solid #25364c;
 border-radius: 14px; font: 16px system-ui, sans-serif; text-align: center; }
</style></head>""")
    index.write_text(html, encoding="utf-8")
    output = root / "dist" / "one-more-scroll-web.zip"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(web.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(web).as_posix())
    with zipfile.ZipFile(output) as archive:
        assert "index.html" in archive.namelist()
        assert archive.testzip() is None
    print(f"Ready to upload: {output}")
    print(f"Preview: {sys.executable} -m http.server 8000 --directory \"{web}\"")


if __name__ == "__main__":
    main()
