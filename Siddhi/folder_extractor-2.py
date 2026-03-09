import os
import json
import time
import hashlib
from dotenv import load_dotenv
from PIL import Image
from google import genai
from google.genai import types

load_dotenv()

# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
OUTPUT_JSON  = os.path.join(SCRIPT_DIR, "ssc_math_database_images.json")
DIAGRAMS_DIR = os.path.join(SCRIPT_DIR, "extracted_diagrams")
MODEL        = "gemini-2.5-flash"
MAX_RETRIES  = 3
RETRY_SLEEP  = 20      # seconds between retries
PAD          = 80      # px padding around cropped diagram

# ─────────────────────────────────────────────────────────
# Prompt  (strict JSON schema so Gemini output is consistent)
# ─────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """You are an expert math question extractor for SSC / competitive-exam prep.

The image contains one or more math questions on the topic: **{topic}**.

For EVERY question visible in the image, return a JSON **array** where each element is an object with EXACTLY these keys:

{{
  "topic":           "<string>  topic name",
  "question_number": "<string or int>  question number as it appears, e.g. 1 or 'Q1'",
  "question_text":   "<string>  full question text including all given data",
  "options":         {{"A": "...", "B": "...", "C": "...", "D": "..."}} or null if no options,
  "correct_option":  "<string>  'A', 'B', 'C', or 'D'>  or null if answer not shown",
  "explanation":     "<string>  step-by-step solution / explanation, or empty string if not shown",
  "has_diagram":     <true | false>,
  "diagram_coords":  [top, left, bottom, right]  in per-mille (0-1000) units relative to image size,
                     or null if has_diagram is false
}}

Rules:
1. **has_diagram** = true when the question includes a geometric figure, shape (circle, triangle, rectangle,
   sector, cone, cylinder, etc.), a graph, or any visual that is integral to solving the question.
   Set to false for purely text questions.

2. **diagram_coords**: When has_diagram is true, give bounding-box coordinates in per-mille units
   (0 = top/left edge, 1000 = bottom/right edge of the FULL image).
   Coordinates order: [top, left, bottom, right].
   Be generous — include 15-20 px of extra space around the shape.
   If has_diagram is true but you cannot reliably locate the diagram, return [0, 0, 500, 500]
   as a fallback — do NOT return null when has_diagram is true.

3. If the image contains concept/formula pages (not individual questions), treat each
   concept/formula block as one entry. Set question_number to a descriptive label like
   "Formula_Circle_i", correct_option to null, and options to null.

