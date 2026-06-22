import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests

# =====================================================================
# 🛠️ DEĞİŞTİRMEN GEREKEN ALANLAR
# =====================================================================
API_TOKEN = '8826147048:AAFkZlZOKsS43RWrFXALU90XHO5sviSJkg0'  # @BotFather'dan aldığın bot tokenı
MASTER_PANEL_API = "https://vip.fastline-tm-belet-film.ru:8000/api"  # Marzban API linkin
MASTER_ADMIN_USERNAME = "komutan31"  # Ana panel süper admin kullanıcı adın
MASTER_ADMIN_PASSWORD = "admin"  # Ana panel süper admin şifren

# 🔐 BOTA ERİŞEBİLECEK TELEGRAM ID'LERİ (Buraya kendi Telegram ID'ni yaz)
# Birden fazla ID eklemek istersen [12345678, 87654321] şeklinde yazabilirsin.
ALLOWED_TELEGRAM_IDS = [8359722718 ,7115611768] 
# =====================================================================

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

# --- GÜVENLİK FİLTRESİ (SADECE YETKİLİ ID'LER KULLANABİLİR) ---
def is_authorized(message_or_call):
    if isinstance(message_or_call, telebot.types.CallbackQuery):
        user_id = message_or_call.from_user.id
    else:
        user_id = message_or_call.chat.id
        
    return user_id in ALLOWED_TELEGRAM_IDS

# --- MARZBAN API TOKEN ALMA FONKSİYONU ---
def get_marzban_token():
    try:
        login_url = f"{MASTER_PANEL_API}/admin/token"
        login_data = {"username": MASTER_ADMIN_USERNAME, "password": MASTER_ADMIN_PASSWORD}
        response = requests.post(login_url, data=login_data, timeout=10)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    except Exception:
        return None

# --- ANA MENÜ (START) ---
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("👥 Panel Adminleri", callback_data="adminleri_listele"),
        InlineKeyboardButton("➕ Admin Ekle", callback_data="admin_ekle_basla")
    )
    markup.row(InlineKeyboardButton("🌐 Hostlar ve IP Değiştir", callback_data="hostlari_listele"))
    return markup

# --- START VE PANEL KOMUTU ---
@bot.message_handler(commands=['panel', 'start'])
def send_welcome(message):
    # Yetkisiz giriş engeli
    if not is_authorized(message):
        bot.send_message(message.chat.id, "❌ **YETKİSİZ ERİŞİM!**\nBu botu kullanmaya yetkiniz bulunmuyor.")
        return

    panel_text = (
        "🛡️ **MARZBAN GELİŞMİŞ KONTROL PANELİ**\n\n"
        "Sisteme başarıyla bağlanıldı. Lütfen işlem yapmak istediğiniz menüyü seçin 👇"
    )
    bot.send_message(message.chat.id, panel_text, parse_mode="Markdown", reply_markup=main_menu())

# =====================================================================
# 👥 BÖLÜM 1: PANEL ADMİNLERİ YÖNETİMİ & EKLEME
# =====================================================================

# --- YENİ ADMİN EKLEME ADIMLARI ---
@bot.callback_query_handler(func=lambda call: call.data == "admin_ekle_basla")
def add_admin_start(call):
    if not is_authorized(call):
        bot.answer_callback_query(call.id, "❌ Yetkiniz yok!", show_alert=True)
        return
        
    chat_id = call.message.chat.id
    user_data[chat_id] = {} # Veriyi sıfırla
    
    msg = bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                                text="👤 **YENİ ADMİN EKLEME (CLI Create)**\n\nOluşturulacak yeni adminin **Kullanıcı Adını (Username)** yazın:")
    bot.register_next_step_handler(msg, get_new_admin_username)

def get_new_admin_username(message):
    if not is_authorized(message): return
    chat_id = message.chat.id
    username = message.text.strip() if message.text else ""
    
    if not username:
        bot.send_message(chat_id, "❌ Geçersiz kullanıcı adı. Lütfen /start ile tekrar deneyin.")
        return

    user_data[chat_id]['new_admin_username'] = username
    msg = bot.send_message(chat_id, f"🔑 `{username}` admini için bir **Şifre (Password)** belirleyin:")
    bot.register_next_step_handler(msg, execute_admin_create)

