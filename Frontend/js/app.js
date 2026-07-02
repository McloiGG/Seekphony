/**
 * Seekphoney - Frontend Controller
 * Developer: Muhammad Ridzuan Bin Bakar
 * Target: Single-Page Multi-modal Dashboard Integration
 */

// --- GLOBAL STATE ---
const API_BASE_URL = 'http://127.0.0.1:8000';
let mediaRecorder = null;
let audioChunks = [];
let analyticsChartInstance = null;
let simulatedPlaytimeMinutes = 0;
let dynamicCatalog = [];

// ADD THIS: Global audio element to play synthesised soundwaves/mock tunes
let activeAudioPlayer = null;

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', async () => {
    setupEventListeners();
    initChart();
    
    // 1. Explicitly clear out the catalog grid so it stays completely blank on load
    renderCatalog([]); 
    
    // 2. Silently fetch data ONLY to populate your analytics charts and totals,
    // without rendering any cards to the UI screen!
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/songs`);
        if (response.ok) {
            const songs = await response.json();
            dynamicCatalog = songs.map(normalizeSong);
            
            // Update the chart bars and total playtime statistics in the sidebar
            updateDashboardCharts();
            updateTotalPlaytimeFromCatalog();
        }
    } catch (e) {
        console.error("Silent background sync failed:", e);
    }
});

function normalizeSong(song) {
    return {
        ...song,
        plays: song.plays ?? song.play_count ?? 0
    };
}

async function loadCatalogFromBackend() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/songs`);

        if (!response.ok) {
            throw new Error("Failed to load catalog");
        }

        const songs = await response.json();
        dynamicCatalog = songs.map(normalizeSong);

        renderCatalog(dynamicCatalog);
        updateDashboardCharts();
        updateTotalPlaytimeFromCatalog();
    } catch (error) {
        console.warn("Backend catalog unavailable. Using local demo catalog:", error);
        renderCatalog(dynamicCatalog);
        updateDashboardCharts();
    }
}

function setupEventListeners() {
    document.getElementById('searchBtn')?.addEventListener('click', handleTextSearch);
    document.getElementById('searchInput')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleTextSearch();
    });

    document.getElementById('micBtn')?.addEventListener('click', toggleAudioRecording);
    document.getElementById('addSongForm')?.addEventListener('submit', handleAddSongSubmit);

    document.getElementsByName('intakeMethod').forEach(radio => {
        radio.addEventListener('change', handleIntakeToggle);
    });

    document.getElementById('analyzeUrlBtn')?.addEventListener('click', parseUrlMetadata);
    document.getElementById('songFile')?.addEventListener('change', parseFileMetadata);
}

// --- MICROPHONE API RECORDER LOGIC ---
async function toggleAudioRecording() {
    const recordingStatus = document.getElementById('recordingStatus');

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
            stream.getTracks().forEach(track => track.stop());
            recordingStatus.classList.add('d-none');

            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await handleAudioSearch(audioBlob);
        };

        mediaRecorder.start();
        recordingStatus.classList.remove('d-none');

        setTimeout(() => {
            if (mediaRecorder && mediaRecorder.state === "recording") {
                mediaRecorder.stop();
            }
        }, 10000);

    } catch (err) {
        console.error("Microphone acquisition failure:", err);
        showSystemAlert("alertContainer", "Microphone access denied. Check browser permissions.", "danger");
    }
}

