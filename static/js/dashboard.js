const socket = io();

// ─── Elements ──────────────────────────────
const dotStream = document.getElementById('dot-stream');
const dotPi = document.getElementById('dot-pi');
const dotAi = document.getElementById('dot-ai');
const labelStream = document.getElementById('label-stream');
const labelPi = document.getElementById('label-pi');
const labelAi = document.getElementById('label-ai');
const clockEl = document.getElementById('clock');
const fpsEl = document.getElementById('fps-display');
const infEl = document.getElementById('inference-display');

const gforceVal = document.getElementById('gforce-val');
const gforceBar = document.getElementById('gforce-bar');
const axEl = document.getElementById('ax');
const ayEl = document.getElementById('ay');
const azEl = document.getElementById('az');

const distVal = document.getElementById('dist-val');
const distBar = document.getElementById('dist-bar');

const tempVal = document.getElementById('temp-val');
const tempBar = document.getElementById('temp-bar');
const tempF = document.getElementById('temp-f');
const tempCard = document.getElementById('card-temp');

const detCount = document.getElementById('det-count');
const detList = document.getElementById('det-list');
const evtCount = document.getElementById('evt-count');
const evtList = document.getElementById('evt-list');

const recBadge = document.getElementById('rec-badge');
const bufferDisplay = document.getElementById('buffer-display');
const recStrip = document.getElementById('rec-strip');

const collisionFlash = document.getElementById('collision-flash');
const toasts = document.getElementById('toasts');
const modal = document.getElementById('media-modal');
const modalContent = document.getElementById('modal-content');
const modalInfo = document.getElementById('modal-info');

// ─── Clock ──────────────────────────────────
function tick() {
    clockEl.textContent = new Date().toLocaleTimeString('en-GB');
}
setInterval(tick, 1000);
tick();

// ─── Status helpers ─────────────────────────
function setOn(dot, label, on) {
    dot.classList.toggle('on', on);
    label.classList.toggle('on', on);
}

// ─── Realtime data ──────────────────────────
socket.on('realtime_data', function(d) {
    if (d.stream) {
        setOn(dotStream, labelStream, d.stream.connected);
        fpsEl.textContent = (d.stream.fps || 0).toFixed(0);
        bufferDisplay.textContent = 'BUFFER ' + Math.round(d.stream.buffer_seconds || 0) + 's';
    }

    if (d.sensor) {
        setOn(dotPi, labelPi, true);
        updateGForce(d.sensor);
        updateDist(d.sensor.distance);
        updateTemp(d.sensor.temperature);
    } else {
        setOn(dotPi, labelPi, false);
    }

    if (d.ai_status) {
        setOn(dotAi, labelAi, true);
        infEl.textContent = (d.ai_status.inference_ms || 0).toFixed(0);
    }

    if (d.detections !== undefined) updateDetections(d.detections);

    recBadge.style.display = d.recording ? 'block' : 'none';
    if (d.event_count !== undefined) evtCount.textContent = d.event_count;
});

socket.on('notification', function(d) { showToast(d.message, d.type || 'success'); });
socket.on('collision_alert', showCollision);

// ─── G-Force ────────────────────────────────
function updateGForce(s) {
    var g = s.g_force || 0;
    var a = s.accel || {};
    gforceVal.innerHTML = g.toFixed(2) + '<small>g</small>';
    var pct = Math.min(g / 2.0 * 100, 100);
    gforceBar.style.width = pct + '%';
    gforceBar.className = 'sensor-bar' + (g > 1.5 ? ' danger' : g > 1.0 ? ' warn' : '');
    axEl.textContent = (a.x || 0).toFixed(2);
    ayEl.textContent = (a.y || 0).toFixed(2);
    azEl.textContent = (a.z || 0).toFixed(2);
}

