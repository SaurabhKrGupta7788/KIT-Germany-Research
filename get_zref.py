import urllib.request
import ssl
import os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
urllib.request.install_opener(opener)

# Direct .sty file URLs from CTAN/GitHub
files_to_get = {
    # zref package files from GitHub (oberdiek bundle)
    'zref-abspage.sty': 'https://raw.githubusercontent.com/ho-tex/zref/main/zref-abspage.sty',
    'zref-base.sty': 'https://raw.githubusercontent.com/ho-tex/zref/main/zref-base.sty',
    'zref.sty': 'https://raw.githubusercontent.com/ho-tex/zref/main/zref.sty',
}

target = 'd:/KIT/'

for fname, url in files_to_get.items():
    dst = os.path.join(target, fname)
    try:
        urllib.request.urlretrieve(url, dst)
        print(f"OK: {fname}")
    except Exception as e:
        print(f"FAIL: {fname} -> {e}")

print("Done")
