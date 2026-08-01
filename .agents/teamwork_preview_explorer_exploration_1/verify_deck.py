import os
import sys

def verify_presentation(html_path):
    print(f"Loading presentation: {html_path}")
    if not os.path.exists(html_path):
        print(f"Error: File {html_path} does not exist!")
        return False
        
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("BeautifulSoup4 is not installed. Doing fallback basic check...")
        return verify_fallback(html_path)

    try:
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
    except Exception as e:
        print(f"Syntax Error: Failed to parse HTML. Details: {e}")
        return False
        
    base_dir = os.path.dirname(os.path.abspath(html_path))
    missing_assets = []
    checked_count = 0
    
    # Check images
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            if src.startswith("http://") or src.startswith("https://"):
                continue
            full_path = os.path.join(base_dir, src)
            checked_count += 1
            if not os.path.exists(full_path):
                print(f"[MISSING IMAGE] Path: {src} -> Resolved: {full_path}")
                missing_assets.append(src)
            else:
                print(f"[OK] Image: {src}")

    # Check videos and posters
    for video in soup.find_all("video"):
        poster = video.get("poster")
        if poster:
            full_path = os.path.join(base_dir, poster)
            checked_count += 1
            if not os.path.exists(full_path):
                print(f"[MISSING POSTER] Path: {poster} -> Resolved: {full_path}")
                missing_assets.append(poster)
            else:
                print(f"[OK] Poster: {poster}")

        for source in video.find_all("source"):
            src = source.get("src")
            if src:
                full_path = os.path.join(base_dir, src)
                checked_count += 1
                if not os.path.exists(full_path):
                    print(f"[MISSING VIDEO] Path: {src} -> Resolved: {full_path}")
                    missing_assets.append(src)
                else:
                    print(f"[OK] Video: {src}")
                    
    print("\n--- Verification Summary ---")
    print(f"Total local assets checked: {checked_count}")
    if missing_assets:
        print(f"Status: FAILED. Missing {len(missing_assets)} assets:")
        for asset in missing_assets:
            print(f" - {asset}")
        return False
    else:
        print("Status: PASSED. All assets verified successfully.")
        return True

def verify_fallback(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    base_dir = os.path.dirname(os.path.abspath(html_path))
    import re
    # Simple regex parsing fallback
    img_srcs = re.findall(r'<img\s+[^>]*src=["\']([^"\']+)["\']', content)
    video_srcs = re.findall(r'<source\s+[^>]*src=["\']([^"\']+)["\']', content)
    posters = re.findall(r'<video\s+[^>]*poster=["\']([^"\']+)["\']', content)
    
    missing_assets = []
    for src in img_srcs + video_srcs + posters:
        if src.startswith("http://") or src.startswith("https://"):
            continue
        full_path = os.path.join(base_dir, src)
        if not os.path.exists(full_path):
            print(f"[MISSING] Path: {src} -> Resolved: {full_path}")
            missing_assets.append(src)
        else:
            print(f"[OK] Asset: {src}")
            
    print(f"Total checked (fallback): {len(img_srcs) + len(video_srcs) + len(posters)}")
    return len(missing_assets) == 0

if __name__ == "__main__":
    target_html = "d:/KIT/html_presentation/index.html"
    success = verify_presentation(target_html)
    sys.exit(0 if success else 1)
