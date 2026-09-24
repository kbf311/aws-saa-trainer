document.addEventListener('DOMContentLoaded', () => {
  let chartInstance = null;
  let currentRecentN = 20;
  let configuredRecentDays =
    window.APP_CONFIG && window.APP_CONFIG.configuredRecentDays
      ? window.APP_CONFIG.configuredRecentDays
      : 7;
  let currentPeriodDays = configuredRecentDays; // 初期選択: 直近n日

  // DOM Elements - Period Switching
  const btnPeriodAll = document.getElementById('btnPeriodAll');
  const btnPeriodRecent = document.getElementById('btnPeriodRecent');
  const btnRecentDaysCount = document.getElementById('btnRecentDaysCount');
  const periodBadge = document.getElementById('periodBadge');

  // DOM Elements - KPI Cards
  const kpiTotalAnswers = document.getElementById('kpiTotalAnswers');
  const kpiTotalAnswersLabel = document.getElementById('kpiTotalAnswersLabel');
  const kpiTodayAnswers = document.getElementById('kpiTodayAnswers');
  const kpiDaysCount = document.getElementById('kpiDaysCount');
  const kpiDaysCountLabel = document.getElementById('kpiDaysCountLabel');
  const kpiLastLearnedDate = document.getElementById('kpiLastLearnedDate');
  const kpiAccuracyRate = document.getElementById('kpiAccuracyRate');
  const kpiAccuracyLabel = document.getElementById('kpiAccuracyLabel');
  const kpiRecentNLabel = document.getElementById('kpiRecentNLabel');

  // DOM Elements - Sections & Headers
  const cumulativeChartTitle = document.getElementById('cumulativeChartTitle');
  const categorySectionDesc = document.getElementById('categorySectionDesc');
  const sessionsSectionTitle = document.getElementById('sessionsSectionTitle');

  // DOM Elements - Controls & Lists
  const slider = document.getElementById('recentRangeSlider');
  const sliderLabel = document.getElementById('sliderLabel');
  const sliderValueBadge = document.getElementById('sliderValueBadge');
  const categoryBarsContainer = document.getElementById('categoryBarsContainer');
  const heatmapGrid = document.getElementById('heatmapGrid');
  const recentSessionsBody = document.getElementById('recentSessionsBody');


  // ダッシュボードデータを取得して描画
  async function loadDashboard(recentN, periodDays = null) {
    try {
      let url = `/api/dashboard/summary?recent_n=${recentN}`;
      if (periodDays !== null && periodDays > 0) {
        url += `&period_days=${periodDays}`;
      }

      const res = await fetch(url);
      if (!res.ok) throw new Error('データ取得に失敗しました');

      const data = await res.json();

      // 設定値の同期
      if (data.configured_recent_days) {
        configuredRecentDays = data.configured_recent_days;
        if (btnRecentDaysCount) {
          btnRecentDaysCount.textContent = configuredRecentDays;
        }
      }

      updatePeriodUI(periodDays);
      renderKPIs(data);
      renderCumulativeChart(data.cumulative_history, periodDays);
      renderCategoryPerformance(data.category_stats);

      // ヒートマップ描画 (年選択対応)
      cachedHeatmapData = data.heatmap || {};
      cachedAvailableYears = data.available_years || [new Date().getFullYear()];
      if (!currentHeatmapYear || !cachedAvailableYears.includes(currentHeatmapYear)) {
        currentHeatmapYear = data.current_year || new Date().getFullYear();
      }
      renderHeatmapYearButtons(cachedAvailableYears, currentHeatmapYear);
      drawHeatmap(cachedHeatmapData, currentHeatmapYear);

      renderRecentSessions(data.recent_sessions, periodDays);

      // エクスポートリンクの更新
      let exportParams = `recent_n=${recentN}`;
      if (periodDays !== null && periodDays > 0) {
        exportParams += `&period_days=${periodDays}`;
      }
      btnExportJson.href = `/api/dashboard/export?format=json&${exportParams}`;
      btnExportCsv.href = `/api/dashboard/export?format=csv&${exportParams}`;
    } catch (err) {
      console.error(err);
    }
  }

  // 期間に応じた見出し・ラベルの切り替え
  function updatePeriodUI(periodDays) {
    if (periodDays !== null && periodDays > 0) {
      if (cumulativeChartTitle) {
        cumulativeChartTitle.textContent = `直近 ${periodDays} 日間の回答推移`;
      }
    } else {
      if (cumulativeChartTitle) {
        cumulativeChartTitle.textContent = '累計回答問題数の推移';
      }
    }
  }

  // ボタンのアクティブ状態の視覚更新
  function setPeriodButtonsState(periodDays) {
    if (periodDays !== null && periodDays > 0) {
      btnPeriodAll.className =
        'period-tab-btn px-4 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white transition flex items-center space-x-1.5';
      btnPeriodRecent.className =
        'period-tab-btn px-4 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 bg-aws-orange text-slate-950 shadow';
    } else {
      btnPeriodAll.className =
        'period-tab-btn px-4 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 bg-aws-orange text-slate-950 shadow';
      btnPeriodRecent.className =
        'period-tab-btn px-4 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white transition flex items-center space-x-1.5';
    }
  }

  // 期間切り替えイベント
  if (btnPeriodAll && btnPeriodRecent) {
    btnPeriodAll.addEventListener('click', () => {
      if (currentPeriodDays !== null) {
        currentPeriodDays = null;
        setPeriodButtonsState(null);
        loadDashboard(currentRecentN, currentPeriodDays);
      }
    });

    btnPeriodRecent.addEventListener('click', () => {
      if (currentPeriodDays !== configuredRecentDays) {
        currentPeriodDays = configuredRecentDays;
        setPeriodButtonsState(configuredRecentDays);
        loadDashboard(currentRecentN, currentPeriodDays);
      }
    });
  }

  // KPIカードのアニメーション用前回収集値
  let prevTotalAnswers = 0;
  let prevDaysCount = 0;
  let prevAccuracyRate = 0.0;

  // 数値カウントアップアニメーション関数（イージング: easeOutCubic）
  function animateValue(element, start, end, duration = 1000, decimals = 0) {
    if (!element) return;
    if (isNaN(end)) {
      element.textContent = end;
      return;
    }
    const startTime = performance.now();

    function update(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Chart.js のラインアニメーション曲線と調和する easeOutCubic
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = start + (end - start) * ease;

      if (decimals > 0) {
        element.textContent = current.toFixed(decimals);
      } else {
        element.textContent = Math.round(current).toLocaleString();
      }

      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        if (decimals > 0) {
          element.textContent = Number(end).toFixed(decimals);
        } else {
          element.textContent = Math.round(end).toLocaleString();
        }
      }
    }

    requestAnimationFrame(update);
  }

  // KPIカード更新
  function renderKPIs(data) {
    const targetTotal = Number(data.total_answers) || 0;
    const targetDays = Number(data.days_count) || 0;
    const accuracy = data.recent_accuracy != null ? data.recent_accuracy : data.overall_accuracy;
    const targetAccuracy = Number(accuracy) || 0.0;

    animateValue(kpiTotalAnswers, prevTotalAnswers, targetTotal, 1000, 0);
    animateValue(kpiDaysCount, prevDaysCount, targetDays, 1000, 0);
    animateValue(kpiAccuracyRate, prevAccuracyRate, targetAccuracy, 1000, 1);

    prevTotalAnswers = targetTotal;
    prevDaysCount = targetDays;
    prevAccuracyRate = targetAccuracy;

    if (targetAccuracy >= 72.0) {
      kpiAccuracyRate.className = 'text-3xl font-extrabold text-emerald-400';
    } else {
      kpiAccuracyRate.className = 'text-3xl font-extrabold text-amber-400';
    }

    const dynamicRecentN = document.getElementById('kpiRecentNLabel');
    if (dynamicRecentN && data.recent_n != null) {
      dynamicRecentN.textContent = data.recent_n;
    }

    if (kpiTodayAnswers) {
      kpiTodayAnswers.textContent = data.today_answers != null ? data.today_answers : 0;
    }

    if (kpiLastLearnedDate) {
      if (data.last_learned_date) {
        kpiLastLearnedDate.textContent = data.last_learned_date;
      } else if (data.last_answered_at) {
        const d = new Date(data.last_answered_at);
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        kpiLastLearnedDate.textContent = `${yyyy}-${mm}-${dd}`;
      } else {
        kpiLastLearnedDate.textContent = '未学習';
      }
    }
  }

  // 累計回答問題数の推移グラフ (Chart.js)
  function renderCumulativeChart(history, periodDays = null) {
    const ctx = document.getElementById('cumulativeChart').getContext('2d');

    const labels = history.labels && history.labels.length > 0 ? history.labels : ['本日'];
    const dataValues = history.cumulative && history.cumulative.length > 0 ? history.cumulative : [0];
    const isPeriodFiltered = periodDays !== null && periodDays > 0;
    const chartLabel = isPeriodFiltered ? `直近 ${periodDays} 日間の累計回答推移` : '累計回答問題数';

    if (chartInstance) {
      chartInstance.data.labels = labels;
      chartInstance.data.datasets[0].label = chartLabel;
      chartInstance.data.datasets[0].data = dataValues;
      chartInstance.options.scales.y.beginAtZero = !isPeriodFiltered;
      chartInstance.update();
      return;
    }

    chartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: chartLabel,
            data: dataValues,
            borderColor: '#FF9900',
            backgroundColor: 'rgba(255, 153, 0, 0.1)',
            fill: true,
            tension: 0,
            borderWidth: 2.5,
            pointBackgroundColor: '#FF9900',
            pointRadius: 3,
            pointHoverRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1e293b',
            titleColor: '#fff',
            bodyColor: '#cbd5e1',
            borderColor: '#475569',
            borderWidth: 1,
            padding: 10,
          },
        },
        scales: {
          x: {
            grid: { color: 'rgba(51, 65, 85, 0.3)' },
            ticks: { color: '#94a3b8', font: { size: 10 } },
          },
          y: {
            beginAtZero: !isPeriodFiltered,
            grid: { color: 'rgba(51, 65, 85, 0.3)' },
            ticks: { color: '#94a3b8', font: { size: 10 }, precision: 0 },
          },
        },
      },
    });
  }

  // カテゴリー別 正解率バーの描画（アニメーション対応）
  function renderCategoryPerformance(stats) {
    categoryBarsContainer.innerHTML = '';
    if (!stats || stats.length === 0) {
      categoryBarsContainer.innerHTML = '<p class="text-xs text-slate-500 py-4">データがありません</p>';
      return;
    }

    const animatedItems = [];

    stats.forEach((cat, index) => {
      const item = document.createElement('div');
      item.className = 'p-3.5 rounded-xl bg-slate-900/60 border border-slate-700/60 hover:border-slate-600 transition';

      const barColor = cat.rate >= 72 ? 'bg-emerald-500' : 'bg-amber-500';
      const targetWidth = cat.has_data ? cat.rate : 0;

      const statusBadge = cat.has_data
        ? `<span class="text-[10px] font-mono px-2 py-0.5 rounded ${cat.rate >= 72 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'}"><span id="catCorrect_${index}">0</span>/${cat.sample_count}問 (<span id="catRate_${index}">0.0</span>%)</span>`
        : '<span class="text-[10px] text-slate-500 px-2 py-0.5 rounded bg-slate-800">未解答</span>';

      item.innerHTML = `
        <div class="flex items-center justify-between text-xs mb-2">
          <div>
            <span class="text-slate-400 text-[11px] block">${cat.major}</span>
            <span class="font-bold text-slate-200 text-sm">${cat.minor}</span>
          </div>
          <div>${statusBadge}</div>
        </div>
        <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
          <div id="catBar_${index}" class="h-2 rounded-full ${barColor}" style="width: 0%; transition: width 1000ms cubic-bezier(0.16, 1, 0.3, 1);"></div>
        </div>
      `;
      categoryBarsContainer.appendChild(item);

      if (cat.has_data) {
        animatedItems.push({
          barEl: item.querySelector(`#catBar_${index}`),
          correctEl: item.querySelector(`#catCorrect_${index}`),
          rateEl: item.querySelector(`#catRate_${index}`),
          targetWidth: targetWidth,
          targetCorrect: cat.correct_count,
          targetRate: cat.rate,
        });
      }
    });

    // 次の描画フレームでバーを 0% から目標値へ伸ばし、数値もカウントアップ
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        animatedItems.forEach((it) => {
          if (it.barEl) {
            it.barEl.style.width = `${it.targetWidth}%`;
          }
          if (it.correctEl) {
            animateValue(it.correctEl, 0, it.targetCorrect, 1000, 0);
          }
          if (it.rateEl) {
            animateValue(it.rateEl, 0, it.targetRate, 1000, 1);
          }
        });
      });
    });
  }

  // 学習ヒートマップ用キャッシュと状態
  let currentHeatmapYear = new Date().getFullYear();
  let cachedHeatmapData = {};
  let cachedAvailableYears = [];

  // ヒートマップ年選択ボタン生成
  function renderHeatmapYearButtons(years, selectedYear) {
    const container = document.getElementById('heatmapYearButtonGroup');
    const badge = document.getElementById('heatmapYearBadge');
    if (!container) return;
    container.innerHTML = '';

    if (badge) {
      badge.textContent = `${selectedYear}年`;
    }

    years.forEach((yr) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      const isSelected = yr === selectedYear;
      btn.className = isSelected
        ? 'px-3 py-1 rounded-lg text-xs font-bold bg-aws-orange text-slate-950 shadow transition'
        : 'px-3 py-1 rounded-lg text-xs font-medium text-slate-400 hover:text-white transition';
      btn.textContent = `${yr}年`;
      btn.addEventListener('click', () => {
        if (currentHeatmapYear !== yr) {
          currentHeatmapYear = yr;
          renderHeatmapYearButtons(years, currentHeatmapYear);
          drawHeatmap(cachedHeatmapData, currentHeatmapYear);
        }
      });
      container.appendChild(btn);
    });
  }

  // 1年分のヒートマップ描画 (GitHub風 1月1日〜12月31日)
  function drawHeatmap(heatmapData, targetYear) {
    const grid = document.getElementById('heatmapGrid');
    const monthRow = document.getElementById('heatmapMonthRow');
    if (!grid) return;
    grid.innerHTML = '';
    if (monthRow) monthRow.innerHTML = '';

    // 対象年の 1月1日 と 12月31日
    const yearStart = new Date(targetYear, 0, 1);
    const yearEnd = new Date(targetYear, 11, 31);

    // 第1週の日曜日
    const startSunday = new Date(yearStart);
    startSunday.setDate(yearStart.getDate() - yearStart.getDay());

    // 最終週の土曜日
    const endSaturday = new Date(yearEnd);
    endSaturday.setDate(yearEnd.getDate() + (6 - yearEnd.getDay()));

    // 総週数を計算 (通常 53週)
    const diffDays = Math.round((endSaturday - startSunday) / (24 * 60 * 60 * 1000)) + 1;
    const numWeeks = Math.ceil(diffDays / 7);

    const today = new Date();
    const todayMidnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());

    let lastRenderedMonth = -1;
    let weeksSinceLastMonth = 99;

    const dayNames = ['日', '月', '火', '水', '木', '金', '土'];

    for (let w = 0; w < numWeeks; w++) {
      // 1. 当該週のカラム（縦7セル: 日〜土）
      const weekCol = document.createElement('div');
      weekCol.className = 'flex flex-col gap-1.5';

      // 2. 当該週の月ラベルセル
      const monthCell = document.createElement('div');
      monthCell.className = 'w-3 text-[10px] text-slate-400 relative h-4 select-none';

      // 当該週に新しく始まる月があるか判定
      let newMonthForWeek = -1;
      for (let d = 0; d < 7; d++) {
        const curDate = new Date(startSunday);
        curDate.setDate(startSunday.getDate() + (w * 7 + d));
        if (curDate.getFullYear() === targetYear) {
          const m = curDate.getMonth();
          if (m !== lastRenderedMonth) {
            newMonthForWeek = m;
            lastRenderedMonth = m;
            break;
          }
        }
      }

      // 月ラベル配置 (最低2週の間隔)
      if (newMonthForWeek !== -1 && weeksSinceLastMonth >= 2) {
        const monthLabel = document.createElement('span');
        monthLabel.className = 'absolute left-0 top-0 whitespace-nowrap text-slate-400 font-semibold';
        monthLabel.textContent = `${newMonthForWeek + 1}月`;
        monthCell.appendChild(monthLabel);
        weeksSinceLastMonth = 0;
      } else {
        weeksSinceLastMonth++;
      }
      if (monthRow) {
        monthRow.appendChild(monthCell);
      }

      // 3. 各曜日のセルを生成（0: 日曜日 〜 6: 土曜日）
      for (let dayOfWeek = 0; dayOfWeek < 7; dayOfWeek++) {
        const cellDate = new Date(startSunday);
        cellDate.setDate(startSunday.getDate() + (w * 7 + dayOfWeek));

        const yyyy = cellDate.getFullYear();
        const mm = String(cellDate.getMonth() + 1).padStart(2, '0');
        const dd = String(cellDate.getDate()).padStart(2, '0');
        const dateStr = `${yyyy}-${mm}-${dd}`;
        const dayLabel = dayNames[dayOfWeek];

        const cell = document.createElement('div');

        if (yyyy !== targetYear) {
          // 年の範囲外（前年・翌年の余白）: 完全非表示
          cell.className = 'w-3 h-3 rounded-sm opacity-0 pointer-events-none';
        } else {
          // 対象年の日（1月1日〜12月31日）: 未来の日も含め未実施日と同じアイコンで表示
          const count = heatmapData[dateStr] || 0;
          cell.className = `w-3 h-3 rounded-sm transition cursor-pointer ${getHeatmapColor(count)}`;
          const countText = count > 0 ? `${count}問 回答` : '学習なし';
          cell.title = `${yyyy}年${cellDate.getMonth() + 1}月${cellDate.getDate()}日 (${dayLabel}): ${countText}`;
        }

        weekCol.appendChild(cell);
      }

      grid.appendChild(weekCol);
    }
  }

  function getHeatmapColor(count) {
    if (count === 0) return 'bg-slate-800/90 border border-slate-700/60 hover:border-slate-400 shadow-sm';
    if (count <= 5) return 'bg-emerald-950 border border-emerald-800/90 hover:border-emerald-500 shadow-sm';
    if (count <= 15) return 'bg-emerald-800 border border-emerald-600/90 hover:border-emerald-400 shadow-sm';
    if (count <= 30) return 'bg-emerald-600 border border-emerald-500/90 hover:border-emerald-300 shadow-sm';
    return 'bg-emerald-400 border border-emerald-300 hover:border-white shadow-sm shadow-emerald-400/40';
  }

  // 直近セッション一覧
  function renderRecentSessions(sessions, periodDays = null) {
    recentSessionsBody.innerHTML = '';
    if (!sessions || sessions.length === 0) {
      const emptyMsg = periodDays
        ? `直近 ${periodDays} 日間の演習履歴はありません`
        : 'まだ演習セッションの履歴がありません';
      recentSessionsBody.innerHTML =
        `<tr><td colspan="4" class="py-4 text-center text-slate-500">${emptyMsg}</td></tr>`;
      return;
    }

    const modeLabels = {
      random: 'カテゴリ均等',
      all_random: '完全ランダム',
      category_weak: '苦手カテゴリ',
      question_weak: '苦手問題',
    };

    sessions.forEach((s) => {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-800/40 transition';
      const passColor = s.rate >= 72.0 ? 'text-emerald-400 font-bold' : 'text-slate-300';

      tr.innerHTML = `
        <td class="py-3 px-3 font-mono text-[11px] text-slate-400">${s.started_at}</td>
        <td class="py-3 px-3 font-medium text-slate-200">${modeLabels[s.mode] || s.mode}</td>
        <td class="py-3 px-3 font-mono">${s.answered}問</td>
        <td class="py-3 px-3 ${passColor}">${s.rate}%</td>
      `;
      recentSessionsBody.appendChild(tr);
    });
  }

  // スライダーイベントリスナー（動的更新）
  let debounceTimeout = null;
  slider.addEventListener('input', (e) => {
    const val = parseInt(e.target.value, 10);
    const dynamicSliderLabel = document.getElementById('sliderLabel');
    if (dynamicSliderLabel) dynamicSliderLabel.textContent = val;
    sliderValueBadge.textContent = `直近 ${val} 問`;

    const dynamicRecentN = document.getElementById('kpiRecentNLabel');
    if (dynamicRecentN) {
      dynamicRecentN.textContent = val;
    }

    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      currentRecentN = val;
      loadDashboard(currentRecentN, currentPeriodDays);
    }, 250);
  });


  // 初期読み込み実行
  loadDashboard(currentRecentN, currentPeriodDays);
});
