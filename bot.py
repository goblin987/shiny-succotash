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
EDITING_WELCOME, ADDING_GROUP_NAME, ADDING_GROUP_ID, CONFIRMING_DELETE = range(4)

def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return str(user_id) in ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - show welcome message and group buttons"""
    user = update.effective_user
    welcome_message = storage.get_welcome_message()
    groups = storage.get_groups()
    
    if not groups:
        await update.message.reply_text(
            f"{welcome_message}\n\n"
            "⚠️ No groups available at the moment. Please check back later."
        )
        return
    
    # Create inline keyboard with group buttons
    keyboard = []
    for group in groups:
        keyboard.append([InlineKeyboardButton(
            group['name'],
            callback_data=f"join_{group['id']}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup
    )
    
    logger.info(f"User {user.id} ({user.first_name}) used /start")

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /admin command - show admin panel"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Access denied. You are not authorized to use this command.")
        logger.warning(f"Unauthorized admin access attempt by {user.id} ({user.first_name})")
        return
    
    keyboard = [
        [InlineKeyboardButton("📝 Edit Welcome Message", callback_data="admin_edit_welcome")],
        [InlineKeyboardButton("🔗 Manage Groups", callback_data="admin_manage_groups")],
        [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    groups_count = len(storage.get_groups())
    
    await update.message.reply_text(
        f"🔧 *Admin Panel*\n\n"
        f"Groups configured: {groups_count}\n\n"
        f"Select an option:",
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
    
    # Handle user group selection
    if data.startswith("join_"):
        group_id = data.replace("join_", "")
        group = storage.get_group_by_id(group_id)
        
        if not group:
            await query.edit_message_text("❌ Group not found. Please try again with /start")
            return ConversationHandler.END
        
        try:
            # Generate single-use invite link
            invite_link = await context.bot.create_chat_invite_link(
                chat_id=group['chat_id'],
                member_limit=1,
                expire_date=None
            )
            
            await query.message.reply_text(
                f"✅ Here is your personal invite link to *{group['name']}*:\n\n"
                f"{invite_link.invite_link}\n\n"
                f"⚠️ This link is single-use and will expire after you join.",
                parse_mode='Markdown'
            )
            
            logger.info(f"Generated invite link for user {user.id} to group {group['name']}")
            
        except Exception as e:
            logger.error(f"Error generating invite link for group {group['name']}: {e}")
            await query.message.reply_text(
                f"❌ Sorry, I couldn't generate an invite link for {group['name']}.\n\n"
                "Please make sure:\n"
                "• The bot is an administrator in the group\n"
                "• The bot has 'Invite Users' permission\n\n"
                "Contact an administrator if the problem persists."
            )
        
        return ConversationHandler.END
    
    # Admin panel callbacks
    if not is_admin(user.id):
        await query.edit_message_text("❌ Access denied.")
        return ConversationHandler.END
    
    if data == "admin_edit_welcome":
        await query.edit_message_text(
            "📝 *Edit Welcome Message*\n\n"
            "Send me the new welcome message.\n\n"
            "Current message:\n"
            f"_{storage.get_welcome_message()}_\n\n"
            "Send /cancel to abort.",
            parse_mode='Markdown'
        )
        return EDITING_WELCOME
    
    elif data == "admin_manage_groups":
        keyboard = [
            [InlineKeyboardButton("➕ Add New Group", callback_data="admin_add_group")],
            [InlineKeyboardButton("📋 View All Groups", callback_data="admin_view_groups")],
            [InlineKeyboardButton("🗑️ Delete Group", callback_data="admin_delete_group")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔗 *Group Management*\n\n"
            "Select an option:",
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
                text += f"   Chat ID: `{group['chat_id']}`\n"
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
            f"Chat ID: `{group['chat_id']}`\n\n"
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
            [InlineKeyboardButton("🔗 Manage Groups", callback_data="admin_manage_groups")],
            [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        groups_count = len(storage.get_groups())
        
        await query.edit_message_text(
            f"🔧 *Admin Panel*\n\n"
            f"Groups configured: {groups_count}\n\n"
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
            [InlineKeyboardButton("🔗 Manage Groups", callback_data="admin_manage_groups")],
            [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        groups_count = len(storage.get_groups())
        
        await update.message.reply_text(
            "✅ *Welcome message updated successfully!*\n\n"
            f"New message:\n_{new_message}_\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔧 *Admin Panel*\n\n"
            f"Groups configured: {groups_count}\n\n"
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
        f"Step 2: Forward a message from the group\n\n"
        f"📋 Instructions:\n"
        f"1. Add the bot to your private group\n"
        f"2. Make the bot an administrator with 'Invite Users' permission\n"
        f"3. Forward ANY message from that group to me\n\n"
        f"I'll automatically extract the group's Chat ID!\n\n"
        f"Send /cancel to abort.",
        parse_mode='Markdown'
    )
    
    return ADDING_GROUP_ID

async def receive_group_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive forwarded message or chat ID from admin"""
    group_name = context.user_data.get('new_group_name', 'Unknown')
    chat_id = None
    
    # Check if message is forwarded from a channel/group
    if update.message.forward_from_chat:
        chat_id = str(update.message.forward_from_chat.id)
        chat_title = update.message.forward_from_chat.title
        
        await update.message.reply_text(
            f"✅ Detected forwarded message from: *{chat_title}*\n"
            f"Chat ID: `{chat_id}`",
            parse_mode='Markdown'
        )
    
    # If not forwarded, try to parse as Chat ID text
    elif update.message.text:
        chat_id = update.message.text.strip()
        
        # Validate chat ID format
        if not chat_id.startswith('-') or not chat_id[1:].isdigit():
            await update.message.reply_text(
                "❌ Please forward a message from the group, or send a valid Chat ID.\n\n"
                "Chat ID should be a negative number (e.g., -1001234567890)\n\n"
                "Send /cancel to abort."
            )
            return ADDING_GROUP_ID
    else:
        await update.message.reply_text(
            "❌ Please forward a message from the group or send the Chat ID.\n\n"
            "Send /cancel to abort."
        )
        return ADDING_GROUP_ID
    
    # Check if group already exists
    if storage.group_exists(chat_id):
        await update.message.reply_text(
            "❌ A group with this Chat ID already exists.\n\n"
            "Please check your groups or use a different group."
        )
        context.user_data.pop('new_group_name', None)
        return ConversationHandler.END
    
    # Try to validate the chat ID by getting chat info
    try:
        chat = await context.bot.get_chat(chat_id)
        
        # Add the group to storage
        new_group = storage.add_group(group_name, chat_id)
        
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
            f"Chat ID: `{new_group['chat_id']}`\n"
            f"Group Title: _{chat.title}_\n\n"
            f"⚠️ Make sure the bot is an administrator in this group with 'Invite Users' permission!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔧 *Admin Panel*\n\n"
            f"Groups configured: {groups_count}\n\n"
            f"Select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        logger.info(f"Admin {update.effective_user.id} added group {group_name} ({chat_id})")
        
    except Exception as e:
        logger.error(f"Error validating chat ID {chat_id}: {e}")
        
        # Still add it to storage
        new_group = storage.add_group(group_name, chat_id)
        
        # Show warning with admin menu
        keyboard = [
            [InlineKeyboardButton("📝 Edit Welcome Message", callback_data="admin_edit_welcome")],
            [InlineKeyboardButton("🔗 Manage Groups", callback_data="admin_manage_groups")],
            [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        groups_count = len(storage.get_groups())
        
        await update.message.reply_text(
            f"⚠️ *Group added, but validation failed*\n\n"
            f"Name: *{group_name}*\n"
            f"Chat ID: `{chat_id}`\n\n"
            f"Error: {str(e)}\n\n"
            f"Please ensure:\n"
            f"• The bot is added to the group\n"
            f"• The bot is an administrator\n"
            f"• The Chat ID is correct\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔧 *Admin Panel*\n\n"
            f"Groups configured: {groups_count}\n\n"
            f"Select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    context.user_data.pop('new_group_name', None)
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
            ADDING_GROUP_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_group_name)
            ],
            ADDING_GROUP_ID: [
                MessageHandler((filters.TEXT | filters.FORWARDED) & ~filters.COMMAND, receive_group_chat_id)
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
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the bot
    logger.info("Multi-Group Portal Bot started successfully!")
    logger.info(f"Authorized admin IDs: {', '.join(ADMIN_IDS)}")
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

