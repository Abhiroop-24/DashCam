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

// ─── SOS Emergency System ───────────────────
var sosOverlay = document.getElementById('sos-overlay');
var sosCountdownEl = document.getElementById('sos-countdown');
var sosReasonEl = document.getElementById('sos-reason');
var sosLocationEl = document.getElementById('sos-location-text');
var sosDispatch = document.getElementById('sos-dispatch');
var sosCancelBtn = document.getElementById('sos-cancel-btn');

var sosTimer = null;
var sosCountdown = 10;
var sosIsActive = false;

// Listen for auto-SOS from server (G-force spikes)
socket.on('sos_triggered', function(d) {
    showSOSOverlay(d.reason || 'Collision detected');
});

socket.on('sos_cancelled', function() {
    if (sosTimer) { clearInterval(sosTimer); sosTimer = null; }
    sosIsActive = false;
    sosCountdownEl.classList.remove('urgent');
    sosOverlay.style.display = 'none';
    sosDispatch.style.display = 'none';
    showToast('SOS Cancelled', 'success');
});

function manualSOS() {
    if (sosIsActive) return;
    if (!confirm('⚠️ TRIGGER EMERGENCY SOS?\n\nThis will contact emergency services.\nOnly use in a real emergency.')) return;
    sendCommand('sos_manual');
    showSOSOverlay('Manual SOS activated from dashboard');
}

function showSOSOverlay(reason) {
    if (sosIsActive) return;
    sosIsActive = true;
    sosCountdown = 10;
    sosCountdownEl.textContent = sosCountdown;
    sosReasonEl.textContent = reason || 'Emergency detected';

    // Reset evidence status
    document.getElementById('sos-ev-video').textContent = '⏳ Video clip';
    document.getElementById('sos-ev-snapshot').textContent = '⏳ Snapshot';
    document.getElementById('sos-ev-sensor').textContent = '⏳ Sensor data';
    document.getElementById('sos-ev-gps').textContent = '⏳ Location';

    // Reset service status
    document.getElementById('sos-ambulance-status').textContent = 'Standby';
    document.getElementById('sos-police-status').textContent = 'Standby';
    document.getElementById('sos-ambulance').className = 'sos-service';
    document.getElementById('sos-police').className = 'sos-service';

    sosLocationEl.textContent = 'Fetching location...';
    sosCancelBtn.style.display = '';

    sosOverlay.style.display = 'flex';

    // Try to get geolocation
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(pos) {
            var lat = pos.coords.latitude.toFixed(6);
            var lon = pos.coords.longitude.toFixed(6);
            sosLocationEl.textContent = lat + ', ' + lon;
            document.getElementById('sos-ev-gps').textContent = '✅ Location';
            document.getElementById('sos-ev-gps').classList.add('ready');
        }, function() {
            sosLocationEl.textContent = 'Location unavailable — using Pi GPS fallback';
        }, { timeout: 5000 });
    }

    // Simulate evidence readiness
    setTimeout(function() {
        document.getElementById('sos-ev-snapshot').textContent = '✅ Snapshot';
        document.getElementById('sos-ev-snapshot').classList.add('ready');
    }, 1500);
    setTimeout(function() {
        document.getElementById('sos-ev-sensor').textContent = '✅ Sensor data';
        document.getElementById('sos-ev-sensor').classList.add('ready');
    }, 2500);
    setTimeout(function() {
        document.getElementById('sos-ev-video').textContent = '✅ Video clip';
        document.getElementById('sos-ev-video').classList.add('ready');
    }, 4000);

    // Start countdown
    sosTimer = setInterval(function() {
        sosCountdown--;
        sosCountdownEl.textContent = sosCountdown;

        if (sosCountdown <= 5) {
            sosCountdownEl.classList.add('urgent');
        }

        // Simulate service connection at different times
        if (sosCountdown === 6) {
            document.getElementById('sos-ambulance-status').textContent = 'Connecting...';
            document.getElementById('sos-ambulance').classList.add('connecting');
        }
        if (sosCountdown === 4) {
            document.getElementById('sos-police-status').textContent = 'Connecting...';
            document.getElementById('sos-police').classList.add('connecting');
        }

        if (sosCountdown <= 0) {
            clearInterval(sosTimer);
            sosTimer = null;
            dispatchSOS();
        }
    }, 1000);

    // Play alert sound (browser beep)
    try {
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        function beep(freq, dur) {
            var osc = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = freq;
            gain.gain.value = 0.3;
            osc.start();
            setTimeout(function() { osc.stop(); }, dur);
        }
        beep(880, 200);
        setTimeout(function() { beep(880, 200); }, 300);
        setTimeout(function() { beep(1200, 400); }, 600);
    } catch(e) {}
}

function dispatchSOS() {
    // Update services to "dispatched"
    document.getElementById('sos-ambulance-status').textContent = 'Dispatched';
    document.getElementById('sos-ambulance').className = 'sos-service dispatched';
    document.getElementById('sos-police-status').textContent = 'Dispatched';
    document.getElementById('sos-police').className = 'sos-service dispatched';

    sosCancelBtn.style.display = 'none';

    // Show dispatch confirmation after 1.5s
    setTimeout(function() {
        sosOverlay.style.display = 'none';
        sosDispatch.style.display = 'flex';
    }, 1500);
}

function cancelSOS() {
    if (sosTimer) {
        clearInterval(sosTimer);
        sosTimer = null;
    }
    sosIsActive = false;
    sosCountdownEl.classList.remove('urgent');
    sosOverlay.style.display = 'none';
    sendCommand('sos_cancel');
    showToast('SOS Cancelled — stay safe', 'success');
}

function closeDispatch() {
    sosDispatch.style.display = 'none';
    sosIsActive = false;
    sosCountdownEl.classList.remove('urgent');
}