def execute_admin_create(message):
    if not is_authorized(message): return
    chat_id = message.chat.id
    password = message.text.strip() if message.text else ""
    
    if not password:
        bot.send_message(chat_id, "❌ Geçersiz şifre. İşlem iptal edildi.")
        return
        
    username = user_data[chat_id].get('new_admin_username')
    token = get_marzban_token()
    
    if not token:
        bot.send_message(chat_id, "❌ Panel API bağlantısı başarısız oldu!")
        return

    status_msg = bot.send_message(chat_id, "⏳ Yeni admin panel veritabanına işleniyor...")

    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Sudo durumu her zaman False (n) olarak ayarlandı
        payload = {
            "username": username,
            "password": password,
            "is_sudo": False 
        }
        
        res = requests.post(f"{MASTER_PANEL_API}/admin", json=payload, headers=headers, timeout=10)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data="ana_menuye_don"))
        
        if res.status_code in [200, 201]:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id,
                                  text=f"✅ **ADMİN BAŞARIYLA OLUŞTU!**\n\n• **Kullanıcı Adı:** `{username}`\n• **Şifre:** `{password}`\n• **Sudo Yetkisi:** `Hayır (n)` 🟢\n\nArtık bu admin kendi paneline girip kullanıcı üretebilir.",
                                  reply_markup=markup, parse_mode="Markdown")
        elif res.status_code == 409:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id,
                                  text=f"❌ **HATA:** `{username}` adında bir admin panelde zaten mevcut!",
                                  reply_markup=markup)
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id,
                                  text=f"❌ **HATA:** Admin oluşturulamadı. API Hata Kodu: `{res.status_code}`",
                                  reply_markup=markup)
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ İşlem sırasında bir sorun oluştu: `{str(e)}`")


# --- ADMİNLERİ LİSTELEME ---
@bot.callback_query_handler(func=lambda call: call.data == "adminleri_listele")
def list_admins(call):
    if not is_authorized(call): return
    chat_id = call.message.chat.id
    token = get_marzban_token()
    if not token:
        bot.answer_callback_query(call.id, "❌ API bağlantısı başarısız!", show_alert=True)
        return

    try:
        headers = {"Authorization": f"Bearer {token}"}
        admins = requests.get(f"{MASTER_PANEL_API}/admins", headers=headers, timeout=10).json()
        
        markup = InlineKeyboardMarkup()
        for admin in admins:
            if isinstance(admin, dict):
                username = admin.get("username")
                role_emoji = "👑" if admin.get("is_sudo") else "👨‍💻"
                markup.add(InlineKeyboardButton(f"{role_emoji} {username}", callback_data=f"adm_detay_{username}"))
            
        markup.add(InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data="ana_menuye_don"))
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                              text="👥 **Panelde Kayıtlı Tüm Adminler:**\n\nDetayları görmek ve yönetmek için bir admin seçin:",
                              reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Admin listesi alınamadı: `{str(e)}`")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_detay_"))
def show_admin_details(call):
    if not is_authorized(call): return
    chat_id = call.message.chat.id
    target_username = call.data.split("_")[2]
    token = get_marzban_token()

    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{MASTER_PANEL_API}/users", headers=headers, timeout=10)
        
        if response.status_code != 200:
            bot.send_message(chat_id, "❌ Kullanıcı listesi panelden çekilemedi.")
            return
            
        users_data = response.json()
        all_users = users_data.get("users", []) if isinstance(users_data, dict) else []
        
        admin_users = []
        for u in all_users:
            if isinstance(u, dict):
                admin_info = u.get("admin")
                if admin_info and isinstance(admin_info, dict):
                    if admin_info.get("username") == target_username:
                        admin_users.append(u)

        user_count = len(admin_users)
        total_bytes = sum([u.get("used_traffic", 0) for u in admin_users if isinstance(u, dict) and u.get("used_traffic")])
        total_gb = round(total_bytes / (1024 ** 3), 2)
        
        user_names_list = ""
        for idx, u in enumerate(admin_users, 1):
            if isinstance(u, dict):
                user_names_list += f"{idx}. `{u.get('username')}`\n"
        
        if not user_names_list:
            user_names_list = "_Bu admin henüz hiç kullanıcı oluşturmamış veya yetkisi yok._"

        detay_metni = (
            f"👤 **ADMİN İSTATİSTİKLERİ: {target_username}**\n\n"
            f"📊 **Üretilen Toplam Kullanıcı:** {user_count}\n"
            f"📉 **Kullanıcıların Toplam Trafiği:** {total_gb} GB\n\n"
            f"📋 **Oluşturulan Kullanıcı Listesi:**\n{user_names_list}"
        )
        
        markup = InlineKeyboardMarkup()
        if target_username != MASTER_ADMIN_USERNAME:
            markup.row(InlineKeyboardButton("🗑️ Admini Sil (CLI Delete)", callback_data=f"adm_sil_{target_username}"))
        markup.row(InlineKeyboardButton("⬅️ Admin Listesine Dön", callback_data="adminleri_listele"))
        
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                              text=detay_metni, reply_markup=markup, parse_mode="Markdown")
                              
    except Exception as e:
        bot.send_message(chat_id, f"❌ Admin detayları işlenirken hata oluştu: `{str(e)}`")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_sil_"))
def delete_admin_execute(call):
    if not is_authorized(call): return
    chat_id = call.message.chat.id
    target_username = call.data.split("_")[2]
    token = get_marzban_token()

    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.delete(f"{MASTER_PANEL_API}/admin/{target_username}", headers=headers, timeout=10)
        
        if res.status_code in [200, 204]:
            bot.answer_callback_query(call.id, f"✅ {target_username} başarıyla silindi!", show_alert=True)
            list_admins(call)
        else:
            bot.answer_callback_query(call.id, "❌ Admin silinemedi (Yetki yetersiz veya sistem hatası).", show_alert=True)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Silme işlemi başarısız: `{str(e)}`")


