"""
enhance_explanations.py

Generate compact explanations for SSC math questions.
"""
import json, os

SRC = r"d:\\COMPETITION EXAMS\\SSC\\ExamExtractor\\1-Exam-Topics\\ssc_math_combined.json"
DST = r"d:\\COMPETITION EXAMS\\SSC\\ExamExtractor\\1-Exam-Topics\\ssc_math_combined_enhanced.json"
MAX_LEN = 200

def compact(text):
    if not text:
        return ""
    txt = " ".join(text.split())
    return txt[:MAX_LEN]

def get_option(entry):
    corr = entry.get("correct_option")
    opts = entry.get("options")
    if not opts:
        return None
    if isinstance(opts, dict):
        if isinstance(corr, str) and corr in opts:
            return opts[corr]
        if isinstance(corr, int) and corr < len(opts):
            return list(opts.values())[corr]
    if isinstance(opts, list):
        if isinstance(corr, int) and 0 <= corr < len(opts):
            return opts[corr]
        if isinstance(corr, str) and corr.isdigit():
            idx = int(corr)
            if 0 <= idx < len(opts):
                return opts[idx]
    return None

def build(entry):
    expl = entry.get("explanation")
    if expl and isinstance(expl, str) and expl.strip():
        return compact(expl)
    opt = get_option(entry)
    answer = f"Answer: {opt}." if opt else "Answer not provided."
    qtxt = entry.get("question_text", "").strip()
    reason = qtxt.split('. ')[0]
    base = f"{answer} {reason}."
    if entry.get("diagram_image_path") or entry.get("diagram_coords"):
        base += " Refer to the diagram for visual aid."
    return compact(base)

def main():
    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)
    out = []
    for e in data:
        ne = dict(e)
        ne["explanation"] = build(e)
        out.append(ne)
    with open(DST, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"Processed {len(data)} entries. Saved to {DST}")
    missing = sum(1 for e in out if not e.get("explanation"))
    print(f"Entries without explanation after processing: {missing}")

if __name__ == "__main__":
    main()
