/**
 * AI Interview Web Client
 *
 * 与后端 API 交互，支持面试、训练、知识库等功能
 */

// API 服务地址
const API_BASE = window.API_BASE || 'http://127.0.0.1:8000';

// State
let interviewSessionId = null;
let trainingSessionId = null;
let currentQuestion = null;

// Initialize
async function init() {
    setupTabs();
    await checkApiStatus();
}

// Tab Navigation
function setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            switchTab(tabId);
        });
    });

    // Setup event listeners
    setupInterviewListeners();
    setupTrainingListeners();
    setupKnowledgeListeners();
}

function switchTab(tabId) {
    // Update buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === tabId);
    });
}

// API Status Check
async function checkApiStatus() {
    const statusEl = document.getElementById('api-status-display');
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            const data = await response.json();
            statusEl.innerHTML = `<span class="success">✓ 服务正常</span><br><small>${data.service} v${data.version || '0.1.0'}</small>`;
            updateStatus('connected', 'API 已连接');
        } else {
            statusEl.innerHTML = `<span class="error">✗ 服务异常</span>`;
            updateStatus('disconnected', 'API 连接失败');
        }
    } catch (error) {
        statusEl.innerHTML = `<span class="error">✗ 服务未运行</span>`;
        updateStatus('disconnected', 'API 未运行');
    }
}

function updateStatus(type, text) {
    const statusEl = document.getElementById('status');
    statusEl.className = `status ${type}`;
    statusEl.textContent = text;
}

// =============================================================================
// Interview Functions
// =============================================================================

function setupInterviewListeners() {
    document.getElementById('interview-start-btn').addEventListener('click', startInterview);
    document.getElementById('interview-submit-btn').addEventListener('click', submitInterviewAnswer);
    document.getElementById('interview-next-btn').addEventListener('click', skipInterviewAnswer);
    document.getElementById('interview-next-question-btn').addEventListener('click', getNextQuestion);
    document.getElementById('interview-end-btn').addEventListener('click', endInterview);
}

