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

# --- ANA MENÜ (START) ---
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("👥 Panel Adminleri", callback_data="adminleri_listele"))
    markup.row(InlineKeyboardButton("🌐 Hostlar ve IP Değiştir", callback_data="hostlari_listele"))
    return markup

@bot.message_handler(commands=['panel', 'start'])
def send_welcome(message):
    panel_text = (
        "🛡️ **MARZBAN GELİŞMİŞ KONTROL PANELİ**\n\n"
        "Sisteme başarıyla bağlanıldı. Lütfen işlem yapmak istediğiniz menüyü seçin 👇"
    )
    bot.send_message(message.chat.id, panel_text, parse_mode="Markdown", reply_markup=main_menu())

# =====================================================================
# 👥 BÖLÜM 1: PANEL ADMİNLERİ YÖNETİMİ
# =====================================================================

@bot.callback_query_handler(func=lambda call: call.data == "adminleri_listele")
def list_admins(call):
    chat_id = call.message.chat.id
    token = get_marzban_token()
    if not token:
        bot.answer_callback_query(call.id, "❌ API bağlantısı başarısız!", show_alert=True)
        return

    try:
        headers = {"Authorization": f"Bearer {token}"}
        # Paneldeki tüm adminleri çekiyoruz
        admins = requests.get(f"{MASTER_PANEL_API}/admins", headers=headers, timeout=10).json()
        
        markup = InlineKeyboardMarkup()
        for admin in admins:
            username = admin.get("username")
            # Süper admini listede korumak veya ayırt etmek için emoji ekleyebiliriz
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
    chat_id = call.message.chat.id
    target_username = call.data.split("_")[2]
    token = get_marzban_token()

    try:
        headers = {"Authorization": f"Bearer {token}"}
        # Admin detayını ve onun altındaki kullanıcıları çekmek için /users endpointini filtreleyebiliriz
        # Marzban API'de doğrudan admin bazlı istatistik ve o adminin oluşturduğu kullanıcı listesi çekilir:
        all_users = requests.get(f"{MASTER_PANEL_API}/users", headers=headers, timeout=10).json().get("users", [])
        
        # Seçilen adminin oluşturduğu kullanıcıları ayıklıyoruz
        admin_users = [u for u in all_users if u.get("admin", {}).get("username") == target_username]
        
        user_count = len(admin_users)
        total_bytes = sum([u.get("used_traffic", 0) for u in admin_users])
        total_gb = round(total_bytes / (1024 ** 3), 2)
        
        # Kullanıcı isimlerini sıralı listeleme
        user_names_list = ""
        for idx, u in enumerate(admin_users, 1):
            user_names_list += f"{idx}. `{u.get('username')}`\n"
        
        if not user_names_list:
            user_names_list = "_Bu admin henüz hiç kullanıcı oluşturmamış._"

        detay_metni = (
            f"👤 **ADMİN İSTATİSTİKLERİ: {target_username}**\n\n"
            f"📊 **Üretilen Toplam Kullanıcı:** {user_count}\n"
            f"📉 **Kullanıcıların Toplam Trafiği:** {total_gb} GB\n\n"
            f"📋 **Oluşturulan Kullanıcı Listesi:**\n{user_names_list}"
        )
        
        markup = InlineKeyboardMarkup()
        # Kendini silmesini engellemek için küçük bir önlem
        if target_username != MASTER_ADMIN_USERNAME:
            markup.row(InlineKeyboardButton("🗑️ Admini Sil (CLI Delete)", callback_data=f"adm_sil_{target_username}"))
        markup.row(InlineKeyboardButton("⬅️ Admin Listesine Dön", callback_data="adminleri_listele"))
        
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                              text=detay_metni, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Admin detayları işlenirken hata oluştu: `{str(e)}`")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_sil_"))
def delete_admin_execute(call):
    chat_id = call.message.chat.id
    target_username = call.data.split("_")[2]
    token = get_marzban_token()

    try:
        headers = {"Authorization": f"Bearer {token}"}
        # marzban cli admin delete komutunun API karşılığı
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
    chat_id = call.message.chat.id
    token = get_marzban_token()
    if not token:
        bot.answer_callback_query(call.id, "❌ API bağlantısı başarısız!", show_alert=True)
        return

    try:
        headers = {"Authorization": f"Bearer {token}"}
        # Paneldeki mevcut host ayarlarını çekiyoruz (vless-xhttp, vless-tcp, shadowsocks-tcp vb.)
        hosts_data = requests.get(f"{MASTER_PANEL_API}/hosts", headers=headers, timeout=10).json()
        
        host_detay_metni = "🌐 **MEVCUT PANEL HOSTLARI VE GİRİŞLERİ**\n\n"
        
        # Fotoğraftaki gibi gelen tüm inbound gruplarını ve içindeki host detaylarını metne döküyoruz
        for inbound, hosts in hosts_data.items():
            host_detay_metni += f"🔹 **İnbound Grubu:** `{inbound}`\n"
            if not hosts:
                host_detay_metni += " └ ⚠️ _Bu gruba tanımlı host bulunmuyor._\n\n"
                continue
                
            for h in hosts:
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
    chat_id = call.message.chat.id
    msg = bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
                                text="🚀 **TOPLU HOST IP GÜNCELLEME**\n\nLütfen tüm hostlara atanacak **Yeni IP Adresini** yazın:")
    bot.register_next_step_handler(msg, execute_bulk_ip_change)