// ─── Distance ───────────────────────────────
function updateDist(dist) {
    if (!dist || dist >= 999) {
        distVal.innerHTML = '--<small>cm</small>';
        distBar.style.width = '100%';
        distBar.className = 'sensor-bar';
        return;
    }
    distVal.innerHTML = Math.round(dist) + '<small>cm</small>';
    var pct = Math.min(dist / 400 * 100, 100);
    distBar.style.width = pct + '%';
    distBar.className = 'sensor-bar' + (dist < 30 ? ' danger' : dist < 50 ? ' warn' : '');
}

// ─── Temperature ────────────────────────────
function updateTemp(temp) {
    if (temp === undefined || temp === null) {
        tempVal.innerHTML = '--<small>°C</small>';
        tempBar.style.width = '0%';
        tempBar.className = 'sensor-bar';
        tempF.textContent = '--°F';
        tempCard.classList.remove('hot', 'warm');
        return;
    }
    tempVal.innerHTML = temp.toFixed(1) + '<small>°C</small>';
    var f = (temp * 9 / 5 + 32).toFixed(1);
    tempF.textContent = f + '°F';
    // Bar: map 20-60°C to 0-100%
    var pct = Math.max(0, Math.min(((temp - 20) / 40) * 100, 100));
    tempBar.style.width = pct + '%';
    tempBar.className = 'sensor-bar' + (temp > 50 ? ' danger' : temp > 40 ? ' warn' : ' temp-normal');
    // Card glow effect
    tempCard.classList.toggle('hot', temp > 50);
    tempCard.classList.toggle('warm', temp > 40 && temp <= 50);
}

// ─── Detections ─────────────────────────────
function updateDetections(dets) {
    detCount.textContent = dets.length;
    if (!dets.length) {
        detList.innerHTML = '<div class="empty-state">No objects detected</div>';
        return;
    }
    var h = '';
    dets.forEach(function(d) {
        var cl = d.too_close ? ' close' : '';
        h += '<div class="det-item' + cl + '">' +
            '<div class="det-item-name"><span class="det-dot"></span>' + d.class_name + '</div>' +
            '<span class="det-item-conf">' + (d.confidence * 100).toFixed(0) + '%</span>' +
            (d.too_close ? '<span class="det-tag">close</span>' : '') +
            '</div>';
    });
    detList.innerHTML = h;
}

// ─── Events ─────────────────────────────────
function loadEvents() {
    fetch('/api/events').then(function(r) { return r.json(); }).then(function(events) {
        evtCount.textContent = events.length;
        if (!events.length) {
            evtList.innerHTML = '<div class="empty-state">No events yet</div>';
            recStrip.innerHTML = '<div class="empty-state">Recordings appear here after events.</div>';
            return;
        }

        var h = '';
        events.slice(0, 12).forEach(function(e) {
            var t = fmtType(e.event_type);
            var cls = e.event_type.includes('collision') ? 'collision' :
                      e.event_type.includes('proximity') ? 'proximity' : 'manual';
            var time = fmtTime(e.timestamp);
            var hasMedia = e.snapshot_url || e.video_url;
            h += '<div class="evt-item" ' + (hasMedia ? 'onclick="openEvent(\'' +
                (e.video_url || e.snapshot_url) + '\',\'' +
                (e.snapshot_url || '') + '\',\'' + t + ' — ' + time + '\')"' : '') + '>' +
                '<div class="evt-stripe ' + cls + '"></div>' +
                '<div class="evt-info"><div class="evt-title">' + t + '</div>' +
                '<div class="evt-time">' + time + '</div></div>' +
                (hasMedia ? '<span class="evt-play">' + (e.video_url ? '▶' : '◻') + '</span>' : '') +
                '</div>';
        });
        evtList.innerHTML = h;

        // Recording strip
        var rh = '';
        events.forEach(function(e) {
            if (!e.snapshot_url && !e.video_url) return;
            var cls = e.event_type.includes('collision') ? 'collision' :
                      e.event_type.includes('proximity') ? 'proximity' : '';
            var time = fmtTime(e.timestamp);
            var src = e.snapshot_url || '';
            var media = e.video_url || e.snapshot_url || '';
            rh += '<div class="rec-card" onclick="openEvent(\'' + media + '\',\'' + src + '\',\'' +
                fmtType(e.event_type) + ' — ' + time + '\')">' +
                (src ? '<img class="rec-thumb" src="' + src + '" alt="">' :
                '<div class="rec-thumb" style="display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:0.7rem;">▶</div>') +
                '<div class="rec-meta"><div class="rec-type ' + cls + '">' +
                fmtType(e.event_type) + '</div>' +
                '<div class="rec-time">' + time + '</div></div></div>';
        });
        recStrip.innerHTML = rh || '<div class="empty-state">No recordings yet</div>';
    }).catch(function() {});
}