async function startInterview() {
    const sessionId = document.getElementById('interview-session-id').value || crypto.randomUUID();
    const resumeContent = document.getElementById('interview-resume-content').value.trim();
    const mode = document.getElementById('interview-mode').value;
    const feedbackMode = document.getElementById('interview-feedback-mode').value;

    interviewSessionId = sessionId;

    const btn = document.getElementById('interview-start-btn');
    btn.disabled = true;
    btn.textContent = '启动中...';

    try {
        const requestBody = {
            session_id: sessionId,
            interview_mode: mode,
            feedback_mode: feedbackMode,
            max_series: 5,
        };

        // 如果有简历内容，先构建知识库
        if (resumeContent) {
            const buildResponse = await fetch(`${API_BASE}/knowledge/build`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    knowledge_base_id: sessionId,
                    source_type: 'resume',
                    content: resumeContent,
                }),
            });

            if (!buildResponse.ok) {
                throw new Error('简历知识库构建失败');
            }

            requestBody.resume_id = sessionId;
        }

        const response = await fetch(`${API_BASE}/interview/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody),
        });

        if (!response.ok) throw new Error('启动失败');

        const data = await response.json();

        // Show active interview UI
        document.querySelector('#interview .card:nth-child(2)').classList.add('hidden');
        document.getElementById('interview-active').classList.remove('hidden');
        document.getElementById('interview-session-info').innerHTML = `
            <p><strong>Session ID:</strong> ${sessionId}</p>
            <p><strong>模式:</strong> ${mode === 'free' ? '自由面试' : '专项训练'}</p>
            <p><strong>反馈模式:</strong> ${feedbackMode === 'realtime' ? '实时反馈' : '录播模式'}</p>
        `;

        if (data.first_question) {
            displayInterviewQuestion(data.first_question);
        }

        updateStatus('connected', '面试进行中');

    } catch (error) {
        alert('启动面试失败: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '开始面试';
    }
}

function displayInterviewQuestion(question) {
    currentQuestion = question;
    const container = document.getElementById('interview-question');
    container.innerHTML = `
        <div class="question-text">
            <p><strong>问题 ${question.series || 1}.${question.number || 1}:</strong></p>
            <p style="margin-top: 10px;">${question.content}</p>
        </div>
    `;
    document.getElementById('interview-answer-section').classList.remove('hidden');
    document.getElementById('interview-answer-input').value = '';
    document.getElementById('interview-answer-input').focus();
    // 注意：不清空反馈内容，让反馈框一直显示
}

function showInterviewFeedback(feedbackData) {
    const container = document.getElementById('interview-feedback-container');
    const thinkingEl = document.getElementById('interview-thinking');
    const feedbackEl = document.getElementById('interview-feedback');

    if (!container || !thinkingEl || !feedbackEl) {
        return;
    }

    // 显示容器
    container.classList.remove('hidden');

    // 解析反馈内容，提取思考过程
    let displayContent = feedbackData.feedback_content || '';
    let thinkingContent = '';
    let answerContent = displayContent;

    // 提取 【思考过程】...【回答】... 格式
    const thinkMatch = displayContent.match(/【思考过程】([\s\S]*?)(?=【回答】)/);
    if (thinkMatch) {
        thinkingContent = thinkMatch[1].trim();
        answerContent = displayContent.replace(/[\s\S]*?【回答】/, '').trim();
    }

    // 设置内容
    thinkingEl.textContent = thinkingContent || '（无思考过程）';
    feedbackEl.textContent = answerContent || '（无反馈内容）';

    // 设置样式类
    feedbackEl.classList.remove('positive', 'negative', 'guidance');
    if (feedbackData.feedback_type === 'correction') {
        feedbackEl.classList.add('negative');
    } else if (feedbackData.feedback_type === 'guidance') {
        feedbackEl.classList.add('guidance');
    } else if (feedbackData.is_correct) {
        feedbackEl.classList.add('positive');
    } else {
        feedbackEl.classList.add('negative');
    }
}

async function getNextQuestion() {
    if (!interviewSessionId) return;

    const btn = document.getElementById('interview-next-question-btn');
    btn.disabled = true;
    btn.textContent = '获取中...';

    try {
        // 使用流式 SSE 获取问题
        const response = await fetch(`${API_BASE}/interview/question?session_id=${interviewSessionId}&stream=true`);
        if (!response.ok) throw new Error('获取问题失败');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let questionContent = '';
        let questionId = '';
        let questionSeries = 1;
        let questionNumber = 1;
        let eventType = '';
        let dataBuffer = '';

        // 设置问题显示容器，带光标
        const container = document.getElementById('interview-question');
        container.innerHTML = `
            <div class="question-text">
                <p><strong>问题 <span id="q-series">1</span>.<span id="q-number">1</span>:</strong></p>
                <p id="q-content" style="margin-top: 10px;"><span id="typewriter-cursor" class="blinking-cursor">|</span></p>
            </div>
        `;
        document.getElementById('interview-answer-section').classList.add('hidden');
        // 清空反馈内容
        const thinkingEl = document.getElementById('interview-thinking');
        const feedbackEl = document.getElementById('interview-feedback');
        if (thinkingEl) thinkingEl.textContent = '等待提交回答...';
        if (feedbackEl) feedbackEl.textContent = '等待提交回答...';

        const qContent = document.getElementById('q-content');
        const qSeries = document.getElementById('q-series');
        const qNumber = document.getElementById('q-number');
        const cursor = document.getElementById('typewriter-cursor');

        // 逐行读取 SSE 流
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('event:')) {
                    eventType = line.slice(6).trim();
                } else if (line.startsWith('data:')) {
                    dataBuffer = line.slice(5).trim();
                } else if (line === '') {
                    // 空行表示事件结束
                    if (eventType && dataBuffer) {
                        try {
                            const data = JSON.parse(dataBuffer);

                            if (eventType === 'question_start') {
                                questionId = data.question_id;
                                questionSeries = data.series;
                                questionNumber = data.number;
                                qSeries.textContent = questionSeries;
                                qNumber.textContent = questionNumber;
                                currentQuestion = { question_id: questionId, series: questionSeries, number: questionNumber, content: '' };

                            } else if (eventType === 'token') {
                                const token = data.content || '';
                                questionContent += token;
                                currentQuestion = { question_id: questionId, series: questionSeries, number: questionNumber, content: questionContent };
                                // 在光标前插入 token
                                cursor.insertAdjacentText('beforebegin', token);

                            } else if (eventType === 'question_end') {
                                // 问题完整，可以启用输入框
                                currentQuestion = { question_id: questionId, series: questionSeries, number: questionNumber, content: questionContent };

                            } else if (eventType === 'feedback') {
                                // 待发送的反馈
                                showInterviewFeedback(data);

                            } else if (eventType === 'end') {
                                // 流结束
                                if (cursor) cursor.remove();
                                document.getElementById('interview-answer-section').classList.remove('hidden');
                                document.getElementById('interview-answer-input').focus();
                            }
                        } catch (e) {
                            console.error('SSE parse error:', e);
                        }
                        eventType = '';
                        dataBuffer = '';
                    }
                }
            }
        }

        // 确保光标被移除
        if (cursor && cursor.parentNode) {
            cursor.remove();
        }

    } catch (error) {
        console.error('Error:', error);
        // 失败时回退到非流式
        const startResponse = await fetch(`${API_BASE}/interview/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: interviewSessionId,
                resume_id: interviewSessionId,
                interview_mode: 'free',
                feedback_mode: 'recorded',
            }),
        });

        if (startResponse.ok) {
            const data = await startResponse.json();
            if (data.first_question) {
                displayInterviewQuestion(data.first_question);
            }
        }
    } finally {
        btn.disabled = false;
        btn.textContent = '下一题';
    }
}

