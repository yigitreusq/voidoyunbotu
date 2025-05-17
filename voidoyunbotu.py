from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    filters
)
import json
import os
import random
from collections import defaultdict
from datetime import datetime

# Settings
DATA_FILE = "user_data.json"
BANNED_FILE = "banned_users.json"
ADMIN_ID = 5573686386  # Replace with your Telegram ID
TOKEN = "7835549456:AAHZ0v8RlD8kIhLzPwYN7SziBE_AhKQB4kI"  # Replace with your bot token

# Data structures
user_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})

def init_user():
    return {
        "balance": 500,
        "username": "",
        "is_banned": False,
        "name_history": [],
        "ban_history": [],
        "first_seen": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "last_seen": datetime.now().strftime("%d.%m.%Y %H:%M")
    }

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            data = json.load(f)
            # Migrate old data format
            for user_id, user_data in data.items():
                if 'name_history' not in user_data:
                    user_data['name_history'] = []
                if 'ban_history' not in user_data:
                    user_data['ban_history'] = []
                if 'first_seen' not in user_data:
                    user_data['first_seen'] = datetime.now().strftime("%d.%m.%Y %H:%M")
                if 'last_seen' not in user_data:
                    user_data['last_seen'] = datetime.now().strftime("%d.%m.%Y %H:%M")
            return data
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_banned():
    if os.path.exists(BANNED_FILE):
        with open(BANNED_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    return []

def save_banned(banned_list):
    with open(BANNED_FILE, "w", encoding='utf-8') as f:
        json.dump(banned_list, f, indent=4, ensure_ascii=False)

def is_banned(user_id):
    return str(user_id) in load_banned()

async def check_banned(update: Update):
    if is_banned(update.effective_user.id):
        await update.message.reply_text("🚫 Banlandınız! Botu kullanamazsınız.")
        return True
    return False

def find_user(target):
    data = load_data()
    target = str(target).lower().lstrip('@')
    
    if target in data:
        return target, data[target]
    
    for uid, user in data.items():
        if user["username"].lower().lstrip('@') == target:
            return uid, user
        for record in user.get("name_history", []):
            if record["name"].lower().lstrip('@') == target:
                return uid, user
    
    return None, None

async def admin_check(update: Update):
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("⛔ Yetkiniz yok!")
        return False
    return True

def calculate_win_chance(user_id):
    stats = user_stats[str(user_id)]
    total = stats['wins'] + stats['losses']
    if total < 5: return 0.45
    win_rate = stats['wins'] / total
    return 0.25 if win_rate > 0.6 else 0.35 if win_rate > 0.4 else 0.45

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned(update): return
    
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.username or update.effective_user.first_name
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    data = load_data()
    if user_id not in data:
        data[user_id] = init_user()
    else:
        if 'name_history' not in data[user_id]:
            data[user_id]['name_history'] = []
        if data[user_id]["username"] != user_name:
            data[user_id]["name_history"].append({
                "name": data[user_id]["username"],
                "changed_at": current_time
            })
    
    data[user_id]["username"] = user_name
    data[user_id]["last_seen"] = current_time
    save_data(data)
    
    await update.message.reply_text(
        f"🎲 VOID OYUN BOTU'na Hoş Geldin {user_name}!\n"
        f"💰 Başlangıç bakiyen: 500$\n"
        f"🆔 ID'niz: {user_id} \n"
        f"🔹 /help - Tüm komutları göster\n"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 VOID OYUN BOTU Komutları\n\n"
        "🔹 /start - Botu başlat\n"
        "🆔 /id - ID'nizi gösterir\n"
        "💰 /balance - Bakiyeniz\n"
        "🎯 /risk [miktar] - Oyun oyna\n"
        "🏆 /top10 - Lider tablosu\n"
        "💸 /gonder [@kullanıcı/ID] [miktar] - Para gönder\n\n\n"
        "👑 Admin Komutları:\n\n"
        "/addmoney [@user/ID] [miktar]\n"
        "/ban [@user/ID]\n"
        "/unban [@user/ID]\n"
        "/reset [@user/ID]\n"
        "/resetall\n"
        "/infaz [@user/ID] - Kullanıcı bilgisi"
    )
    await update.message.reply_text(help_text)

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"🆔 Sizin ID: {user_id}")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned(update): return
    
    user_id = str(update.effective_user.id)
    data = load_data()
    await update.message.reply_text(f"💰 Bakiyeniz: {data.get(user_id, {}).get('balance', 0)}$")

