import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import paramiko
import time
import requests

# =====================================================================
# 🛠️ DEĞİŞTİRMEN GEREKEN ALANLAR
# =====================================================================
API_TOKEN = '8826147048:AAFkZlZOKsS43RWrFXALU90XHO5sviSJkg0'  # @BotFather'dan aldığın bot tokenı
MASTER_PANEL_API = "https://vip.fastline-tm-belet-film.ru:8000/api"  # Marzban API linkin
MASTER_ADMIN_USERNAME = "komutan31"  # Marzban panel kullanıcı adın
MASTER_ADMIN_PASSWORD = "admin"  # Marzban panel şifren
# =====================================================================

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

# --- MARZBAN API TOKEN ALMA FONKSİYONU ---
def get_marzban_token():
    try:
        login_url = f"{MASTER_PANEL_API}/admin/token"
        login_data = {"username": MASTER_ADMIN_USERNAME, "password": MASTER_ADMIN_PASSWORD}
        response = requests.post(login_url, data=login_data, timeout=10).json()
        return response.get("access_token")
    except Exception:
        return None

# --- ANA MENÜ KLAVYENİZ ---
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🖥️ Node Listesi (Durum/Trafik)", callback_data="node_listesi_goruntule"))
    markup.row(InlineKeyboardButton("🔄 IP Değiştir (Node Seç)", callback_data="ip_degistir_secim"))
    return markup

# --- PANEL BAŞLANGICI (/start veya /panel) ---
@bot.message_handler(commands=['panel', 'start'])
def send_welcome(message):
    panel_text = (
        "🛡️ **GÜVENLİK KONTROL PANELİ**\n\n"
        "Lütfen yapmak istediğiniz işlemi aşağıdaki menüden seçin:"
    )
    bot.send_message(message.chat.id, panel_text, parse_mode="Markdown", reply_markup=main_menu())

# --- ÖZELLİK 1: NODE LİSTESİNİ BUTON OLARAK GÖSTERME ---
@bot.callback_query_handler(func=lambda call: call.data == "node_listesi_goruntule")
def show_nodes_status(call):
    chat_id = call.message.chat.id
    token = get_marzban_token()
    
    if not token:
        bot.answer_callback_query(call.id, "❌ Panel API bağlantısı başarısız!", show_alert=True)
        return

    try:
        headers = {"Authorization": f"Bearer {token}"}
        nodes_response = requests.get(f"{MASTER_PANEL_API}/nodes", headers=headers, timeout=10).json()
        
        markup = InlineKeyboardMarkup()
        
        for node in nodes_response:
            status = node.get("status", "disconnected")
            status_emoji = "🟢" if status == "connected" else "🟡" if status == "connecting" else "🔴"
            node_name = node.get("name", "Bilinmeyen Node")
            node_id = node.get("id")
            
            markup.add(InlineKeyboardButton(f"{status_emoji} {node_name}", callback_data=f"node_detay_{node_id}"))
            
        markup.add(InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data="ana_menuye_don"))
        
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, 
                              text="🖥️ **Mevcut Marzban Nodeları:**\n\nCanlı trafik ve bağlantı durumunu görmek için bir node seçin:", 
                              reply_markup=markup, parse_mode="Markdown")
                              
    except Exception as e:
        bot.send_message(chat_id, f"❌ Node listesi alınırken hata oluştu: `{str(e)}`")

