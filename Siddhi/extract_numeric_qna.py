"""
Extract entries with a purely numeric `question_number` from ssc_math_compiled_qna.json
and write them to ssc_math_numeric_qna.json.
"""
import json, os, sys

SRC = r"d:\COMPETITION EXAMS\SSC\ExamExtractor\1-Exam-Topics\ssc_math_compiled_qna.json"
DST = r"d:\COMPETITION EXAMS\SSC\ExamExtractor\1-Exam-Topics\ssc_math_numeric_qna.json"

def is_strict_number(val):
    """Return True if val is an int or a string consisting only of digits."""
    if isinstance(val, int):
        return True
    if isinstance(val, str) and val.isdigit():
        return True
    return False

def main():
    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Expect a list of question objects
    filtered = [q for q in data if is_strict_number(q.get("question_number"))]
    print(f"Loaded {len(data)} entries, keeping {len(filtered)} with numeric question_number.")
    with open(DST, "w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)
    print(f"Saved to {DST}, size: {os.path.getsize(DST)/1024:.2f} KB")

if __name__ == "__main__":
    main()
