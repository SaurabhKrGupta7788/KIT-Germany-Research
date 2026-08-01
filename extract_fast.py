from PIL import Image
import os

def extract_frames_fast(gif_path, output_dir, prefix, skip=3):
    if not os.path.exists(gif_path):
        print(f"Missing {gif_path}")
        return 0
    os.makedirs(output_dir, exist_ok=True)
    img = Image.open(gif_path)
    count = 0
    written = 0
    try:
        while True:
            if count % skip == 0:
                frame = img.convert('RGB')
                frame.save(os.path.join(output_dir, f"{prefix}{written}.png"))
                written += 1
            count += 1
            img.seek(img.tell() + 1)
    except EOFError:
        pass
    print(f"Extracted {written} frames from {gif_path} to {output_dir}")
    return written

if __name__ == "__main__":
    cafm_written = extract_frames_fast("d:/KIT/cafm_simulation.gif", "d:/KIT/ppt_image/cafm_frames_fast", "frame_", skip=3)
    gp_written = extract_frames_fast("d:/KIT/gp_fitting.gif", "d:/KIT/ppt_image/gp_frames_fast", "frame_", skip=2)
    
    with open("d:/KIT/fast_counts.txt", "w") as f:
        f.write(f"CAFM: {cafm_written}, GP: {gp_written}")
