/**
 * Seekphoney - Simplified Controller Focus
 */

const API_BASE_URL = 'http://127.0.0.1:8000';
let mediaRecorder = null;
let audioChunks = [];
let dynamicCatalog = [];
let hummingChartInstance = null;
let recordingCountdownTimer = null;
let overallGaugeChartInstance = null;
// Optional: Add your custom Google Developer YouTube Data API Key here if needed
const YOUTUBE_API_KEY = "YOUR_YOUTUBE_API_KEY_HERE"; // Replace with your actual API key or leave empty for fallback

function setupEventListeners() {
    document.getElementById('searchButton')?.addEventListener('click', handleTextSearch);
    document.getElementById('searchInput')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleTextSearch();
    });
    document.getElementById('micButton')?.addEventListener('click', toggleAudioRecording);
}

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

function stopYouTubeVideo() {
    const iframe = document.getElementById('youtubePlayerFrame');
    if (iframe) iframe.src = '';
    updateYouTubeStreamLink('#', 'No stream loaded');
    
    document.querySelectorAll('[id^="play-btn-"]').forEach(btn => {
        btn.innerHTML = '<i class="bi bi-play-fill me-1"></i>Play';
    });
}

function normalizeSong(song) {
    return {
        id: song.id ?? 999,
        title: song.title || "Unknown Track",
        artist: song.artist || "Unknown Artist",
        genre: song.genre || "General",
        source_url: song.source_url || ""
    };
}

