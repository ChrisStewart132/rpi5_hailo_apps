// --- Element References ---
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const toggleButton = document.getElementById('toggleButton');
const statusSpan = document.getElementById('status');
const fovSlider = document.getElementById('fovSlider');
const fovValue = document.getElementById('fovValue');
const distanceSlider = document.getElementById('distanceSlider');
const distanceValue = document.getElementById('distanceValue');
const confidenceSlider = document.getElementById('confidenceSlider');
const confidenceValue = document.getElementById('confidenceValue');

const CANVAS_WIDTH = canvas.width;
const CANVAS_HEIGHT = canvas.height;
const POLLING_INTERVAL_MS = 50;

// --- Color Mapping for COCO Classes ---
const CLASS_COLORS = {
    'person': '#e06c75', 'car': '#61afef', 'bicycle': '#56b6c2', 'motorcycle': '#56b6c2', 'bus': '#c678dd', 'truck': '#c678dd', 'traffic light': '#e5c07b', 'stop sign': '#e5c07b', 'dog': '#98c379', 'cat': '#98c379', 'default': '#abb2bf'
};

// --- Configuration & State Management ---
let isPollingActive = false;
let pollingIntervalID = null;

// Use 'let' instead of 'const' so sliders can update these values
let HORIZONTAL_FOV = parseInt(fovSlider.value);
let DISTANCE_SCALE = parseInt(distanceSlider.value);
let MIN_CONFIDENCE = parseFloat(confidenceSlider.value);

// --- Core Minimap Functions ---
function drawMinimapBackground() {
    const observerX = CANVAS_WIDTH / 2;
    const observerY = CANVAS_HEIGHT;
    ctx.beginPath(); ctx.arc(observerX, observerY, 10, 0, 2 * Math.PI); ctx.fillStyle = '#61afef'; ctx.fill();
    const maxDist = CANVAS_HEIGHT * 0.95; const fovRad = HORIZONTAL_FOV * (Math.PI / 180);
    ctx.beginPath(); ctx.moveTo(observerX - maxDist * Math.tan(fovRad / 2), observerY - maxDist); ctx.lineTo(observerX, observerY); ctx.lineTo(observerX + maxDist * Math.tan(fovRad / 2), observerY - maxDist); ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)'; ctx.stroke();
    [0.25, 0.5, 0.75].forEach(r => { ctx.beginPath(); ctx.arc(observerX, observerY, r * CANVAS_HEIGHT, 0, 2 * Math.PI); ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)'; ctx.stroke(); });
}

function drawLegend() {
    let yOffset = 30, xOffset = 20;
    ctx.font = 'bold 16px sans-serif'; ctx.fillStyle = '#abb2bf'; ctx.textAlign = 'left'; ctx.fillText('Legend', xOffset, yOffset);
    yOffset += 25; ctx.font = '14px sans-serif';
    for (const [className, color] of Object.entries(CLASS_COLORS)) {
        if (className === 'default') continue;
        ctx.fillStyle = color; ctx.fillRect(xOffset, yOffset - 10, 10, 10);
        ctx.fillStyle = '#abb2bf'; const displayName = className.charAt(0).toUpperCase() + className.slice(1); ctx.fillText(displayName, xOffset + 20, yOffset);
        yOffset += 22;
    }
}

function drawMinimap(detections) {
    ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
    drawMinimapBackground();
    drawLegend();

    if (!detections || detections.length === 0) return;

    detections.forEach(det => {
        // NEW: Filter detections by the confidence slider value
        if (det.confidence < MIN_CONFIDENCE) {
            return; // Skip this detection
        }

        const bbox = det.bbox_normalized;
        const bbox_center_x = (bbox.xmin + bbox.xmax) / 2;
        const bbox_height = bbox.ymax - bbox.ymin;
        if (bbox_height < 0.01) return;

        const angleDegrees = (bbox_center_x - 0.5) * HORIZONTAL_FOV;
        const distance = DISTANCE_SCALE / bbox_height;

        const angleRadians = angleDegrees * (Math.PI / 180);
        const observerX = CANVAS_WIDTH / 2; const observerY = CANVAS_HEIGHT;
        const mapX = observerX + distance * Math.sin(angleRadians);
        const mapY = observerY - distance * Math.cos(angleRadians);
        const color = CLASS_COLORS[det.label] || CLASS_COLORS.default;

        ctx.beginPath(); ctx.arc(mapX, mapY, 6, 0, 2 * Math.PI); ctx.fillStyle = color; ctx.fill();
        const label = `${det.label} (${(det.confidence * 100).toFixed(0)}%)`;
        ctx.fillStyle = color; ctx.font = '14px sans-serif'; ctx.textAlign = 'center'; ctx.fillText(label, mapX, mapY - 10);
    });
}

// --- Polling and UI Control Functions ---
async function fetchDetections() {
    try {
        const response = await fetch('/api/detections');
        const detections = await response.json();
        if (isPollingActive) { // Only draw if we are still active
            drawMinimap(detections);
        }
    } catch (error) {
        console.error("Error fetching detections:", error);
        stopPolling(); 
    }
}

function startPolling() {
    if (isPollingActive) return;
    isPollingActive = true;
    pollingIntervalID = setInterval(fetchDetections, POLLING_INTERVAL_MS);
    fetchDetections();
    toggleButton.textContent = 'Stop Polling'; toggleButton.classList.add('active');
    statusSpan.textContent = 'Status: ON'; statusSpan.style.color = '#98c379';
}

function stopPolling() {
    if (!isPollingActive) return;
    isPollingActive = false;
    clearInterval(pollingIntervalID);
    pollingIntervalID = null;
    ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
    drawMinimapBackground(); drawLegend();
    toggleButton.textContent = 'Start Polling'; toggleButton.classList.remove('active');
    statusSpan.textContent = 'Status: OFF'; statusSpan.style.color = '#e06c75';
}

// --- Event Listeners ---
toggleButton.addEventListener('click', () => { isPollingActive ? stopPolling() : startPolling(); });

fovSlider.addEventListener('input', (e) => {
    HORIZONTAL_FOV = parseInt(e.target.value);
    fovValue.textContent = `${HORIZONTAL_FOV}°`;
});

distanceSlider.addEventListener('input', (e) => {
    DISTANCE_SCALE = parseInt(e.target.value);
    distanceValue.textContent = DISTANCE_SCALE;
});

confidenceSlider.addEventListener('input', (e) => {
    MIN_CONFIDENCE = parseFloat(e.target.value);
    confidenceValue.textContent = `${Math.round(MIN_CONFIDENCE * 100)}%`;
});

// --- Initial Setup ---
drawMinimapBackground();
drawLegend();