import logging
import requests
import json
import subprocess
import paramiko
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# Loglama ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- KONFIGÜRASYON --------------------
TOKEN = "8826147048:AAFkZlZOKsS43RWrFXALU90XHO5sviSJkg0"  # Telegram Bot Token

# Marzban Panel Bilgileri
MARZBAN_URL = "https://vip.fastline-tm-belet-film.ru:8000"  # Kendi panel adresiniz
MARZBAN_USERNAME = "komutan31"  # Marzban admin kullanıcı adı
MARZBAN_PASSWORD = "admin"  # Marzban admin şifresi

# VPS SSH Bilgileri (node script'ini kurmak için)
VPS_IP = "5.42.117.80"  # Node'un kurulu olduğu VPS IP
SSH_USERNAME = "root"
SSH_PASSWORD = "t6-rvs-tTHKYB5"  # Veya SSH key kullanabilirsiniz
NODE_SCRIPT_URL = "https://github.com/Gozargah/Marzban-scripts/raw/master/marzban-node.sh"  # Node script URL

# Conversation States
(IP_SOR, SIFRE_SOR) = range(2)

# -------------------- MARZBAN API İŞLEMLERİ --------------------
def get_marzban_token():
    """Marzban API'den token alır"""
    try:
        url = f"{MARZBAN_URL}/api/admin/token"
        payload = {
            "username": MARZBAN_USERNAME,
            "password": MARZBAN_PASSWORD
        }
        response = requests.post(url, json=payload, verify=False)
        response.raise_for_status()
        token_data = response.json()
        return token_data.get("access_token")
    except Exception as e:
        logger.error(f"Marzban token alınamadı: {e}")
        return None

def get_nodes():
    """Marzban'daki node'ları listeler"""
    try:
        token = get_marzban_token()
        if not token:
            return None
        
        url = f"{MARZBAN_URL}/api/nodes"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Node'lar alınamadı: {e}")
        return None

def update_node_ip(node_id, new_ip, node_password):
    """Node IP'sini günceller"""
    try:
        token = get_marzban_token()
        if not token:
            return False, "Token alınamadı"
        
        # Önce node'u getir
        url = f"{MARZBAN_URL}/api/nodes/{node_id}"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        node_data = response.json()
        
        # IP'yi güncelle
        node_data["address"] = new_ip
        
        # Node'u güncelle (PUT metodunu kullan)
        response = requests.put(url, json=node_data, headers=headers, verify=False)
        response.raise_for_status()
        
        return True, "Node IP başarıyla güncellendi"
    except Exception as e:
        logger.error(f"Node IP güncellenemedi: {e}")
        return False, f"Hata: {str(e)}"

# -------------------- SSH VE SCRIPT İŞLEMLERİ --------------------
def update_node_script_on_vps(vps_ip, ssh_user, ssh_password, new_ip, node_password):
    """VPS'de node script'ini yeni IP ile günceller"""
    try:
        # SSH bağlantısı
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(vps_ip, username=ssh_user, password=ssh_password, timeout=10)
        
        # Node'u durdur
        ssh.exec_command("systemctl stop marzban-node")
        
        # Script'i indir ve çalıştır
        command = f"""
        # Eski node'u temizle
        rm -rf /opt/marzban-node
        
        # Script'i indir
        curl -s {NODE_SCRIPT_URL} > /tmp/install_node.sh
        chmod +x /tmp/install_node.sh
        
        # Script'i yeni IP ve şifre ile çalıştır
        bash /tmp/install_node.sh --ip {new_ip} --password {node_password}
        
        # Node'u başlat
        systemctl start marzban-node
        systemctl enable marzban-node
        
        # Durumu kontrol et
        systemctl status marzban-node --no-pager
        """
        
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        ssh.close()
        
        if "active (running)" in output or "active (running)" in error:
            return True, "VPS'de node script başarıyla güncellendi"
        else:
            return False, f"Script hatası: {error or output}"
            
    except Exception as e:
        logger.error(f"VPS'de script güncellenemedi: {e}")
        return False, f"SSH hatası: {str(e)}"

