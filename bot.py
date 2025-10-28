import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
import storage

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get configuration from environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = os.getenv('ADMIN_IDS', '').split(',')
ADMIN_IDS = [admin_id.strip() for admin_id in ADMIN_IDS if admin_id.strip()]

# Conversation states
EDITING_WELCOME, ADDING_GROUP_NAME, ADDING_GROUP_ID, CONFIRMING_DELETE, UPLOADING_MEDIA = range(5)

def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return str(user_id) in ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - show welcome message and group buttons"""
    user = update.effective_user
    
    # Handle referral deep linking
    if context.args:
        ref_param = context.args[0]
        if ref_param.startswith('ref_'):
            referrer_id = ref_param.replace('ref_', '')
            # Register this user with the referrer
            if referrer_id != str(user.id):  # Can't refer yourself
                storage.register_user(user.id, referrer_id)
                logger.info(f"User {user.id} registered via referral from {referrer_id}")
    
    # Register user if they're not already registered (without referrer)
    if not storage.get_referral_data(str(user.id)):
        storage.register_user(user.id)
        logger.info(f"User {user.id} registered without referrer")
    
    welcome_message = storage.get_welcome_message()
    welcome_media, media_type = storage.get_welcome_media()
    groups = storage.get_groups()
    
    if not groups:
        message_text = f"{welcome_message}\n\n⚠️ Šiuo metu nėra prieinamų grupių. Prašome pabandyti vėliau."
        
        if welcome_media and media_type:
            if media_type == "photo":
                await update.message.reply_photo(photo=welcome_media, caption=message_text)
            elif media_type == "video":
                await update.message.reply_video(video=welcome_media, caption=message_text)
        else:
            await update.message.reply_text(message_text)
        return
    
    # Create inline keyboard with group buttons
    keyboard = []
    for group in groups:
        keyboard.append([InlineKeyboardButton(
            group['name'],
            callback_data=f"join_{group['id']}"
        )])
    
    # Add referral button at the bottom
    keyboard.append([InlineKeyboardButton(
        "🔗 Gauti Mano Nuorodą",
        callback_data="get_referral_link"
    )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send with media if available
    if welcome_media and media_type:
        if media_type == "photo":
            await update.message.reply_photo(
                photo=welcome_media,
                caption=welcome_message,
                reply_markup=reply_markup
            )
        elif media_type == "video":
            await update.message.reply_video(
                video=welcome_media,
                caption=welcome_message,
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup
        )
    
    logger.info(f"User {user.id} ({user.first_name}) used /start")

async def referral_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /referral command - show user's referral link and stats"""
    user = update.effective_user
    
    # Ensure user is registered
    if not storage.get_referral_data(str(user.id)):
        storage.register_user(user.id)
    
    # Get user's referral count
    referral_count = storage.get_user_referral_count(str(user.id))
    
    # Get bot username for generating the link
    bot = context.bot
    bot_username = (await bot.get_me()).username
    
    # Generate referral link
    referral_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
    
    # Create message in Lithuanian
    message = (
        f"🔗 *Jūsų Referavimo Nuoroda*\n\n"
        f"`{referral_link}`\n\n"
        f"📊 *Jūsų Statistika*\n"
        f"👥 Žmonės, kuriuos pakvietėte: *{referral_count}*\n\n"
        f"💡 *Kaip tai veikia:*\n"
        f"• Pasidalinkite šia nuoroda su kitais\n"
        f"• Kai jie spusteli ir prisijungia prie grupės, jums skaitoma\n"
        f"• Kiekvienas asmuo skaičiuojamas tik vieną kartą (pirmą grupę)\n\n"
        f"Pradėkite dalintis, kad padidintumėte savo kvietimų skaičių! 🚀"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')
    logger.info(f"User {user.id} checked referral stats (count: {referral_count})")

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /admin command - show admin panel"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Prieiga uždrausta. Neturite leidimo naudoti šią komandą.")
        logger.warning(f"Unauthorized admin access attempt by {user.id} ({user.first_name})")
        return
    
    keyboard = [
        [InlineKeyboardButton("📝 Redaguoti Sveikinimo Žinutę", callback_data="admin_edit_welcome")],
        [InlineKeyboardButton("🖼️ Įkelti Sveikinimo Mediją", callback_data="admin_upload_media")],
        [InlineKeyboardButton("🗑️ Pašalinti Sveikinimo Mediją", callback_data="admin_remove_media")],
        [InlineKeyboardButton("🔗 Valdyti Grupes", callback_data="admin_manage_groups")],
        [InlineKeyboardButton("📊 Referavimo Statistika", callback_data="admin_referral_stats")],
        [InlineKeyboardButton("❌ Uždaryti", callback_data="admin_close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    groups_count = len(storage.get_groups())
    media_file_id, media_type = storage.get_welcome_media()
    media_status = f"📷 {media_type.capitalize()}" if media_file_id else "❌ Nėra medijos"
    total_users = storage.get_total_users()
    total_referrals = storage.get_total_referrals()
    
    await update.message.reply_text(
        f"🔧 *Administravimo Skydelis*\n\n"
        f"Sukonfigūruotų grupių: {groups_count}\n"
        f"Sveikinimo medija: {media_status}\n"
        f"Viso vartotojų: {total_users}\n"
        f"Viso referalų: {total_referrals}\n\n"
        f"Pasirinkite parinktį:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    logger.info(f"Admin {user.id} opened admin panel")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    # Handle referral link button
    if data == "get_referral_link":
        # Ensure user is registered
        if not storage.get_referral_data(str(user.id)):
            storage.register_user(user.id)
        
        # Get user's referral count
        referral_count = storage.get_user_referral_count(str(user.id))
        
        # Get bot username for generating the link
        bot = context.bot
        bot_username = (await bot.get_me()).username
        
        # Generate referral link
        referral_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
        
        # Create message in Lithuanian
        message = (
            f"🔗 *Jūsų Referavimo Nuoroda*\n\n"
            f"`{referral_link}`\n\n"
            f"📊 *Jūsų Statistika*\n"
            f"👥 Žmonės, kuriuos pakvietėte: *{referral_count}*\n\n"
            f"💡 *Kaip tai veikia:*\n"
            f"• Pasidalinkite šia nuoroda su kitais\n"
            f"• Kai jie spusteli ir prisijungia prie grupės, jums skaitoma\n"
            f"• Kiekvienas asmuo skaičiuojamas tik vieną kartą (pirmą grupę)\n\n"
            f"Pradėkite dalintis, kad padidintumėte savo kvietimų skaičių! 🚀"
        )
        
        await query.answer()
        await query.message.reply_text(message, parse_mode='Markdown')
        logger.info(f"User {user.id} requested referral link from main menu (count: {referral_count})")
        
        return ConversationHandler.END
    
    # Handle user group selection
    if data.startswith("join_"):
        group_id = data.replace("join_", "")
        group = storage.get_group_by_id(group_id)
        
        if not group:
            await query.answer("❌ Grupė nerasta. Prašome bandyti /start iš naujo", show_alert=True)
            return ConversationHandler.END
        
        invite_link = group.get('invite_link')
        
        if not invite_link:
            await query.answer(
                f"❌ Nėra sukonfigūruotos nuorodos grupei {group['name']}. Susisiekite su administratoriumi.",
                show_alert=True
            )
            return ConversationHandler.END
        
        # Mark user as having joined a group (this counts the referral)
        is_first_join = storage.mark_user_joined_group(user.id)
        if is_first_join:
            logger.info(f"User {user.id} joined their first group - referral counted")
        
        # Open the invite link directly (no extra message needed!)
        await query.answer(url=invite_link)
        
        logger.info(f"Opened invite link for user {user.id} to group {group['name']}")
        
        return ConversationHandler.END
    
    # Admin panel callbacks
    if not is_admin(user.id):
        await query.edit_message_text("❌ Prieiga uždrausta.")
        return ConversationHandler.END
    
    if data == "admin_edit_welcome":
        await query.edit_message_text(
            "📝 *Redaguoti Sveikinimo Žinutę*\n\n"
            "Atsiųskite man naują sveikinimo žinutę.\n\n"
            "Dabartinė žinutė:\n"
            f"_{storage.get_welcome_message()}_\n\n"
            "Siųskite /cancel norėdami atšaukti.",
            parse_mode='Markdown'
        )
        return EDITING_WELCOME
    
    elif data == "admin_upload_media":
        media_file_id, media_type = storage.get_welcome_media()
        current = f"Dabartinė: {media_type.capitalize()}" if media_file_id else "Medija neįkelta"
        
        await query.edit_message_text(
            "🖼️ *Įkelti Sveikinimo Mediją*\n\n"
            f"{current}\n\n"
            "Atsiųskite man nuotrauką arba vaizdo įrašą, kuris bus rodomas virš sveikinimo žinutės.\n\n"
            "Siųskite /cancel norėdami atšaukti.",
            parse_mode='Markdown'
        )
        return UPLOADING_MEDIA
    
    elif data == "admin_remove_media":
        if storage.remove_welcome_media():
            await query.edit_message_text(
                "✅ Sveikinimo medija sėkmingai pašalinta!"
            )
            logger.info(f"Admin {user.id} removed welcome media")
        else:
            await query.edit_message_text(
                "❌ Klaida šalinant mediją."
            )
        return ConversationHandler.END
    
    elif data == "admin_referral_stats":
        stats = storage.get_all_referral_stats()
        total_users = storage.get_total_users()
        users_joined_groups = storage.get_users_who_joined_groups()
        total_referrals = storage.get_total_referrals()
        
        if not stats:
            text = "📊 *Referavimo Statistika*\n\n" "Dar nėra užregistruotų vartotojų."
        else:
            text = f"📊 *Referavimo Statistika*\n\n"
            text += f"👥 Viso vartotojų: *{total_users}*\n"
            text += f"✅ Prisijungė prie grupių: *{users_joined_groups}*\n"
            text += f"🔗 Viso referalų: *{total_referrals}*\n"
            
            # Calculate conversion rate (users who actually joined groups)
            if total_users > 0:
                conversion_rate = (users_joined_groups / total_users) * 100
                text += f"📈 Konversijos rodiklis: *{conversion_rate:.1f}%*\n"
            
            # Calculate referral rate (of users who joined, how many were referred)
            if users_joined_groups > 0:
                referral_rate = (total_referrals / users_joined_groups) * 100
                text += f"🎯 Referavimo rodiklis: *{referral_rate:.1f}%*\n\n"
            else:
                text += "\n"
            
            text += "🏆 *Geriausi Referalai:*\n"
            text += "_(Skaičiuojami tik vartotojai, prisijungę prie grupių)_\n\n"
            
            # Show top 10 referrers
            top_referrers = [s for s in stats if s['referral_count'] > 0][:10]
            
            if not top_referrers:
                text += "Dar nėra referalų.\n"
            else:
                for i, stat in enumerate(top_referrers, 1):
                    user_id = stat['user_id']
                    count = stat['referral_count']
                    
                    # Add medal emojis for top 3
                    if i == 1:
                        medal = "🥇"
                    elif i == 2:
                        medal = "🥈"
                    elif i == 3:
                        medal = "🥉"
                    else:
                        medal = f"{i}."
                    
                    referral_word = "referalas" if count == 1 else "referalai" if count < 10 else "referalų"
                    text += f"{medal} Vartotojas `{user_id}`: *{count}* {referral_word}\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ Grįžti į Pagrindinį Meniu", callback_data="admin_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    elif data == "admin_manage_groups":
        keyboard = [
            [InlineKeyboardButton("➕ Pridėti Naują Grupę", callback_data="admin_add_group")],
            [InlineKeyboardButton("📋 Peržiūrėti Visas Grupes", callback_data="admin_view_groups")],
            [InlineKeyboardButton("🗑️ Ištrinti Grupę", callback_data="admin_delete_group")],
            [InlineKeyboardButton("⬅️ Grįžti į Pagrindinį Meniu", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔗 *Grupių Valdymas*\n\n"
            "Pasirinkite parinktį:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    elif data == "admin_add_group":
        await query.edit_message_text(
            "➕ *Add New Group*\n\n"
            "Step 1: Enter the group name\n"
            "(This will appear on the button for users)\n\n"
            "Send /cancel to abort.",
            parse_mode='Markdown'
        )
        return ADDING_GROUP_NAME
    
    elif data == "admin_view_groups":
        groups = storage.get_groups()
        
        if not groups:
            text = "📋 *All Groups*\n\n" "No groups configured yet."
        else:
            text = "📋 *All Groups*\n\n"
            for i, group in enumerate(groups, 1):
                text += f"{i}. *{group['name']}*\n"
                text += f"   Invite Link: `{group.get('invite_link', 'N/A')}`\n"
                text += f"   ID: `{group['id']}`\n\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="admin_manage_groups")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    elif data == "admin_delete_group":
        groups = storage.get_groups()
        
        if not groups:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="admin_manage_groups")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🗑️ *Delete Group*\n\n"
                "No groups to delete.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        keyboard = []
        for group in groups:
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {group['name']}",
                callback_data=f"delete_{group['id']}"
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="admin_manage_groups")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🗑️ *Delete Group*\n\n"
            "Select a group to delete:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return CONFIRMING_DELETE
    
    elif data.startswith("delete_"):
        group_id = data.replace("delete_", "")
        group = storage.get_group_by_id(group_id)
        
        if not group:
            await query.edit_message_text("❌ Group not found.")
            return ConversationHandler.END
        
        # Store group_id in user data for confirmation
        context.user_data['delete_group_id'] = group_id
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Delete", callback_data="confirm_delete_yes"),
                InlineKeyboardButton("❌ No, Cancel", callback_data="confirm_delete_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ *Confirm Deletion*\n\n"
            f"Are you sure you want to delete:\n"
            f"*{group['name']}*\n"
            f"Invite Link: `{group.get('invite_link', 'N/A')}`\n\n"
            f"This action cannot be undone!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return CONFIRMING_DELETE
    
    elif data == "confirm_delete_yes":
        group_id = context.user_data.get('delete_group_id')
        
        if not group_id:
            await query.edit_message_text("❌ Error: No group selected for deletion.")
            return ConversationHandler.END
        
        group = storage.get_group_by_id(group_id)
        group_name = group['name'] if group else "Unknown"
        
        if storage.delete_group(group_id):
            await query.edit_message_text(
                f"✅ Successfully deleted group: *{group_name}*",
                parse_mode='Markdown'
            )
            logger.info(f"Admin {user.id} deleted group {group_name}")
        else:
            await query.edit_message_text("❌ Error deleting group.")
        
        context.user_data.pop('delete_group_id', None)
        return ConversationHandler.END
    
    elif data == "confirm_delete_no":
        context.user_data.pop('delete_group_id', None)
        await query.edit_message_text("✅ Deletion cancelled.")
        return ConversationHandler.END
    
    elif data == "admin_back":
        keyboard = [
            [InlineKeyboardButton("📝 Edit Welcome Message", callback_data="admin_edit_welcome")],
            [InlineKeyboardButton("🖼️ Upload Welcome Media", callback_data="admin_upload_media")],
            [InlineKeyboardButton("🗑️ Remove Welcome Media", callback_data="admin_remove_media")],
            [InlineKeyboardButton("🔗 Manage Groups", callback_data="admin_manage_groups")],
            [InlineKeyboardButton("📊 Referral Statistics", callback_data="admin_referral_stats")],
            [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        groups_count = len(storage.get_groups())
        media_file_id, media_type = storage.get_welcome_media()
        media_status = f"📷 {media_type.capitalize()}" if media_file_id else "❌ No media"
        total_users = storage.get_total_users()
        total_referrals = storage.get_total_referrals()
        
        await query.edit_message_text(
            f"🔧 *Admin Panel*\n\n"
            f"Groups configured: {groups_count}\n"
            f"Welcome media: {media_status}\n"
            f"Total users: {total_users}\n"
            f"Total referrals: {total_referrals}\n\n"
            f"Select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    elif data == "admin_close":
        await query.edit_message_text("✅ Admin panel closed.")
        return ConversationHandler.END
    
    return ConversationHandler.END

async def receive_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive new welcome message from admin"""
    new_message = update.message.text
    
    if storage.update_welcome_message(new_message):
        # Show success message with admin menu
        keyboard = [
            [InlineKeyboardButton("📝 Edit Welcome Message", callback_data="admin_edit_welcome")],
            [InlineKeyboardButton("🖼️ Upload Welcome Media", callback_data="admin_upload_media")],
            [InlineKeyboardButton("🗑️ Remove Welcome Media", callback_data="admin_remove_media")],
            [InlineKeyboardButton("🔗 Manage Groups", callback_data="admin_manage_groups")],
            [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        groups_count = len(storage.get_groups())
        media_file_id, media_type = storage.get_welcome_media()
        media_status = f"📷 {media_type.capitalize()}" if media_file_id else "❌ No media"
        
        await update.message.reply_text(
            "✅ *Welcome message updated successfully!*\n\n"
            f"New message:\n_{new_message}_\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔧 *Admin Panel*\n\n"
            f"Groups configured: {groups_count}\n"
            f"Welcome media: {media_status}\n\n"
            f"Select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        logger.info(f"Admin {update.effective_user.id} updated welcome message")
    else:
        await update.message.reply_text("❌ Error updating welcome message. Please try again.")
    
    return ConversationHandler.END

async def receive_group_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive group name from admin"""
    group_name = update.message.text.strip()
    
    if not group_name:
        await update.message.reply_text("❌ Group name cannot be empty. Please try again.")
        return ADDING_GROUP_NAME
    
    context.user_data['new_group_name'] = group_name
    
    await update.message.reply_text(
        f"✅ Group name: *{group_name}*\n\n"
        f"Step 2: Send the group's invite link\n\n"
        f"📋 To get the invite link:\n"
        f"1. Open your private group\n"
        f"2. Tap the group name → 'Invite to Group via Link'\n"
        f"3. Copy the invite link (looks like: https://t.me/+xxxxxxxxxxxx)\n"
        f"4. Send it to me\n\n"
        f"⚠️ Note: The bot does NOT need to be added to the group!\n\n"
        f"Send /cancel to abort.",
        parse_mode='Markdown'
    )
    
    return ADDING_GROUP_ID

async def receive_group_invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive invite link from admin"""
    group_name = context.user_data.get('new_group_name', 'Unknown')
    
    if not update.message.text:
        await update.message.reply_text(
            "❌ Please send the group's invite link.\n\n"
            "Send /cancel to abort."
        )
        return ADDING_GROUP_ID
    
    invite_link = update.message.text.strip()
    
    # Basic validation for Telegram invite links
    if not (invite_link.startswith('https://t.me/') or invite_link.startswith('http://t.me/')):
        await update.message.reply_text(
            "❌ Invalid invite link format.\n\n"
            "The link should start with https://t.me/ or http://t.me/\n\n"
            "Example: https://t.me/+xxxxxxxxxxxx\n\n"
            "Please try again or send /cancel to abort."
        )
        return ADDING_GROUP_ID
    
    # Check if group with this link already exists
    if storage.group_exists(invite_link):
        await update.message.reply_text(
            "❌ A group with this invite link already exists.\n\n"
            "Please check your groups or use a different link."
        )
        context.user_data.pop('new_group_name', None)
        return ConversationHandler.END
    
    # Add the group to storage
    new_group = storage.add_group(group_name, invite_link)
    
    # Show success message with admin menu
    keyboard = [
        [InlineKeyboardButton("📝 Edit Welcome Message", callback_data="admin_edit_welcome")],
        [InlineKeyboardButton("🔗 Manage Groups", callback_data="admin_manage_groups")],
        [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    groups_count = len(storage.get_groups())
    
    await update.message.reply_text(
        f"✅ *Group added successfully!*\n\n"
        f"Name: *{new_group['name']}*\n"
        f"Invite Link: `{new_group['invite_link']}`\n\n"
        f"Users will receive this link when they click the '{group_name}' button.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔧 *Admin Panel*\n\n"
        f"Groups configured: {groups_count}\n\n"
        f"Select an option:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    logger.info(f"Admin {update.effective_user.id} added group {group_name} with invite link")
    
    context.user_data.pop('new_group_name', None)
    return ConversationHandler.END

async def receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive photo or video from admin for welcome media"""
    media_file_id = None
    media_type = None
    
    if update.message.photo:
        # Get the largest photo
        media_file_id = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.video:
        media_file_id = update.message.video.file_id
        media_type = "video"
    else:
        await update.message.reply_text(
            "❌ Please send a photo or video.\n\n"
            "Send /cancel to abort."
        )
        return UPLOADING_MEDIA
    
    # Save the media
    if storage.update_welcome_media(media_file_id, media_type):
        # Show success message with admin menu
        keyboard = [
            [InlineKeyboardButton("📝 Edit Welcome Message", callback_data="admin_edit_welcome")],
            [InlineKeyboardButton("🖼️ Upload Welcome Media", callback_data="admin_upload_media")],
            [InlineKeyboardButton("🗑️ Remove Welcome Media", callback_data="admin_remove_media")],
            [InlineKeyboardButton("🔗 Manage Groups", callback_data="admin_manage_groups")],
            [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        groups_count = len(storage.get_groups())
        
        await update.message.reply_text(
            f"✅ *Welcome {media_type} uploaded successfully!*\n\n"
            f"This {media_type} will now appear above the welcome message when users use /start.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔧 *Admin Panel*\n\n"
            f"Groups configured: {groups_count}\n"
            f"Welcome media: 📷 {media_type.capitalize()}\n\n"
            f"Select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        logger.info(f"Admin {update.effective_user.id} uploaded welcome {media_type}")
    else:
        await update.message.reply_text("❌ Error uploading media. Please try again.")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current conversation"""
    await update.message.reply_text(
        "✅ Operation cancelled.",
        reply_markup=None
    )
    context.user_data.clear()
    return ConversationHandler.END

def main() -> None:
    """Start the bot"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is not set!")
        print("ERROR: BOT_TOKEN environment variable is required!")
        return
    
    if not ADMIN_IDS:
        logger.error("ADMIN_IDS environment variable is not set!")
        print("ERROR: ADMIN_IDS environment variable is required!")
        return
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler for admin operations
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_callback)
        ],
        states={
            EDITING_WELCOME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_welcome_message)
            ],
            UPLOADING_MEDIA: [
                MessageHandler((filters.PHOTO | filters.VIDEO) & ~filters.COMMAND, receive_media)
            ],
            ADDING_GROUP_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_group_name)
            ],
            ADDING_GROUP_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_group_invite_link)
            ],
            CONFIRMING_DELETE: [
                CallbackQueryHandler(button_callback)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_user=True,
        per_chat=True
    )
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_menu))
    application.add_handler(CommandHandler("referral", referral_info))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the bot
    logger.info("Multi-Group Portal Bot started successfully!")
    logger.info(f"Authorized admin IDs: {', '.join(ADMIN_IDS)}")
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

