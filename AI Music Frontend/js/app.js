/**
 * Seekphoney - Frontend Controller
 * Developer: Muhammad Ridzuan Bin Bakar
 * Target: Single-Page Multi-modal Dashboard Integration
 */

// --- GLOBAL STATE ---
const API_BASE_URL = 'http://127.0.0.1:8000'; // FastAPI server address
let mediaRecorder = null;
let audioChunks = [];
let analyticsChartInstance = null;
let simulatedPlaytimeMinutes = 0;

// Mock database storage for active tracking on UI
let dynamicCatalog = [
    { id: 1, title: "Example Track Title", artist: "Artist Name", genre: "Genre", plays: 3 }
];

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    renderCatalog(dynamicCatalog);
    setupEventListeners();
});

function setupEventListeners() {
    // Search actions
    document.getElementById('searchBtn')?.addEventListener('click', handleTextSearch);
    document.getElementById('searchInput')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleTextSearch();
    });

    // Mic action
    document.getElementById('micBtn')?.addEventListener('click', toggleAudioRecording);

    // Modal Ingestion Form Submission
    document.getElementById('addSongForm')?.addEventListener('submit', handleAddSongSubmit);

    // NEW: Handle toggle switches inside the import modal
    document.getElementsByName('intakeMethod').forEach(radio => {
        radio.addEventListener('change', handleIntakeToggle);
    });

    // NEW: Analytical triggers for URL parsing & Local file changes
    document.getElementById('analyzeUrlBtn')?.addEventListener('click', parseUrlMetadata);
    document.getElementById('songFile')?.addEventListener('change', parseFileMetadata);
}

// --- 🎤 1. MICROPHONE API RECORDER LOGIC ---
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
            stream.getTracks().forEach(track => track.stop()); // Clean resource allocation
            recordingStatus.classList.add('d-none'); // Hide UI spinner

            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await handleAudioSearch(audioBlob);
        };

        mediaRecorder.start();
        recordingStatus.classList.remove('d-none'); // Show UI spinner

        // Enforce the strict 5-second maximum requirement
        setTimeout(() => {
            if (mediaRecorder && mediaRecorder.state === "recording") {
                mediaRecorder.stop();
            }
        }, 5000);

    } catch (err) {
        console.error("Microphone acquisition failure:", err);
        showSystemAlert("alertContainer", "Microphone access denied. Check browser permissions.", "danger");
    }
}

// --- 🌐 2. FETCH NETWORK CALLS & WORKFLOWS ---

// A. Handle Text Input Request
async function handleTextSearch() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) return;

    try {
        const response = await fetch(`${API_BASE_URL}/api/search?q=${encodeURIComponent(query)}`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
        });
        const data = await response.json();
        handleSearchResponse(response.status, data);
    } catch (error) {
        handleErrorCommunication(error);
    }
}

// B. Handle Audio Hum Input Payload (Multi-part FormData)
async function handleAudioSearch(audioBlob) {
    try {
        const formData = new FormData();
        formData.append('file', audioBlob, 'humming_snippet.webm');

        const response = await fetch(`${API_BASE_URL}/api/search/audio`, {
            method: 'POST',
            body: formData,
            headers: { 'Accept': 'application/json' }
        });
        const data = await response.json();
        handleSearchResponse(response.status, data);
    } catch (error) {
        handleErrorCommunication(error);
    }
}

// C. Search Response Evaluation
function handleSearchResponse(statusCode, data) {
    // Clear any preceding system notifications
    document.getElementById('alertContainer').innerHTML = '';

    if (statusCode === 200 && data.song) {
        // Match found: Add track temporarily to localized dynamic array & visually highlight
        const match = data.song;
        if (!dynamicCatalog.some(s => s.title.toLowerCase() === match.title.toLowerCase())) {
            dynamicCatalog.push({ ...match, plays: 1 });
        }
        renderCatalog(dynamicCatalog);
        showSystemAlert("alertContainer", `Match Discovered: "${match.title}" by ${match.artist}!`, "success");
    } else {
        // No match found workflow trigger
        promptCatalogIngestion();
    }
}

