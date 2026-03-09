/**
 * SSC Math Mastery - Application Logic
 */

class QuizApp {
    constructor() {
        this.allQuestions = [];
        this.currentSet = [];
        this.currentIndex = 0;
        this.userAnswers = {}; // index -> selectedOption
        this.topics = {};

        this.init();
    }

    async init() {
        try {
            const response = await fetch('ssc_math_numeric_qna_clean.json');
            this.allQuestions = await response.json();

            this.processMetadata();
            this.renderTopics();
            this.updateWelcomeStats();
        } catch (err) {
            console.error('Failed to load questions:', err);
            document.getElementById('q-text').innerText = 'Error loading question database. Please ensure ssc_math_numeric_qna_clean.json is present.';
        }
    }

    processMetadata() {
        this.topics = this.allQuestions.reduce((acc, q) => {
            const topic = q.topic || 'Uncategorized';
            acc[topic] = (acc[topic] || 0) + 1;
            return acc;
        }, {});
    }

    updateWelcomeStats() {
        document.getElementById('stat-total-q').innerText = this.allQuestions.length.toLocaleString();
        document.getElementById('stat-total-topics').innerText = Object.keys(this.topics).length;
        document.getElementById('stat-diagrams').innerText = this.allQuestions.filter(q => q.diagram_image_path).length;
    }

    renderTopics() {
        const list = document.getElementById('topic-list');
        list.innerHTML = '';

        // Add "All Topics"
        const allItem = this.createTopicElement('All Topics', this.allQuestions.length);
        allItem.onclick = () => this.startTopicQuiz('All Topics');
        list.appendChild(allItem);

        Object.keys(this.topics).sort().forEach(topic => {
            const item = this.createTopicElement(topic, this.topics[topic]);
            item.onclick = () => this.startTopicQuiz(topic);
            list.appendChild(item);
        });
    }

    createTopicElement(name, count) {
        const li = document.createElement('li');
        li.className = 'topic-item';
        li.innerHTML = `
            <span>${name}</span>
            <span class="topic-count">${count}</span>
        `;
        return li;
    }

    startTopicQuiz(topic) {
        if (topic === 'All Topics') {
            this.currentSet = [...this.allQuestions];
        } else {
            this.currentSet = this.allQuestions.filter(q => q.topic === topic);
        }

        this.currentIndex = 0;
        this.userAnswers = {};
        this.showQuizView();
        this.renderQuestion();
    }

    startRandomQuiz() {
        this.currentSet = [...this.allQuestions].sort(() => Math.random() - 0.5).slice(0, 20);
        this.currentIndex = 0;
        this.userAnswers = {};
        this.showQuizView();
        this.renderQuestion();
    }

    showQuizView() {
        document.getElementById('welcome-view').style.display = 'none';
        document.getElementById('quiz-view').style.display = 'block';
        document.getElementById('progress-card').style.display = 'block';
        document.getElementById('quiz-meta').style.display = 'flex';
    }

    renderQuestion() {
        const q = this.currentSet[this.currentIndex];
        const card = document.getElementById('question-card');
        const diagramSide = document.getElementById('diagram-side');
        const diagramImg = document.getElementById('q-diagram');

        // Reset state
        document.getElementById('explanation-box').style.display = 'none';

        // Header info
        document.getElementById('q-topic').innerText = q.topic || 'General Math';
        document.getElementById('q-text').innerText = q.question_text;

        // Diagram handling
        const diagramPath = this.resolveDiagramPath(q.diagram_image_path);
        if (diagramPath) {
            card.classList.add('has-diagram');
            diagramSide.style.display = 'flex';
            diagramImg.src = diagramPath;
            diagramImg.onerror = () => {
                card.classList.remove('has-diagram');
                diagramSide.style.display = 'none';
            };
        } else {
            card.classList.remove('has-diagram');
            diagramSide.style.display = 'none';
            diagramImg.removeAttribute('src');
        }

        // Options
        this.renderOptions(q);
        this.updateProgress();

        // Control buttons
        document.getElementById('prev-btn').disabled = (this.currentIndex === 0);
        document.getElementById('next-btn').innerText = (this.currentIndex === this.currentSet.length - 1) ? 'Finish Quiz' : 'Next Question';
    }

