from PIL import Image
import os

def extract_frames(gif_path, output_dir, prefix):
    if not os.path.exists(gif_path):
        print(f"File {gif_path} not found.")
        return 0
    os.makedirs(output_dir, exist_ok=True)
    img = Image.open(gif_path)
    count = 0
    try:
        while True:
            # Convert to RGB to ensure PNG saves correctly without palette issues
            frame = img.convert('RGB')
            frame.save(os.path.join(output_dir, f"{prefix}{count}.png"))
            count += 1
            img.seek(img.tell() + 1)
    except EOFError:
        pass
    print(f"Extracted {count} frames from {gif_path} to {output_dir}")
    return count

if __name__ == "__main__":
    cafm_count = extract_frames("d:/KIT/cafm_simulation.gif", "d:/KIT/cafm_frames", "frame_")
    gp_count = extract_frames("d:/KIT/gp_fitting.gif", "d:/KIT/gp_frames", "frame_")
    
    with open("d:/KIT/frame_counts.txt", "w") as f:
        f.write(f"CAFM: {cafm_count}\nGP: {gp_count}\n")
