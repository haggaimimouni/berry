import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, ConversationHandler
import telegram.ext.filters as filters
import random

# Configuration du logging
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

# Base de données pour stocker les GIFs, questions de quiz et contrats crypto
user_data = {
    'gif': None,
    'quiz_questions': []
}
crypto_contracts = {}

# Commande /gif
async def gif(update: Update, context: CallbackContext) -> None:
    gif = user_data.get('gif')
    if gif:
        try:
            # Vérifiez si le GIF est une URL ou un fichier local
            if gif.startswith('http'):
                await update.message.reply_animation(animation=gif)
            else:
                await update.message.reply_animation(animation=InputFile(gif))
        except Exception as e:
            logging.error(f"Error sending GIF: {e}")
            await update.message.reply_text("An error occurred while sending the GIF.")
    else:
        await update.message.reply_text("No GIF is set yet. Use /setgif to set one.")

async def save_gif(update: Update, context: CallbackContext) -> None:
    if update.message.document or update.message.photo:
        file = update.message.document or update.message.photo[-1]
        file_obj = await file.get_file()
        file_path = file_obj.file_path
        user_data['gif'] = file_path
        await update.message.reply_text("GIF has been set successfully!")
    elif update.message.text:
        user_data['gif'] = update.message.text
        await update.message.reply_text("GIF link has been saved!")
    else:
        await update.message.reply_text("Invalid input. Please send a GIF or a link.")
    return ConversationHandler.END

# Commande /setquiz
async def set_quiz(update: Update, context: CallbackContext) -> None:
    set_quiz_message = await update.message.reply_text("Reply to this message with your question in this format: `question;correct_answer`")
    context.user_data['set_quiz_message_id'] = set_quiz_message.message_id
    return 2

async def save_quiz(update: Update, context: CallbackContext) -> None:
    if update.message.reply_to_message and update.message.reply_to_message.message_id == context.user_data.get('set_quiz_message_id'):
        question_data = update.message.text
        if ';' in question_data:
            user_data['quiz_questions'].append(question_data)
            await update.message.reply_text("Quiz question saved successfully!")
            await update.message.delete()
            await pose_quiz(update, context)
        else:
            await update.message.reply_text("Invalid format. Please use: `question;correct_answer`")
        return ConversationHandler.END

async def pose_quiz(update: Update, context: CallbackContext) -> None:
    question_data = user_data['quiz_questions'][-1]
    question, correct_answer = question_data.split(';')
    
    quiz_message = await update.message.reply_text(question)
    context.user_data['current_answer'] = correct_answer
    context.user_data['quiz_message_id'] = quiz_message.message_id
    context.user_data['quiz_active'] = True

async def handle_quiz_response(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('quiz_active') and update.message.reply_to_message and update.message.reply_to_message.message_id == context.user_data.get('quiz_message_id'):
        user_answer = update.message.text
        correct_answer = context.user_data.get('current_answer')
        user_name = update.message.from_user.full_name

        if user_answer.lower() == correct_answer.lower():
            await update.message.reply_text(f"Correct, {user_name}! 🏴‍☠️, You want 10000 $BERRY 🪙")
            context.user_data['quiz_active'] = False
        else:
            await update.message.reply_text(f"Wrong, {user_name}! ❌ Try again Pirate.")
            # Supprimer le message après 10 secondes
            await asyncio.sleep(10)
            await update.message.delete()

# Commande /ca pour les contrats crypto
async def handle_ca(update: Update, context: CallbackContext) -> None:
    if len(context.args) == 0:
        if not crypto_contracts:
            await update.message.reply_text("No contracts saved yet. Use /ca <token_name> <contract_address> to add one.")
        else:
            contracts_list = "\n".join([f"{name}: {address}" for name, address in crypto_contracts.items()])
            await update.message.reply_text(f"📜Contracts:\n{contracts_list}")
    elif len(context.args) == 2:
        token_name = context.args[0].upper()
        contract_address = context.args[1]
        crypto_contracts[token_name] = contract_address
        await update.message.reply_text(f"✅ Contract for {token_name} saved: {contract_address}")
    else:
        await update.message.reply_text("Usage: /ca <token_name> <contract_address> to save a contract or /ca to list all saved contracts.")

# Commande /start
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Welcome to the One Piece Bot! 🏴‍☠️\n"
        "Commands:\n"
        "/berry - Send the current GIF\n"
        "/setgif - Set a new GIF\n"
        "/setquiz - Add a new quiz question\n"
        "/ca - Manage crypto contracts\n"
        "Type /help for more info."
    )

# Gestionnaire d'erreurs
async def error_handler(update: Update, context: CallbackContext) -> None:
    logging.error(f"Update {update} caused error {context.error}")

# Fonction principale
def main() -> None:
    application = Application.builder().token("7826413482:AAHDSvHEfB3JXldwHgF3YoKsRjR-5YffLvE").build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))

    # /gif and /setgif commands
    application.add_handler(CommandHandler("berry", gif))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("setgif", set_gif)],
        states={1: [MessageHandler(filters.TEXT | filters.Document.ALL | filters.PHOTO, save_gif)]},
        fallbacks=[]
    ))

    # /setquiz command
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("setquiz", set_quiz)],
        states={2: [MessageHandler(filters.TEXT, save_quiz)]},
        fallbacks=[]
    ))

    # Handle quiz responses
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quiz_response))

    # /ca command
    application.add_handler(CommandHandler("ca", handle_ca))

    # Error handler
    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
