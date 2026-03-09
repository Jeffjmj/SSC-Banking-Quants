import os
import json
import time
from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client()

def process_image_folders(base_directory, output_json="ssc_math_database_images.json"):
    # RESUME LOGIC: Skips already processed files
    if os.path.exists(output_json):
        with open(output_json, "r", encoding="utf-8") as f:
            try:
                final_dataset = json.load(f)
            except:
                final_dataset = []
    else:
        final_dataset = []

    processed_files = {q.get('original_file') for q in final_dataset}
    diagrams_dir = os.path.join(os.getcwd(), "extracted_diagrams")
    os.makedirs(diagrams_dir, exist_ok=True)

    for folder_name in os.listdir(base_directory):
        folder_path = os.path.join(base_directory, folder_name)
        if not os.path.isdir(folder_path): continue
            
        print(f"\n--- Topic: {folder_name} ---")
        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg')) and file_name not in processed_files:
                img_path = os.path.join(folder_path, file_name)
                print(f"Processing {file_name}...")
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # FIXED: Use 'file=' argument
                        gemini_file = client.files.upload(file=img_path)
                        
                        prompt = f"Extract math questions for topic '{folder_name}'. Output JSON with keys: topic, question_number, question_text, options (A, B, C, D), correct_option, explanation, diagram_coords [top, left, bottom, right]."
                        
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=[gemini_file, prompt],
                            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0)
                        )
                        
                        page_data = json.loads(response.text)
                        for q in page_data: q['original_file'] = file_name

                        # Diagram Cropping (75px padding)
                        for q_index, question in enumerate(page_data):
                            coords = question.get('diagram_coords')
                            if coords and len(coords) == 4:
                                img = Image.open(img_path)
                                w, h = img.size
                                t, l, b, r = coords
                                pad = 75
                                c_l, c_t = max(0, int((l/1000)*w)-pad), max(0, int((t/1000)*h)-pad)
                                c_r, c_b = min(w, int((r/1000)*w)+pad), min(h, int((b/1000)*h)+pad)
                                diag_path = os.path.join(diagrams_dir, f"diag_{file_name}_q{q_index}.png")
                                img.crop((c_l, c_t, c_r, c_b)).save(diag_path)
                                question['diagram_image_path'] = diag_path
                                del question['diagram_coords']

                        final_dataset.extend(page_data)
                        with open(output_json, "w", encoding="utf-8") as f: json.dump(final_dataset, f, indent=4)
                        client.files.delete(name=gemini_file.name)
                        break 
                    except Exception as e:
                        print(f"Network error on {file_name}. Retrying... ({attempt+1}/3)")
                        time.sleep(15)

# PATHS confirmed from your screenshot
my_image_dir = r"D:\COMPETITION EXAMS\SSC\ExamExtractor\1-Exam-Topics"
process_image_folders(my_image_dir)