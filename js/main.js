/**
 * あおのデイリーニュース - メインJavaScript
 */

// グローバル設定
const CONFIG = {
    dataPath: 'data/news.json',
    archivePath: 'data/archive/',
    categories: ['ai', 'minpaku', 'rental']
};

// DOM読み込み完了時に実行
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

/**
 * アプリケーション初期化
 */
async function initApp() {
    setupCategoryTabs();
    await loadNews();
    await loadArchiveList();
    updateDateDisplay();
}

/**
 * カテゴリタブの設定
 */
function setupCategoryTabs() {
    const tabs = document.querySelectorAll('.category-tab');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // タブのアクティブ状態を切り替え
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // セクションの表示切り替え
            const category = tab.dataset.category;
            showSection(category);
        });
    });
}

/**
 * セクションの表示切り替え
 */
function showSection(category) {
    const sections = document.querySelectorAll('.news-section');

    sections.forEach(section => {
        section.classList.remove('active');
    });

    const targetSection = document.getElementById(`${category}-section`);
    if (targetSection) {
        targetSection.classList.add('active');
    }
}

/**
 * ニュースデータを読み込み
 */
async function loadNews(date = null) {
    try {
        const path = date
            ? `${CONFIG.archivePath}${date}.json`
            : CONFIG.dataPath;

        const response = await fetch(path);

        if (!response.ok) {
            throw new Error('ニュースデータの読み込みに失敗しました');
        }

        const data = await response.json();
        renderNews(data);

        // 日付表示を更新
        if (data.date) {
            document.getElementById('current-date').textContent = formatDate(data.date);
        }

    } catch (error) {
        console.error('Error loading news:', error);
        showError();
    }
}

/**
 * ニュースを描画
 */
function renderNews(data) {
    // AIニュース
    if (data.ai && data.ai.length > 0) {
        renderCategoryNews('ai-news', data.ai, 'ai');
    } else {
        showNoNews('ai-news');
    }

    // 民泊ニュース
    if (data.minpaku && data.minpaku.length > 0) {
        renderCategoryNews('minpaku-news', data.minpaku, 'minpaku');
    } else {
        showNoNews('minpaku-news');
    }

    // レンタルスペースニュース
    if (data.rental && data.rental.length > 0) {
        renderCategoryNews('rental-news', data.rental, 'rental');
    } else {
        showNoNews('rental-news');
    }
}

/**
 * カテゴリごとのニュースを描画
 */
function renderCategoryNews(containerId, newsItems, category) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = newsItems.map((item, index) => createNewsCard(item, category, index)).join('');

    // クリックイベントを設定
    setupCardToggle(container);
}

/**
 * カードの開閉イベントを設定
 */
function setupCardToggle(container) {
    const cards = container.querySelectorAll('.news-card');
    cards.forEach(card => {
        const header = card.querySelector('.news-card-header');
        header.addEventListener('click', () => {
            card.classList.toggle('expanded');
        });
    });
}

/**
 * ニュースカードのHTML生成
 */
function createNewsCard(item, category, index) {
    const toolBadges = item.tools
        ? `<div class="ai-tools-badge">
            ${item.tools.map(tool => `<span class="tool-badge ${tool.toLowerCase()}">${tool}</span>`).join('')}
           </div>`
        : '';

    // 配信日の表示
    const publishedDate = item.publishedDate
        ? `<span class="news-date">${escapeHtml(item.publishedDate)}</span>`
        : '';

    // 掲載元リンク
    const sourceLink = item.url
        ? `<a href="${item.url}" target="_blank" rel="noopener noreferrer" class="source-link" onclick="event.stopPropagation();">
            元記事を読む <span class="link-icon">&#x2197;</span>
           </a>`
        : '';

    return `
        <article class="news-card ${category}" data-index="${index}">
            <div class="news-card-header">
                <div class="news-card-title-area">
                    <h3 class="news-title">${escapeHtml(item.title)}</h3>
                    <div class="news-meta">
                        ${item.source ? `<span class="news-source">${escapeHtml(item.source)}</span>` : ''}
                        ${publishedDate}
                    </div>
                </div>
                <span class="toggle-icon">&#x25BC;</span>
            </div>

            <div class="news-card-body">
                <div class="news-summary">
                    <h4>まとめ</h4>
                    <p>${escapeHtml(item.summary)}</p>
                    ${toolBadges}
                </div>

                ${item.detail
                    ? `<div class="news-detail">
                        <h4>詳細</h4>
                        <p>${escapeHtml(item.detail)}</p>
                       </div>`
                    : ''
                }

                <div class="ao-comment">
                    <div class="ao-comment-header">
                        <span class="ao-avatar">あ</span>
                        あおの一言
                    </div>
                    <p class="ao-comment-text">${escapeHtml(item.aoComment)}</p>
                </div>

                ${sourceLink ? `<div class="source-link-area">${sourceLink}</div>` : ''}
            </div>
        </article>
    `;
}

/**
 * ニュースなし表示
 */
function showNoNews(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="no-news">
                <p>本日のニュースはまだありません。</p>
                <p>毎朝7時頃に更新されます。</p>
            </div>
        `;
    }
}

/**
 * エラー表示
 */
function showError() {
    CONFIG.categories.forEach(category => {
        const container = document.getElementById(`${category}-news`);
        if (container) {
            container.innerHTML = `
                <div class="error">
                    <p>ニュースの読み込みに失敗しました。</p>
                    <p>しばらく経ってから再度お試しください。</p>
                </div>
            `;
        }
    });
}

/**
 * アーカイブリストを読み込み
 */
async function loadArchiveList() {
    try {
        const response = await fetch('data/archive/index.json');

        if (!response.ok) {
            showNoArchive();
            return;
        }

        const archiveList = await response.json();
        renderArchiveList(archiveList);

    } catch (error) {
        console.error('Error loading archive list:', error);
        showNoArchive();
    }
}

/**
 * アーカイブリストを描画
 */
function renderArchiveList(archiveList) {
    const container = document.getElementById('archive-list');
    if (!container) return;

    if (!archiveList || archiveList.length === 0) {
        showNoArchive();
        return;
    }

    // 最新10件を表示
    const recentArchives = archiveList.slice(0, 10);

    container.innerHTML = recentArchives.map(date => `
        <a href="#" class="archive-link" data-date="${date}" onclick="loadArchiveNews('${date}'); return false;">
            ${formatDate(date)}
        </a>
    `).join('');
}

/**
 * アーカイブなし表示
 */
function showNoArchive() {
    const container = document.getElementById('archive-list');
    if (container) {
        container.innerHTML = '<p class="no-archive">まだアーカイブはありません。</p>';
    }
}

/**
 * アーカイブニュースを読み込み
 */
async function loadArchiveNews(date) {
    await loadNews(date);

    // スクロールをトップに
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * 日付表示を更新
 */
function updateDateDisplay() {
    const dateElement = document.getElementById('current-date');
    if (dateElement && dateElement.textContent === '-') {
        dateElement.textContent = formatDate(new Date().toISOString().split('T')[0]);
    }
}

/**
 * 日付フォーマット
 */
function formatDate(dateStr) {
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const weekdays = ['日', '月', '火', '水', '木', '金', '土'];
    const weekday = weekdays[date.getDay()];

    return `${year}年${month}月${day}日（${weekday}）`;
}

/**
 * HTMLエスケープ
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// グローバル関数としてエクスポート
window.loadArchiveNews = loadArchiveNews;
