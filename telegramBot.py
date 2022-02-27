import telebot

import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import recordAudio, takeScreenShot, timeStamp


with open('./.env') as f:
    ALLOWED_USERS = f.read().strip().split('\n')
    TOKEN = ALLOWED_USERS.pop(0)
    ALLOWED_USERS = [int(i) for i in ALLOWED_USERS]
    print(TOKEN, ALLOWED_USERS)



bot= telebot.TeleBot(TOKEN, parse_mode='HTML')
rec = recordAudio()





@bot.message_handler(commands='screenshot')
def send_screenshot(message):
    user = message.from_user.id

    if user not in ALLOWED_USERS : return

    file = takeScreenShot()
    with open(file,'rb') as f:
        bot.send_photo(user, f)
    # os.remove(file)





@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    file = f"Audio_{timeStamp()}.wav"
    if call.data == "cb_stop":
        bot.send_message(call.from_user.id, "Processing please wait")

        rec.stop(file)
        with open(file,'rb') as f:
            bot.send_audio(call.from_user.id, f)
        # os.remove(file)

    elif call.data == "cb_cancel":
        rec.stop(file,True)
        bot.send_message(call.from_user.id, "Recording terminated")




def audioMarkup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Finish", callback_data="cb_stop"),
                InlineKeyboardButton("Cancel", callback_data="cb_cancel"))
    return markup




@bot.message_handler(commands='audio')
def send_audio(message):
    user = message.from_user.id
    if user not in ALLOWED_USERS : return
    if rec.running: 
        bot.send_message(user, "Recording already in progress.")
    else:
        rec.start()
        bot.send_message(user, "Recording started.", reply_markup=audioMarkup())



bot.infinity_polling()