document.addEventListener('DOMContentLoaded', () => {
  const urlParams = new URLSearchParams(window.location.search);
  const sessionId = urlParams.get('session_id');

  if (!sessionId) {
    alert('セッションIDが見つかりません。試験設定画面へ移動します。');
    window.location.href = '/setup';
    return;
  }

  // DOM Elements
  const loadingIndicator = document.getElementById('loadingIndicator');
  const questionContainer = document.getElementById('questionContainer');
  const progressCurrent = document.getElementById('progressCurrent');
  const progressTotal = document.getElementById('progressTotal');
  const progressLabel = document.getElementById('progressLabel');
  const progressBarFill = document.getElementById('progressBarFill');
  const textMajor = document.getElementById('textMajor');
  const textMinor = document.getElementById('textMinor');
  const questionTypeBadge = document.getElementById('questionTypeBadge');
  const questionIdLabel = document.getElementById('questionIdLabel');
  const questionText = document.getElementById('questionText');
  const questionHintText = document.getElementById('questionHintText');
  const optionsContainer = document.getElementById('optionsContainer');

  const explanationContainer = document.getElementById('explanationContainer');
  const resultAlertBox = document.getElementById('resultAlertBox');
  const resultIcon = document.getElementById('resultIcon');
  const resultTitle = document.getElementById('resultTitle');
  const resultSub = document.getElementById('resultSub');
  const resultCorrectKeys = document.getElementById('resultCorrectKeys');
  const explanationText = document.getElementById('explanationText');

  const btnSubmitAnswer = document.getElementById('btnSubmitAnswer');
  const btnNextQuestion = document.getElementById('btnNextQuestion');
  const btnNextLabel = document.getElementById('btnNextLabel');
  const btnEndEarly = document.getElementById('btnEndEarly');
  const labelEndEarly = document.getElementById('labelEndEarly');

  let currentQuestion = null;
  let selectedAnswers = new Set();
  let isAnswered = false;
  let hasNextQuestion = true;
  let hasNextQuestionOriginal = true;
  let finishAfterCurrent = false;
  let currentLastResult = null;
  let isNavigatingAway = false;

  const storageKey = `quiz_session_${sessionId}`;

  // ブラウザバック対策: 戻る操作時に確認して setup.html に戻す
  history.pushState(null, '', window.location.href);
  window.addEventListener('popstate', () => {
    if (isNavigatingAway) return;
    const leave = confirm('演習を中断して試験設定画面に戻りますか？');
    if (leave) {
      isNavigatingAway = true;
      clearSessionStorage();
      window.location.href = '/setup';
    } else {
      // 戻るをキャンセルして留まる
      history.pushState(null, '', window.location.href);
    }
  });

  // セッション状態の保存
  function saveCurrentState(extra = {}) {
    if (!currentQuestion) return;
    try {
      const data = {
        currentQuestion,
        selectedAnswers: Array.from(selectedAnswers),
        isAnswered,
        hasNextQuestionOriginal,
        finishAfterCurrent,
        lastResult: extra.lastResult || currentLastResult || null,
      };
      sessionStorage.setItem(storageKey, JSON.stringify(data));
    } catch (e) {
      console.warn('Failed to save state to sessionStorage:', e);
    }
  }

  // セッション状態の消去
  function clearSessionStorage() {
    try {
      sessionStorage.removeItem(storageKey);
    } catch (e) {
      console.warn('Failed to clear sessionStorage:', e);
    }
  }

  // 「この問題で終了する」トグルのUI反映
  function updateEndEarlyUI() {
    if (!btnEndEarly || !labelEndEarly) return;

    if (finishAfterCurrent) {
      btnEndEarly.className =
        'text-xs text-amber-300 font-medium px-3 py-2 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 transition flex items-center shadow-sm';
      labelEndEarly.textContent = 'この問題で終了する（予約中）';
    } else {
      btnEndEarly.className =
        'text-xs text-slate-400 hover:text-slate-200 px-3 py-2 rounded-lg bg-slate-800/50 hover:bg-slate-800 border border-slate-700/60 transition flex items-center';
      labelEndEarly.textContent = 'この問題で終了する';
    }
  }

  // 次へ/サマリーへボタンの表示更新
  function updateNextButtonUI() {
    const shouldFinish = finishAfterCurrent || !hasNextQuestionOriginal;
    if (shouldFinish) {
      btnNextLabel.textContent = '結果サマリーを見る';
      hasNextQuestion = false;
    } else {
      btnNextLabel.textContent = '次の問題へ進む';
      hasNextQuestion = true;
    }
  }

  // 次の問題を読み込む
  async function loadNextQuestion() {
    clearSessionStorage();
    currentLastResult = null;
    isAnswered = false;
    finishAfterCurrent = false;
    updateEndEarlyUI();
    selectedAnswers.clear();
    btnSubmitAnswer.disabled = true;
    btnSubmitAnswer.innerHTML = '<span>回答を確定する</span><i class="fa-solid fa-arrow-right text-xs"></i>';
    btnSubmitAnswer.classList.remove('hidden');
    btnNextQuestion.classList.add('hidden');
    explanationContainer.classList.add('hidden');
    optionsContainer.innerHTML = '';

    loadingIndicator.classList.remove('hidden');
    questionContainer.classList.add('hidden');

    try {
      const res = await fetch(`/api/quiz/session/${sessionId}/next`);
      if (res.status === 404) {
        // 全問題解答完了
        finishSession();
        return;
      }
      if (!res.ok) {
        throw new Error('問題データの取得に失敗しました');
      }

      currentQuestion = await res.json();
      renderQuestion(currentQuestion);
      saveCurrentState();
    } catch (err) {
      console.error(err);
      alert('問題の読み込み中にエラーが発生しました。サマリー画面へ進みます。');
      finishSession();
    }
  }

  // 問題を画面に描画
  function renderQuestion(q) {
    loadingIndicator.classList.add('hidden');
    questionContainer.classList.remove('hidden');

    // プログレス
    progressCurrent.textContent = q.current_index;
    if (q.is_endless) {
      progressTotal.textContent = '';
      progressLabel.textContent = `エンドレス: ${q.current_index}問目`;
      progressBarFill.style.width = '100%';
    } else {
      progressTotal.textContent = `/${q.target_count}`;
      progressLabel.textContent = `第 ${q.current_index} 問目`;
      const pct = Math.min(100, Math.round((q.current_index / q.target_count) * 100));
      progressBarFill.style.width = `${pct}%`;
    }

    // カテゴリ・メタ情報
    textMajor.textContent = q.category_major || '全般';
    textMinor.textContent = q.category_minor || '総合';
    questionIdLabel.textContent = q.question_id.substring(0, 8);

    const isMultiple = q.question_type === 'multiple';
    questionTypeBadge.textContent = isMultiple ? '複数選択問題' : '単一選択問題';
    questionHintText.innerHTML = isMultiple
      ? '該当する選択肢をすべて選択してください。'
      : '最も適切な選択肢を <strong>1つ</strong> 選択してください。';

    questionText.innerHTML = formatSentenceBreaksHtml(q.question_text);

    // 選択肢カード描画
    q.options.forEach((opt, idx) => {
      const keyNumber = idx + 1;
      const card = document.createElement('label');
      card.id = `opt-${opt.id}`;
      card.className =
        'option-card flex items-start p-4 rounded-xl border-2 border-slate-700/70 bg-slate-800/50 hover:bg-slate-800/90 hover:border-slate-500 cursor-pointer transition select-none group';

      card.innerHTML = `
        <input type="${isMultiple ? 'checkbox' : 'radio'}" name="question_opt" value="${opt.id}" class="sr-only">
        <div class="opt-badge w-8 h-8 rounded-lg bg-slate-700 text-slate-200 font-bold flex items-center justify-center shrink-0 mr-4 transition">
          ${opt.id}
        </div>
        <div class="flex-1 pt-1">
          <p class="text-sm sm:text-base text-slate-200 leading-normal">${formatSentenceBreaksHtml(opt.text)}</p>
        </div>
        <span class="shortcut-key hidden sm:inline-block text-[11px] font-mono text-slate-500 border border-slate-700 px-1.5 py-0.5 rounded ml-2">${keyNumber}</span>
      `;

      card.addEventListener('click', (e) => {
        e.preventDefault();
        if (isAnswered) return;
        toggleOption(opt.id, isMultiple);
      });

      optionsContainer.appendChild(card);
    });
  }

  // 選択肢のトグル
  function toggleOption(optId, isMultiple) {
    if (isMultiple) {
      if (selectedAnswers.has(optId)) {
        selectedAnswers.delete(optId);
      } else {
        selectedAnswers.add(optId);
      }
    } else {
      selectedAnswers.clear();
      selectedAnswers.add(optId);
    }
    updateOptionSelectionUI();
    saveCurrentState();
  }

  // 選択状態のUI反映
  function updateOptionSelectionUI() {
    const cards = optionsContainer.querySelectorAll('.option-card');
    cards.forEach((card) => {
      const optId = card.id.replace('opt-', '');
      if (selectedAnswers.has(optId)) {
        card.classList.add('selected');
        const badge = card.querySelector('.opt-badge');
        badge.classList.remove('bg-slate-700', 'text-slate-200');
        badge.classList.add('bg-aws-orange', 'text-slate-950');
      } else {
        card.classList.remove('selected');
        const badge = card.querySelector('.opt-badge');
        badge.classList.remove('bg-aws-orange', 'text-slate-950');
        badge.classList.add('bg-slate-700', 'text-slate-200');
      }
    });

    btnSubmitAnswer.disabled = selectedAnswers.size === 0;
  }

  // 回答送信
  async function submitAnswer() {
    if (isAnswered || selectedAnswers.size === 0) return;

    btnSubmitAnswer.disabled = true;
    btnSubmitAnswer.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> 判定中...';

    try {
      const res = await fetch(`/api/quiz/session/${sessionId}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: currentQuestion.question_id,
          selected_answers: Array.from(selectedAnswers),
        }),
      });

      if (!res.ok) {
        throw new Error('回答送信に失敗しました');
      }

      const result = await res.json();
      showAnswerResult(result);
    } catch (err) {
      alert(err.message || 'エラーが発生しました');
      btnSubmitAnswer.disabled = false;
      btnSubmitAnswer.innerHTML = '<span>回答を確定する</span><i class="fa-solid fa-arrow-right text-xs ml-2"></i>';
    }
  }

  // 判定結果・解説の表示
  function showAnswerResult(result, isRestoring = false) {
    isAnswered = true;
    currentLastResult = result;
    hasNextQuestionOriginal = result.has_next;

    // 各選択肢の正誤スタイル反映
    const correctAnswers = new Set(result.correct_answers);
    const cards = optionsContainer.querySelectorAll('.option-card');

    cards.forEach((card) => {
      const optId = card.id.replace('opt-', '');
      const badge = card.querySelector('.opt-badge');
      card.classList.remove('hover:border-slate-500', 'cursor-pointer');
      card.style.cursor = 'default';

      if (correctAnswers.has(optId)) {
        // 正解
        card.classList.add('correct');
        badge.className =
          'opt-badge w-8 h-8 rounded-lg bg-emerald-500 text-slate-950 font-bold flex items-center justify-center shrink-0 mr-4';
        badge.innerHTML = '<i class="fa-solid fa-check"></i>';
      } else if (selectedAnswers.has(optId)) {
        // 不正解で自分が選んだもの
        card.classList.add('incorrect');
        badge.className =
          'opt-badge w-8 h-8 rounded-lg bg-rose-500 text-white font-bold flex items-center justify-center shrink-0 mr-4';
        badge.innerHTML = '<i class="fa-solid fa-xmark"></i>';
      }

      // 各選択肢の個別解説をカード内に表示
      if (result.options) {
        const optData = result.options.find((o) => o.id === optId);
        if (optData && optData.explanation) {
          const contentWrapper = card.querySelector('.flex-1');
          if (contentWrapper && !card.querySelector('.opt-reason')) {
            const reasonDiv = document.createElement('div');
            reasonDiv.className =
              'opt-reason mt-2 pt-2 border-t border-slate-700/50 text-xs sm:text-sm text-slate-300 font-normal leading-relaxed';
            reasonDiv.innerHTML = window.inlineFormat
              ? window.inlineFormat(optData.explanation)
              : escapeHtml(optData.explanation);
            contentWrapper.appendChild(reasonDiv);
          }
        }
      }
    });

    // 結果アラートボックス
    if (result.is_correct) {
      resultAlertBox.className =
        'p-4 rounded-xl border flex items-center space-x-3 mb-6 bg-emerald-500/10 border-emerald-500/30 text-emerald-400';
      resultIcon.className = 'fa-solid fa-circle-check text-2xl text-emerald-400';
      resultTitle.className = 'font-bold text-base text-emerald-400';
      resultTitle.textContent = '正解です！素晴らしい判断です。';
    } else {
      resultAlertBox.className =
        'p-4 rounded-xl border flex items-center space-x-3 mb-6 bg-rose-500/10 border-rose-500/30 text-rose-400';
      resultIcon.className = 'fa-solid fa-circle-xmark text-2xl text-rose-400';
      resultTitle.className = 'font-bold text-base text-rose-400';
      resultTitle.textContent = '不正解です。解説を確認して復習しましょう。';
    }

    resultCorrectKeys.textContent = result.correct_answers.join(', ');
    resultSub.innerHTML = `正解: <strong>${result.correct_answers.join(', ')}</strong> (あなたの回答: ${Array.from(selectedAnswers).join(', ')})`;

    // 解説表示
    if (result.options && window.formatStructuredExplanationHtml) {
      explanationText.innerHTML = window.formatStructuredExplanationHtml(result.explanation, result.options);
    } else if (window.formatExplanationHtml) {
      explanationText.innerHTML = window.formatExplanationHtml(result.explanation);
    } else {
      explanationText.innerHTML = formatSentenceBreaksHtml(result.explanation);
    }
    explanationContainer.classList.remove('hidden');

    // ボタン切り替え
    btnSubmitAnswer.classList.add('hidden');
    btnNextQuestion.classList.remove('hidden');

    updateNextButtonUI();

    if (!isRestoring) {
      saveCurrentState({ lastResult: result });
      // 解説へスムーズスクロール
      explanationContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  // セッション終了（サマリー画面遷移）
  async function finishSession() {
    isNavigatingAway = true;
    clearSessionStorage();
    try {
      await fetch(`/api/quiz/session/${sessionId}/complete`, { method: 'POST' });
    } catch (e) {
      console.warn('Session complete API error:', e);
    }
    window.location.href = `/summary?session_id=${sessionId}`;
  }

  // ボタンイベントリスナー
  btnSubmitAnswer.addEventListener('click', submitAnswer);

  btnNextQuestion.addEventListener('click', () => {
    if (finishAfterCurrent || !hasNextQuestion) {
      finishSession();
    } else {
      clearSessionStorage();
      loadNextQuestion();
    }
  });

  btnEndEarly.addEventListener('click', () => {
    finishAfterCurrent = !finishAfterCurrent;
    updateEndEarlyUI();
    if (isAnswered) {
      updateNextButtonUI();
    }
    saveCurrentState();
  });

  // キーボードショートカット
  document.addEventListener('keydown', (e) => {
    // 入力欄にフォーカスがある場合は無視
    if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

    if (!isAnswered && currentQuestion) {
      const isMultiple = currentQuestion.question_type === 'multiple';
      // 数字キー 1..9
      if (e.key >= '1' && e.key <= '9') {
        const idx = parseInt(e.key, 10) - 1;
        if (currentQuestion.options[idx]) {
          toggleOption(currentQuestion.options[idx].id, isMultiple);
        }
      }
      // アルファベットキー A..F
      const upper = e.key.toUpperCase();
      if (['A', 'B', 'C', 'D', 'E', 'F'].includes(upper)) {
        const opt = currentQuestion.options.find((o) => o.id === upper);
        if (opt) {
          toggleOption(opt.id, isMultiple);
        }
      }
      // Enterで確定
      if (e.key === 'Enter' && selectedAnswers.size > 0) {
        submitAnswer();
      }
    } else if (isAnswered) {
      // 回答済みの場合、Enterで次へ
      if (e.key === 'Enter') {
        if (finishAfterCurrent || !hasNextQuestion) {
          finishSession();
        } else {
          clearSessionStorage();
          loadNextQuestion();
        }
      }
    }
  });

  // Markdown（箇条書きリスト、番号付きリスト、太字、インラインコード等）と句点の改行を処理してHTMLを返す
  function formatSentenceBreaksHtml(text) {
    if (!text) return '';

    // 1. 安全にHTML特殊文字をエスケープ
    let escaped = escapeHtml(text);

    // 2. インラインMarkdown（太字・コード）の変換
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong class="text-white font-semibold">$1</strong>');
    escaped = escaped.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded text-[0.9em] bg-slate-950/80 border border-slate-700 text-amber-300 font-mono">$1</code>');

    // 3. 行ごとに分解してリストと通常段落を処理
    const rawLines = escaped.split(/\r?\n/);
    const parts = [];
    let currentList = [];
    let currentListType = null; // 'ul' | 'ol'
    let currentListStart = 1;

    function flushList() {
      if (currentList.length > 0 && currentListType) {
        const listItems = currentList.map((item) => `<li>${item}</li>`).join('');
        if (currentListType === 'ol') {
          const startAttr = currentListStart !== 1 ? ` start="${currentListStart}"` : '';
          parts.push(`<ol class="markdown-ordered-list"${startAttr}>${listItems}</ol>`);
        } else {
          parts.push(`<ul class="markdown-bullet-list">${listItems}</ul>`);
        }
        currentList = [];
        currentListType = null;
      }
    }

    for (let i = 0; i < rawLines.length; i++) {
      const trimmed = rawLines[i].trim();
      const bulletMatch = trimmed.match(/^(?:[-*•]\s+|・\s*)(.*)$/);
      const orderedMatch = trimmed.match(/^(\d+)[\.\)]\s+(.*)$/);

      if (bulletMatch) {
        if (currentListType !== 'ul') {
          flushList();
          currentListType = 'ul';
        }
        let itemText = bulletMatch[1];
        itemText = itemText.replace(/。(?![\r\n]|$)/g, '。<br>');
        currentList.push(itemText);
      } else if (orderedMatch) {
        const num = parseInt(orderedMatch[1], 10);
        if (currentListType !== 'ol') {
          flushList();
          currentListType = 'ol';
          currentListStart = num;
        }
        let itemText = orderedMatch[2];
        itemText = itemText.replace(/。(?![\r\n]|$)/g, '。<br>');
        currentList.push(itemText);
      } else {
        flushList();
        if (trimmed === '') {
          parts.push('');
        } else {
          let lineText = trimmed.replace(/。(?![\r\n]|$)/g, '。<br>');
          parts.push(lineText);
        }
      }
    }
    flushList();

    // 4. parts を結合してHTMLを生成（リスト前後の余白を整理）
    let html = '';
    const isListTag = (p) => p.startsWith('<ul') || p.startsWith('<ol');

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (isListTag(part)) {
        html += part;
      } else if (part === '') {
        const prevIsList = i > 0 && isListTag(parts[i - 1]);
        const nextIsList = i + 1 < parts.length && isListTag(parts[i + 1]);
        if (!prevIsList && !nextIsList) {
          html += '<br>';
        }
      } else {
        if (i > 0 && parts[i - 1] !== '' && !isListTag(parts[i - 1])) {
          html += '<br>';
        } else if (i > 0 && parts[i - 1] === '') {
          const prevPrevIsList = i > 1 && isListTag(parts[i - 2]);
          if (!prevPrevIsList) {
            html += '<br>';
          }
        }
        html += part;
      }
    }

    return html;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // 初期ロード開始（キャッシュ復元または新規問題ロード）
  function initQuiz() {
    try {
      const raw = sessionStorage.getItem(storageKey);
      if (raw) {
        const saved = JSON.parse(raw);
        if (saved && saved.currentQuestion && saved.currentQuestion.session_id === sessionId) {
          currentQuestion = saved.currentQuestion;
          finishAfterCurrent = !!saved.finishAfterCurrent;
          hasNextQuestionOriginal = saved.hasNextQuestionOriginal ?? true;
          updateEndEarlyUI();

          renderQuestion(currentQuestion);

          if (Array.isArray(saved.selectedAnswers)) {
            saved.selectedAnswers.forEach((ans) => selectedAnswers.add(ans));
            updateOptionSelectionUI();
          }

          if (saved.isAnswered && saved.lastResult) {
            showAnswerResult(saved.lastResult, true);
          }
          return;
        }
      }
    } catch (e) {
      console.warn('Failed to restore quiz state from sessionStorage:', e);
    }

    loadNextQuestion();
  }

  initQuiz();
});
