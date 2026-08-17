// ── IDM Clone - YouTube Download Button ──────────────────────────────────────
// One-click approach: no server fetch needed for resolution list.
// We show a static standard-res dropdown immediately, then send to IDM.

(function () {
    'use strict';

    let injected = false;
    let lastUrl = '';
    let debounceTimer = null;

    const STANDARD_RES = ['2160p', '1440p', '1080p', '720p', '480p', '360p', '240p', '144p', 'best'];

    // ── Styles ──────────────────────────────────────────────────────────────────
    const STYLES = `
        #idm-panel {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 10px;
            padding: 8px 14px;
            background: rgba(0,0,0,0.55);
            border: 1px solid #444;
            border-radius: 10px;
            backdrop-filter: blur(6px);
            font-family: 'Roboto', sans-serif;
        }
        #idm-res-select {
            background: #222;
            color: #fff;
            border: 1px solid #555;
            border-radius: 6px;
            padding: 5px 10px;
            font-size: 13px;
            cursor: pointer;
            outline: none;
        }
        #idm-res-select:hover { border-color: #00ADB5; }
        #idm-sub-label {
            display: flex;
            align-items: center;
            gap: 5px;
            color: #ccc;
            font-size: 13px;
            cursor: pointer;
            user-select: none;
        }
        #idm-download-btn {
            background: linear-gradient(135deg, #00ADB5, #0090a0);
            color: #fff;
            border: none;
            border-radius: 7px;
            padding: 7px 18px;
            font-size: 13px;
            font-weight: bold;
            cursor: pointer;
            transition: opacity 0.2s, transform 0.1s;
            letter-spacing: 0.3px;
        }
        #idm-download-btn:hover { opacity: 0.88; transform: scale(1.03); }
        #idm-download-btn:active { transform: scale(0.97); }
        #idm-download-btn:disabled { opacity: 0.5; cursor: default; transform: none; }
        #idm-status-msg {
            font-size: 12px;
            color: #aaa;
            margin-left: 4px;
        }
    `;

    function injectStyles() {
        if (document.getElementById('idm-styles')) return;
        const el = document.createElement('style');
        el.id = 'idm-styles';
        el.textContent = STYLES;
        document.head.appendChild(el);
    }

    function removePanel() {
        const old = document.getElementById('idm-panel');
        if (old) old.remove();
        injected = false;
    }

    function injectPanel() {
        if (injected) return;

        // Find YouTube's title container
        const titleEl = document.querySelector('h1.ytd-watch-metadata yt-formatted-string') ||
                        document.querySelector('h1.ytd-watch-metadata') ||
                        document.querySelector('#above-the-fold #title h1');
        if (!titleEl) return;

        injectStyles();

        // Build panel
        const panel = document.createElement('div');
        panel.id = 'idm-panel';

        // Resolution select
        const resSelect = document.createElement('select');
        resSelect.id = 'idm-res-select';
        STANDARD_RES.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r;
            opt.textContent = r === 'best' ? '🔝 Best Quality' : `🎬 ${r}`;
            if (r === '1080p') opt.selected = true;
            resSelect.appendChild(opt);
        });

        // Subtitle checkbox
        const subLabel = document.createElement('label');
        subLabel.id = 'idm-sub-label';
        const subCheck = document.createElement('input');
        subCheck.type = 'checkbox';
        subCheck.id = 'idm-sub-check';
        subCheck.checked = true;
        subLabel.appendChild(subCheck);
        subLabel.append(' 📝 Subtitles (.srt)');

        // Download button
        const dlBtn = document.createElement('button');
        dlBtn.id = 'idm-download-btn';
        dlBtn.textContent = '⬇ Download';

        // Status message
        const statusMsg = document.createElement('span');
        statusMsg.id = 'idm-status-msg';

        panel.appendChild(resSelect);
        panel.appendChild(subLabel);
        panel.appendChild(dlBtn);
        panel.appendChild(statusMsg);

        // Insert after title element
        const parent = titleEl.closest('h1') || titleEl;
        parent.insertAdjacentElement('afterend', panel);

        injected = true;

        // ── Click handler ───────────────────────────────────────────────────────
        dlBtn.addEventListener('click', () => {
            // Strip playlist params — only keep the video ID
            const rawUrl = window.location.href;
            const urlObj = new URL(rawUrl);
            const videoId = urlObj.searchParams.get('v');
            const cleanUrl = videoId
                ? `https://www.youtube.com/watch?v=${videoId}`
                : rawUrl;

            const resolution = resSelect.value;
            const wantSubs = subCheck.checked;

            dlBtn.disabled = true;
            dlBtn.textContent = '⏳ Sending...';
            statusMsg.textContent = '';

            chrome.runtime.sendMessage({
                action: 'download',
                url: cleanUrl,
                type: 'youtube',
                resolution: resolution,
                separate_subs: wantSubs
            }, (response) => {
                if (chrome.runtime.lastError || !response) {
                    dlBtn.disabled = false;
                    dlBtn.textContent = '⬇ Download';
                    statusMsg.style.color = '#e74c3c';
                    statusMsg.textContent = '❌ Error — Is IDM Clone running?';
                    return;
                }
                if (response.status === 'success') {
                    dlBtn.textContent = '✅ Sent!';
                    statusMsg.style.color = '#2ecc71';
                    statusMsg.textContent = 'Added to download queue';
                    // Reset after 4s
                    setTimeout(() => {
                        dlBtn.disabled = false;
                        dlBtn.textContent = '⬇ Download';
                        statusMsg.textContent = '';
                    }, 4000);
                } else {
                    dlBtn.disabled = false;
                    dlBtn.textContent = '⬇ Download';
                    statusMsg.style.color = '#e74c3c';
                    statusMsg.textContent = '❌ Failed — check IDM Clone app';
                }
            });
        });
    }

    // ── Watch for navigation ────────────────────────────────────────────────────

    let retryTimer = null;
    let retryCount = 0;
    const MAX_RETRIES = 20;     // Try up to 20 times (20 × 500ms = 10 seconds max)
    const RETRY_INTERVAL = 500; // ms between each retry

    function tryInject() {
        const currentUrl = window.location.href;

        // Not a video page — clean up and stop
        if (!currentUrl.includes('watch?v=')) {
            removePanel();
            retryCount = 0;
            return;
        }

        // URL changed (navigated to a new video) — reset
        if (currentUrl !== lastUrl) {
            lastUrl = currentUrl;
            removePanel();
            retryCount = 0;
        }

        // Already injected for this URL
        if (injected) return;

        // Attempt injection
        injectPanel();

        if (injected) {
            // Success — stop retrying
            retryCount = 0;
            return;
        }

        // Failed — title not in DOM yet. Retry if budget remaining
        retryCount++;
        if (retryCount < MAX_RETRIES) {
            retryTimer = setTimeout(tryInject, RETRY_INTERVAL);
        }
    }

    function scheduleInject() {
        clearTimeout(debounceTimer);
        clearTimeout(retryTimer);
        retryCount = 0;
        debounceTimer = setTimeout(tryInject, 300);
    }

    // Listen to YouTube's own navigation event (most reliable)
    window.addEventListener('yt-navigate-finish', scheduleInject);

    // Also watch DOM mutations for older YouTube builds / fallback
    const observer = new MutationObserver(scheduleInject);
    observer.observe(document.body, { childList: true, subtree: false });

    // Run immediately on first load (e.g. direct URL open)
    scheduleInject();
})();
