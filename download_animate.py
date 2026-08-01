import urllib.request
import zipfile
import os

url = "http://mirrors.ctan.org/macros/latex/contrib/animate.zip"
zip_path = "d:/KIT/animate.zip"
extract_path = "d:/KIT/"

print("Downloading animate package...")
try:
    urllib.request.urlretrieve(url, zip_path)
    print("Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    
    # Move files from d:/KIT/animate/ to d:/KIT/ if they are in a subfolder
    animate_dir = os.path.join(extract_path, "animate")
    if os.path.exists(animate_dir):
        for item in os.listdir(animate_dir):
            import shutil
            shutil.move(os.path.join(animate_dir, item), extract_path)
    print("Done!")
except Exception as e:
    print(f"Error: {e}")
