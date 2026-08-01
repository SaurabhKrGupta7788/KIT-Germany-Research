import re
import subprocess
import sys
import os

def check_syntax():
    html_path = r"d:\KIT\html_presentation\index.html"
    print(f"Reading {html_path}...")
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all <script>...</script> blocks
    # We want to match script content, ignoring src scripts
    pattern = re.compile(r'<script\b[^>]*>(.*?)</script>', re.DOTALL)
    scripts = pattern.findall(content)

    success = True
    for i, script_content in enumerate(scripts):
        # Skip empty or external scripts (if matched, though pattern is simple)
        if not script_content.strip():
            continue
        
        # Check if the start tag has src
        # Let's verify by checking the match position context
        # We can find script tags manually by splitting
        
    # Let's do a more robust parsing using BeautifulSoup or a simpler approach
    # Let's just find matches.
    # Actually, we can just split on <script> and </script>
    parts = content.split('<script')
    script_idx = 1
    for part in parts[1:]:
        if '>' not in part:
            continue
        tag_attrs, remaining = part.split('>', 1)
        if 'src' in tag_attrs:
            # External script, skip
            continue
        
        if '</script>' not in remaining:
            print(f"Warning: Unterminated script tag")
            continue
            
        script_code = remaining.split('</script>')[0]
        
        temp_filename = f"temp_script_{script_idx}.js"
        temp_filepath = os.path.join(r"d:\KIT\.agents\teamwork_preview_challenger_challenge_1", temp_filename)
        
        with open(temp_filepath, "w", encoding="utf-8") as temp_f:
            temp_f.write(script_code)
            
        print(f"\nChecking syntax of script {script_idx} (saved to {temp_filename})...")
        try:
            res = subprocess.run(["node", "--check", temp_filepath], capture_output=True, text=True, check=True)
            print(f"Script {script_idx}: Syntax is valid.")
        except subprocess.CalledProcessError as e:
            print(f"Script {script_idx}: Syntax ERROR!")
            print(e.stderr)
            success = False
        finally:
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
        
        script_idx += 1
        
    if not success:
        sys.exit(1)
    else:
        print("\nAll JavaScript syntax checks PASSED.")

if __name__ == "__main__":
    check_syntax()