async function submitInterviewAnswer() {
    const answer = document.getElementById('interview-answer-input').value.trim();
    if (!answer) {
        alert('请输入回答');
        return;
    }
    if (!currentQuestion) return;

    const btn = document.getElementById('interview-submit-btn');
    btn.disabled = true;

    try {
        // 使用SSE流式获取追问
        const response = await fetch(`${API_BASE}/interview/answer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: interviewSessionId,
                question_id: currentQuestion.question_id || 'unknown',
                user_answer: answer,
            }),
        });

        if (!response.ok) throw new Error('提交失败');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let questionContent = '';
        let questionId = '';
        let questionSeries = currentQuestion.series || 1;
        let questionNumber = currentQuestion.number + 1;
        let eventType = '';
        let dataBuffer = '';

        // 设置问题显示容器，带光标（复用getNextQuestion的UI模式）
        const container = document.getElementById('interview-question');
        container.innerHTML = `
            <div class="question-text">
                <p><strong>问题 <span id="q-series">${questionSeries}</span>.<span id="q-number">${questionNumber}</span>:</strong></p>
                <p id="q-content" style="margin-top: 10px;"><span id="typewriter-cursor" class="blinking-cursor">|</span></p>
            </div>
        `;
        document.getElementById('interview-answer-section').classList.add('hidden');

        const qContent = document.getElementById('q-content');
        const qSeries = document.getElementById('q-series');
        const qNumber = document.getElementById('q-number');
        const cursor = document.getElementById('typewriter-cursor');

        // 逐行读取SSE流
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('event:')) {
                    eventType = line.slice(6).trim();
                } else if (line.startsWith('data:')) {
                    dataBuffer = line.slice(5).trim();
                } else if (line === '') {
                    // 空行表示事件结束
                    if (eventType && dataBuffer) {
                        try {
                            const data = JSON.parse(dataBuffer);

                            if (eventType === 'evaluation') {
                                // 评估结果，可以用来更新UI或显示评分
                                console.log('[submit] evaluation:', data);

                            } else if (eventType === 'question_start') {
                                questionId = data.question_id;
                                questionSeries = data.series || questionSeries;
                                questionNumber = data.number || questionNumber;
                                qSeries.textContent = questionSeries;
                                qNumber.textContent = questionNumber;
                                currentQuestion = { question_id: questionId, series: questionSeries, number: questionNumber, content: '' };

                            } else if (eventType === 'token') {
                                const token = data.content || '';
                                questionContent += token;
                                currentQuestion = { question_id: questionId, series: questionSeries, number: questionNumber, content: questionContent };
                                cursor.insertAdjacentText('beforebegin', token);

                            } else if (eventType === 'question_end') {
                                currentQuestion = { question_id: questionId, series: questionSeries, number: questionNumber, content: questionContent };

                            } else if (eventType === 'feedback') {
                                // 待发送的反馈（来自pending_feedbacks）
                                showInterviewFeedback(data);

                            } else if (eventType === 'end') {
                                // 流结束
                                if (cursor) cursor.remove();
                                if (data.should_continue) {
                                    document.getElementById('interview-answer-section').classList.remove('hidden');
                                    document.getElementById('interview-answer-input').focus();
                                } else {
                                    // 面试结束
                                    document.getElementById('interview-active').classList.add('hidden');
                                    document.getElementById('interview-result').classList.remove('hidden');
                                }
                            }
                        } catch (e) {
                            console.error('SSE parse error:', e);
                        }
                        eventType = '';
                        dataBuffer = '';
                    }
                }
            }
        }

        // 确保光标被移除
        if (cursor && cursor.parentNode) {
            cursor.remove();
        }

    } catch (error) {
        alert('提交失败: ' + error.message);
    } finally {
        btn.disabled = false;
    }
}

function skipInterviewAnswer() {
    document.getElementById('interview-answer-input').value = '';
}

async function endInterview() {
    if (!interviewSessionId) return;

    const btn = document.getElementById('interview-end-btn');
    btn.disabled = true;
    btn.textContent = '结束中...';

    try {
        const response = await fetch(`${API_BASE}/interview/end?session_id=${interviewSessionId}`, {
            method: 'POST',
        });

        if (!response.ok) throw new Error('结束失败');

        const data = await response.json();

        // Show results
        document.getElementById('interview-active').classList.add('hidden');
        document.getElementById('interview-result').classList.remove('hidden');

        const resultEl = document.getElementById('interview-result-display');
        resultEl.innerHTML = `
            <div class="result-item">
                <div class="result-label">会话 ID</div>
                <div class="result-value">${data.session_id}</div>
            </div>
            <div class="result-item">
                <div class="result-label">状态</div>
                <div class="result-value">${data.status}</div>
            </div>
            <div class="result-item">
                <div class="result-label">问题数量</div>
                <div class="result-value">${data.total_questions || 0}</div>
            </div>
            <div class="result-item">
                <div class="result-label">系列数</div>
                <div class="result-value">${data.total_series || 0}</div>
            </div>
        `;

        if (data.final_feedback) {
            const ff = data.final_feedback;
            let ffHtml = `<h4>最终反馈</h4>`;
            if (ff.overall_score !== undefined) {
                ffHtml += `<div class="result-item"><div class="result-label">综合评分</div><div class="result-value">${(ff.overall_score * 100).toFixed(1)}%</div></div>`;
            }
            if (ff.strengths && ff.strengths.length) {
                ffHtml += `<div class="result-item"><div class="result-label">优点</div><div class="result-value">${ff.strengths.join(', ')}</div></div>`;
            }
            if (ff.weaknesses && ff.weaknesses.length) {
                ffHtml += `<div class="result-item"><div class="result-label">待改进</div><div class="result-value">${ff.weaknesses.join(', ')}</div></div>`;
            }
            if (ff.suggestions && ff.suggestions.length) {
                ffHtml += `<div class="result-item"><div class="result-label">建议</div><div class="result-value">${ff.suggestions.join(', ')}</div></div>`;
            }
            resultEl.innerHTML += ffHtml;
        }

        updateStatus('disconnected', '面试已结束');

    } catch (error) {
        alert('结束面试失败: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '结束面试';
    }
}

// =============================================================================
// Training Functions
// =============================================================================

function setupTrainingListeners() {
    document.getElementById('training-start-btn').addEventListener('click', startTraining);
    document.getElementById('training-submit-btn').addEventListener('click', submitTrainingAnswer);
    document.getElementById('training-next-question-btn').addEventListener('click', getNextTrainingQuestion);
    document.getElementById('training-end-btn').addEventListener('click', endTraining);
}

async function startTraining() {
    const sessionId = document.getElementById('training-session-id').value || crypto.randomUUID();
    const skillPoint = document.getElementById('training-skill-point').value;

    trainingSessionId = sessionId;

    const btn = document.getElementById('training-start-btn');
    btn.disabled = true;
    btn.textContent = '启动中...';

    try {
        const response = await fetch(`${API_BASE}/train/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                resume_id: sessionId,
                skill_point: skillPoint,
            }),
        });

        if (!response.ok) throw new Error('启动失败');

        const data = await response.json();

        // Show active training UI
        document.querySelector('#training .card:nth-child(2)').classList.add('hidden');
        document.getElementById('training-active').classList.remove('hidden');
        document.getElementById('training-skill-label').textContent = skillPoint;

        if (data.first_question) {
            displayTrainingQuestion(data.first_question);
        }

        updateStatus('connected', '训练进行中');

    } catch (error) {
        alert('启动训练失败: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '开始训练';
    }
}

