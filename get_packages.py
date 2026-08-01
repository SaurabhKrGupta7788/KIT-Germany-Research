import urllib.request
import zipfile
import os
import shutil
import ssl

# Disable SSL verification for CTAN mirrors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

packages = {
    'pdfbase': 'https://mirrors.ctan.org/macros/latex/contrib/pdfbase.zip',
    'ocgx2': 'https://mirrors.ctan.org/macros/latex/contrib/ocgx2.zip',
}

target = 'd:/KIT/'

for name, url in packages.items():
    zip_path = os.path.join(target, f'{name}.zip')
    print(f"Downloading {name}...")
    try:
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(url, zip_path)
        print(f"  Extracting {name}...")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(target)
        print(f"  Done: {name}")
    except Exception as e:
        print(f"  Error with {name}: {e}")

# Now copy all .sty files from extracted dirs into d:/KIT/ so pdflatex finds them
for name in packages:
    pkg_dir = os.path.join(target, name)
    if os.path.isdir(pkg_dir):
        for f in os.listdir(pkg_dir):
            if f.endswith('.sty') or f.endswith('.def'):
                src = os.path.join(pkg_dir, f)
                dst = os.path.join(target, f)
                shutil.copy2(src, dst)
                print(f"  Copied {f} to {target}")

print("\nAll done!")
