// Discord Lyric Status Sync Frontend Logic
document.addEventListener("DOMContentLoaded", () => {
    // --- State ---
    let isAuthenticated = false;
    let lyrics = [];
    let trackInfo = null;
    let currentState = "stopped"; // "stopped", "playing", "paused"
    let currentLineIdx = -1;
    let pollInterval = null;

    // --- DOM Elements ---
    const authInput = document.getElementById("authInput");
    const togglePasswordBtn = document.getElementById("togglePasswordBtn");
    const verifyBtn = document.getElementById("verifyBtn");
    const testStatusBtn = document.getElementById("testStatusBtn");
    const clearStatusBtn = document.getElementById("clearStatusBtn");
    const connectionPill = document.getElementById("connectionPill");
    const connectionText = document.getElementById("connectionText");
    const userProfile = document.getElementById("userProfile");
    const userAvatar = document.getElementById("userAvatar");
    const userGlobalName = document.getElementById("userGlobalName");
    const userHandle = document.getElementById("userHandle");
    const userId = document.getElementById("userId");

    const copySnippetBtn = document.getElementById("copySnippetBtn");
    const tokenSnippet = document.getElementById("tokenSnippet");

    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    const songUrlInput = document.getElementById("songUrlInput");
    const fetchUrlBtn = document.getElementById("fetchUrlBtn");

    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");

    const loadSampleBtns = document.querySelectorAll(".load-sample-btn");

    const currentTrackTitle = document.getElementById("currentTrackTitle");
    const currentTrackArtist = document.getElementById("currentTrackArtist");
    const currentTimeDisplay = document.getElementById("currentTimeDisplay");
    const totalTimeDisplay = document.getElementById("totalTimeDisplay");
    const timelineSlider = document.getElementById("timelineSlider");

    const btnPlay = document.getElementById("btnPlay");
    const btnPause = document.getElementById("btnPause");
    const btnStop = document.getElementById("btnStop");

    const offsetValue = document.getElementById("offsetValue");
    const offsetBtns = document.querySelectorAll(".btn-offset");

    const previewAvatar = document.getElementById("previewAvatar");
    const previewDisplayName = document.getElementById("previewDisplayName");
    const previewUsername = document.getElementById("previewUsername");
    const previewEmoji = document.getElementById("previewEmoji");
    const previewStatusText = document.getElementById("previewStatusText");

    const lyricsContainer = document.getElementById("lyricsContainer");
    const lyricsCount = document.getElementById("lyricsCount");

    const logContainer = document.getElementById("logContainer");
    const clearLogsBtn = document.getElementById("clearLogsBtn");

    const emojiInput = document.getElementById("emojiInput");
    const formatSelect = document.getElementById("formatSelect");
    const targetSelect = document.getElementById("targetSelect");
    const clearOnFinishCheck = document.getElementById("clearOnFinishCheck");

    const searchModal = document.getElementById("searchModal");
    const closeModalBtn = document.getElementById("closeModalBtn");
    const candidateList = document.getElementById("candidateList");

    // --- Helper Functions ---
    function formatTime(seconds) {
        if (isNaN(seconds) || seconds < 0) seconds = 0;
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    function addLogEntry(message, level = "info") {
        const entry = document.createElement("div");
        entry.className = `log-entry ${level}`;
        const now = new Date();
        const timeStr = now.toTimeString().split(' ')[0];
        entry.innerHTML = `<span class="log-time">${timeStr}</span> <span>${message}</span>`;
        logContainer.appendChild(entry);
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    // --- Toggle Password Visibility ---
    togglePasswordBtn.addEventListener("click", () => {
        if (authInput.type === "password") {
            authInput.type = "text";
            togglePasswordBtn.textContent = "🙈";
        } else {
            authInput.type = "password";
            togglePasswordBtn.textContent = "👁️";
        }
    });

    // --- Copy Snippet ---
    copySnippetBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(tokenSnippet.textContent).then(() => {
            copySnippetBtn.textContent = "✅ Đã Copy!";
            setTimeout(() => copySnippetBtn.textContent = "📋 Copy", 2000);
        }).catch(() => {
            alert("Không thể tự copy. Hãy bôi đen đoạn mã và nhấn Ctrl+C");
        });
    });

    // --- Tab Navigation ---
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));
            btn.classList.add("active");
            document.getElementById(btn.dataset.tab).classList.add("active");
        });
    });

    // --- Discord Auth Verify ---
    verifyBtn.addEventListener("click", async () => {
        const val = authInput.value.trim();
        if (!val) {
            alert("Vui lòng dán Token hoặc Cookie Discord!");
            return;
        }

        verifyBtn.disabled = true;
        verifyBtn.innerHTML = "⏳ Đang kiểm tra...";

        try {
            const resp = await fetch("/api/auth/verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ auth_input: val })
            });
            const data = await resp.json();

            if (data.success) {
                isAuthenticated = true;
                const user = data.user;
                
                // Update header pill
                connectionPill.className = "status-pill online";
                connectionText.textContent = `@${user.username} (Đã kết nối)`;

                // Update user banner
                userAvatar.src = user.avatar_url;
                userGlobalName.textContent = user.global_name;
                userHandle.textContent = `@${user.username}`;
                userId.textContent = user.id;
                userProfile.classList.remove("hidden");

                // Update preview card
                previewAvatar.src = user.avatar_url;
                previewDisplayName.textContent = user.global_name;
                previewUsername.textContent = `@${user.username}`;

                // Enable action buttons
                testStatusBtn.disabled = false;
                clearStatusBtn.disabled = false;
                if (lyrics.length > 0) btnPlay.disabled = false;

                addLogEntry(`Đăng nhập thành công: @${user.username} (${user.global_name})`, "success");
            } else {
                alert(`Lỗi đăng nhập: ${data.error}`);
                addLogEntry(`Lỗi xác thực: ${data.error}`, "error");
            }
        } catch (err) {
            alert("Lỗi kết nối máy chủ backend: " + err.message);
        } finally {
            verifyBtn.disabled = false;
            verifyBtn.innerHTML = '<span class="btn-icon">⚡</span> Xác Thực Tài Khoản';
        }
    });

    // --- Test Status ---
    testStatusBtn.addEventListener("click", async () => {
        testStatusBtn.disabled = true;
        try {
            const resp = await fetch("/api/discord/test-status", { method: "POST" });
            const data = await resp.json();
            if (data.success) {
                previewStatusText.textContent = "🎵 Đang kiểm tra tool đổi lyric status...";
                addLogEntry("Đã đổi trạng thái thử nghiệm lên Discord!", "success");
            } else {
                addLogEntry(`Lỗi test status: ${data.error}`, "error");
            }
        } catch (err) {
            addLogEntry("Lỗi gửi test status: " + err.message, "error");
        } finally {
            testStatusBtn.disabled = false;
        }
    });

    // --- Clear Status ---
    clearStatusBtn.addEventListener("click", async () => {
        clearStatusBtn.disabled = true;
        try {
            const resp = await fetch("/api/discord/clear-status", { method: "POST" });
            const data = await resp.json();
            if (data.success) {
                previewStatusText.textContent = "Chưa có trạng thái";
                addLogEntry("Đã xóa trạng thái trên tài khoản Discord", "info");
            }
        } finally {
            clearStatusBtn.disabled = false;
        }
    });

    // --- Render Lyrics in Karaoke Scroller ---
    function renderLyrics(lyricList) {
        lyrics = lyricList;
        lyricsCount.textContent = `${lyrics.length} câu`;
        lyricsContainer.innerHTML = "";

        if (!lyrics || lyrics.length === 0) {
            lyricsContainer.innerHTML = `
                <div class="empty-lyrics-state">
                    <div class="empty-icon">📜</div>
                    <p>Chưa có lời bài hát nào</p>
                    <span>Hãy quét từ link hoặc tải file .lrc để bắt đầu xem lời và đồng bộ</span>
                </div>
            `;
            return;
        }

        lyrics.forEach((item, idx) => {
            const row = document.createElement("div");
            row.className = "lyric-line";
            row.dataset.index = idx;
            row.dataset.time = item.time;

            row.innerHTML = `
                <span class="lyric-time">${item.time_str}</span>
                <span class="lyric-text">${item.text}</span>
            `;

            row.addEventListener("click", () => {
                seekTo(item.time);
            });

            lyricsContainer.appendChild(row);
        });

        // Set timeline slider max
        const lastTime = lyrics[lyrics.length - 1].time;
        timelineSlider.max = Math.ceil(lastTime + 10);
        totalTimeDisplay.textContent = formatTime(timelineSlider.max);

        if (isAuthenticated) {
            btnPlay.disabled = false;
        }
    }

    // --- Fetch Lyrics by URL or Song Name ---
    fetchUrlBtn.addEventListener("click", async () => {
        const query = songUrlInput.value.trim();
        if (!query) {
            alert("Vui lòng nhập link bài hát hoặc tên bài hát!");
            return;
        }

        fetchUrlBtn.disabled = true;
        fetchUrlBtn.innerHTML = "⏳ Đang quét...";

        try {
            const resp = await fetch("/api/lyrics/fetch-url", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: query })
            });
            const data = await resp.json();

            if (data.success) {
                trackInfo = data.track_info;
                currentTrackTitle.textContent = trackInfo.track_name;
                currentTrackArtist.textContent = trackInfo.artist_name || "Ca sĩ";
                renderLyrics(data.lyrics);

                addLogEntry(`Đã tải thành công lời bài hát: ${trackInfo.track_name} (${data.lyrics.length} câu)`, "success");

                if (data.is_plain_fallback) {
                    addLogEntry("⚠️ Lưu ý: Bài hát này chỉ có lời thường, tool tự động phân bổ nhịp đều 4s/câu.", "info");
                }
            } else {
                // If not found, open candidate search
                addLogEntry(data.error || "Không tìm thấy lời bài hát.", "error");
                openSearchModal(query);
            }
        } catch (err) {
            addLogEntry("Lỗi quét link: " + err.message, "error");
        } finally {
            fetchUrlBtn.disabled = false;
            fetchUrlBtn.innerHTML = '<span class="btn-icon">🔍</span> Quét Lời Nhạc';
        }
    });

    songUrlInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") fetchUrlBtn.click();
    });

    // --- Candidate Search Modal ---
    async function openSearchModal(query) {
        searchModal.classList.remove("hidden");
        candidateList.innerHTML = "<p style='color: var(--text-muted);'>Đang tìm kiếm bản ghi khác...</p>";
        try {
            const resp = await fetch(`/api/lyrics/search?q=${encodeURIComponent(query)}`);
            const data = await resp.json();
            if (data.success && data.results.length > 0) {
                candidateList.innerHTML = "";
                data.results.forEach(item => {
                    const el = document.createElement("div");
                    el.className = "candidate-item";
                    el.innerHTML = `
                        <div>
                            <strong>${item.track_name}</strong> - <span>${item.artist_name}</span>
                            <div style="font-size: 11px; color: var(--text-muted);">${item.album_name || ''}</div>
                        </div>
                        <div>
                            ${item.has_synced ? '<span class="candidate-synced-badge">LRC Chuẩn Giây ✅</span>' : '<span style="font-size: 10px; color: var(--text-muted);">Lời thường</span>'}
                        </div>
                    `;
                    el.addEventListener("click", async () => {
                        searchModal.classList.add("hidden");
                        const selResp = await fetch("/api/lyrics/select-candidate", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify(item)
                        });
                        const selData = await selResp.json();
                        if (selData.success) {
                            trackInfo = selData.track_info;
                            currentTrackTitle.textContent = trackInfo.track_name;
                            currentTrackArtist.textContent = trackInfo.artist_name;
                            renderLyrics(selData.lyrics);
                            addLogEntry(`Đã nạp bài hát: ${trackInfo.track_name}`, "success");
                        }
                    });
                    candidateList.appendChild(el);
                });
            } else {
                candidateList.innerHTML = "<p style='color: var(--red);'>Không tìm thấy bản ghi nào trên cơ sở dữ liệu. Bạn vui lòng dùng Tab 'Tải File' để chọn tệp .lrc!</p>";
            }
        } catch (err) {
            candidateList.innerHTML = `<p style='color: var(--red);'>Lỗi: ${err.message}</p>`;
        }
    }

    closeModalBtn.addEventListener("click", () => searchModal.classList.add("hidden"));

    // --- File Drag & Drop Upload ---
    dropZone.addEventListener("click", () => fileInput.click());

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    async function handleFileUpload(file) {
        const formData = new FormData();
        formData.append("file", file);

        addLogEntry(`Đang tải lên tệp: ${file.name}...`, "info");
        try {
            const resp = await fetch("/api/lyrics/upload", {
                method: "POST",
                body: formData
            });
            const data = await resp.json();
            if (data.success) {
                trackInfo = data.track_info;
                currentTrackTitle.textContent = trackInfo.track_name;
                currentTrackArtist.textContent = trackInfo.artist_name;
                renderLyrics(data.lyrics);
                addLogEntry(`Đã nạp thành công ${data.lyrics.length} câu hát từ tệp ${file.name}`, "success");
            } else {
                alert(`Lỗi đọc tệp: ${data.error}`);
            }
        } catch (err) {
            alert("Lỗi tải tệp: " + err.message);
        }
    }

    // --- Load Sample Songs ---
    loadSampleBtns.forEach(btn => {
        btn.addEventListener("click", async () => {
            const sampleName = btn.dataset.sample;
            btn.disabled = true;
            try {
                const resp = await fetch(`/api/lyrics/sample/${sampleName}`);
                const data = await resp.json();
                if (data.success) {
                    trackInfo = data.track_info;
                    currentTrackTitle.textContent = trackInfo.track_name;
                    currentTrackArtist.textContent = trackInfo.artist_name;
                    renderLyrics(data.lyrics);
                    addLogEntry(`Đã tải bài hát mẫu: ${trackInfo.track_name}`, "success");
                }
            } catch (err) {
                alert("Lỗi tải mẫu: " + err.message);
            } finally {
                btn.disabled = false;
            }
        });
    });

    // --- Playback Controls ---
    btnPlay.addEventListener("click", async () => {
        if (!isAuthenticated) {
            alert("Vui lòng xác thực tài khoản Discord trước!");
            return;
        }
        if (lyrics.length === 0) {
            alert("Chưa có bài hát nào được nạp!");
            return;
        }

        const resp = await fetch("/api/sync/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ start_time: parseFloat(timelineSlider.value) || 0.0 })
        });
        const data = await resp.json();
        if (data.success) {
            currentState = "playing";
            btnPlay.style.display = "none";
            btnPause.style.display = "inline-flex";
            btnStop.disabled = false;
            startPolling();
        } else {
            alert(data.message || data.error);
        }
    });

    btnPause.addEventListener("click", async () => {
        const resp = await fetch("/api/sync/pause", { method: "POST" });
        const data = await resp.json();
        if (data.success) {
            currentState = "paused";
            btnPause.style.display = "none";
            btnPlay.style.display = "inline-flex";
            btnPlay.innerHTML = '<span class="btn-icon">▶</span> Tiếp Tục Đồng Bộ';
        }
    });

    btnStop.addEventListener("click", async () => {
        const resp = await fetch("/api/sync/stop", { method: "POST" });
        const data = await resp.json();
        if (data.success) {
            currentState = "stopped";
            btnPlay.style.display = "inline-flex";
            btnPlay.innerHTML = '<span class="btn-icon">▶</span> Bắt Đầu Đồng Bộ';
            btnPause.style.display = "none";
            btnStop.disabled = true;
            timelineSlider.value = 0;
            currentTimeDisplay.textContent = "00:00";
            clearActiveKaraokeHighlight();
            previewStatusText.textContent = "Chưa có trạng thái";
        }
    });

    async function seekTo(targetTime) {
        timelineSlider.value = targetTime;
        currentTimeDisplay.textContent = formatTime(targetTime);
        await fetch("/api/sync/seek", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ time: targetTime })
        });
    }

    timelineSlider.addEventListener("input", (e) => {
        currentTimeDisplay.textContent = formatTime(e.target.value);
    });

    timelineSlider.addEventListener("change", (e) => {
        seekTo(parseFloat(e.target.value));
    });

    // --- Offset Calibrator ---
    offsetBtns.forEach(btn => {
        btn.addEventListener("click", async () => {
            const delta = parseFloat(btn.dataset.delta);
            const resp = await fetch("/api/sync/offset", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ delta: delta })
            });
            const data = await resp.json();
            if (data.success) {
                const off = data.offset;
                offsetValue.textContent = (off >= 0 ? "+" : "") + off.toFixed(2) + "s";
            }
        });
    });

    // --- Settings Updates ---
    function sendSettingsUpdate() {
        const config = {
            emoji: emojiInput.value.trim() || "🎵",
            format: formatSelect.value,
            target: targetSelect.value,
            clear_on_finish: clearOnFinishCheck.checked
        };
        fetch("/api/sync/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(config)
        });
        previewEmoji.textContent = config.emoji;
    }

    emojiInput.addEventListener("input", sendSettingsUpdate);
    formatSelect.addEventListener("change", sendSettingsUpdate);
    targetSelect.addEventListener("change", sendSettingsUpdate);
    clearOnFinishCheck.addEventListener("change", sendSettingsUpdate);

    // --- Karaoke Active Line Highlight ---
    function highlightKaraokeLine(idx) {
        if (idx === currentLineIdx) return;
        currentLineIdx = idx;

        const allRows = lyricsContainer.querySelectorAll(".lyric-line");
        allRows.forEach(r => r.classList.remove("active"));

        if (idx >= 0 && idx < allRows.length) {
            const activeRow = allRows[idx];
            activeRow.classList.add("active");
            activeRow.scrollIntoView({ behavior: "smooth", block: "center" });

            // Update Discord live preview
            const lineData = lyrics[idx];
            previewStatusText.textContent = lineData.text;
        }
    }

    function clearActiveKaraokeHighlight() {
        currentLineIdx = -1;
        const allRows = lyricsContainer.querySelectorAll(".lyric-line");
        allRows.forEach(r => r.classList.remove("active"));
    }

    // --- State Poller Loop ---
    async function pollState() {
        try {
            const resp = await fetch("/api/sync/state");
            if (!resp.ok) return;
            const data = await resp.json();

            // Update timing
            if (data.state === "playing") {
                timelineSlider.value = data.current_time;
                currentTimeDisplay.textContent = formatTime(data.current_time);
                highlightKaraokeLine(data.current_line_idx);
            } else if (data.state === "finished") {
                currentState = "stopped";
                btnPlay.style.display = "inline-flex";
                btnPlay.innerHTML = '<span class="btn-icon">▶</span> Bắt Đầu Đồng Bộ';
                btnPause.style.display = "none";
                btnStop.disabled = true;
                clearActiveKaraokeHighlight();
            }

            // Update live status text on mockup if present
            if (data.last_sent_text) {
                previewStatusText.textContent = data.last_sent_text;
            }
        } catch (e) {
            // silent catch
        }
    }

    function startPolling() {
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(pollState, 200);
    }

    // Background poll every 1.5s for logs / state
    setInterval(pollState, 1500);

    // Clear logs
    clearLogsBtn.addEventListener("click", () => {
        logContainer.innerHTML = '<div class="log-entry info"><span class="log-time">--:--:--</span> Nhật ký đã được xóa.</div>';
    });
});