# =====================================================================
# 🌐 BÖLÜM 2: HOSTLAR VE TOPLU IP DEĞİŞTİRME YÖNETİMİ
# =====================================================================

@bot.callback_query_handler(func=lambda call: call.data == "hostlari_listele")
def list_hosts(call):
    if not is_authorized(call): return
    chat_id = call.message.chat.id
    token = get_marzban_token()
    if not token:
        bot.answer_callback_query(call.id, "❌ API bağlantısı başarısız!", show_alert=True)
        return

    try:
        headers = {"Authorization": f"Bearer {token}"}
        hosts_data = requests.get(f"{MASTER_PANEL_API}/hosts", headers=headers, timeout=10).json()
        
        host_detay_metni = "🌐 **MEVCUT PANEL HOSTLARI VE GİRİŞLERİ**\n\n"
        
        if isinstance(hosts_data, dict):
            for inbound, hosts in hosts_data.items():
                host_detay_metni += f"🔹 **İnbound Grubu:** `{inbound}`\n"
                if not hosts or not isinstance(hosts, list):
                    host_detay_metni += " └ ⚠️ _Bu gruba tanımlı host bulunmuyor._\n\n"
                    continue
                    
                for h in hosts:
                    if isinstance(h, dict):
                        host_detay_metni += (
                            f" ├ 📍 Remark: `{h.get('remark', 'Yok')}`\n"
                            f" ├ 🔗 Adres (IP/Domain): `{h.get('address')}`\n"
                            f" └ 🔌 Port: `{h.get('port', 'Default')}`\n"
                        )
                host_detay_metni += "\n"
            
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔄 Tüm Hostların IP'sini Değiştir", callback_data="toplu_ip_degistir_istek"))
        markup.row(InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data="ana_menuye_don"))
        
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                              text=host_detay_metni, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Host listesi alınırken hata oluştu: `{str(e)}`")

@bot.callback_query_handler(func=lambda call: call.data == "toplu_ip_degistir_istek")
def request_new_ip_for_hosts(call):
    if not is_authorized(call): return
    chat_id = call.message.chat.id
    msg = bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                                text="🚀 **TOPLU HOST IP GÜNCELLEME**\n\nLütfen tüm hostlara atanacak **Yeni IP Adresini** yazın:")
    bot.register_next_step_handler(msg, execute_bulk_ip_change)

def execute_bulk_ip_change(message):
    if not is_authorized(message): return
    chat_id = message.chat.id
    new_ip = message.text.strip() if message.text else ""
    
    if not new_ip:
        bot.send_message(chat_id, "❌ Geçersiz IP adresi. İşlem iptal edildi.")
        return
        
    token = get_marzban_token()
    status_msg = bot.send_message(chat_id, "⏳ Hostlar taranıyor ve IP adresleri değiştiriliyor...")
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        hosts_data = requests.get(f"{MASTER_PANEL_API}/hosts", headers=headers, timeout=10).json()
        
        updated_hosts_data = {}
        if isinstance(hosts_data, dict):
            for inbound, hosts in hosts_data.items():
                updated_hosts_data[inbound] = []
                if isinstance(hosts, list):
                    for h in hosts:
                        if isinstance(h, dict):
                            h['address'] = new_ip
                            updated_hosts_data[inbound].append(h)
                
        res = requests.put(f"{MASTER_PANEL_API}/hosts", json=updated_hosts_data, headers=headers, timeout=10)
        
        if res.status_code in [200, 204]:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data="ana_menuye_don"))
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id,
                                  text=f"✅ **İŞLEM TAMAMLANDI!**\n\nTüm inbound alanlarının IP adresleri başarıyla `{new_ip}` olarak güncellendi ve kaydedildi! ⚡",
                                  reply_markup=markup)
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id,
                                  text=f"❌ API güncelleme isteğini reddetti. Hata Kodu: `{res.status_code}`")
    except Exception as e:
        bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id,
                              text=f"❌ Toplu IP güncellenirken hata oluştu: `{str(e)}`")


# =====================================================================
# 🔄 YARDIMCI GEÇİŞ CALLBACK HANDLERI
# =====================================================================
@bot.callback_query_handler(func=lambda call: call.data == "ana_menuye_don")
def back_to_main(call):
    if not is_authorized(call): return
    panel_text = (
        "🛡️ **MARZBAN GELİŞMİŞ KONTROL PANELİ**\n\n"
        "Sisteme başarıyla bağlanıldı. Lütfen işlem yapmak istediğiniz menüyü seçin 👇"
    )
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=panel_text, reply_markup=main_menu(), parse_mode="Markdown")

# --- BOTU BAŞLAT ---
if __name__ == '__main__':
    print("🤖 Marzban Güvenli API Kontrol Botu aktif ve istekleri dinliyor...")
    bot.infinity_polling()
