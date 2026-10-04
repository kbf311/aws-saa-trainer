/**
 * AWS SAA-C03 Trainer - Quiz Header Timer
 * ヘッダーに表示するシンプルな演習時間カウントアップタイマー (00:00形式)
 */
(function () {
  'use strict';

  const urlParams = new URLSearchParams(window.location.search);
  const sessionId = urlParams.get('session_id');
  if (!sessionId) return;

  const timerDigits = document.getElementById('quizTimerDigits');
  if (!timerDigits) return;

  // セッション単位で開始時刻を管理（画面リロードや問題遷移でもカウントを継続）
  const KEY_START_TIME = `quiz_timer_start_${sessionId}`;

  const savedStart = sessionStorage.getItem(KEY_START_TIME);
  let startTime = savedStart ? parseInt(savedStart, 10) : null;

  if (!startTime || isNaN(startTime)) {
    startTime = Date.now();
    sessionStorage.setItem(KEY_START_TIME, startTime.toString());
  }

  function formatTime(totalSeconds) {
    const s = Math.max(0, Math.floor(totalSeconds));
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    const pad = (n) => String(n).padStart(2, '0');

    if (mins >= 60) {
      const hours = Math.floor(mins / 60);
      const remMins = mins % 60;
      return `${hours}:${pad(remMins)}:${pad(secs)}`;
    }
    return `${pad(mins)}:${pad(secs)}`;
  }

  function renderTimer() {
    const elapsedSec = Math.floor((Date.now() - startTime) / 1000);
    timerDigits.textContent = formatTime(elapsedSec);
  }

  // 初回即時描画
  renderTimer();

  // 1秒ごとにカウントアップ更新
  const intervalId = setInterval(renderTimer, 1000);

  window.addEventListener('beforeunload', () => {
    clearInterval(intervalId);
  });
})();