async def risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned(update): return
    
    user_id = str(update.effective_user.id)
    data = load_data()
    
    try:
        bet = int(context.args[0])
        if bet <= 0: raise ValueError
        
        if data[user_id]["balance"] < bet:
            await update.message.reply_text(f"❌ Yetersiz bakiye! Bakiyeniz: {data[user_id]['balance']}$")
            return
        
        win_chance = calculate_win_chance(user_id)
        if random.random() < win_chance:
            data[user_id]["balance"] += bet
            user_stats[user_id]['wins'] += 1
            result = f"🎉 Kazandınız! +{bet}$\n💰 Yeni bakiye: {data[user_id]['balance']}$"
        else:
            data[user_id]["balance"] -= bet
            user_stats[user_id]['losses'] += 1
            result = f"💥 Kaybettiniz! -{bet}$\n💰 Yeni bakiye: {data[user_id]['balance']}$"
        
        save_data(data)
        await update.message.reply_text(result)
    except:
        await update.message.reply_text("❌ Kullanım: /risk [miktar]")

async def top10(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = sorted(load_data().items(), key=lambda x: x[1]["balance"], reverse=True)[:10]
    if not data:
        await update.message.reply_text("❌ Henüz oyuncu yok!")
        return
    
    msg = "🏆 VOID TOP 10 🏆\n\n"
    for idx, (uid, user) in enumerate(data, 1):
        msg += f"{idx}. @{user['username']} - {user['balance']}$ (ID: {uid})\n"
    await update.message.reply_text(msg)

async def infaz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update): return
    
    try:
        target = context.args[0]
        uid, user = find_user(target)
        
        if not user:
            await update.message.reply_text("❌ Kullanıcı bulunamadı!")
            return
        
        report = (
            f"⚡️ *VOID İNFAZ RAPORU* ⚡️\n\n"
            f"🆔 *ID:* `{uid}`\n"
            f"👤 *Şimdiki İsim:* @{user.get('username', 'Bilinmiyor')}\n"
            f"📅 *İlk Giriş:* {user.get('first_seen', 'Bilinmiyor')}\n"
            f"🕒 *Son Giriş:* {user.get('last_seen', 'Bilinmiyor')}\n"
            f"💰 *Bakiye:* {user.get('balance', 0)}$\n"
            f"🔒 *Durum:* {'BANLI ⛔' if user.get('is_banned', False) else 'Aktif ✅'}\n\n"
        )
        
        if user.get("name_history"):
            report += "📜 *Tüm İsim Geçmişi:*\n"
            for record in user["name_history"]:
                report += f"• `{record['name']}` ({record.get('changed_at', 'Bilinmiyor')})\n"
        else:
            report += "ℹ️ İsim değişikliği yok\n"
        
        if user.get("ban_history"):
            report += "\n⛔ *Ban Geçmişi:*\n"
            for ban in user["ban_history"]:
                report += f"• {ban.get('date', 'Bilinmiyor')} (by {ban.get('by', 'Bilinmiyor')})\n"
        
        stats = user_stats.get(uid, {'wins': 0, 'losses': 0})
        report += (
            f"\n🎯 *Oyun İstatistikleri:*\n"
            f"• Toplam Oyun: {stats['wins'] + stats['losses']}\n"
            f"• Kazanma: {stats['wins']}\n"
            f"• Kaybetme: {stats['losses']}\n"
            f"• Başarı Oranı: {stats['wins']/max(1, stats['wins']+stats['losses']):.1%}"
        )
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {str(e)}")

async def add_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update): return
    
    try:
        target = context.args[0]
        amount = int(context.args[1])
        
        uid, user = find_user(target)
        if not user:
            await update.message.reply_text("❌ Kullanıcı bulunamadı!")
            return
        
        data = load_data()
        data[uid]["balance"] += amount
        save_data(data)
        await update.message.reply_text(f"✅ @{user['username']} ({uid}) +{amount}$\nYeni bakiye: {data[uid]['balance']}$")
    except:
        await update.message.reply_text("❌ Kullanım: /addmoney [@user/ID] [miktar]")

