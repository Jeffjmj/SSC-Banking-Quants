import json
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

with open(r'd:\COMPETITION EXAMS\SSC\ExamExtractor\1-Exam-Topics\ssc_math_numeric_qna_clean.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

def has(val):
    if val is None: return False
    if isinstance(val, str) and val.strip() == '': return False
    if isinstance(val, (list, dict)) and len(val) == 0: return False
    return True

topics = defaultdict(lambda: {'total':0, 'with_answer':0, 'with_expl':0, 'with_diag':0})

for q in data:
    t = q.get('topic','unknown')
    topics[t]['total'] += 1
    if has(q.get('correct_option')): topics[t]['with_answer'] += 1
    if has(q.get('explanation')):    topics[t]['with_expl'] += 1
    if has(q.get('diagram_image_path')): topics[t]['with_diag'] += 1

print(f'{"Topic":<45} {"Total":>6} {"Ans":>5} {"Expl":>5} {"Diag":>5}')
print('-'*72)
for t, v in sorted(topics.items()):
    print(f'{t:<45} {v["total"]:>6} {v["with_answer"]:>5} {v["with_expl"]:>5} {v["with_diag"]:>5}')
print('-'*72)

totals = dict(
    total=sum(v['total'] for v in topics.values()),
    with_answer=sum(v['with_answer'] for v in topics.values()),
    with_expl=sum(v['with_expl'] for v in topics.values()),
    with_diag=sum(v['with_diag'] for v in topics.values()),
)
print(f'{"TOTAL":<45} {totals["total"]:>6} {totals["with_answer"]:>5} {totals["with_expl"]:>5} {totals["with_diag"]:>5}')