# --- ÖZELLİK 2: SEÇİLEN NODE'UN DETAYLI DURUM VE TRAFİK BİLGİSİ ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("node_detay_"))
def show_node_details(call):
    chat_id = call.message.chat.id
    node_id = call.data.split("_")[2]
    token = get_marzban_token()
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        node = requests.get(f"{MASTER_PANEL_API}/node/{node_id}", headers=headers, timeout=10).json()
        
        total_bytes = node.get("uplink", 0) + node.get("downlink", 0)
        total_gb = total_bytes / (1024 ** 3)
        uplink_gb = node.get("uplink", 0) / (1024 ** 3)
        downlink_gb = node.get("downlink", 0) / (1024 ** 3)
        
        status = node.get("status", "disconnected")
        status_text = "Bağlı 🟢" if status == "connected" else "Bağlanıyor 🟡" if status == "connecting" else "Bağlantı Yok 🔴"
        
        detay_mesaj = (
            f"🖥️ **NODE DETAYLARI: {node.get('name')}**\n\n"
            f"🌐 **IP Adresi:** `{node.get('address')}`\n"
            f"🔌 **Port:** `{node.get('port')}`\n"
            f"⚡ **Sistem Durumu:** {status_text}\n\n"
            f"📊 **Trafik Tüketimi:**\n"
            f"🔼 Yükleme (Uplink): {round(uplink_gb, 2)} GB\n"
            f"🔽 İndirme (Downlink): {round(downlink_gb, 2)} GB\n"
            f"📈 **Toplam Trafik:** {round(total_gb, 2)} GB"
        )
        
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔄 Bu Node'un IP'sini Değiştir", callback_data=f"node_select_{node_id}"))
        markup.row(InlineKeyboardButton("⬅️ Node Listesine Dön", callback_data="node_listesi_goruntule"))
        
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, 
                              text=detay_mesaj, reply_markup=markup, parse_mode="Markdown")
                              
    except Exception as e:
        bot.send_message(chat_id, f"❌ Node detayları alınamadı: `{str(e)}`")

# --- ÖZELLİK 3: IP DEĞİŞTİRMEK İÇİN NODE SEÇİM MENÜSÜ ---
@bot.callback_query_handler(func=lambda call: call.data == "ip_degistir_secim")
def choose_node_for_ip(call):
    chat_id = call.message.chat.id
    token = get_marzban_token()
    
    if not token:
        bot.answer_callback_query(call.id, "❌ Panel API bağlantısı başarısız!", show_alert=True)
        return

    try:
        headers = {"Authorization": f"Bearer {token}"}
        nodes_response = requests.get(f"{MASTER_PANEL_API}/nodes", headers=headers, timeout=10).json()
        
        markup = InlineKeyboardMarkup()
        for node in nodes_response:
            markup.add(InlineKeyboardButton(f"🖥️ {node.get('name')} ({node.get('address')})", callback_data=f"node_select_{node.get('id')}"))
            
        markup.add(InlineKeyboardButton("⬅️ Ana Menü", callback_data="ana_menuye_don"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, 
                              text="📝 Hangi Node'un IP adresini değiştirmek ve sıfırdan kurmak istiyorsunuz?", reply_markup=markup)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Liste alınırken hata oluştu: `{str(e)}`")

# Seçilen Node'u kaydedip IP isteme adımı
@bot.callback_query_handler(func=lambda call: call.data.startswith("node_select_"))
def node_selected(call):
    chat_id = call.message.chat.id
    selected_node_id = call.data.split("_")[2]
    
    user_data[chat_id] = {'node_id': selected_node_id}
    
    msg = bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, 
                                text="🚀 Seçim başarılı. Şimdi yeni kuracağınız **VPS IP Adresini** yazın:")
    bot.register_next_step_handler(msg, get_new_ip)

def get_new_ip(message):
    chat_id = message.chat.id
    user_data[chat_id]['new_ip'] = message.text.strip()
    
    msg = bot.send_message(chat_id, "🔑 Yeni VPS sunucusunun **root şifresini** yazın:")
    bot.register_next_step_handler(msg, start_automation)

