from PIL import Image, JpegImagePlugin
import os

def create_multipage_pdf(input_dir, output_pdf, prefix, total_frames):
    images = []
    first_image = None
    
    for i in range(total_frames):
        img_path = os.path.join(input_dir, f"{prefix}{i}.png")
        if os.path.exists(img_path):
            img = Image.open(img_path).convert('RGB')
            if first_image is None:
                first_image = img
            else:
                images.append(img)
                
    if first_image is not None:
        first_image.save(output_pdf, save_all=True, append_images=images)
        print(f"Saved {output_pdf} with {len(images)+1} frames.")
    else:
        print(f"No frames found in {input_dir}")

if __name__ == '__main__':
    create_multipage_pdf("d:/KIT/ppt_image/cafm_frames", "d:/KIT/ppt_image/cafm_animation.pdf", "frame_", 150)
    create_multipage_pdf("d:/KIT/ppt_image/gp_frames", "d:/KIT/ppt_image/gp_animation.pdf", "frame_", 60)