function extractYouTubeVideoId(value) {
    if (!value) return "";

    const text = String(value).trim();
    const patterns = [
        /(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/|live\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/,
        /[?&]v=([a-zA-Z0-9_-]{11})/,
        /"videoId":"([a-zA-Z0-9_-]{11})"/,
    ];

    for (const pattern of patterns) {
        const match = text.match(pattern);
        if (match && match[1]) {
            return match[1];
        }
    }

    if (/^[a-zA-Z0-9_-]{11}$/.test(text)) {
        return text;
    }

    return "";
}

function playYouTubeEmbed(videoId) {
    const playerFrame = document.getElementById('youtubePlayerFrame');
    if (!playerFrame) return false;

    const watchUrl = `https://www.youtube.com/watch?v=${videoId}`;
    playerFrame.src = `https://www.youtube.com/embed/${videoId}?autoplay=1&mute=0&controls=1&origin=${encodeURIComponent(window.location.origin)}`;

    const streamLink = document.getElementById('youtubeStreamLink');
    if (streamLink) {
        streamLink.href = watchUrl;
        streamLink.textContent = watchUrl;
    }
    return true;
}

function buildYouTubeSearchUrl(title, artist) {
    const query = `${title} ${artist} official audio`.trim();
    return `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
}

function updateYouTubeStreamLink(url, label) {
    const streamLink = document.getElementById('youtubeStreamLink');
    if (!streamLink) return;

    streamLink.href = url || '#';
    streamLink.textContent = label || url || 'No stream loaded';
}

// --- TEXT SEARCH ASSIGNMENT FLOW ---
async function handleTextSearch() {
    const queryInput = document.getElementById('searchInput');
    const query = queryInput ? queryInput.value.trim() : "";
    if (!query) return;

    stopYouTubeVideo();

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (response.ok && data.song) {
            const matchedSong = normalizeSong(data.song);
            dynamicCatalog = [matchedSong];
            renderCatalog(dynamicCatalog);
            showSystemAlert("alertContainer", `Match found: "${matchedSong.title}"`, "success");
        } else {
            renderCatalog([]);
            showSystemAlert("alertContainer", data.message || "No exact match found in catalog.", "warning");
        }
    } catch (error) {
        console.error(error);
        showSystemAlert("alertContainer", "Search backend service is currently unreachable.", "danger");
    }
}

// --- AUDIO RECORDING OPERATION ---
async function toggleAudioRecording() {
    const micButton = document.getElementById('micButton');
    const micIcon = document.getElementById('micIcon');
    const micProgressText = document.getElementById('micProgressText');
    const recordingStatus = document.getElementById('recordingStatus');

    stopYouTubeVideo();

    // If already recording, stop it immediately on click
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            // Clean up timer and UI states when recording stops
            clearInterval(recordingCountdownTimer);
            stream.getTracks().forEach(track => track.stop());
            
            // Revert button layout back to standard mic icon state
            micButton.className = "btn btn-outline-danger d-flex align-items-center";
            micProgressText.classList.add('d-none');
            recordingStatus.classList.add('d-none');
            micIcon.className = "bi bi-mic-fill me-1";

            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await handleAudioSearch(audioBlob);
        };

        // Start recording
        mediaRecorder.start();
        
        // Transform the button into an active red recording bar status indicator
        micButton.className = "btn btn-danger text-white d-flex align-items-center animate-pulse";
        micProgressText.classList.remove('d-none');
        recordingStatus.classList.remove('d-none');
        micIcon.className = "bi bi-record-circle-fill text-white spinner-border-sm me-1";

        let timeLeft = 10;
        micProgressText.innerText = `Recording (${timeLeft}s)`;

        // Update countdown text every second
        recordingCountdownTimer = setInterval(() => {
            timeLeft--;
            if (timeLeft > 0) {
                micProgressText.innerText = `Recording (${timeLeft}s)`;
            } else {
                clearInterval(recordingCountdownTimer);
                if (mediaRecorder && mediaRecorder.state === "recording") {
                    mediaRecorder.stop();
                }
            }
        }, 1000);

    } catch (err) {
        console.error("Microphone hardware error context:", err);
        showSystemAlert("alertContainer", "Microphone access denied or audio hardware not found.", "danger");
    }
}
// --- AUDIOMATCH NETWORK BRIDGE ---
async function handleAudioSearch(audioBlob) {
    try {
        showSystemAlert("alertContainer", "Analyzing hummingbird acoustic prints across the cloud...", "info");
        
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');

        const response = await fetch(`${API_BASE_URL}/api/v1/search/audio`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();

        if (response.ok && result.song) {
            const match = normalizeSong(result.song);
            dynamicCatalog = [match];
            
            // 1. Re-render catalog container grid structure
            renderCatalog(dynamicCatalog);
            
            // 2. Refresh target metric charts
            if (result.analysis) {
                if (result.analysis.overall <= 1.0) {
                    result.analysis.overall = Math.round(result.analysis.overall * 100);
                } else {
                    result.analysis.overall = Math.round(result.analysis.overall);
                }
                
                // Refresh target metric charts with safely adjusted integer types
                renderHummingAnalysisChart(result.analysis);
            }

            updateYouTubeStreamLink(
                buildYouTubeSearchUrl(match.title, match.artist),
                `${match.title} - ${match.artist}`
            );

            const videoId = extractYouTubeVideoId(match.source_url);

            if (videoId) {
                showSystemAlert("alertContainer", `Acoustic Match Confirmed: "${match.title}" by ${match.artist}. Launching stream...`, "success");
                playYouTubeEmbed(videoId);
            } else {
                showSystemAlert("alertContainer", `Acoustic Match Confirmed: "${match.title}" by ${match.artist}. Searching YouTube...`, "info");
                await searchAndPlayYouTube(match.title, match.artist);
            }
        } else {
            renderCatalog([]);
            showSystemAlert("alertContainer", "Vocal footprint could not be cleanly targeted inside databases.", "warning");
        }
    } catch (error) {
        console.error(error);
        renderCatalog([]);
        showSystemAlert("alertContainer", "Audio tracking network gateway returned an execution exception.", "danger");
    }
}

// --- YOUTUBE BACKEND STREAM HANDOVER ---
async function searchAndPlayYouTube(title, artist) {
    const query = `${title} ${artist} audio`;
    updateYouTubeStreamLink(buildYouTubeSearchUrl(title, artist), `${title} - ${artist}`);
    try {
        let videoId = "";

        if (YOUTUBE_API_KEY) {
            const url = `https://www.googleapis.com/youtube/v3/search?part=snippet&q=${encodeURIComponent(query)}&type=video&maxResults=1&key=${YOUTUBE_API_KEY}`;
            const res = await fetch(url);
            const data = await res.json();
            if (data.items && data.items.length > 0) {
                videoId = data.items[0].id.videoId;
            }
        } else {
            const fallbackUrl = `https://images${Math.floor(Math.random() * 3) + 1}-focus-opensocial.googleusercontent.com/gadgets/proxy?container=none&url=${encodeURIComponent('https://www.youtube.com/results?search_query=' + encodeURIComponent(query))}`;
            const res = await fetch(fallbackUrl);
            const html = await res.text();
            const match = html.match(/"videoId":"([^"]+)"/);
            if (match) videoId = match[1];
        }

        if (videoId) {
            playYouTubeEmbed(videoId);
            updateYouTubeStreamLink(`https://www.youtube.com/watch?v=${videoId}`, `${title} - ${artist}`);

            const targetBtn = document.getElementById(`play-btn-999`);
            if (targetBtn) {
                targetBtn.innerHTML = '<i class="bi bi-soundwave text-warning me-1"></i>Streaming Now';
                targetBtn.className = "btn btn-sm btn-warning";
            }
        } else {
            showSystemAlert("alertContainer", "Could not capture active stream hooks from YouTube.", "warning");
        }
    } catch (err) {
        console.error(err);
        showSystemAlert("alertContainer", "YouTube interface parsing execution failure.", "danger");
    }
}

