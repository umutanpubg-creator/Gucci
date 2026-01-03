import asyncio
import logging
import json
from datetime import datetime, timedelta
# storm
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
# storm
BOT_TOKEN = "8144561331:AAHz-5ya0LGZD8zp_DD8dBagF0tp174mK20"
ADMIN_ID = 8289508688
# storm
DATA_FILE = "bot_data.json"
# storm
class AdminStates(StatesGroup):
    add_sponsor_channel = State()
    remove_sponsor_channel = State()
    add_adlist_link = State()
    change_vpn_message = State()
    broadcast_message = State()
    add_admin = State()
    remove_admin = State()
    ban_user = State()
    unban_user = State()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    data.setdefault("sponsor_channels", [])
    data.setdefault("vpn_message", "Heniz düzülmedi | Bot tarapyndan bellenilmedi")
    data.setdefault("users", {})
    data.setdefault("admins", [])
    data.setdefault("banned_users", [])
    data.setdefault("adlist_links", [])
    
    return data

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class IsAdmin(BaseFilter):
    async def __call__(self, message: types.Update) -> bool:
        user = message.from_user
        if not user:
             return False
        data = load_data()
        return user.id == ADMIN_ID or user.id in data.get("admins", [])

def add_user_to_db(user_id):
    data = load_data()
    user_id_str = str(user_id)
    if user_id_str not in data["users"]:
        data["users"][user_id_str] = {
            "join_date": datetime.now().isoformat()
        }
        save_data(data)

async def check_subscription(user_id: int):
    data = load_data()
    sponsor_channels = data["sponsor_channels"]
    if not sponsor_channels:
        return True

    for channel in sponsor_channels:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except (TelegramBadRequest, TelegramAPIError) as e:
            logging.error(f"Kanal {channel} kontrol edilirken hata: {e}")
            return False
    return True

@dp.message(CommandStart())
async def command_start_handler(message: Message):
    user_id = message.from_user.id
    data = load_data()

    if user_id in data.get("banned_users", []):
        await message.answer("Siz botdan banlandyňyz.")
        return

    add_user_to_db(user_id)

    is_subscribed = await check_subscription(user_id)
    if is_subscribed:
        await message.answer(f"✅ Siz ähli sponsor kanallara goşuldyňyz!\n\n<b>Siziň VPN koduňyz:</b>\n<code>{data['vpn_message']}</code>", parse_mode="HTML")
    else:
        await message.answer(
            "👋 Gyw boty ulanmak üçin, ilki bilen sponsor kanallarymyza goşulmagyňyzy haýyş edýäris!",
            reply_markup=await get_channels_keyboard()
        )

@dp.message(Command("admin"), IsAdmin())
@dp.message(F.text.lower() == "admin", IsAdmin())
async def admin_panel_handler(message: Message):
    await message.answer("Salam, admin! Admin paneline hoş geldiňiz.", reply_markup=get_admin_panel_keyboard())

