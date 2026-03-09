"""
Build a meaningful question-answer dataset by compiling:
  - ssc_math_database-1.json
  - ssc_math_database_images.json

Output:
  - ssc_math_compiled_qna.json

The compiler uses two stages:
1) Within each source file, pair question rows with answer rows using
   topic + numeric question id + record order.
2) Merge the two source outputs by normalized (topic, question_text).
"""

import json
import os
import re
from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB1_PATH = os.path.join(BASE_DIR, "ssc_math_database-1.json")
DB2_PATH = os.path.join(BASE_DIR, "ssc_math_database_images.json")
OUT_PATH = os.path.join(BASE_DIR, "ssc_math_compiled_qna.json")


ANSWER_STYLE_QN_RE = re.compile(r"^\s*\d+\s*\.?\s*\(\s*([A-Da-d])\s*\)")


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    if isinstance(value, dict) and len(value) == 0:
        return True
    return False


def has_text(value: Any) -> bool:
    return not is_empty(value)


def normalized_text(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def extract_base_number(question_number: Any) -> Optional[int]:
    if question_number is None:
        return None
    match = re.search(r"\d+", str(question_number))
    return int(match.group()) if match else None


def option_from_question_number(question_number: Any) -> str:
    if question_number is None:
        return ""
    match = ANSWER_STYLE_QN_RE.search(str(question_number))
    if not match:
        return ""
    return match.group(1).upper()


def non_empty_option_map(options: Any) -> bool:
    if not isinstance(options, dict):
        return False
    for value in options.values():
        if has_text(value):
            return True
    return False


def token_set(text: Any) -> set:
    norm = normalized_text(text)
    if not norm:
        return set()
    norm = re.sub(r"(cosec|sec|sin|cos|tan|cot)([a-z])", r"\1 \2", norm)
    return set(re.findall(r"[a-z0-9]+", norm))


def text_similarity(a: Any, b: Any) -> float:
    ta = token_set(a)
    tb = token_set(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta.intersection(tb))
    union = len(ta.union(tb))
    if union == 0:
        return 0.0
    jaccard = inter / union
    overlap = inter / min(len(ta), len(tb))
    return max(jaccard, overlap)


def answer_signal(row: Dict[str, Any]) -> bool:
    if has_text(row.get("correct_option")):
        return True
    if has_text(row.get("explanation")):
        return True
    if option_from_question_number(row.get("question_number")):
        return True
    return False


def make_candidate(
    row: Dict[str, Any],
    source_name: str,
    order_index: int,
) -> Dict[str, Any]:
    qn_opt = option_from_question_number(row.get("question_number"))
    correct_opt = row.get("correct_option")
    if is_empty(correct_opt) and qn_opt:
        correct_opt = qn_opt

    source_files = []
    if has_text(row.get("original_file")):
        source_files.append(row.get("original_file"))

    q_text_raw = str(row.get("question_text") or "")
    q_text_norm = normalized_text(q_text_raw)
    question_like = (
        non_empty_option_map(row.get("options"))
        or "?" in q_text_raw
        or ":" in q_text_raw
        or bool(re.search(r"\b(if|find|what|which|evaluate|simplify|prove|show|value)\b", q_text_norm))
        or len(q_text_norm) >= 40
    )

    return {
        "topic": row.get("topic"),
        "question_number": row.get("question_number"),
        "base_number": extract_base_number(row.get("question_number")),
        "question_text": row.get("question_text"),
        "options": row.get("options"),
        "correct_option": correct_opt,
        "explanation": row.get("explanation"),
        "diagram_coords": row.get("diagram_coords"),
        "original_file": row.get("original_file"),
        "diagram_image_path": row.get("diagram_image_path"),
        "source_files": source_files,
        "source_databases": [source_name],
        "_question_like": question_like,
        "_source": source_name,
        "_order": order_index,
    }


def merge_options(existing: Any, new_val: Any) -> Any:
    if is_empty(existing):
        return deepcopy(new_val)
    if is_empty(new_val):
        return existing
    if not isinstance(existing, dict) or not isinstance(new_val, dict):
        return existing

    merged = deepcopy(existing)
    for key, value in new_val.items():
        if key not in merged or is_empty(merged.get(key)):
            merged[key] = value
    return merged


def merge_candidate_fields(
    target: Dict[str, Any],
    source: Dict[str, Any],
    prefer_longer_text: bool = True,
) -> None:
    if is_empty(target.get("question_number")) and has_text(source.get("question_number")):
        target["question_number"] = source.get("question_number")

    if is_empty(target.get("question_text")) and has_text(source.get("question_text")):
        target["question_text"] = source.get("question_text")
    elif (
        prefer_longer_text
        and has_text(target.get("question_text"))
        and has_text(source.get("question_text"))
        and len(str(source.get("question_text"))) > len(str(target.get("question_text")))
    ):
        target["question_text"] = source.get("question_text")

    target["options"] = merge_options(target.get("options"), source.get("options"))

    if is_empty(target.get("correct_option")) and has_text(source.get("correct_option")):
        target["correct_option"] = str(source.get("correct_option")).strip().upper()

    if is_empty(target.get("explanation")) and has_text(source.get("explanation")):
        target["explanation"] = source.get("explanation")
    elif (
        has_text(target.get("explanation"))
        and has_text(source.get("explanation"))
        and len(str(source.get("explanation"))) > len(str(target.get("explanation")))
    ):
        target["explanation"] = source.get("explanation")

    if is_empty(target.get("diagram_coords")) and not is_empty(source.get("diagram_coords")):
        target["diagram_coords"] = source.get("diagram_coords")

    if is_empty(target.get("original_file")) and has_text(source.get("original_file")):
        target["original_file"] = source.get("original_file")

    if is_empty(target.get("diagram_image_path")) and has_text(source.get("diagram_image_path")):
        target["diagram_image_path"] = source.get("diagram_image_path")

    for db in source.get("source_databases", []):
        if db not in target["source_databases"]:
            target["source_databases"].append(db)

    for sf in source.get("source_files", []):
        if sf and sf not in target["source_files"]:
            target["source_files"].append(sf)


def compile_single_source(rows: List[Dict[str, Any]], source_name: str) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    candidates: List[Dict[str, Any]] = []
    answer_rows: List[Dict[str, Any]] = []

    for idx, row in enumerate(rows):
        topic = row.get("topic")
        q_text = row.get("question_text")
        has_q_text = has_text(q_text)
        has_answer = answer_signal(row)
        answer_style_qn = bool(ANSWER_STYLE_QN_RE.search(str(row.get("question_number", ""))))

        if has_q_text and not (answer_style_qn and has_answer):
            candidates.append(make_candidate(row, source_name, idx))
            continue

        if has_answer:
            answer_rows.append(
                {
                    "topic": topic,
                    "question_number": row.get("question_number"),
                    "base_number": extract_base_number(row.get("question_number")),
                    "question_text": q_text,
                    "correct_option": (
                        str(row.get("correct_option")).strip().upper()
                        if has_text(row.get("correct_option"))
                        else option_from_question_number(row.get("question_number"))
                    ),
                    "explanation": row.get("explanation"),
                    "diagram_coords": row.get("diagram_coords"),
                    "original_file": row.get("original_file"),
                    "diagram_image_path": row.get("diagram_image_path"),
                    "_source": source_name,
                    "_order": idx,
                }
            )

    key_to_candidate_idxs: Dict[Tuple[str, int], List[int]] = defaultdict(list)
    for c_idx, cand in enumerate(candidates):
        if cand.get("topic") is None or cand.get("base_number") is None:
            continue
        key_to_candidate_idxs[(cand["topic"], cand["base_number"])].append(c_idx)

    linked_answers = 0
    fallback_created = 0

    for ans in answer_rows:
        topic = ans.get("topic")
        base_num = ans.get("base_number")
        if topic is None or base_num is None:
            continue

        possible = key_to_candidate_idxs.get((topic, base_num), [])
        target_idx: Optional[int] = None

        if possible:
            prior = [i for i in possible if candidates[i]["_order"] < ans["_order"]]
            candidate_pool = prior if prior else possible
            ans_text = ans.get("question_text")

            # Prefer semantic matching when answer row includes a question restatement.
            if has_text(ans_text):
                needs_fill_pool = [
                    i
                    for i in candidate_pool
                    if is_empty(candidates[i].get("correct_option"))
                    or is_empty(candidates[i].get("explanation"))
                ]
                score_pool = needs_fill_pool if needs_fill_pool else candidate_pool
                question_like_pool = [i for i in score_pool if candidates[i].get("_question_like")]
                if question_like_pool:
                    score_pool = question_like_pool

                scored = []
                for i in score_pool:
                    cand = candidates[i]
                    sim = text_similarity(ans_text, cand.get("question_text"))
                    score = sim
                    scored.append((score, sim, i))

                scored.sort(reverse=True, key=lambda x: x[0])
                if scored and scored[0][1] >= 0.18:
                    target_idx = scored[0][2]

            # If no text match, use order proximity only for answer-only rows.
            if target_idx is None and not has_text(ans_text):
                if prior:
                    need_fill = [
                        i
                        for i in prior
                        if is_empty(candidates[i].get("correct_option"))
                        or is_empty(candidates[i].get("explanation"))
                    ]
                    if need_fill:
                        target_idx = max(need_fill, key=lambda i: candidates[i]["_order"])
                    else:
                        target_idx = max(prior, key=lambda i: candidates[i]["_order"])
                else:
                    need_fill = [
                        i
                        for i in possible
                        if is_empty(candidates[i].get("correct_option"))
                        or is_empty(candidates[i].get("explanation"))
                    ]
                    if need_fill:
                        target_idx = min(need_fill, key=lambda i: candidates[i]["_order"])

        if target_idx is not None:
            if is_empty(candidates[target_idx].get("correct_option")) and has_text(ans.get("correct_option")):
                candidates[target_idx]["correct_option"] = ans.get("correct_option")

            if is_empty(candidates[target_idx].get("explanation")) and has_text(ans.get("explanation")):
                candidates[target_idx]["explanation"] = ans.get("explanation")

            if is_empty(candidates[target_idx].get("diagram_coords")) and not is_empty(ans.get("diagram_coords")):
                candidates[target_idx]["diagram_coords"] = ans.get("diagram_coords")

            if is_empty(candidates[target_idx].get("original_file")) and has_text(ans.get("original_file")):
                candidates[target_idx]["original_file"] = ans.get("original_file")

            if is_empty(candidates[target_idx].get("diagram_image_path")) and has_text(ans.get("diagram_image_path")):
                candidates[target_idx]["diagram_image_path"] = ans.get("diagram_image_path")

            if has_text(ans.get("original_file")) and ans.get("original_file") not in candidates[target_idx]["source_files"]:
                candidates[target_idx]["source_files"].append(ans.get("original_file"))

            linked_answers += 1
        else:
            # If there is no question row to attach to, keep answer row as its own QA row.
            if has_text(ans.get("question_text")):
                fallback = {
                    "topic": ans.get("topic"),
                    "question_number": ans.get("question_number"),
                    "base_number": ans.get("base_number"),
                    "question_text": ans.get("question_text"),
                    "options": None,
                    "correct_option": ans.get("correct_option"),
                    "explanation": ans.get("explanation"),
                    "diagram_coords": ans.get("diagram_coords"),
                    "original_file": ans.get("original_file"),
                    "diagram_image_path": ans.get("diagram_image_path"),
                    "source_files": [ans.get("original_file")] if has_text(ans.get("original_file")) else [],
                    "source_databases": [source_name],
                    "_source": source_name,
                    "_order": ans.get("_order"),
                }
                candidates.append(fallback)
                c_idx = len(candidates) - 1
                if fallback.get("topic") is not None and fallback.get("base_number") is not None:
                    key_to_candidate_idxs[(fallback["topic"], fallback["base_number"])].append(c_idx)
                fallback_created += 1

    stats = {
        "input_rows": len(rows),
        "question_candidates": len(candidates),
        "answer_rows": len(answer_rows),
        "answers_linked": linked_answers,
        "answer_fallback_rows": fallback_created,
    }
    return candidates, stats


def merge_sources(
    left_rows: List[Dict[str, Any]],
    right_rows: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    merged: List[Dict[str, Any]] = []
    key_map: Dict[Tuple[str, str], int] = {}
    added = 0
    merged_count = 0

    for row in left_rows + right_rows:
        topic = row.get("topic")
        text_key = normalized_text(row.get("question_text"))

        if is_empty(topic) or text_key == "":
            # Keep unkeyable rows as standalone if they have any usable content.
            if has_text(row.get("question_text")) or has_text(row.get("explanation")):
                clean = deepcopy(row)
                merged.append(clean)
                added += 1
            continue

        key = (str(topic), text_key)
        if key not in key_map:
            clean = deepcopy(row)
            key_map[key] = len(merged)
            merged.append(clean)
            added += 1
        else:
            target_idx = key_map[key]
            merge_candidate_fields(merged[target_idx], row)
            merged_count += 1

    # Second pass: attach remaining answer-style rows (e.g., "5.(c)") to
    # same topic/base-number question rows when text overlap is strong.
    grouped: Dict[Tuple[str, int], List[int]] = defaultdict(list)
    for idx, row in enumerate(merged):
        topic = row.get("topic")
        base = row.get("base_number")
        if is_empty(topic) or base is None:
            continue
        grouped[(str(topic), int(base))].append(idx)

    remove_idxs = set()
    answer_style_merged = 0

    for (_, _), idxs in grouped.items():
        donors = [
            i
            for i in idxs
            if bool(ANSWER_STYLE_QN_RE.search(str(merged[i].get("question_number", ""))))
            and (
                has_text(merged[i].get("correct_option"))
                or has_text(merged[i].get("explanation"))
            )
        ]
        if not donors:
            continue

        targets = [
            i
            for i in idxs
            if i not in donors
            and (
                is_empty(merged[i].get("correct_option"))
                or is_empty(merged[i].get("explanation"))
            )
        ]
        if not targets:
            continue

        for d_idx in donors:
            donor = merged[d_idx]
            best_target = None
            best_score = 0.0
            for t_idx in targets:
                target = merged[t_idx]
                sim = text_similarity(donor.get("question_text"), target.get("question_text"))
                if sim > best_score:
                    best_score = sim
                    best_target = t_idx

            if best_target is not None and best_score >= 0.30:
                merge_candidate_fields(merged[best_target], donor, prefer_longer_text=False)
                remove_idxs.add(d_idx)
                answer_style_merged += 1

    if remove_idxs:
        merged = [row for i, row in enumerate(merged) if i not in remove_idxs]

    for row in merged:
        row.pop("_source", None)
        row.pop("_order", None)
        row.pop("_question_like", None)
        row.pop("base_number", None)

        if not row.get("source_databases"):
            row["source_databases"] = []
        if not row.get("source_files"):
            row["source_files"] = []

    stats = {
        "final_rows": len(merged),
        "rows_added": added,
        "rows_merged_by_text": merged_count,
        "answer_style_rows_merged": answer_style_merged,
    }
    return merged, stats


def load_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array.")
    return data


def main() -> None:
    db1 = load_json(DB1_PATH)
    db2 = load_json(DB2_PATH)

    compiled_db1, stats_db1 = compile_single_source(db1, "db1")
    compiled_db2, stats_db2 = compile_single_source(db2, "db2")

    final_rows, merge_stats = merge_sources(compiled_db1, compiled_db2)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_rows, f, indent=2, ensure_ascii=False)

    print(f"Loaded db1 rows: {len(db1)}")
    print(f"Loaded db2 rows: {len(db2)}")
    print(
        "db1 compile stats: "
        f"candidates={stats_db1['question_candidates']}, "
        f"answer_rows={stats_db1['answer_rows']}, "
        f"answers_linked={stats_db1['answers_linked']}, "
        f"fallback={stats_db1['answer_fallback_rows']}"
    )
    print(
        "db2 compile stats: "
        f"candidates={stats_db2['question_candidates']}, "
        f"answer_rows={stats_db2['answer_rows']}, "
        f"answers_linked={stats_db2['answers_linked']}, "
        f"fallback={stats_db2['answer_fallback_rows']}"
    )
    print(
        "merge stats: "
        f"final_rows={merge_stats['final_rows']}, "
        f"added={merge_stats['rows_added']}, "
        f"merged_by_text={merge_stats['rows_merged_by_text']}, "
        f"answer_style_merged={merge_stats['answer_style_rows_merged']}"
    )
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
