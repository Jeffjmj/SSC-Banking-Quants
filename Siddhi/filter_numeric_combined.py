"""
Filter entries from ssc_math_combined.json where `question_number` is strictly numeric (int or digit-only string).
Output saved to `ssc_math_combined_numeric.json`.
"""
import json, os

SRC = r"d:\\COMPETITION EXAMS\\SSC\\ExamExtractor\\1-Exam-Topics\\ssc_math_combined.json"
DST = r"d:\\COMPETITION EXAMS\\SSC\\ExamExtractor\\1-Exam-Topics\\ssc_math_combined_numeric.json"

def is_strict_number(val):
    if isinstance(val, int):
        return True
    if isinstance(val, str) and val.isdigit():
        return True
    return False

def main():
    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)
    filtered = [q for q in data if is_strict_number(q.get("question_number"))]
    print(f"Loaded {len(data)} entries, keeping {len(filtered)} with numeric question_number.")
    with open(DST, "w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)
    print(f"Saved to {DST}, size: {os.path.getsize(DST)/1024:.2f} KB")

if __name__ == "__main__":
    main()