    renderOptions(q) {
        const container = document.getElementById('options-container');
        container.innerHTML = '';

        const options = this.normalizeOptions(q.options);
        if (!options) return;

        const keys = Object.keys(options).sort();

        keys.forEach(key => {
            const btn = document.createElement('button');
            btn.className = 'option-btn';

            // If already answered
            if (this.userAnswers[this.currentIndex] !== undefined) {
                const correctOption = this.normalizeCorrectOption(q.correct_option, options);
                if (correctOption && key === correctOption) btn.classList.add('correct');
                if (correctOption && key === this.userAnswers[this.currentIndex] && key !== correctOption) btn.classList.add('wrong');
                btn.disabled = true;
                this.showExplanation();
            }

            btn.innerHTML = `
                <div class="option-prefix">${key}</div>
                <div class="option-text">${options[key]}</div>
            `;

            btn.onclick = () => this.handleSelection(key);
            container.appendChild(btn);
        });
    }

    handleSelection(key) {
        if (this.userAnswers[this.currentIndex] !== undefined) return;

        this.userAnswers[this.currentIndex] = key;
        const q = this.currentSet[this.currentIndex];

        // Update UI
        this.renderOptions(q);
        this.showExplanation();
        this.updateProgress();
    }

    showExplanation() {
        const q = this.currentSet[this.currentIndex];
        const box = document.getElementById('explanation-box');
        const text = document.getElementById('explanation-text');

        if (q.explanation) {
            box.style.display = 'block';
            text.innerText = q.explanation;
        }
    }

    updateProgress() {
        const total = this.currentSet.length;
        const current = this.currentIndex + 1;
        const percent = (current / total) * 100;

        document.getElementById('progress-text').innerText = `Question ${current} of ${total}`;
        document.getElementById('progress-percent').innerText = `${Math.round(percent)}%`;
        document.getElementById('progress-bar').style.width = `${percent}%`;

        // Accuracy
        const answeredCount = Object.keys(this.userAnswers).length;
        if (answeredCount > 0) {
            let correctCount = 0;
            Object.entries(this.userAnswers).forEach(([idx, key]) => {
                const q = this.currentSet[idx];
                const options = this.normalizeOptions(q.options);
                const correctOption = this.normalizeCorrectOption(q.correct_option, options || {});
                if (correctOption && key === correctOption) correctCount++;
            });
            const accuracy = (correctCount / answeredCount) * 100;
            document.getElementById('accuracy-val').innerText = `${Math.round(accuracy)}%`;
        }
    }

    normalizeOptions(options) {
        if (!options || typeof options !== 'object') return null;

        const normalized = {};
        Object.entries(options).forEach(([k, v]) => {
            const key = String(k).trim().toUpperCase();
            const value = String(v || '').trim();
            if (key && value) {
                normalized[key] = value;
            }
        });

        return Object.keys(normalized).length ? normalized : null;
    }

    normalizeCorrectOption(correctOption, options) {
        if (!correctOption) return null;

        const normalized = String(correctOption).trim().toUpperCase();
        if (options[normalized] !== undefined) return normalized;

        const idx = Number.parseInt(normalized, 10);
        if (!Number.isNaN(idx)) {
            const keys = Object.keys(options).sort();
            if (idx >= 0 && idx < keys.length) return keys[idx];
            if (idx >= 1 && idx <= keys.length) return keys[idx - 1];
        }

        return null;
    }

    resolveDiagramPath(rawPath) {
        if (!rawPath || typeof rawPath !== 'string') return null;

        let normalized = rawPath.replaceAll('\\', '/').trim();
        if (!normalized) return null;

        const extractedDiagramsIndex = normalized.toLowerCase().indexOf('extracted_diagrams/');
        if (extractedDiagramsIndex >= 0) {
            return normalized.slice(extractedDiagramsIndex);
        }

        const filename = normalized.split('/').pop();
        return filename ? `extracted_diagrams/${filename}` : null;
    }

    nextQuestion() {
        if (this.currentIndex < this.currentSet.length - 1) {
            this.currentIndex++;
            this.renderQuestion();
        } else {
            alert('Quiz Complete! Check your final stats in the sidebar.');
            // Implementation of final results screen could go here
        }
    }

    prevQuestion() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this.renderQuestion();
        }
    }
}

// Global instance
const app = new QuizApp();