4. Output ONLY a valid JSON array. No markdown fences, no extra text.
"""

# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def load_or_create_dataset(path: str) -> list:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass
    return []


def save_dataset(path: str, data: list):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def make_unique_key(topic: str, file_name: str) -> str:
    """
    Resume key = topic + filename to avoid cross-folder collisions.
    (Two folders can have identically-named image files.)
    """
    return f"{topic}|{file_name}"


def short_hash(s: str, length: int = 8) -> str:
    return hashlib.md5(s.encode()).hexdigest()[:length]


def crop_and_save_diagram(img_path: str, coords: list, out_path: str) -> bool:
    """
    Crop diagram from image using per-mille coords [top, left, bottom, right].
    Returns True on success, False on error.
    """
    try:
        img = Image.open(img_path)
        w, h = img.size
        top, left, bottom, right = coords

        c_l = max(0, int((left   / 1000) * w) - PAD)
        c_t = max(0, int((top    / 1000) * h) - PAD)
        c_r = min(w, int((right  / 1000) * w) + PAD)
        c_b = min(h, int((bottom / 1000) * h) + PAD)

        # Sanity check — ensure non-zero crop region
        if c_r <= c_l or c_b <= c_t:
            print(f"  [WARNING] Invalid crop region for {out_path}. Skipping diagram crop.")
            return False

        img.crop((c_l, c_t, c_r, c_b)).save(out_path)
        return True
    except Exception as e:
        print(f"  [WARNING] Could not crop diagram: {e}")
        return False


def extract_response_text(response) -> str:
    """
    Safely pull text from a Gemini response object.
    `response.text` can be None when the model hits a safety filter
    or returns an empty candidate — fall back to reading candidates directly.
    Raises ValueError if no usable text is found.
    """
    # Fast path
    if response.text is not None:
        return response.text

    # Fallback: dig into candidates
    try:
        text = response.candidates[0].content.parts[0].text
        if text:
            return text
    except (AttributeError, IndexError, TypeError):
        pass

    # Log finish reason to help diagnose
    try:
        reason = response.candidates[0].finish_reason
        raise ValueError(f"Empty response from Gemini (finish_reason={reason}). "
                         "Image may have been blocked by safety filters — skipping.")
    except (AttributeError, IndexError):
        raise ValueError("Empty response from Gemini (no candidates). Skipping.")


def parse_gemini_response(text: str) -> list:
    """
    Gemini sometimes wraps JSON in markdown fences. Strip them.
    Also handle the case where model returns a dict instead of a list.
    """
    text = text.strip()
    if text.startswith("```"):
        # Remove opening and closing fences
        lines = text.split("\n")
        # drop first line (```json or ```) and last line (```)
        text = "\n".join(lines[1:-1]).strip()

    data = json.loads(text)
    if isinstance(data, dict):
        # Single question returned as dict, wrap in list
        data = [data]
    elif not isinstance(data, list):
        raise ValueError(f"Unexpected JSON type: {type(data)}")
    return data


# ─────────────────────────────────────────────────────────
# Main processing function
# ─────────────────────────────────────────────────────────

def process_image_folders(base_directory: str):
    os.makedirs(DIAGRAMS_DIR, exist_ok=True)

    final_dataset = load_or_create_dataset(OUTPUT_JSON)

    # Build resume set: topic|filename pairs that are already done
    processed_keys = {
        make_unique_key(q.get("topic", ""), q.get("original_file", ""))
        for q in final_dataset
    }

    client = genai.Client()

    for folder_name in sorted(os.listdir(base_directory)):
        folder_path = os.path.join(base_directory, folder_name)
        if not os.path.isdir(folder_path):
            continue

        image_files = sorted([
            f for f in os.listdir(folder_path)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ])
        if not image_files:
            continue

        print(f"\n{'='*60}")
        print(f"  Topic: {folder_name}  ({len(image_files)} images)")
        print(f"{'='*60}")

        for file_name in image_files:
            resume_key = make_unique_key(folder_name, file_name)
            if resume_key in processed_keys:
                print(f"  [SKIP] Already processed: {file_name}")
                continue

            img_path = os.path.join(folder_path, file_name)
            print(f"\n  Processing: {file_name}")

            gemini_file = None
            success = False

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    # Upload image to Gemini Files API
                    gemini_file = client.files.upload(file=img_path)

                    prompt = PROMPT_TEMPLATE.format(topic=folder_name)

                    response = client.models.generate_content(
                        model=MODEL,
                        contents=[gemini_file, prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.0
                        )
                    )

                    raw_text  = extract_response_text(response)
                    page_data = parse_gemini_response(raw_text)

                    # ── Post-process each question ──────────────────────
                    for q_index, question in enumerate(page_data):
                        # Ensure required fields exist with defaults
                        question.setdefault("topic",           folder_name)
                        question.setdefault("question_number", q_index + 1)
                        question.setdefault("question_text",   "")
                        question.setdefault("options",         None)
                        question.setdefault("correct_option",  None)
                        question.setdefault("explanation",     "")
                        question.setdefault("has_diagram",     False)
                        question.setdefault("diagram_coords",  None)

                        # Record source file (key for resume logic)
                        question["original_file"] = file_name
                        question["topic"]         = folder_name  # normalise

                        # ── Diagram cropping ──────────────────────────
                        coords = question.get("diagram_coords")
                        has_diagram = question.get("has_diagram", False)

                        if has_diagram and coords and len(coords) == 4:
                            # Build a stable, short filename for the cropped diagram
                            img_stem   = os.path.splitext(file_name)[0]
                            # Avoid Windows path-length issues with long filenames
                            stem_hash  = short_hash(img_stem)
                            diag_name  = f"diag_{folder_name}_{stem_hash}_q{q_index}.png"
                            diag_path  = os.path.join(DIAGRAMS_DIR, diag_name)

                            ok = crop_and_save_diagram(img_path, coords, diag_path)
                            if ok:
                                question["diagram_image_path"] = diag_path
                                print(f"    → Diagram saved: {diag_name}")
                            else:
                                question["diagram_image_path"] = None
                        else:
                            question["diagram_image_path"] = None

                        # Remove raw coords from final output (keep image path instead)
                        question.pop("diagram_coords", None)

                    # ── Save progress ────────────────────────────────
                    final_dataset.extend(page_data)
                    save_dataset(OUTPUT_JSON, final_dataset)
                    processed_keys.add(resume_key)

                    print(f"    ✓ Extracted {len(page_data)} question(s)")
                    success = True
                    break  # exit retry loop

                except ValueError as e:
                    # Non-retriable: bad/empty response (safety block, etc.)
                    print(f"    [SKIP] {e}")
                    success = True   # mark as 'handled' so we don't loop
                    break
                except Exception as e:
                    print(f"    [ERROR] Attempt {attempt}/{MAX_RETRIES}: {e}")
                    if attempt < MAX_RETRIES:
                        print(f"    Retrying in {RETRY_SLEEP}s...")
                        time.sleep(RETRY_SLEEP)

                finally:
                    # Always clean up the uploaded Gemini file
                    if gemini_file is not None:
                        try:
                            client.files.delete(name=gemini_file.name)
                        except Exception:
                            pass
                        gemini_file = None

            if not success:
                print(f"    ✗ FAILED after {MAX_RETRIES} attempts — skipping {file_name}")

    print(f"\n{'='*60}")
    print(f"  Done! Total records: {len(final_dataset)}")
    print(f"  Output: {OUTPUT_JSON}")
    print(f"{'='*60}\n")


# ─────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    my_image_dir = r"D:\COMPETITION EXAMS\SSC\ExamExtractor\1-Exam-Topics"
    process_image_folders(my_image_dir)
