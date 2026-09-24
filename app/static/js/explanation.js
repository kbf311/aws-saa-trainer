/**
 * AWS SAA Trainer - 解説フォーマッター
 * 問題解説文 (explanation) のMarkdownライクな見出し (**見出し**: 本文) を解析し、
 * 正解アプローチを強調表示するリッチなHTMLに変換します。
 */

(function () {
  // HTML特殊文字のエスケープ
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // 文中のインライン記法 (**太字** や `コード`) を安全にHTMLタグへ変換し、句点および改行による改行を適用
  function inlineFormat(text) {
    if (!text) return '';
    let safe = escapeHtml(text);
    safe = safe
      .replace(/\*\*([^*]+)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
      .replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded text-[0.9em] bg-slate-950/80 border border-slate-700 text-amber-300 font-mono">$1</code>');
    // 句点の直後に文字が続く場合の <br> 挿入
    safe = safe.replace(/。(?![\r\n]|$)/g, '。<br>');
    // 改行コードの <br> 変換
    safe = safe.replace(/\r?\n/g, '<br>');
    return safe;
  }

  /**
   * 解説テキストをパースして見出し・本文・正解フラグの配列に変換
   * @param {string} rawText 
   * @returns {Array<{title: string|null, body: string, isCorrect: boolean, isIntro: boolean}>}
   */
  function parseExplanation(rawText) {
    if (!rawText || !rawText.trim()) return [];

    const blocks = rawText
      .split(/\n\s*\n/)
      .map(b => b.trim())
      .filter(Boolean);

    if (blocks.length === 0) return [];

    const results = [];
    let firstTitleGroupFound = false;

    for (const block of blocks) {
      const lines = block.split('\n');
      const hasTitle = lines.some(l => /^\*\*([^*]+)\*\*[:：]/.test(l.trim()));

      let isCorrectGroup = false;
      if (hasTitle && !firstTitleGroupFound) {
        firstTitleGroupFound = true;
        isCorrectGroup = true;
      }

      let currTitle = null;
      let currLines = [];

      for (const line of lines) {
        const lineStr = line.trim();
        if (!lineStr) continue;

        // **見出し**: 本文 の正規表現パターン
        const match = lineStr.match(/^\*\*([^*]+)\*\*[:：]\s*(.*)$/);
        if (match) {
          if (currTitle !== null) {
            results.push({
              title: currTitle,
              body: currLines.join('\n'),
              isCorrect: isCorrectGroup,
              isIntro: false
            });
            currLines = [];
          }
          currTitle = match[1].trim();
          if (match[2].trim()) {
            currLines.push(match[2].trim());
          }
        } else {
          currLines.push(lineStr);
        }
      }

      if (currTitle !== null) {
        results.push({
          title: currTitle,
          body: currLines.join('\n'),
          isCorrect: isCorrectGroup,
          isIntro: false
        });
      } else if (currLines.length > 0) {
        results.push({
          title: null,
          body: currLines.join('\n'),
          isCorrect: false,
          isIntro: !firstTitleGroupFound // まだ正解見出しの前にある場合はイントロ文
        });
      }
    }

    return results;
  }

  /**
   * 解説テキストをリッチなHTMLにフォーマットして出力
   * @param {string} rawText 
   * @returns {string} HTML文字列
   */
  function formatExplanationHtml(rawText) {
    if (!rawText || !rawText.trim()) {
      return '<p class="text-slate-400 text-sm">解説はありません。</p>';
    }

    const sections = parseExplanation(rawText);

    // 見出しが全く見つからなかった場合は安全なフォールバック
    if (sections.length === 0 || sections.every(s => !s.title)) {
      return rawText
        .split(/\n\s*\n/)
        .map(p => `<p class="mb-3 text-slate-200 text-sm leading-relaxed">${inlineFormat(p)}</p>`)
        .join('');
    }

    const correctSections = sections.filter(s => s.isCorrect);
    const otherSections = sections.filter(s => !s.isCorrect && !s.isIntro);
    const introSections = sections.filter(s => s.isIntro);

    let html = '';

    // 1. 設問の前提・イントロダクション（存在する場合のみ）
    if (introSections.length > 0) {
      for (const intro of introSections) {
        html += `
          <div class="mb-4 p-3.5 rounded-xl bg-sky-950/30 border border-sky-500/30 text-sky-200 text-xs sm:text-sm flex items-start gap-2.5">
            <i class="fa-solid fa-circle-info text-sky-400 mt-0.5 text-base flex-shrink-0"></i>
            <div class="leading-relaxed text-slate-200">${inlineFormat(intro.body)}</div>
          </div>
        `;
      }
    }

    // 2. 正解のアプローチ・ソリューション（目立つスタイル！）
    if (correctSections.length > 0) {
      for (const correct of correctSections) {
        html += `
          <div class="mb-4 rounded-xl border-2 border-emerald-500/50 bg-gradient-to-br from-emerald-950/50 via-slate-900/90 to-slate-900/90 p-4 sm:p-5 shadow-lg shadow-emerald-950/30 transition">
            <div class="flex flex-wrap items-center gap-2 mb-2">
              <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                <i class="fa-solid fa-circle-check text-emerald-400 text-xs"></i>
                正解のアプローチ
              </span>
              <h4 class="font-bold text-sm sm:text-base text-emerald-300 tracking-wide">${escapeHtml(correct.title)}</h4>
            </div>
            <div class="text-xs sm:text-sm text-slate-200 leading-relaxed font-normal">${inlineFormat(correct.body)}</div>
          </div>
        `;
      }
    }

    // 3. 不正解選択肢の解説（整理されたカードスタイル）
    if (otherSections.length > 0) {
      html += `
        <div class="mt-4 pt-2">
          <div class="flex items-center gap-2 mb-3 text-xs font-bold text-slate-400 uppercase tracking-wider">
            <i class="fa-solid fa-list-check text-slate-500"></i>
            <span>選択肢の検討・不正解の理由</span>
          </div>
          <div class="space-y-2.5">
      `;

      for (const other of otherSections) {
        html += `
          <div class="rounded-xl border border-slate-700/60 bg-slate-800/40 p-3 sm:p-4 hover:border-slate-600/80 transition">
            <div class="flex items-center gap-2 mb-1.5">
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-700/50 text-slate-400 border border-slate-600/40 flex-shrink-0">
                <i class="fa-solid fa-circle-xmark text-rose-400/80 text-[10px]"></i>
                不正解
              </span>
              <h5 class="font-semibold text-xs sm:text-sm text-slate-200">${escapeHtml(other.title)}</h5>
            </div>
            <div class="text-xs sm:text-sm text-slate-400 leading-relaxed pl-1">${inlineFormat(other.body)}</div>
          </div>
        `;
      }

      html += `
          </div>
        </div>
      `;
    }

    return html;
  }

  /**
   * 選択肢構造化データ付きの解説HTMLフォーマット
   * @param {string} overallExplanation 
   * @param {Array<{id: string, text: string, explanation?: string, is_correct?: boolean}>} options 
   * @returns {string} HTML文字列
   */
  function formatStructuredExplanationHtml(overallExplanation, options) {
    if (!options || options.length === 0 || !options.some(o => o.explanation)) {
      // 選択肢解説がない場合は従来のパース処理へフォールバック
      return formatExplanationHtml(overallExplanation);
    }

    let html = '';

    // 1. 全体解説・アーキテクチャの要点
    if (overallExplanation && overallExplanation.trim()) {
      html += `
        <div class="mb-5 p-4 rounded-xl bg-gradient-to-r from-sky-950/40 via-slate-900/80 to-slate-900/80 border border-sky-500/30 text-slate-200 text-xs sm:text-sm shadow-md">
          <div class="flex items-center gap-2 mb-2 font-bold text-sky-400">
            <i class="fa-solid fa-circle-info text-base"></i>
            <span>アーキテクチャの要点・解説</span>
          </div>
          <div class="leading-relaxed pl-1">${inlineFormat(overallExplanation)}</div>
        </div>
      `;
    }

    // 2. 正解の選択肢解説
    const correctOptions = options.filter(o => o.is_correct);
    if (correctOptions.length > 0) {
      for (const opt of correctOptions) {
        html += `
          <div class="mb-4 rounded-xl border-2 border-emerald-500/50 bg-gradient-to-br from-emerald-950/50 via-slate-900/90 to-slate-900/90 p-4 sm:p-5 shadow-lg shadow-emerald-950/30 transition">
            <div class="flex flex-wrap items-center gap-2 mb-2">
              <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                <i class="fa-solid fa-circle-check text-emerald-400 text-xs"></i>
                正解の選択肢 [${escapeHtml(opt.id)}]
              </span>
              <span class="text-xs text-slate-300 font-medium truncate max-w-md">${escapeHtml(opt.text)}</span>
            </div>
            <div class="text-xs sm:text-sm text-slate-200 leading-relaxed font-normal">${inlineFormat(opt.explanation || '')}</div>
          </div>
        `;
      }
    }

    // 3. 不正解の選択肢解説
    const incorrectOptions = options.filter(o => !o.is_correct);
    if (incorrectOptions.length > 0) {
      html += `
        <div class="mt-4 pt-2">
          <div class="flex items-center gap-2 mb-3 text-xs font-bold text-slate-400 uppercase tracking-wider">
            <i class="fa-solid fa-list-check text-slate-500"></i>
            <span>選択肢の検討・不正解の理由</span>
          </div>
          <div class="space-y-2.5">
      `;

      for (const opt of incorrectOptions) {
        html += `
          <div class="rounded-xl border border-slate-700/60 bg-slate-800/40 p-3 sm:p-4 hover:border-slate-600/80 transition">
            <div class="flex items-center gap-2 mb-1.5">
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-700/50 text-slate-400 border border-slate-600/40 flex-shrink-0">
                <i class="fa-solid fa-circle-xmark text-rose-400/80 text-[10px]"></i>
                選択肢 [${escapeHtml(opt.id)}] 不正解
              </span>
              <span class="text-xs text-slate-400 truncate">${escapeHtml(opt.text)}</span>
            </div>
            <div class="text-xs sm:text-sm text-slate-300 leading-relaxed pl-1">${inlineFormat(opt.explanation || '')}</div>
          </div>
        `;
      }

      html += `
          </div>
        </div>
      `;
    }

    return html;
  }

  // グローバル（window）にエクスポート
  window.formatExplanationHtml = formatExplanationHtml;
  window.formatStructuredExplanationHtml = formatStructuredExplanationHtml;
  window.inlineFormat = inlineFormat;
  window.escapeHtml = window.escapeHtml || escapeHtml;
})();