async def transfer_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned(update): return
    
    user_id = str(update.effective_user.id)
    data = load_data()
    
    try:
        if len(context.args) < 2:
            raise ValueError("Eksik parametre!")
            
        target = context.args[0]
        amount = int(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text("❌ Gönderilecek miktar 0'dan büyük olmalı!")
            return
            
        if user_id not in data or data[user_id]["balance"] < amount:
            await update.message.reply_text(f"❌ Yetersiz bakiye! Bakiyeniz: {data.get(user_id, {}).get('balance', 0)}$")
            return
            
        # Find recipient
        recipient_id, recipient = find_user(target)
        if not recipient:
            await update.message.reply_text("❌ Alıcı bulunamadı!")
            return
            
        if recipient_id == user_id:
            await update.message.reply_text("❌ Kendinize para gönderemezsiniz!")
            return
            
        # Perform transfer
        data[user_id]["balance"] -= amount
        data[recipient_id]["balance"] += amount
        
        save_data(data)
        
        await update.message.reply_text(
            f"✅ Para transferi başarılı!\n"
            f"👤 Alıcı: @{recipient['username']}\n"
            f"💸 Miktar: {amount}$\n"
            f"💰 Yeni bakiyeniz: {data[user_id]['balance']}$"
        )
        
    except ValueError as e:
        await update.message.reply_text(f"❌ Hatalı giriş! Kullanım: /gonder [@kullanıcı/ID] [miktar]")
    except Exception as e:
        await update.message.reply_text(f"❌ Bir hata oluştu: {str(e)}")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update): return
    
    try:
        target = context.args[0]
        uid, user = find_user(target)
        if not user:
            await update.message.reply_text("❌ Kullanıcı bulunamadı!")
            return
        
        data = load_data()
        banned = load_banned()
        
        data[uid]["ban_history"].append({
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "by": update.effective_user.username or str(update.effective_user.id)
        })
        
        data[uid]["balance"] = 0
        data[uid]["is_banned"] = True
        banned.append(uid)
        
        save_data(data)
        save_banned(banned)
        await update.message.reply_text(f"⛔ @{user['username']} ({uid}) VOID tarafından infaz edildi!")
    except:
        await update.message.reply_text("❌ Kullanım: /ban [@user/ID]")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update): return
    
    try:
        target = context.args[0]
        uid, user = find_user(target)
        if not user:
            await update.message.reply_text("❌ Kullanıcı bulunamadı!")
            return
        
        banned = load_banned()
        if uid in banned:
            banned.remove(uid)
            save_banned(banned)
            
            data = load_data()
            data[uid]["is_banned"] = False
            save_data(data)
            
            await update.message.reply_text(f"✅ @{user['username']} ({uid}) banı kaldırıldı!")
        else:
            await update.message.reply_text("ℹ️ Bu kullanıcı zaten banlı değil")
    except:
        await update.message.reply_text("❌ Kullanım: /unban [@user/ID]")

async def reset_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update): return
    
    try:
        target = context.args[0]
        uid, user = find_user(target)
        if not user:
            await update.message.reply_text("❌ Kullanıcı bulunamadı!")
            return
        
        data = load_data()
        data[uid]["balance"] = 500
        data[uid]["is_banned"] = False
        user_stats[uid] = {'wins': 0, 'losses': 0}
        
        save_data(data)
        await update.message.reply_text(f"✅ @{user['username']} ({uid}) sıfırlandı! Yeni bakiye: 500$")
    except:
        await update.message.reply_text("❌ Kullanım: /reset [@user/ID]")

async def reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update): return
    
    data = load_data()
    for uid in data:
        data[uid]["balance"] = 500
        data[uid]["is_banned"] = False
    
    save_data(data)
    global user_stats
    user_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})
    
    save_banned([])
    await update.message.reply_text("✅ Tüm veriler sıfırlandı! Herkesin bakiyesi 500$ oldu")

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Error handler
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        print(f"Hata oluştu: {context.error}")
    
    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("risk", risk))
    app.add_handler(CommandHandler("top10", top10))
    app.add_handler(CommandHandler("infaz", infaz))
    app.add_handler(CommandHandler("gonder", transfer_money))
    
    # Admin commands
    app.add_handler(CommandHandler("addmoney", add_money))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("reset", reset_user))
    app.add_handler(CommandHandler("resetall", reset_all))
    
    app.add_error_handler(error_handler)
    
    print("🤖 VOID OYUN BOTU aktif! Çıkmak için CTRL+C")
    app.run_polling()

if __name__ == "__main__":
    main()