# --- ÖZELLİK 4: SSH OTOMASYONU VE GÜNCEL SCRIPT KURULUM MOTORU ---
def start_automation(message):
    chat_id = message.chat.id
    user_data[chat_id]['vps_password'] = message.text.strip()
    
    node_id = user_data[chat_id]['node_id']
    new_ip = user_data[chat_id]['new_ip']
    vps_pass = user_data[chat_id]['vps_password']
    
    status_msg = bot.send_message(chat_id, "⏳ Otomasyon başlatıldı...\n1. Ana sunucudan güvenlik sertifikası alınıyor...")
    
    try:
        # SÜREÇ 1: Sertifikayı ana panel API'sinden çekme
        cert_text = get_marzban_certificate() 
        
        bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, 
                              text=f"⏳ [1/3] Sertifika başarıyla alındı.\n2. `{new_ip}` VPS'ine SSH bağlantısı kuruluyor ve yeni script yükleniyor...")

        # SÜREÇ 2: SSH Bağlantısı ve Kurulum
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=new_ip, username='root', password=vps_pass, timeout=15)
        
        # SİZİN VERDİĞİNİZ GÜNCEL SCRIPT BURAYA EKLENDİ (Onay sorusunu geçmek için echo "y" entegre edildi)
        install_cmd = 'echo "y" | sudo bash -c "$(curl -sL https://github.com/Gozargah/Marzban-scripts/raw/master/marzban-node.sh)" @ install'
        stdin, stdout, stderr = ssh.exec_command(install_cmd)
        stdout.channel.recv_exit_status()  # Kurulum bitene kadar akışı bekletir
        
        # SÜREÇ 3: Sertifikayı otomatik dosyaya yazma
        cert_write_cmd = f"echo '{cert_text}' > /var/lib/marzban-node/ssl_client_cert.pem"
        ssh.exec_command(cert_write_cmd)
        
        # Node servisini yenileyerek sertifikayı okumasını sağlama
        ssh.exec_command("marzban-node restart")
        ssh.close()
        
        bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, 
                              text=f"⏳ [2/3] Yeni script kuruldu ve sertifika işlendi.\n3. Marzban panelindeki (Master) IP adresi güncelleniyor...")

        # SÜREÇ 4: Ana Panel API'si üzerinden IP'yi güncelleme
        update_node_ip_on_master(node_id, new_ip)
        
        # Başarılı Sonuçlandırma ve Ana Menü Kısayolu
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data="ana_menuye_don"))
        
        bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, 
                              text=f"✅ **İŞLEM BAŞARIYLA TAMAMLANDI!**\n\n• İstediğiniz güncel `Marzban-scripts` kurularak bağlandı.\n• Sertifika otomatik entegre edildi.\n• Panel üzerindeki IP adresi `{new_ip}` olarak güncellendi! 🟢",
                              reply_markup=markup)

    except Exception as e:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data="ana_menuye_don"))
        bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, 
                              text=f"❌ **HATA OLUŞTU**\nSüreç kesintiye uğradı: `{str(e)}`", reply_markup=markup)

# --- YARDIMCI API ARAÇLARI ---
def get_marzban_certificate():
    token = get_marzban_token()
    headers = {"Authorization": f"Bearer {token}"}
    cert_response = requests.get(f"{MASTER_PANEL_API}/node/settings", headers=headers, timeout=10).json()
    return cert_response.get("ssl_client_cert")

def update_node_ip_on_master(node_id, new_ip):
    token = get_marzban_token()
    headers = {"Authorization": f"Bearer {token}"}
    node_url = f"{MASTER_PANEL_API}/node/{node_id}"
    
    current_node = requests.get(node_url, headers=headers, timeout=10).json()
    
    payload = {
        "name": current_node.get("name"),
        "address": new_ip,
        "port": current_node.get("port", 62050),
        "api_port": current_node.get("api_port", 62051),
        "usage_ratio": current_node.get("usage_ratio", 1)
    }
    requests.put(node_url, json=payload, headers=headers, timeout=10)

# Geri dönüş callback'i
@bot.callback_query_handler(func=lambda call: call.data == "ana_menuye_don")
def back_to_main(call):
    panel_text = "🛡️ **GÜVENLİK KONTROL PANELİ**\n\nLütfen yapmak istediğiniz işlemi aşağıdaki menüden seçin:"
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                          text=panel_text, reply_markup=main_menu(), parse_mode="Markdown")

# --- BOTU BAŞLAT ---
if __name__ == '__main__':
    print("🤖 Marzban Yönetim Botu aktif ve çalışıyor...")
    bot.infinity_polling()
