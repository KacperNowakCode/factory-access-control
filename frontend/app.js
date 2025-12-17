const API_URL = "http://127.0.0.1:5000/api";
let html5QrcodeScanner = null;
let currentQrCode = null;
let faceStream = null;

window.onload = function() {
    startQrScanner();
    document.getElementById('qr-file-input').addEventListener('change', scanQrFromFile);
};

// --- NAWIGACJA ---
function toggleAdmin() {
    const admin = document.getElementById('admin-panel');
    const gate = document.getElementById('gate-interface');
    
    if (admin.style.display === 'none') {
        admin.style.display = 'block';
        gate.style.display = 'none';
        stopQrScanner();
        loadAdminData();
    } else {
        admin.style.display = 'none';
        gate.style.display = 'block';
        resetProcess();
    }
}

function showStep(n) {
    document.querySelectorAll('.step-container').forEach(el => el.classList.remove('active'));
    document.getElementById(`step-${n}`).classList.add('active');
}

// --- KROK 1: QR ---
function startQrScanner() {
    showStep(1);
    html5QrcodeScanner = new Html5Qrcode("qr-reader");
    html5QrcodeScanner.start({ facingMode: "user" }, { fps: 10, qrbox: 250 }, onScanSuccess);
}

function scanQrFromFile(e) {
    if (!e.target.files.length) return;
    new Html5Qrcode("qr-reader").scanFile(e.target.files[0], true)
        .then(onScanSuccess).catch(() => alert("Brak kodu QR na zdjęciu"));
}

function onScanSuccess(decodedText) {
    currentQrCode = decodedText;
    stopQrScanner();
    goToFaceStep();
}

function stopQrScanner() {
    if(html5QrcodeScanner) try { html5QrcodeScanner.stop().then(() => html5QrcodeScanner.clear()); } catch(e){}
}

// --- KROK 2: VIDEO (PODGLĄD) ---
function goToFaceStep() {
    showStep(2);
    document.getElementById('detected-qr-code').innerText = currentQrCode;
    const video = document.getElementById('face-video');
    
    // Czyścimy canvas (usuwamy starą ramkę)
    const ctx = document.getElementById('face-canvas').getContext('2d');
    ctx.clearRect(0, 0, 640, 480);

    navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
        .then(stream => {
            faceStream = stream;
            video.srcObject = stream;
        })
        .catch(err => alert("Błąd kamery!"));
}

// --- KLUCZOWA FUNKCJA: KLIKNIĘCIE I WERYFIKACJA ---
async function captureAndVerify() {
    const video = document.getElementById('face-video');
    const canvas = document.createElement('canvas'); // Wirtualny canvas do zrzutu
    canvas.width = 640;
    canvas.height = 480;
    
    // Robimy zdjęcie z wideo
    canvas.getContext('2d').drawImage(video, 0, 0, 640, 480);
    
    canvas.toBlob(async function(blob) {
        const formData = new FormData();
        formData.append('qr_code', currentQrCode);
        formData.append('frame', blob, 'capture.jpg');

        try {
            const response = await fetch(`${API_URL}/verify_entry`, { method: 'POST', body: formData });
            const data = await response.json();

            // Rysujemy ramkę na "żywym" podglądzie (zostanie tam)
            drawResultBox(data);

            if (data.status === 'success') {
                // Poczekaj sekundę żeby użytkownik zobaczył zieloną ramkę, potem pokaż wynik
                setTimeout(() => showFinalResult(data, true), 1000);
            } else {
                // Jeśli błąd, też pokaż ramkę (czerwoną)
                if(!data.face_rect) alert("Nie widzę twarzy! Spróbuj ponownie.");
            }

        } catch (e) {
            console.error(e);
            alert("Błąd połączenia z serwerem");
        }
    }, 'image/jpeg');
}

function drawResultBox(data) {
    const canvas = document.getElementById('face-canvas');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, 640, 480); // Czyść stare

    if (data.face_rect) {
        const { x, y, w, h } = data.face_rect;
        ctx.lineWidth = 5;
        ctx.strokeStyle = (data.status === 'success') ? '#2ecc71' : '#e74c3c';
        ctx.strokeRect(x, y, w, h);
    }
}

function showFinalResult(data, success) {
    showStep(3);
    const resDiv = document.getElementById('final-result');
    if (success) {
        resDiv.innerText = `DOSTĘP PRZYZNANY\nWitaj: ${data.user}`;
        resDiv.className = 'result-box success';
    } else {
        resDiv.innerText = `ODMOWA DOSTĘPU\n${data.reason}`;
        resDiv.className = 'result-box denied';
    }
}

function resetProcess() {
    if(faceStream) faceStream.getTracks().forEach(track => track.stop());
    stopQrScanner();
    currentQrCode = null;
    startQrScanner();
}

// --- ADMIN ---
async function loadAdminData() {
    const users = await (await fetch(`${API_URL}/users`)).json();
    document.getElementById('userTableBody').innerHTML = users.map(u => `
        <tr>
            <td><img src="http://127.0.0.1:5000${u.photo}" class="mini-img"></td>
            <td>${u.name}</td>
            <td><a href="http://127.0.0.1:5000/static/qrcodes/${u.qr}.png" target="_blank"><img src="http://127.0.0.1:5000/static/qrcodes/${u.qr}.png" class="qr-preview"></a></td>
            <td><button class="btn-delete" onclick="deleteUser(${u.id})">USUŃ</button></td>
        </tr>
    `).join('');

    const logs = await (await fetch(`${API_URL}/logs`)).json();
    document.getElementById('logList').innerHTML = logs.map(l => 
        `<li style="color:${l.status==='SUCCESS'?'green':'red'}">[${l.time}] ${l.user}</li>`
    ).join('');
}

async function registerUser() {
    const name = document.getElementById('newName').value;
    const photo = document.getElementById('newPhoto').files[0];
    if(!name || !photo) return alert("Podaj dane!");
    
    const fd = new FormData(); fd.append('name', name); fd.append('photo', photo);
    await fetch(`${API_URL}/register`, {method:'POST', body:fd});
    loadAdminData();
}

async function deleteUser(id) {
    if(confirm("Usunąć?")) { await fetch(`${API_URL}/users/${id}`, {method:'DELETE'}); loadAdminData(); }
}