@dp.callback_query(F.data == "check_subscription")
async def callback_check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in load_data().get("banned_users", []):
        await callback.answer("Siz botdan banlandyňyz.", show_alert=True)
        return

    is_subscribed = await check_subscription(user_id)
    if is_subscribed:
        await callback.message.delete()
        await callback.message.answer(
            f"✅ Siz ähli sponsor kanallara goşuldyňyz!\n\n<b>Siziň VPN koduňyz:</b>\n<code>{load_data()['vpn_message']}</code>",
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Siz entek ähli sponsor kanallara goşulmadyňyz. Haýyş, goşulyň we täzeden synanyşyň.", show_alert=True)

async def get_channels_keyboard():
    builder = InlineKeyboardBuilder()
    data = load_data()
    sponsor_channels = data.get("sponsor_channels", [])
    if sponsor_channels:
        channel_buttons = []
        for i, channel_id in enumerate(sponsor_channels):
            try:
                chat = await bot.get_chat(channel_id)
                invite_link = chat.invite_link or f"https://t.me/{chat.username}"
                channel_buttons.append(InlineKeyboardButton(text=f"Sponsor {i+1}", url=invite_link))
            except (TelegramBadRequest, TelegramAPIError) as e:
                logging.error(f"Kanal bilgisi alınamadı {channel_id}: {e}")
                channel_buttons.append(InlineKeyboardButton(text=f"Sponsor {i+1}", url=f"https://t.me/c/{str(channel_id).replace('-100', '')}"))
        
        for i in range(0, len(channel_buttons), 2):
            builder.row(*channel_buttons[i:i+2])
    
    adlist_links = data.get("adlist_links", [])
    if adlist_links:
        latest_link = adlist_links[-1]
        builder.row(InlineKeyboardButton(text="📁 Adlist Klasörü", url=latest_link))

    builder.row(InlineKeyboardButton(text="✅ Barla", callback_data="check_subscription"))
    return builder.as_markup()

def get_admin_panel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Sponsor goş", callback_data="action_add_sponsor")
    builder.button(text="➖ Sponsor aýyr", callback_data="action_remove_sponsor")
    builder.button(text="➕ Adlist goş", callback_data="action_add_adlist")
    builder.button(text="➖ Adlist aýyr", callback_data="action_remove_adlist")
    builder.button(text="✍️ VPN kody üýtget", callback_data="action_change_vpn")
    builder.button(text="📊 Statistika", callback_data="action_show_stats")
    builder.button(text="📣 Rassylka", callback_data="action_broadcast")
    builder.button(text="➕ Admin goş", callback_data="action_add_admin")
    builder.button(text="➖ Admin aýyr", callback_data="action_remove_admin")
    builder.button(text="🚫 Banla", callback_data="action_ban_user")
    builder.button(text="✅ Bany aýyr", callback_data="action_unban_user")
    builder.adjust(2, 2, 1, 2, 2, 2)
    return builder.as_markup()
    
def back_to_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Yza", callback_data="back_to_admin")]])

@dp.callback_query(F.data == "back_to_admin", IsAdmin())
async def back_to_admin_panel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Admin paneli:", reply_markup=get_admin_panel_keyboard())

@dp.callback_query(F.data.startswith('action_'), IsAdmin())
async def handle_admin_actions(callback: CallbackQuery, state: FSMContext):
    action = callback.data.replace("action_", "")
    await callback.message.delete()
    
    actions = {
        "add_sponsor": (AdminStates.add_sponsor_channel, "Goşmak isleýän sponsor kanalyňyzyň ID-sini ýa-da ulanyjy adyny (@username) giriziň:"),
        "add_adlist": (AdminStates.add_adlist_link, "Goşmak isleýän Adlist klasör linkini giriziň:"),
        "change_vpn": (AdminStates.change_vpn_message, "Ulanyjylara görkeziljek täze VPN koduny ýa-da habaryny giriziň:"),
        "broadcast": (AdminStates.broadcast_message, "Ähli ulanyjylara ibermek üçin habaryňyzy giriziň:"),
        "add_admin": (AdminStates.add_admin, "Goşmak isleýän täze adminiň Telegram ID-sini giriziň:"),
        "ban_user": (AdminStates.ban_user, "Banlamak isleýän ulanyjynyň Telegram ID-sini giriziň:")
    }
# storm
    if action in actions:
        state_to_set, text = actions[action]
        await state.set_state(state_to_set)
        await callback.message.answer(text, reply_markup=back_to_admin_keyboard())
    elif action == "remove_sponsor":
        await show_channels_for_removal(callback.message)
    elif action == "remove_adlist":
        await show_adlists_for_removal(callback.message)
    elif action == "show_stats":
        await show_statistics(callback.message)
    elif action == "remove_admin":
        await show_admins_for_removal(callback.message)
    elif action == "unban_user":
        await show_banned_users_for_removal(callback.message)

async def show_statistics(message: Message):
    data = load_data()
    total_users = len(data["users"])
    now = datetime.now()
    users_last_24_hours = sum(1 for u in data["users"].values() if now - datetime.fromisoformat(u["join_date"]) <= timedelta(hours=24))
    stats_text = (
        "<b>📊 Bot Statistikasy</b>\n\n"
        f"👤 Jemi ulanyjylar: {total_users}\n"
        f"🕒 Soňky 24 sagatda goşulanlar: {users_last_24_hours}\n"
        f"📢 Sponsor kanallaryň sany: {len(data['sponsor_channels'])}\n"
        f"👑 Adminleriň sany: {len(data.get('admins', [])) + 1}\n"
        f"🚫 Banlanan ulanyjylar: {len(data.get('banned_users', []))}"
    )
    await message.answer(stats_text, parse_mode="HTML", reply_markup=get_admin_panel_keyboard())

@dp.message(AdminStates.add_sponsor_channel)
async def process_add_sponsor(message: Message, state: FSMContext):
    data = load_data()
    data["sponsor_channels"].append(message.text)
    save_data(data)
    await state.clear()
    await message.answer(f"✅ Sponsor kanaly '{message.text}' üstünlikli goşuldy!", reply_markup=get_admin_panel_keyboard())

@dp.message(AdminStates.add_adlist_link)
async def process_add_adlist_link(message: Message, state: FSMContext):
    link = message.text
    if link.startswith("https://t.me/addlist/") or link.startswith("https://t.me/addfolder/"):
        data = load_data()
        data["adlist_links"].append(link)
        save_data(data)
        await state.clear()
        await message.answer(f"✅ Adlist klasör linki üstünlikli goşuldy!", reply_markup=get_admin_panel_keyboard())
    else:
        await message.answer("❌ Näsaz link. Haýyş, dogry bir Telegram klasör linki giriziň.", reply_markup=back_to_admin_keyboard())

@dp.message(AdminStates.add_admin)
async def process_add_admin(message: Message, state: FSMContext):
    try:
        new_admin_id = int(message.text)
        data = load_data()
        if new_admin_id not in data["admins"] and new_admin_id != ADMIN_ID:
            data["admins"].append(new_admin_id)
            save_data(data)
            await message.answer(f"✅ Täze admin ({new_admin_id}) üstünlikli goşuldy!", reply_markup=get_admin_panel_keyboard())
        else:
            await message.answer("Bu ulanyjy eýýäm admin.", reply_markup=get_admin_panel_keyboard())
    except ValueError:
        await message.answer("❌ Näsaz ID. Diňe sanlardan ybarat bolan Telegram ID-sini giriziň.", reply_markup=get_admin_panel_keyboard())
    await state.clear()

@dp.message(AdminStates.ban_user)
async def process_ban_user(message: Message, state: FSMContext):
    try:
        user_id_to_ban = int(message.text)
        data = load_data()
        if user_id_to_ban != ADMIN_ID and user_id_to_ban not in data["admins"] and user_id_to_ban not in data["banned_users"]:
            data["banned_users"].append(user_id_to_ban)
            save_data(data)
            await message.answer(f"✅ Ulanyjy ({user_id_to_ban}) üstünlikli banlandy!", reply_markup=get_admin_panel_keyboard())
        else:
            await message.answer("❌ Bu ulanyjy eýýäm banlanan ýa-da admin.", reply_markup=get_admin_panel_keyboard())
    except ValueError:
        await message.answer("❌ Näsaz ID.", reply_markup=get_admin_panel_keyboard())
    await state.clear()

async def show_channels_for_removal(message: Message):
    data = load_data()
    channels = data.get("sponsor_channels", [])
    if not channels:
        await message.answer("Aýyrmak üçin sponsor kanal tapylmady.", reply_markup=get_admin_panel_keyboard())
        return
    builder = InlineKeyboardBuilder()
    for channel in channels:
        builder.button(text=f"❌ {channel}", callback_data=f"delete_sponsor_{channel}")
    builder.button(text="⬅️ Yza", callback_data="back_to_admin")
    builder.adjust(1)
    await message.answer("Haýsy sponsor kanalyny aýyrmak isleýärsiňiz?", reply_markup=builder.as_markup())

async def show_adlists_for_removal(message: Message):
    data = load_data()
    adlist_links = data.get("adlist_links", [])
    if not adlist_links:
        await message.answer("Aýyrmak üçin Adlist linki tapylmady.", reply_markup=get_admin_panel_keyboard())
        return
    builder = InlineKeyboardBuilder()
    for i, link in enumerate(adlist_links):
        builder.button(text=f"❌ Link {i+1}", callback_data=f"delete_adlist_{i}")
    builder.button(text="⬅️ Yza", callback_data="back_to_admin")
    builder.adjust(1)
    await message.answer("Haýsy Adlist linkini aýyrmak isleýärsiňiz?", reply_markup=builder.as_markup())

async def show_admins_for_removal(message: Message):
    data = load_data()
    admins = data.get("admins", [])
    if not admins:
        await message.answer("Aýyrmak üçin başga admin tapylmady.", reply_markup=get_admin_panel_keyboard())
        return
    builder = InlineKeyboardBuilder()
    for admin_id in admins:
        builder.button(text=f"❌ {admin_id}", callback_data=f"delete_admin_{admin_id}")
    builder.button(text="⬅️ Yza", callback_data="back_to_admin")
    builder.adjust(1)
    await message.answer("Haýsy admini aýyrmak isleýärsiňiz?", reply_markup=builder.as_markup())

async def show_banned_users_for_removal(message: Message):
    data = load_data()
    banned_users = data.get("banned_users", [])
    if not banned_users:
        await message.answer("Aýyrmak üçin banlanan ulanyjy tapylmady.", reply_markup=get_admin_panel_keyboard())
        return
    builder = InlineKeyboardBuilder()
    for user_id in banned_users:
        builder.button(text=f"✅ {user_id}", callback_data=f"unban_user_{user_id}")
    builder.button(text="⬅️ Yza", callback_data="back_to_admin")
    builder.adjust(1)
    await message.answer("Haýsy ulanyjynyň banyny aýyrmak isleýärsiňiz?", reply_markup=builder.as_markup())
# kali
@dp.callback_query(F.data.startswith("delete_sponsor_"))
async def process_remove_sponsor(callback: CallbackQuery):
    channel_id = callback.data.replace("delete_sponsor_", "")
    data = load_data()
    if channel_id in data["sponsor_channels"]:
        data["sponsor_channels"].remove(channel_id)
        save_data(data)
        await callback.answer("✅ Kanal aýyryldy!", show_alert=True)
    await callback.message.edit_text("Admin paneli:", reply_markup=get_admin_panel_keyboard())

@dp.callback_query(F.data.startswith("delete_adlist_"))
async def process_remove_adlist(callback: CallbackQuery):
    link_index = int(callback.data.replace("delete_adlist_", ""))
    data = load_data()
    if 0 <= link_index < len(data["adlist_links"]):
        data["adlist_links"].pop(link_index)
        save_data(data)
        await callback.answer("✅ Adlist linki aýyryldy!", show_alert=True)
    await callback.message.edit_text("Admin paneli:", reply_markup=get_admin_panel_keyboard())

@dp.callback_query(F.data.startswith("delete_admin_"))
async def process_remove_admin(callback: CallbackQuery):
    admin_id = int(callback.data.replace("delete_admin_", ""))
    data = load_data()
    if admin_id in data["admins"]:
        data["admins"].remove(admin_id)
        save_data(data)
        await callback.answer("✅ Admin aýyryldy!", show_alert=True)
    await callback.message.edit_text("Admin paneli:", reply_markup=get_admin_panel_keyboard())

@dp.callback_query(F.data.startswith("unban_user_"))
async def process_unban_user(callback: CallbackQuery):
    user_id = int(callback.data.replace("unban_user_", ""))
    data = load_data()
    if user_id in data["banned_users"]:
        data["banned_users"].remove(user_id)
        save_data(data)
        await callback.answer("✅ Ulanyjynyň bany aýyryldy!", show_alert=True)
    await callback.message.edit_text("Admin paneli:", reply_markup=get_admin_panel_keyboard())

@dp.message(AdminStates.change_vpn_message)
async def process_change_vpn_message(message: Message, state: FSMContext):
    data = load_data()
    data["vpn_message"] = message.text
    save_data(data)
    await state.clear()
    await message.answer(f"✅ VPN kody/habary üstünlikli üýtgedildi!", reply_markup=get_admin_panel_keyboard())

@dp.message(AdminStates.broadcast_message)
async def process_broadcast(message: Message, state: FSMContext):
    await state.clear()
    data = load_data()
    users_to_send = [int(uid) for uid in data["users"].keys() if int(uid) not in data["banned_users"]]
    successful_sends, failed_sends = 0, 0
    await message.answer(f"📢 Rassylka başlady... {len(users_to_send)} ulanyja iberilýär.")
    for user_id in users_to_send:
        try:
            await bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
            successful_sends += 1
        except Exception as e:
            logging.error(f"Mesaj gönderilemedi {user_id}: {e}")
            failed_sends += 1
        await asyncio.sleep(0.1)
    await message.answer(f"✅ Rassylka tamamlandy!\n👍 Üstünlikli: {successful_sends}\n👎 Şowsuz: {failed_sends}", reply_markup=get_admin_panel_keyboard())

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