function displayTrainingQuestion(question) {
    currentQuestion = question;
    const container = document.getElementById('training-question');
    container.innerHTML = `
        <div class="question-text">
            <p><strong>问题 ${question.series || 1}.${question.number || 1}:</strong></p>
            <p style="margin-top: 10px;">${question.content}</p>
        </div>
    `;
    document.getElementById('training-answer-section').classList.remove('hidden');
    document.getElementById('training-answer-input').value = '';
    document.getElementById('training-answer-input').focus();
    document.getElementById('training-feedback').classList.add('hidden');
}

async function getNextTrainingQuestion() {
    if (!trainingSessionId) return;

    const btn = document.getElementById('training-next-question-btn');
    btn.disabled = true;
    btn.textContent = '获取中...';

    try {
        const startResponse = await fetch(`${API_BASE}/train/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: trainingSessionId,
                resume_id: trainingSessionId,
                skill_point: document.getElementById('training-skill-point').value,
            }),
        });

        if (startResponse.ok) {
            const data = await startResponse.json();
            if (data.first_question) {
                displayTrainingQuestion(data.first_question);
            }
        }

    } catch (error) {
        console.error('Error:', error);
    } finally {
        btn.disabled = false;
        btn.textContent = '下一题';
    }
}

async function submitTrainingAnswer() {
    const answer = document.getElementById('training-answer-input').value.trim();
    if (!answer) {
        alert('请输入回答');
        return;
    }
    if (!currentQuestion) return;

    const btn = document.getElementById('training-submit-btn');
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/train/answer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: trainingSessionId,
                question_id: currentQuestion.question_id || 'unknown',
                user_answer: answer,
            }),
        });

        if (!response.ok) throw new Error('提交失败');

        const data = await response.json();

        if (data.feedback) {
            const feedbackEl = document.getElementById('training-feedback');
            feedbackEl.classList.remove('hidden', 'positive', 'negative');
            feedbackEl.classList.add(data.feedback.is_correct ? 'positive' : 'negative');
            feedbackEl.textContent = data.feedback.content || JSON.stringify(data.feedback);
        }

        if (data.next_question_content) {
            currentQuestion = {
                question_id: data.next_question_id,
                series: currentQuestion.series,
                number: currentQuestion.number + 1,
                content: data.next_question_content,
            };
            displayTrainingQuestion(currentQuestion);
        }

    } catch (error) {
        alert('提交失败: ' + error.message);
    } finally {
        btn.disabled = false;
    }
}

async function endTraining() {
    if (!trainingSessionId) return;

    const btn = document.getElementById('training-end-btn');
    btn.disabled = true;
    btn.textContent = '结束中...';

    try {
        const response = await fetch(`${API_BASE}/train/end?session_id=${trainingSessionId}`, {
            method: 'POST',
        });

        if (!response.ok) throw new Error('结束失败');

        const data = await response.json();

        document.getElementById('training-active').classList.add('hidden');
        document.getElementById('training-result').classList.remove('hidden');

        const resultEl = document.getElementById('training-result-display');
        resultEl.innerHTML = `
            <div class="result-item">
                <div class="result-label">技能点</div>
                <div class="result-value">${data.skill_point}</div>
            </div>
            <div class="result-item">
                <div class="result-label">状态</div>
                <div class="result-value">${data.status}</div>
            </div>
            <div class="result-item">
                <div class="result-label">已回答问题</div>
                <div class="result-value">${data.questions_answered || 0}</div>
            </div>
        `;

        if (data.final_feedback) {
            const ff = data.final_feedback;
            let ffHtml = `<h4>训练反馈</h4>`;
            if (ff.overall_score !== undefined) {
                ffHtml += `<div class="result-item"><div class="result-label">综合评分</div><div class="result-value">${(ff.overall_score * 100).toFixed(1)}%</div></div>`;
            }
            resultEl.innerHTML += ffHtml;
        }

        updateStatus('disconnected', '训练已结束');

    } catch (error) {
        alert('结束训练失败: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '结束训练';
    }
}

// =============================================================================
// Knowledge Base Functions
// =============================================================================

function setupKnowledgeListeners() {
    document.getElementById('kb-source-type').addEventListener('change', toggleSkillPointsInput);
    document.getElementById('kb-build-btn').addEventListener('click', buildKnowledgeBase);
    document.getElementById('kb-query-btn').addEventListener('click', queryKnowledgeBase);
}

function toggleSkillPointsInput() {
    const sourceType = document.getElementById('kb-source-type').value;
    const skillPointsSection = document.getElementById('kb-skill-points-section');
    const resumeSection = document.getElementById('kb-resume-section');
    skillPointsSection.classList.toggle('hidden', sourceType !== 'skill_point');
    resumeSection.classList.toggle('hidden', sourceType !== 'resume');
}

async function buildKnowledgeBase() {
    const kbId = document.getElementById('kb-id').value || 'default';
    const sourceType = document.getElementById('kb-source-type').value;

    const btn = document.getElementById('kb-build-btn');
    const statusEl = document.getElementById('kb-build-status');

    btn.disabled = true;
    btn.textContent = '构建中...';
    statusEl.className = 'build-status loading';
    statusEl.textContent = '正在构建知识库...';

    try {
        const requestBody = {
            knowledge_base_id: kbId,
            source_type: sourceType,
        };

        if (sourceType === 'skill_point') {
            const skillPointsInput = document.getElementById('kb-skill-points').value;
            requestBody.skill_points = skillPointsInput.split(',').map(s => s.trim()).filter(s => s);
        } else if (sourceType === 'resume') {
            const resumeContent = document.getElementById('kb-resume-content').value.trim();
            if (!resumeContent) {
                statusEl.className = 'build-status error';
                statusEl.textContent = '简历内容不能为空';
                btn.disabled = false;
                btn.textContent = '构建知识库';
                return;
            }
            requestBody.content = resumeContent;
        }

        const response = await fetch(`${API_BASE}/knowledge/build`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody),
        });

        if (!response.ok) throw new Error('构建失败');

        const data = await response.json();

        statusEl.className = 'build-status success';
        statusEl.textContent = `构建完成！状态: ${data.status}, 文档数: ${data.documents_count || 0}`;

    } catch (error) {
        statusEl.className = 'build-status error';
        statusEl.textContent = '构建失败: ' + error.message;
    } finally {
        btn.disabled = false;
        btn.textContent = '构建知识库';
    }
}

async function queryKnowledgeBase() {
    const query = document.getElementById('kb-query-input').value.trim();
    if (!query) {
        alert('请输入查询内容');
        return;
    }

    const btn = document.getElementById('kb-query-btn');
    const resultsEl = document.getElementById('kb-query-results');

    btn.disabled = true;
    btn.textContent = '查询中...';
    resultsEl.innerHTML = '<p class="loading">正在查询...</p>';

    try {
        const response = await fetch(`${API_BASE}/knowledge/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                knowledge_base_id: 'default',
                top_k: 5,
            }),
        });

        if (!response.ok) throw new Error('查询失败');

        const data = await response.json();

        if (data.results && data.results.length > 0) {
            resultsEl.innerHTML = data.results.map(r => `
                <div class="query-result-item">
                    <p>${r.page_content || JSON.stringify(r)}</p>
                </div>
            `).join('');
        } else {
            resultsEl.innerHTML = '<p>没有找到相关结果</p>';
        }

    } catch (error) {
        resultsEl.innerHTML = `<p style="color: #c00;">查询失败: ${error.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = '查询';
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