// D. Catalog Data Ingestion (Validation & Duplicate Rejection)
async function handleAddSongSubmit(e) {
    e.preventDefault();
    document.getElementById('modalAlertContainer').innerHTML = '';

    // Extrapolate your clean manual inputs explicitly
    const title = document.getElementById('modalTitle').value.trim();
    const artist = document.getElementById('modalArtist').value.trim();
    const genre = document.getElementById('modalGenre').value.trim();

    // Construct request parameters matching FastAPI expected object structure
    const payload = { title, artist, genre };

    try {
        const response = await fetch(`${API_BASE_URL}/api/songs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.status === 409) {
            // Requirement Met: Prompt rejection duplication alert banner inside modal context
            showSystemAlert("modalAlertContainer", "Duplication detected! This track already exists in the global catalog database.", "danger");
        } else if (response.ok) {
            // Success workflow
            showSystemAlert("alertContainer", `Successfully cataloged "${title}"!`, "success");
            
            // Push locally and update charts
            dynamicCatalog.push({ id: Date.now(), title, artist, genre, plays: 0 });
            renderCatalog(dynamicCatalog);
            updateDashboardCharts();

            // Clear, dismiss Bootstrap modal container
            const modalEl = document.getElementById('addSongModal');
            const modalInstance = bootstrap.Modal.getInstance(modalEl);
            modalInstance?.hide();
            e.target.reset();
        } else {
            showSystemAlert("modalAlertContainer", data.detail || "Validation check failure.", "warning");
        }
    } catch (error) {
        handleErrorCommunication(error);
    }
}

// --- 🎧 3. SIMULATED PLAYER ENGINE & ANALYTICS INGESTION ---

async function simulatePlayback(songId) {
    const targetSong = dynamicCatalog.find(s => s.id === songId);
    if (!targetSong) return;

    try {
        // Send statistical tracking signal to backend engine
        await fetch(`${API_BASE_URL}/api/analytics/play`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ song_id: songId })
        });

        // Mutate metrics locally to display changes instantly
        targetSong.plays += 1;
        simulatedPlaytimeMinutes += Math.floor(Math.random() * 3) + 2; // Mimic adding a 2-4 min duration run

        // Sync view components
        document.getElementById('totalPlaytime').innerText = `${simulatedPlaytimeMinutes} mins`;
        renderCatalog(dynamicCatalog);
        updateDashboardCharts();
        
        showSystemAlert("alertContainer", `▶ Simulated play tracking for "${targetSong.title}". Metrics aggregated!`, "info");
    } catch (error) {
        console.warn("Analytics backend unreachable. Updating metrics locally for demo visibility:", error);
        // Fallback for visual demonstration continuity if backend goes offline
        targetSong.plays += 1;
        simulatedPlaytimeMinutes += 3;
        document.getElementById('totalPlaytime').innerText = `${simulatedPlaytimeMinutes} mins`;
        renderCatalog(dynamicCatalog);
        updateDashboardCharts();
    }
}

// --- 🎨 UI RENDERING & INJECTIONS ---

function renderCatalog(songs) {
    const catalogGrid = document.getElementById('catalogGrid');
    if (!catalogGrid) return;

    catalogGrid.innerHTML = songs.map(song => `
        <div class="col">
            <div class="card h-100 shadow-sm border-0 border-start border-success border-3">
                <div class="card-body d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="card-title mb-1 fw-bold">${escapeHtml(song.title)}</h6>
                        <p class="text-muted small mb-0">${escapeHtml(song.artist)} • <span class="badge bg-light text-dark">${escapeHtml(song.genre)}</span></p>
                        <small class="text-primary tracking-monospace" style="font-size: 0.75rem;">Plays: ${song.plays}</small>
                    </div>
                    <button class="btn btn-success btn-sm rounded-circle shadow-sm" onclick="simulatePlayback(${song.id})" title="Simulate Play Track">
                        <i class="bi bi-play-fill"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
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
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// --- 📊 CHART.JS CONFIGURATION ---
function initChart() {
    const ctx = document.getElementById('analyticsChart')?.getContext('2d');
    if (!ctx) return;

    analyticsChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dynamicCatalog.map(s => s.title),
            datasets: [{
                label: 'Play Counts',
                data: dynamicCatalog.map(s => s.plays),
                backgroundColor: 'rgba(25, 135, 84, 0.85)',
                borderColor: '#198754',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            indexAxis: 'y', // Makes it a horizontal bar chart for clean sidebar integration
            scales: {
                x: { beginAtZero: true, ticks: { stepSize: 1 } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

// --- NEW INTAKE CONTROL LOGIC ---

function handleIntakeToggle(e) {
    const urlContainer = document.getElementById('urlInputContainer');
    const fileContainer = document.getElementById('fileInputContainer');
    
    if (e.target.id === 'methodUrl') {
        urlContainer.classList.remove('d-none');
        fileContainer.classList.add('d-none');
        document.getElementById('songFile').value = ''; // Clear file input buffer
    } else {
        urlContainer.classList.add('d-none');
        fileContainer.classList.remove('d-none');
        document.getElementById('songUrl').value = ''; // Clear URL text string
    }
}

async function parseUrlMetadata() {
    const urlValue = document.getElementById('songUrl').value.trim();
    if (!urlValue) return;

    toggleExtractionLoader(true);
    try {
        const response = await fetch(`${API_BASE_URL}/api/extract/url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: urlValue })
        });
        
        const data = await response.json();
        if (response.ok) {
            populateFormFields(data.title, data.artist, data.genre);
        } else {
            showSystemAlert("modalAlertContainer", data.detail || "URL processing failed.", "warning");
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
        const response = await fetch(`${API_BASE_URL}/api/extract/file`, {
            method: 'POST',
            body: filePayload
        });
        
        const data = await response.json();
        if (response.ok) {
            populateFormFields(data.title, data.artist, data.genre);
        } else {
            showSystemAlert("modalAlertContainer", data.detail || "Audio tags parsing failed.", "warning");
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
    
    // Sort songs by play count descending and extract top 5 for neat styling
    const sortedSongs = [...dynamicCatalog].sort((a, b) => b.plays - a.plays).slice(0, 5);

    analyticsChartInstance.data.labels = sortedSongs.map(s => s.title);
    analyticsChartInstance.data.datasets[0].data = sortedSongs.map(s => s.plays);
    analyticsChartInstance.update();
}