// --- RENDERING INTEGRATION FOR SCORING BREAKDOWN ---
function renderHummingAnalysisChart(analysis) {
    const container = document.getElementById('hummingAnalysisContainer');
    const placeholder = document.getElementById('chartPlaceholder');
    
    if (placeholder) placeholder.classList.add('d-none');
    if (container) container.classList.remove('d-none');
    
    // --- 📊 SUB-CHART 1: RADAR GRAPH (CORE BREAKDOWN ATTRIBUTES ONLY) ---
    const ctxRadar = document.getElementById('hummingAnalysisChart')?.getContext('2d');
    if (ctxRadar) {
        const radarData = [
            analysis.pitch,
            analysis.melody,
            analysis.tone,
            analysis.clarity
        ];

        if (hummingChartInstance) {
            hummingChartInstance.data.datasets[0].data = radarData;
            hummingChartInstance.update();
        } else {
            hummingChartInstance = new Chart(ctxRadar, {
                type: 'radar',
                data: {
                    labels: ['Pitch Alignment', 'Melody Contours', 'Tone Profile', 'Clarity Level'],
                    datasets: [{
                        label: 'Match Confidence Metrics (%)',
                        data: radarData,
                        backgroundColor: 'rgba(220, 53, 69, 0.2)',
                        borderColor: 'rgba(220, 53, 69, 1)',
                        pointBackgroundColor: 'rgba(220, 53, 69, 1)',
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: 'rgba(220, 53, 69, 1)'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        r: {
                            angleLines: { display: true },
                            suggestedMin: 0,
                            suggestedMax: 100,
                            ticks: { stepSize: 20 }
                        }
                    }
                }
            });
        }
    }

    // --- 🧭 SUB-CHART 2: DOUGHNUT METER (DYNAMICALLY COLORED OVERALL MATCH GAUGE) ---
    const ctxGauge = document.getElementById('overallScoreChart')?.getContext('2d');
    const scoreDisplay = document.getElementById('gaugeScoreText');
    const insightDisplay = document.getElementById('gaugeInsightText');
    
    if (ctxGauge) {
        const score = analysis.overall;
        
        // Output text tracking injection updates
        if (scoreDisplay) scoreDisplay.innerText = `${score}%`;

        // Insights Rule Palette & Label Engine Matcher
        let gaugeColor = '#DC3545'; // Less than 60% (Red) Default
        let insightLabel = 'DISSAPOINTMENT!';
        
        if (score === 100) {
            gaugeColor = '#FFD700'; // Exact 100% (Gold)
            insightLabel = '🏆 PERFECT SCORE!';
        } else if (score >= 90 && score <= 99) {
            gaugeColor = '#198754'; // 90% to 99% (Green)
            insightLabel = '🟢 EXCELLENT SCORE!';
        } else if (score >= 60 && score <= 89) {
            gaugeColor = '#8B4513'; // 60% to 89% (Brown)
            insightLabel = '🟤 GOOD SCORE!';
        }

        // Apply textual label evaluation and dynamically match text colors to the chart gauge color
        if (insightDisplay) {
            insightDisplay.innerText = insightLabel;
            insightDisplay.style.color = gaugeColor;
        }

        const gaugeDataset = [score, 100 - score];

        if (overallGaugeChartInstance) {
            overallGaugeChartInstance.data.datasets[0].data = gaugeDataset;
            overallGaugeChartInstance.data.datasets[0].backgroundColor = [gaugeColor, '#E9ECEF'];
            overallGaugeChartInstance.update();
        } else {
            overallGaugeChartInstance = new Chart(ctxGauge, {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: gaugeDataset,
                        backgroundColor: [gaugeColor, '#E9ECEF'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    rotation: -90,      
                    circumference: 180, 
                    cutout: '80%',      
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: false }
                    }
                }
            });
        }
    }
}

function renderCatalog(songs) {
    const catalogGrid = document.getElementById('catalogGrid');
    if (!catalogGrid) return;

    if (songs.length === 0) {
        catalogGrid.innerHTML = `
            <div class="col-12 text-center text-muted py-4 bg-white rounded shadow-sm border">
                <i class="bi bi-music-note fs-2 mb-2 d-block"></i> No music tracks active to display. Try searching or humming.
            </div>
        `;
        return;
    }

    catalogGrid.innerHTML = songs.map(song => {
        return `
            <div class="col">
                <div class="card shadow-sm border-0 border-start border-success border-3">
                    <div class="card-body d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="card-title mb-1 fw-bold">${escapeHtml(song.title)}</h6>
                            <p class="text-muted small mb-0">${escapeHtml(song.artist)} • <span class="badge bg-light text-dark">${escapeHtml(song.genre)}</span></p>
                        </div>
                        <button id="play-btn-${song.id}" class="btn btn-sm btn-primary px-3" 
                            onclick="searchAndPlayYouTube('${escapeHtml(song.title)}', '${escapeHtml(song.artist)}')" title="Play Track">
                            <i class="bi bi-play-fill me-1"></i>Play
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function showSystemAlert(targetId, message, type) {
    const anchor = document.getElementById(targetId);
    if (!anchor) return;
    anchor.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show shadow-sm border-0" role="alert">
            <i class="bi ${type === 'danger' ? 'bi-x-circle-fill' : type === 'success' ? 'bi-check-circle-fill' : 'bi-info-circle-fill'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
}

function escapeHtml(str) {
    return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}