# -------------------- TELEGRAM BOT KOMUTLARI --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    server_status = (
        "🛡 GÜVENLİK KONTROL PANELİ\n\n"
        "🌐 SUNUCU DURUMU\n"
        "Marzban Node Yönetimi\n"
        "Sistem Durumu: 🟢 Aktif\n\n"
        "⚙️ NODE YAPILANDIRMA\n"
        "IP Değiştirme ve Güncelleme"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 IP Değiştir", callback_data='ip_degistir')],
        [InlineKeyboardButton("📊 Node Durumu", callback_data='node_durum')],
        [InlineKeyboardButton("🔄 Node Yeniden Başlat", callback_data='node_restart')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(server_status, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'ip_degistir':
        await query.edit_message_text(
            "📝 **Yeni IP Adresini Girin:**\n\n"
            "Örnek: 192.168.1.100\n"
            "İptal etmek için /cancel yazın."
        )
        return IP_SOR
    
    elif query.data == 'node_durum':
        nodes = get_nodes()
        if nodes:
            status_text = "📊 **NODE DURUMU**\n\n"
            for node in nodes:
                status_text += f"🔹 {node.get('name', 'İsimsiz')}\n"
                status_text += f"   IP: {node.get('address', 'Bilinmiyor')}\n"
                status_text += f"   Durum: {'🟢 Aktif' if node.get('status') else '🔴 Pasif'}\n"
                status_text += f"   Port: {node.get('port', 'Bilinmiyor')}\n\n"
            await query.edit_message_text(status_text)
        else:
            await query.edit_message_text("❌ Node bilgileri alınamadı!")
            
    elif query.data == 'node_restart':
        await query.edit_message_text("🔄 Node yeniden başlatılıyor...")
        success, message = update_node_script_on_vps(
            VPS_IP, SSH_USERNAME, SSH_PASSWORD, 
            "mevcut_ip", "mevcut_sifre"
        )
        await query.edit_message_text(f"✅ {message}" if success else f"❌ {message}")

# -------------------- IP VE ŞİFRE ALMA KONUŞMASI --------------------
async def ip_al(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_ip = update.message.text.strip()
    
    # Basit IP kontrolü
    import re
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(ip_pattern, new_ip):
        await update.message.reply_text("❌ Geçersiz IP formatı! Lütfen tekrar deneyin (örn: 192.168.1.100)")
        return IP_SOR
    
    context.user_data['new_ip'] = new_ip
    await update.message.reply_text(
        "🔑 **Node Şifresini Girin:**\n\n"
        "Node'a bağlanmak için kullanılacak şifre.\n"
        "İptal etmek için /cancel yazın."
    )
    return SIFRE_SOR

async def sifre_al(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    node_password = update.message.text.strip()
    
    if len(node_password) < 6:
        await update.message.reply_text("❌ Şifre en az 6 karakter olmalı! Tekrar deneyin.")
        return SIFRE_SOR
    
    context.user_data['node_password'] = node_password
    new_ip = context.user_data['new_ip']
    node_password = context.user_data['node_password']
    
    await update.message.reply_text(
        f"⏳ **İşlem Başlatılıyor...**\n\n"
        f"📌 Yeni IP: `{new_ip}`\n"
        f"🔑 Şifre: `{node_password}`\n\n"
        f"Bu işlem 2-3 dakika sürebilir..."
    )
    
    try:
        # 1. Marzban'daki node IP'sini güncelle
        nodes = get_nodes()
        if not nodes:
            await update.message.reply_text("❌ Node listesi alınamadı!")
            return ConversationHandler.END
            
        node_id = nodes[0]['id']  # İlk node'u al
        
        success, message = update_node_ip(node_id, new_ip, node_password)
        if not success:
            await update.message.reply_text(f"❌ Marzban güncelleme hatası: {message}")
            return ConversationHandler.END
        
        await update.message.reply_text("✅ Marzban panel güncellendi")
        
        # 2. VPS'de node script'ini güncelle
        await update.message.reply_text("📦 VPS'de node script güncelleniyor...")
        
        success, message = update_node_script_on_vps(
            VPS_IP, SSH_USERNAME, SSH_PASSWORD,
            new_ip, node_password
        )
        
        if success:
            await update.message.reply_text(
                f"✅ **İŞLEM BAŞARIYLA TAMAMLANDI!**\n\n"
                f"🌐 Yeni IP: `{new_ip}`\n"
                f"🔑 Yeni Şifre: `{node_password}`\n\n"
                f"Node artık yeni IP ile çalışıyor."
            )
        else:
            await update.message.reply_text(f"❌ VPS güncelleme hatası: {message}")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Beklenmeyen hata: {str(e)}")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ İşlem iptal edildi.")
    return ConversationHandler.END

# -------------------- ANA FONKSİYON --------------------
def main():
    application = Application.builder().token(TOKEN).build()
    
    # Conversation handler (IP ve şifre alma)
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern='ip_degistir')],
        states={
            IP_SOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, ip_al)],
            SIFRE_SOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, sifre_al)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("🚀 Bot başarıyla başlatıldı...")
    application.run_polling()

if __name__ == '__main__':
    main()
