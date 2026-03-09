"""
Filter out entries whose `options` field is null (or empty) from ssc_math_numeric_qna.json.
- Writes entries with valid options to `ssc_math_numeric_qna_clean.json`
- Writes removed entries (options null) to `ssc_math_numeric_qna_no_options.json`
"""
import json, os

SRC = r"d:\\COMPETITION EXAMS\\SSC\\ExamExtractor\\1-Exam-Topics\\ssc_math_numeric_qna.json"
DST_CLEAN = r"d:\\COMPETITION EXAMS\\SSC\\ExamExtractor\\1-Exam-Topics\\ssc_math_numeric_qna_clean.json"
DST_REMOVED = r"d:\\COMPETITION EXAMS\\SSC\\ExamExtractor\\1-Exam-Topics\\ssc_math_numeric_qna_no_options.json"

def is_null_options(val):
    # Consider None, empty dict/list, or empty string as null
    if val is None:
        return True
    if isinstance(val, (list, dict)) and len(val) == 0:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False

def main():
    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)
    clean = []
    removed = []
    for entry in data:
        if is_null_options(entry.get("options")):
            removed.append(entry)
        else:
            clean.append(entry)
    print(f"Loaded {len(data)} entries. Keeping {len(clean)} with options, removing {len(removed)}.")
    # Write clean file
    with open(DST_CLEAN, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False)
    # Write removed file
    with open(DST_REMOVED, "w", encoding="utf-8") as f:
        json.dump(removed, f, indent=2, ensure_ascii=False)
    print(f"Saved cleaned data to {DST_CLEAN} ({os.path.getsize(DST_CLEAN)/1024:.2f} KB)")
    print(f"Saved removed entries to {DST_REMOVED} ({os.path.getsize(DST_REMOVED)/1024:.2f} KB)")

if __name__ == "__main__":
    main()
