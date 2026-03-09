class SiddhiQuizApp {
  constructor() {
    this.allQuestions = [];
    this.filtered = [];
    this.index = 0;

    this.topicSelect = document.getElementById('topic-select');
    this.meta = document.getElementById('meta');

    document.getElementById('prev-btn').addEventListener('click', () => this.move(-1));
    document.getElementById('next-btn').addEventListener('click', () => this.move(1));
    document.getElementById('shuffle-btn').addEventListener('click', () => this.shuffleCurrent());
    document.getElementById('show-answer-btn').addEventListener('click', () => this.toggleAnswer());
    this.topicSelect.addEventListener('change', () => this.filterByTopic());

    this.load();
  }

  async load() {
    try {
      const res = await fetch('../Siddhi/ssc_math_numeric_qna_clean.json');
      this.allQuestions = await res.json();
      this.setupTopics();
      this.filterByTopic();
    } catch (error) {
      this.meta.textContent = 'Failed to load dataset.';
      document.getElementById('q-text').textContent = 'Could not load ../Siddhi/ssc_math_numeric_qna_clean.json';
      console.error(error);
    }
  }

  setupTopics() {
    const topics = [...new Set(this.allQuestions.map(q => q.topic || 'Unknown'))].sort();
    this.topicSelect.innerHTML = `<option value="ALL">All Topics (${this.allQuestions.length})</option>`;
    topics.forEach(topic => {
      const count = this.allQuestions.filter(q => (q.topic || 'Unknown') === topic).length;
      this.topicSelect.insertAdjacentHTML('beforeend', `<option value="${this.escapeHtml(topic)}">${this.escapeHtml(topic)} (${count})</option>`);
    });
  }

  filterByTopic() {
    const selected = this.topicSelect.value;
    if (selected === 'ALL') {
      this.filtered = [...this.allQuestions];
    } else {
      this.filtered = this.allQuestions.filter(q => (q.topic || 'Unknown') === selected);
    }
    this.index = 0;
    this.render();
  }

  shuffleCurrent() {
    for (let i = this.filtered.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [this.filtered[i], this.filtered[j]] = [this.filtered[j], this.filtered[i]];
    }
    this.index = 0;
    this.render();
  }

  move(step) {
    if (!this.filtered.length) return;
    this.index += step;
    if (this.index < 0) this.index = 0;
    if (this.index > this.filtered.length - 1) this.index = this.filtered.length - 1;
    this.render();
  }

  toggleAnswer() {
    document.getElementById('answer-box').classList.toggle('hidden');
    document.getElementById('explanation-box').classList.toggle('hidden');
  }

  normalizeCorrectOption(q) {
    const options = q.options || {};
    const keys = Object.keys(options).sort();
    const raw = (q.correct_option || '').toString().trim().toUpperCase();
    if (keys.includes(raw)) return raw;

    const idx = Number.parseInt(raw, 10);
    if (!Number.isNaN(idx)) {
      if (idx >= 0 && idx < keys.length) return keys[idx];
      if (idx >= 1 && idx <= keys.length) return keys[idx - 1];
    }
    return '';
  }

  render() {
    if (!this.filtered.length) {
      this.meta.textContent = 'No questions for selected topic.';
      return;
    }

    const q = this.filtered[this.index];
    const options = q.options || {};
    const correct = this.normalizeCorrectOption(q);

    this.meta.textContent = `Showing ${this.index + 1} / ${this.filtered.length}`;
    document.getElementById('q-number').textContent = `Q${q.question_number ?? '-'}`;
    document.getElementById('q-topic').textContent = q.topic || 'Unknown';
    document.getElementById('q-text').textContent = q.question_text || '-';

    const optionsBox = document.getElementById('options');
    optionsBox.innerHTML = '';
    Object.keys(options).sort().forEach(key => {
      const div = document.createElement('div');
      div.className = `option${key === correct ? ' correct' : ''}`;
      div.innerHTML = `<strong>${this.escapeHtml(key)}.</strong> ${this.escapeHtml(String(options[key]))}`;
      optionsBox.appendChild(div);
    });

    document.getElementById('answer-option').textContent = correct || 'Not available';
    document.getElementById('answer-text').textContent = correct ? (options[correct] || '') : 'Correct answer not provided in data.';
    document.getElementById('explanation-text').textContent = q.explanation || 'Explanation not available.';

    document.getElementById('answer-box').classList.add('hidden');
    document.getElementById('explanation-box').classList.add('hidden');
  }

  escapeHtml(text) {
    return String(text)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }
}

new SiddhiQuizApp();
