const API_URL = "http://127.0.0.1:5000/api";
let html5QrcodeScanner = null;
let currentQrCode = null;
let faceStream = null;

window.onload = function() {
    startQrScanner();
    // Nasłuchiwanie na wgranie pliku QR
    document.getElementById('qr-file-input').addEventListener('change', scanQrFromFile);
};

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

// --- BRAMKA: KROK 1 (QR) ---
function startQrScanner() {
    showStep(1);
    html5QrcodeScanner = new Html5Qrcode("qr-reader");
    const config = { fps: 10, qrbox: { width: 200, height: 200 } };
    
    html5QrcodeScanner.start({ facingMode: "user" }, config, onScanSuccess)
    .catch(err => {
        console.log("Kamera zajęta lub brak uprawnień - użyj uploadu pliku.");
    });
}

function scanQrFromFile(e) {
    if (e.target.files.length === 0) return;
    const imageFile = e.target.files[0];
    
    const tempScanner = new Html5Qrcode("qr-reader"); // Instancja do pliku
    tempScanner.scanFile(imageFile, true)
        .then(decodedText => {
            onScanSuccess(decodedText, null);
        })
        .catch(err => {
            alert("Nie znaleziono kodu QR na tym zdjęciu.");
        });
}

function onScanSuccess(decodedText, decodedResult) {
    console.log(`QR: ${decodedText}`);
    currentQrCode = decodedText;
    stopQrScanner();
    goToFaceStep();
}

function stopQrScanner() {
    if(html5QrcodeScanner) {
        try { html5QrcodeScanner.stop().then(() => html5QrcodeScanner.clear()); } catch(e) {}
    }
}

// --- BRAMKA: KROK 2 (TWARZ) ---
function goToFaceStep() {
    showStep(2);
    document.getElementById('detected-qr-code').innerText = currentQrCode;
    const video = document.getElementById('face-video');
    
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            faceStream = stream;
            video.srcObject = stream;
        })
        .catch(err => console.error("Błąd kamery Face:", err));
}

async function captureAndVerify() {
    const video = document.getElementById('face-video');
    const canvas = document.getElementById('face-canvas');
    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, 320, 240);
    
    canvas.toBlob(async function(blob) {
        const formData = new FormData();
        formData.append('qr_code', currentQrCode);
        formData.append('frame', blob, 'capture.jpg');

        showStep(3);
        const resDiv = document.getElementById('final-result');
        resDiv.innerText = "Weryfikacja...";
        resDiv.className = 'result-box';

        try {
            const response = await fetch(`${API_URL}/verify_entry`, { method: 'POST', body: formData });
            const data = await response.json();

            if (data.status === 'success') {
                resDiv.innerText = `DOSTĘP PRZYZNANY\nWitaj: ${data.user}`;
                resDiv.className = 'result-box success';
            } else {
                resDiv.innerText = `ODMOWA DOSTĘPU\n${data.reason}`;
                resDiv.className = 'result-box denied';
            }
        } catch (e) {
            resDiv.innerText = "Błąd serwera.";
        }
        if(faceStream) faceStream.getTracks().forEach(track => track.stop());
    }, 'image/jpeg');
}

function showStep(n) {
    document.querySelectorAll('.step-container').forEach(el => el.classList.remove('active'));
    document.getElementById(`step-${n}`).classList.add('active');
}

function resetProcess() {
    if(faceStream) faceStream.getTracks().forEach(track => track.stop());
    stopQrScanner();
    currentQrCode = null;
    document.getElementById('qr-file-input').value = ""; // Reset inputa
    startQrScanner();
}

// --- ADMIN ---
async function registerUser() {
    const name = document.getElementById('newName').value;
    const photo = document.getElementById('newPhoto').files[0];
    if(!name || !photo) return alert("Podaj nazwę i zdjęcie");

    const fd = new FormData(); fd.append('name', name); fd.append('photo', photo);
    const res = await fetch(`${API_URL}/register`, {method:'POST', body:fd});
    const data = await res.json();
    
    if(data.error) alert(data.error);
    else { alert("Dodano!"); loadAdminData(); }
}

async function loadAdminData() {
    // Tabela użytkowników
    const users = await (await fetch(`${API_URL}/users`)).json();
    const tbody = document.getElementById('userTableBody');
    tbody.innerHTML = users.map(u => `
        <tr>
            <td>${u.photo ? `<img src="http://127.0.0.1:5000${u.photo}" class="photo-preview">` : '-'}</td>
            <td>${u.name}</td>
            <td><a href="http://127.0.0.1:5000/static/qrcodes/${u.qr}.png" target="_blank">POBIERZ QR</a></td>
            <td><button class="btn-delete" onclick="deleteUser(${u.id})">USUŃ</button></td>
        </tr>
    `).join('');

    // Logi
    const logs = await (await fetch(`${API_URL}/logs`)).json();
    const lList = document.getElementById('logList');
    lList.innerHTML = logs.map(l => {
        let snap = l.snapshot ? `<br><a href="http://127.0.0.1:5000${l.snapshot}" target="_blank">PODGLĄD INCYDENTU</a>` : '';
        return `<li style="color:${l.status==='SUCCESS'?'green':'red'}">[${l.time}] ${l.user} ${snap}</li>`;
    }).join('');
}

async function deleteUser(id) {
    if(confirm("Usunąć użytkownika?")) {
        await fetch(`${API_URL}/users/${id}`, { method: 'DELETE' });
        loadAdminData();
    }
}