function fmtType(t) { return t.replace(/_/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); }); }
function fmtTime(ts) {
    try {
        var d = new Date(ts);
        return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }) + ' ' +
               d.toLocaleTimeString('en-GB');
    } catch(e) { return ts; }
}

setInterval(loadEvents, 5000);
loadEvents();

// ─── Commands ───────────────────────────────
function sendCommand(cmd) { socket.emit('command', { command: cmd }); }

function clearAll() {
    if (!confirm('Delete all recordings and snapshots?')) return;
    fetch('/api/clear', { method: 'POST' }).then(function() {
        showToast('All cleared', 'success');
        loadEvents();
    });
}

// ─── Modal ──────────────────────────────────
function openEvent(mediaUrl, thumbUrl, info) {
    var html = '';
    if (mediaUrl && mediaUrl.endsWith('.mp4')) {
        html = '<video controls autoplay src="' + mediaUrl + '"></video>';
    } else if (mediaUrl) {
        html = '<img src="' + mediaUrl + '" alt="Event">';
    }
    modalContent.innerHTML = html;
    modalInfo.textContent = info || '';
    modal.style.display = 'flex';
}

function closeModal(e) {
    if (e && e.target !== modal) return;
    modal.style.display = 'none';
    modalContent.innerHTML = '';
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeModal();
});

// ─── Collision ──────────────────────────────
function showCollision() {
    collisionFlash.style.display = 'flex';
    setTimeout(function() { collisionFlash.style.display = 'none'; }, 3500);
    loadEvents();
}

// ─── Toast ──────────────────────────────────
function showToast(msg, type) {
    var t = document.createElement('div');
    t.className = 'toast ' + (type || 'success');
    t.textContent = msg;
    toasts.appendChild(t);
    setTimeout(function() { t.remove(); }, 3000);
}

// ─── Connection ─────────────────────────────
socket.on('connect', function() { showToast('Connected', 'success'); });
socket.on('disconnect', function() {
    showToast('Disconnected', 'error');
    setOn(dotStream, labelStream, false);
    setOn(dotPi, labelPi, false);
    setOn(dotAi, labelAi, false);
});

// ─── Settings slider ────────────────────────
var distSlider = document.getElementById('dist-threshold');
var distSliderVal = document.getElementById('dist-threshold-val');
var settingsTimer = null;

distSlider.addEventListener('input', function() {
    distSliderVal.textContent = distSlider.value + 'cm';
});

distSlider.addEventListener('change', function() {
    clearTimeout(settingsTimer);
    settingsTimer = setTimeout(function() {
        fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ distance_threshold: parseInt(distSlider.value) })
        }).then(function() {
            showToast('Threshold: ' + distSlider.value + 'cm', 'success');
        });
    }, 300);
});

fetch('/api/settings').then(function(r) { return r.json(); }).then(function(s) {
    if (s.distance_threshold) {
        distSlider.value = s.distance_threshold;
        distSliderVal.textContent = s.distance_threshold + 'cm';
    }
});