// --- FETCH NETWORK CALLS & WORKFLOWS ---
async function handleTextSearch() {
    const queryInput = document.getElementById('searchInput');
    const query = queryInput ? queryInput.value.trim() : "";
    
    if (!query) return;

    try {
        // Use your versioned endpoint base url layout 
        const response = await fetch(`${API_BASE_URL}/api/v1/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (response.ok && data.song) {
            // Normalize the single matching track entity 
            const matchedSong = normalizeSong(data.song);
            
            // Render ONLY this specific track onto the dashboard layout container!
            renderCatalog([matchedSong]);
            
            showSystemAlert("mainAlertContainer", `Match found: "${matchedSong.title}"`, "success");
        } else {
            // Clear out the display catalog list area if no match is found
            renderCatalog([]);
            showSystemAlert("mainAlertContainer", data.message || "No matching track found inside database storage.", "warning");
        }
    } catch (error) {
        renderCatalog([]);
        showSystemAlert("mainAlertContainer", "Backend search server is currently unreachable.", "danger");
    }
}

async function handleAudioSearch(audioBlob) {
    // Locate or create an alert area container anchor in your template layout
    const alertContainer = "mainAlertContainer"; 
    
    try {
        // Clear any old warnings off the alert window before starting a new search
        document.getElementById('alertContainer').innerHTML = '';

        const formData = new FormData();
        // Append the webm chunk capturing voice parameters securely 
        formData.append('file', audioBlob, 'recording.webm');

        // 1. Send the file payload directly to your versioned FastAPI endpoint base layout
        const response = await fetch(`${API_BASE_URL}/api/v1/search/audio`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();

        // 2. THE NEW DECISION BRIDGE ROUTING ENGINE
        if (response.ok && result.song) {
            // Normalize matching track data payload
            const match = normalizeSong(result.song);

            // Append it to the client side dictionary cache pool if it isn't registered yet
            if (!dynamicCatalog.some(s => s.id === match.id)) {
                dynamicCatalog.push(match);
            }

            // Render it explicitly onto the catalog screen grid view layout 
            renderCatalog([match]);
            updateDashboardCharts();
            updateTotalPlaytimeFromCatalog();
            
            showSystemAlert(alertContainer, `Acoustic Match Confirmed: "${match.title}" by ${match.artist}!`, "success");
        } 
        else if (result.status === "no_match" || !result.song) {
            // 🚀 TARGET FALLBACK INTEGRATION POINT:
            // ACRCloud returned a clean response but found no match, clear catalog cards and trigger your ingestion wizard banner!
            renderCatalog([]);
            promptCatalogIngestion();
            
            showSystemAlert(alertContainer, "Acoustic signature could not be identified inside cloud charts.", "warning");
        }

    } catch (error) {
        console.error("Audio detection flow network exception:", error);
        renderCatalog([]);
        showSystemAlert(alertContainer, "Audio recognition cloud network timed out or became unreachable.", "danger");
    }
}

function handleSearchResponse(statusCode, data) {
    document.getElementById('alertContainer').innerHTML = '';

    if (statusCode === 200 && data.song) {
        const match = normalizeSong(data.song);

        if (!dynamicCatalog.some(s => s.id === match.id)) {
            dynamicCatalog.push(match);
        }

        renderCatalog(dynamicCatalog);
        updateDashboardCharts();
        showSystemAlert("alertContainer", `Match Discovered: "${match.title}" by ${match.artist}!`, "success");
    } else if (statusCode === 200 && data.status === "candidates") {
        const candidates = data.candidates.map(candidate => normalizeSong(candidate.song));

        renderCatalog(candidates);
        updateDashboardCharts();
        showSystemAlert("alertContainer", "No exact match found, but similar songs are available.", "info");
    } else {
        promptCatalogIngestion();
    }
}

async function handleAddSongSubmit(e) {
    e.preventDefault();
    document.getElementById('modalAlertContainer').innerHTML = '';

    const title = document.getElementById('modalTitle').value.trim();
    const artist = document.getElementById('modalArtist').value.trim();
    const genre = document.getElementById('modalGenre').value.trim();
    const songUrl = document.getElementById('songUrl')?.value.trim();
    const songFile = document.getElementById('songFile')?.files?.[0];

    try {
        let response;

        if (songFile) {
            const formData = new FormData();
            formData.append('title', title);
            formData.append('artist', artist);
            formData.append('genre', genre);
            formData.append('file', songFile);

            response = await fetch(`${API_BASE_URL}/api/v1/songs`, {
                method: 'POST',
                body: formData
            });
        } else {
            const payload = { title, artist, genre };

            if (songUrl) {
                payload.source_url = songUrl;
            }

            response = await fetch(`${API_BASE_URL}/api/v1/songs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        const data = await response.json();

        if (response.status === 409) {
            showSystemAlert("modalAlertContainer", "Duplication detected! This track already exists in the global catalog database.", "danger");
        } else if (response.ok && data.song) {
            const savedSong = normalizeSong(data.song);

            dynamicCatalog.push(savedSong);
            renderCatalog(dynamicCatalog);
            updateDashboardCharts();
            updateTotalPlaytimeFromCatalog();

            showSystemAlert("alertContainer", `Successfully cataloged "${savedSong.title}"!`, "success");

            const modalEl = document.getElementById('addSongModal');
            const modalInstance = bootstrap.Modal.getInstance(modalEl);
            modalInstance?.hide();
            e.target.reset();
        } else {
            showSystemAlert("modalAlertContainer", data.message || data.detail || "Validation check failure.", "warning");
        }
    } catch (error) {
        handleErrorCommunication(error);
    }
}

// --- SIMULATED PLAYER ENGINE & ANALYTICS INGESTION ---
async function simulatePlayback(songId) {
    console.log(`Initializing audio streaming telemetry track tracking for Song ID: ${songId}`);
    
    const playBtn = document.getElementById(`play-btn-${songId}`);
    
    // 1. RESUME/PAUSE TOGGLE CASE: If the user clicked the same song that is already active
    if (activeAudioPlayer && activeAudioPlayer.src.includes(`/api/v1/songs/stream/${songId}`)) {
        if (!activeAudioPlayer.paused) {
            // The music is playing, so pause it
            activeAudioPlayer.pause();
            if (playBtn) playBtn.innerHTML = '<i class="bi bi-play-fill me-1"></i>Play';
            showSystemAlert("mainAlertContainer", "Playback paused.", "info");
        } else {
            // The music is paused, so resume playing
            await activeAudioPlayer.play();
            if (playBtn) playBtn.innerHTML = '<i class="bi bi-pause-fill me-1"></i>Pause';
            showSystemAlert("mainAlertContainer", "Playback resumed.", "success");
        }
        return;
    }

    // 2. NEW TRACK CASE: Reset previous audio state completely if playing a new song
    if (activeAudioPlayer) {
        activeAudioPlayer.pause();
        // Reset all other button icons back to "Play"
        document.querySelectorAll('[id^="play-btn-"]').forEach(btn => {
            btn.innerHTML = '<i class="bi bi-play-fill me-1"></i>Play';
        });
    }

    // Connect the HTML5 Audio interface to stream the actual backend audio file
    try {
        const streamUrl = `${API_BASE_URL}/api/v1/songs/stream/${songId}`;
        activeAudioPlayer = new Audio(streamUrl);
        
        // Start streaming audio through browser sound system
        await activeAudioPlayer.play();
        if (playBtn) playBtn.innerHTML = '<i class="bi bi-pause-fill me-1"></i>Pause';

        // Reset button icon when song finishes playing naturally
        activeAudioPlayer.onended = () => {
            if (playBtn) playBtn.innerHTML = '<i class="bi bi-play-fill me-1"></i>Play';
        };

    } catch (e) {
        console.error("Audio playback streaming engagement failed:", e);
        showSystemAlert("mainAlertContainer", "Audio stream could not be loaded or format is unsupported.", "danger");
    }

    // ANALYTICS TELEMETRY SYNC (Keeps your play counting intact)
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/analytics/play`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ song_id: songId, duration_seconds: 10 })
        });

        if (response.ok) {
            const data = await response.json();
            
            const matchingIndex = dynamicCatalog.findIndex(s => s.id === parseInt(songId));
            if (matchingIndex !== -1 && data.song) {
                dynamicCatalog[matchingIndex] = normalizeSong(data.song);
                
                updateDashboardCharts();
                updateTotalPlaytimeFromCatalog();
                
                showSystemAlert("mainAlertContainer", `Now streaming: "${data.song.title}" by ${data.song.artist}`, "success");
            }
        }
    } catch (error) {
        console.error("Failed to post playback telemetry counters:", error);
    }
}

// ADD THIS NEW FUNCTION RIGHT BELOW SIMULATEPLAYBACK TO HANDLE DELETION
async function deleteSongTrack(songId) {
    if (!confirm("Are you sure you want to delete this song permanently from the database?")) return;

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/songs/${songId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showSystemAlert("mainAlertContainer", "Song record successfully deleted.", "success");
            
            // Stop audio if deleting the currently playing track
            if (activeAudioPlayer && activeAudioPlayer.src.includes(`/api/v1/songs/stream/${songId}`)) {
                activeAudioPlayer.pause();
                activeAudioPlayer = null;
            }

            // Remove from local array and re-render dashboard
            dynamicCatalog = dynamicCatalog.filter(s => s.id !== parseInt(songId));
            renderCatalog(dynamicCatalog);
            updateDashboardCharts();
            updateTotalPlaytimeFromCatalog();
        } else {
            showSystemAlert("alertContainer", "Failed to remove the song from backend database.", "danger");
        }
    } catch (error) {
        console.error("Error deleting song:", error);
        showSystemAlert("alertContainer", "Backend database server is unreachable.", "danger");
    }
}

// --- UI RENDERING & INJECTIONS ---
function renderCatalog(songs) {
    const catalogGrid = document.getElementById('catalogGrid');
    if (!catalogGrid) return;

    catalogGrid.innerHTML = songs.map(song => {
        const plays = song.plays ?? song.play_count ?? 0;

        return `
            <div class="col">
                <div class="card h-100 shadow-sm border-0 border-start border-success border-3">
                    <div class="card-body d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="card-title mb-1 fw-bold">${escapeHtml(song.title)}</h6>
                            <p class="text-muted small mb-0">${escapeHtml(song.artist)} • <span class="badge bg-light text-dark">${escapeHtml(song.genre)}</span></p>
                            <small class="text-primary tracking-monospace" style="font-size: 0.75rem;">Plays: ${plays}</small>
                        </div>
                        <div class="d-flex flex-column gap-2">
                            <button id="play-btn-${song.id}" class="btn btn-sm btn-primary" onclick="simulatePlayback(${song.id})" title="Play/Pause Track">
                                <i class="bi bi-play-fill me-1"></i>Play
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteSongTrack(${song.id})" title="Delete Track">
                                <i class="bi bi-trash-fill me-1"></i>Delete
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function promptCatalogIngestion() {
    const container = document.getElementById('alertContainer');
    container.innerHTML = `
        <div class="alert alert-warning border-0 shadow-sm d-flex justify-content-between align-items-center my-3" role="alert">
            <div>
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                <strong>No song available in database.</strong> Do you want to add the song?
            </div>
            <button class="btn btn-sm btn-dark shadow-sm" data-bs-toggle="modal" data-bs-target="#addSongModal">Yes, Add Song</button>
        </div>
    `;
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

function handleErrorCommunication(err) {
    console.error(err);
    showSystemAlert("alertContainer", "System Connection Timeout. Ensure FastAPI is running on port 8000.", "danger");
}

function escapeHtml(str) {
    return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// --- CHART.JS CONFIGURATION ---
function initChart() {
    const ctx = document.getElementById('analyticsChart')?.getContext('2d');
    if (!ctx) return;

    analyticsChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dynamicCatalog.map(s => s.title),
            datasets: [{
                label: 'Play Counts',
                data: dynamicCatalog.map(s => s.plays ?? s.play_count ?? 0),
                backgroundColor: 'rgba(25, 135, 84, 0.85)',
                borderColor: '#198754',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            indexAxis: 'y',
            scales: {
                x: { beginAtZero: true, ticks: { stepSize: 1 } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

// --- INTAKE CONTROL LOGIC ---
function handleIntakeToggle(e) {
    const urlContainer = document.getElementById('urlInputContainer');
    const fileContainer = document.getElementById('fileInputContainer');

    if (e.target.id === 'methodUrl') {
        urlContainer.classList.remove('d-none');
        fileContainer.classList.add('d-none');
        document.getElementById('songFile').value = '';
    } else {
        urlContainer.classList.add('d-none');
        fileContainer.classList.remove('d-none');
        document.getElementById('songUrl').value = '';
    }
}

async function parseUrlMetadata() {
    const urlValue = document.getElementById('songUrl').value.trim();
    if (!urlValue) return;

    toggleExtractionLoader(true);

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/extract/url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: urlValue })
        });

        const data = await response.json();

        if (response.ok) {
            populateFormFields(data.title, data.artist, data.genre);
        } else {
            showSystemAlert("modalAlertContainer", data.message || data.detail || "URL processing failed.", "warning");
        }
    } catch (error) {
        showSystemAlert("modalAlertContainer", "Backend processing engine unavailable.", "danger");
    } finally {
        toggleExtractionLoader(false);
    }
}

async function parseFileMetadata(e) {
    const localAudioFile = e.target.files[0];
    if (!localAudioFile) return;

    const filePayload = new FormData();
    filePayload.append('file', localAudioFile);

    toggleExtractionLoader(true);

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/extract/file`, {
            method: 'POST',
            body: filePayload
        });

        const data = await response.json();

        if (response.ok) {
            populateFormFields(data.title, data.artist, data.genre);
        } else {
            showSystemAlert("modalAlertContainer", data.message || data.detail || "Audio tags parsing failed.", "warning");
        }
    } catch (error) {
        showSystemAlert("modalAlertContainer", "Backend metadata server unreachable.", "danger");
    } finally {
        toggleExtractionLoader(false);
    }
}

function toggleExtractionLoader(show) {
    const spinner = document.getElementById('extractionSpinner');
    if (!spinner) return;

    show ? spinner.classList.remove('d-none') : spinner.classList.add('d-none');
}

function populateFormFields(title, artist, genre) {
    document.getElementById('modalTitle').value = title || '';
    document.getElementById('modalArtist').value = artist || '';
    document.getElementById('modalGenre').value = genre || '';

    showSystemAlert("modalAlertContainer", "Seekphoney successfully populated matching information! Review before saving.", "success");
}

function updateDashboardCharts() {
    if (!analyticsChartInstance) return;

    const sortedSongs = [...dynamicCatalog]
        .sort((a, b) => (b.plays ?? b.play_count ?? 0) - (a.plays ?? a.play_count ?? 0))
        .slice(0, 5);

    analyticsChartInstance.data.labels = sortedSongs.map(s => s.title);
    analyticsChartInstance.data.datasets[0].data = sortedSongs.map(s => s.plays ?? s.play_count ?? 0);
    analyticsChartInstance.update();
}

function updateTotalPlaytimeFromCatalog() {
    const totalSeconds = dynamicCatalog.reduce((sum, song) => {
        return sum + (song.total_listen_seconds || 0);
    }, 0);

    if (totalSeconds > 0) {
        document.getElementById('totalPlaytime').innerText = `${Math.round(totalSeconds / 60)} mins`;
    } else {
        document.getElementById('totalPlaytime').innerText = `${simulatedPlaytimeMinutes} mins`;
    }
}