def execute_bulk_ip_change(message):
    chat_id = message.chat.id
    new_ip = message.text.strip()
    token = get_marzban_token()
    
    status_msg = bot.send_message(chat_id, "⏳ Hostlar taranıyor ve IP adresleri değiştiriliyor...")
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        # Önce mevcut host yapısını çekiyoruz
        hosts_data = requests.get(f"{MASTER_PANEL_API}/hosts", headers=headers, timeout=10).json()
        
        # Tüm inbound gruplarındaki hostların adres bilgisini yeni IP ile güncelliyoruz
        updated_hosts_data = {}
        for inbound, hosts in hosts_data.items():
            updated_hosts_data[inbound] = []
            for h in hosts:
                h['address'] = new_ip  # IP adresini değiştiriyoruz
                updated_hosts_data[inbound].append(h)
                
        # API'ye güncellenmiş yeni host listesini gönderiyoruz (Fotoğraftaki 'Apply' butonunun tetiklediği işlem)
        res = requests.put(f"{MASTER_PANEL_API}/hosts", json=updated_hosts_data, headers=headers, timeout=10)
        
        if res.status_code in [200, 204]:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⬅️ Ana Menüye Dön", callback_data="ana_menuye_don"))
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id,
                                  text=f"✅ **İŞLEM TAMAMLANDI!**\n\nFotoğraftaki tüm inbound alanlarının (`vless-xhttp`, `vless-tcp`, `shadowsocks-tcp` vb.) IP adresleri başarıyla `{new_ip}` olarak güncellendi ve kaydedildi! ⚡",
                                  reply_markup=markup)
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id,
                                  text="❌ API güncelleme isteğini reddetti. Yapılandırmanızı kontrol edin.")
    except Exception as e:
        bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id,
                              text=f"❌ Toplu IP güncellenirken hata oluştu: `{str(e)}`")


# =====================================================================
# 🔄 YARDIMCI GEÇİŞ CALLBACK HANDLERI
# =====================================================================
@bot.callback_query_handler(func=lambda call: call.data == "ana_menuye_don")
def back_to_main(call):
    panel_text = (
        "🛡️ **MARZBAN GELİŞMİŞ KONTROL PANELİ**\n\n"
        "Sisteme başarıyla bağlanıldı. Lütfen işlem yapmak istediğiniz menüyü seçin 👇"
    )
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=panel_text, reply_markup=main_menu(), parse_mode="Markdown")

# --- BOTU BAŞLAT ---
if __name__ == '__main__':
    print("🤖 Marzban API Kontrol Botu aktif ve istekleri dinliyor...")
    bot.infinity_polling()
