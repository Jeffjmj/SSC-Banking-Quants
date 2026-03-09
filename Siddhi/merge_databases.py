"""
Merge ssc_math_database-1.json and ssc_math_database_images.json into:
  - ssc_math_combined.json  (all unique questions, with complemented data)
"""
import json
import sys
import os

DB1_PATH = r"d:\COMPETITION EXAMS\SSC\ExamExtractor\1-Exam-Topics\ssc_math_database-1.json"
DB2_PATH = r"d:\COMPETITION EXAMS\SSC\ExamExtractor\1-Exam-Topics\ssc_math_database_images.json"
OUT_COMBINED = r"d:\COMPETITION EXAMS\SSC\ExamExtractor\1-Exam-Topics\ssc_math_combined.json"

# All possible fields across both files (superset)
ALL_FIELDS = [
    "topic", "question_number", "question_text", "options",
    "correct_option", "explanation", "diagram_coords",
    "original_file", "diagram_image_path", "source_files"
]

def normalize(text):
    """Normalize question text for matching."""
    if not text:
        return ""
    return text.strip().lower()

def is_empty(val):
    """Check if a value is effectively empty/null."""
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    if isinstance(val, list) and len(val) == 0:
        return True
    if isinstance(val, dict) and len(val) == 0:
        return True
    return False

def merge_question(existing, new_q):
    """
    Complement existing question with data from new_q.
    For each field, if existing is empty but new_q has data, use new_q's value.
    For list fields like options, prefer the longer/more complete version.
    Track all source files.
    """
    merged = dict(existing)  # start with existing

    for key in ALL_FIELDS:
        if key == "source_files":
            continue  # handled separately
        
        existing_val = existing.get(key)
        new_val = new_q.get(key)

        if is_empty(existing_val) and not is_empty(new_val):
            # Fill missing data from the other record
            merged[key] = new_val
        elif not is_empty(existing_val) and not is_empty(new_val):
            # Both have data — pick the richer one for specific fields
            if key == "options" and isinstance(existing_val, dict) and isinstance(new_val, dict):
                # Merge option dicts, preferring non-empty values
                for opt_key in set(list(existing_val.keys()) + list(new_val.keys())):
                    if is_empty(existing_val.get(opt_key)) and not is_empty(new_val.get(opt_key)):
                        merged.setdefault("options", {})[opt_key] = new_val[opt_key]
            elif key == "explanation":
                # Keep the longer explanation
                if isinstance(new_val, str) and isinstance(existing_val, str):
                    if len(new_val) > len(existing_val):
                        merged[key] = new_val
    
    # Track source files
    src_existing = set(merged.get("source_files", []))
    if existing.get("original_file"):
        src_existing.add(existing["original_file"])
    if new_q.get("original_file"):
        src_existing.add(new_q["original_file"])
    if src_existing:
        merged["source_files"] = sorted(list(src_existing))

    return merged

def tag_source(q, source_label):
    """Add a source tag to track origin."""
    q = dict(q)
    if "source_files" not in q:
        q["source_files"] = []
    if q.get("original_file"):
        if q["original_file"] not in q["source_files"]:
            q["source_files"].append(q["original_file"])
    return q

def main():
    # Load
    with open(DB1_PATH, "r", encoding="utf-8") as f:
        db1 = json.load(f)
    with open(DB2_PATH, "r", encoding="utf-8") as f:
        db2 = json.load(f)

    print(f"Loaded db1: {len(db1)} questions")
    print(f"Loaded db2: {len(db2)} questions")

    # Build lookup: normalized_text -> merged question
    seen = {}        # normalized_text -> merged question dict
    combined = []    # final ordered list
    duplicates_merged = 0
    skipped_empty = 0

    # Process db1 first
    for q in db1:
        key = normalize(q.get("question_text"))
        if not key:
            skipped_empty += 1
            continue
        
        q_tagged = tag_source(q, "db1")
        
        if key in seen:
            # Merge with existing
            idx = seen[key]["_idx"]
            combined[idx] = merge_question(combined[idx], q_tagged)
            duplicates_merged += 1
        else:
            idx = len(combined)
            seen[key] = {"_idx": idx}
            combined.append(q_tagged)

    db1_unique = len(combined)
    print(f"After db1: {db1_unique} unique questions ({duplicates_merged} internal dups merged, {skipped_empty} empty skipped)")

    # Process db2
    db2_new = 0
    db2_merged = 0
    for q in db2:
        key = normalize(q.get("question_text"))
        if not key:
            skipped_empty += 1
            continue
        
        q_tagged = tag_source(q, "db2")

        if key in seen:
            # Merge with existing (complement data)
            idx = seen[key]["_idx"]
            combined[idx] = merge_question(combined[idx], q_tagged)
            db2_merged += 1
        else:
            idx = len(combined)
            seen[key] = {"_idx": idx}
            combined.append(q_tagged)
            db2_new += 1

    print(f"After db2: {db2_new} new unique questions added, {db2_merged} merged with existing")
    print(f"Total empty question_text skipped: {skipped_empty}")

    # Clean up: ensure all records have all fields
    for q in combined:
        for field in ALL_FIELDS:
            if field not in q:
                q[field] = None

    print(f"\n{'='*50}")
    print(f"COMBINED FILE: {len(combined)} unique questions")
    print(f"{'='*50}")

    # Count how many have complemented data (data from both sources)
    complemented = sum(1 for q in combined if q.get("source_files") and len(q["source_files"]) > 1)
    has_diagram_path = sum(1 for q in combined if not is_empty(q.get("diagram_image_path")))
    has_diagram_coords = sum(1 for q in combined if not is_empty(q.get("diagram_coords")))
    has_explanation = sum(1 for q in combined if not is_empty(q.get("explanation")))
    has_options = sum(1 for q in combined if not is_empty(q.get("options")))

    print(f"  With complemented data (multi-source): {complemented}")
    print(f"  With diagram_image_path              : {has_diagram_path}")
    print(f"  With diagram_coords                  : {has_diagram_coords}")
    print(f"  With explanation                     : {has_explanation}")
    print(f"  With options                         : {has_options}")

    # Save combined
    with open(OUT_COMBINED, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {OUT_COMBINED}")
    print(f"File size: {os.path.getsize(OUT_COMBINED) / (1024*1024):.2f} MB")

if __name__ == "__main__":
    main()
