import os
import time
import datetime
import pandas as pd
import pytesseract
from collections import defaultdict
import pyautogui
import pyscreenshot as ImageGrab
import clipboard
import gspread
from sys import exit

from oauth2client.service_account import ServiceAccountCredentials

class ROKScanner:
    #Global Settings
    no_run = 300
    # Whitelist all your alliance character you wished to track
    #283
    alliance_list = ['283F','283C']
    save_local = True
    save_google = True

    #Google Settings
    worksheet_filename = 'Kingdom 1283 Management Sheet'
    sheetname_OCR = 'OCR DATA'
    updateRegister = False
    sheetname_kingdom_register = 'Player Register'

    #bluestackpath
    bluestackPath = r"/Applications/BlueStacks.app"
    #setup and positioning
    #scale the bluestack to non-full screen
    #location placed at:
    #top left: 208,97
    #bottom right: 1712,984


# 获取图片中像素点数量最多的像素
def get_threshold(image_tmp):
    pixel_dict = defaultdict(int)
    # 像素及该像素出现次数的字典
    rows, cols = image_tmp.size
    for i in range(rows):
        for j in range(cols):
            pixel = image_tmp.getpixel((i, j))
            pixel_dict[pixel] += 1
    count_max = max(pixel_dict.values())  # 获取像素出现出多的次数
    pixel_dict_reverse = {v: k for k, v in pixel_dict.items()}
    threshold = pixel_dict_reverse[count_max]  # 获取出现次数最多的像素点
    return threshold


# 按照阈值进行二值化处理
# threshold: 像素阈值
def get_bin_table(threshold):
    # 获取灰度转二值的映射table
    table = []
    for i in range(256):
        rate = 0.1  # 在threshold的适当范围内进行处理
        if threshold * (1 - rate) <= i <= threshold * (1 + rate):
            table.append(1)
        else:
            table.append(0)
    return table

# 去掉二值化处理后的图片中的噪声点
def cut_noise(image_tmp):
    rows, cols = image_tmp.size  # 图片的宽度和高度
    change_pos = []  # 记录噪声点位置
    # 遍历图片中的每个点，除掉边缘
    for i in range(1, rows - 1):
        for j in range(1, cols - 1):
            # pixel_set用来记录该店附近的黑色像素的数量
            pixel_set = []
            # 取该点的邻域为以该点为中心的九宫格
            for m in range(i - 1, i + 2):
                for n in range(j - 1, j + 2):
                    if image_tmp.getpixel((m, n)) != 1:  # 1为白色,0位黑色
                        pixel_set.append(image_tmp.getpixel((m, n)))
            # 如果该位置的九宫内的黑色数量小于等于4，则判断为噪声
            if len(pixel_set) <= 4:
                change_pos.append((i, j))
    # 对相应位置进行像素修改，将噪声处的像素置为1（白色）
    for pos in change_pos:
        image_tmp.putpixel(pos, 1)
    return image_tmp  # 返回修改后的图片


def OCR_digital(image_to_recognize):
    imgry = image_to_recognize.convert('L')  # 转化为灰度图
    # 获取图片中的出现次数最多的像素，即为该图片的背景
    max_pixel = get_threshold(imgry)
    # 将图片进行二值化处理
    # 注意，是否使用二值化要看具体情况，有些图片二值化之后，可能关键信息会丢失，反而识别不出来
    table = get_bin_table(threshold=max_pixel)
    out = imgry.point(table, '1')
    # 去掉图片中的噪声（孤立点）
    out = cut_noise(out)
    # 仅识别图片中的数字
    text = pytesseract.image_to_string(out, config='-c tessedit_char_whitelist=01234567890 --psm 7')

    return text


def OCR_box(image_to_recognize):
    text = pytesseract.image_to_boxes(image_to_recognize)
    text = text.split('\n')
    num_list = []
    num = 0
    for _ in range(len(text)):
        text[_] = text[_].split(' ')
        if text[_][0].isnumeric() is True:
            num_list.append(int(text[_][0]))
    for _ in range(len(num_list)):
        num = num * 10 + num_list[_]
    return num


def w2b(image_tmp):
    image_tmp = image_tmp.convert('L')
    thresh = 125
    fn = lambda x: 255 if x < thresh else 0
    new_image = image_tmp.convert('L').point(fn, mode='1')
    return new_image


def checkPlayerId(id, df):
    if df['id'].str.contains(id).any() or not id:
        print('skipping because player info already collected: ', id)
        return True
    else:
        return False


def closeProfile():
    # move to profile close and click
    pyautogui.moveTo(1490, 235)
    time.sleep(2)
    pyautogui.click()
    time.sleep(2)


def copyNickSelectKillDetail():
    # Copy Nick before
    pyautogui.moveTo(840, 410)
    time.sleep(2)
    pyautogui.click()
    time.sleep(2)
    # move to kill details and click
    pyautogui.moveTo(1258, 468)
    time.sleep(2)
    pyautogui.click()
    time.sleep(2)


def selectProfile(index):
    x = 960
    y = 400  # 1st profile position
    pyautogui.moveTo(y, y + (index * 95))
    time.sleep(2)
    pyautogui.click()
    time.sleep(2)

def changeProfile(df):
    # select 5th profile, skipping 4th profile
    selectProfile(4)
    # crop image to id only
    check_img_id = ImageGrab.grab(bbox=(935, 360, 1035, 385))
    # read ID
    check_id = OCR_digital(check_img_id)
    if checkPlayerId(check_id, df):
        closeProfile()
        # select 5th profile again
        selectProfile(5)
        # crop image to id only
        check2_img_id = ImageGrab.grab(bbox=(935, 360, 1035, 385))
        # read ID
        check2_id = OCR_digital(check2_img_id)
        # if 5th profile still doesn't work
        if checkPlayerId(check2_id, df):
            closeProfile()
            # select 6th profile
            selectProfile(6)


def updateKingdomRegister(df, id, nick,alliance,register_sheet):
    if any(df.ID == int(id)):
        print("updating existing record")
        df.loc[df.ID == int(id), 'NAME'] = nick
        if (alliance in ROKScanner.alliance_list):
            df.loc[df.ID == int(id), 'ALLIANCE'] = alliance
    else:
        print("adding new record")
        df.loc[len(df)] = [id,nick,alliance,'','',id,id]

    register_sheet.update([df.columns.values.tolist()] + df.values.tolist())

def getX(img):
    x = pyautogui.locateOnScreen(img, confidence = 0.9)
    #count = 0
    #while (count<10):
    if (x):
        print("Found: " +  img + " at: " + str(x))
        return x
    else:
        print("Not Found... Try again in 5 seconds")
        return False
        #time.sleep(5)
        #++count



def calculateY():
    ranked_1 = getX("ranked_1.png")
    print(ranked_1)
    ranked_2 = getX("ranked_2.png")
    print(ranked_2)
    deltaY =  ranked_2.top - ranked_1.top
    print(deltaY)

if __name__ == '__main__':
    if ROKScanner.save_google:
        # use creds to create a client to interact with the Google Drive API
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('secret.json', scope)
        client = gspread.authorize(creds)

        # Open Workbook and sheet
        file = client.open(ROKScanner.worksheet_filename)
        OCR_Sheet = file.worksheet(ROKScanner.sheetname_OCR)
        if ROKScanner.updateRegister:
            Register_Sheet = file.worksheet(ROKScanner.sheetname_kingdom_register)
            #initial load kingdom register into dataframe
            df_player_register = pd.DataFrame(file.worksheet(ROKScanner.sheetname_kingdom_register).get_all_records())

    #Get time now for record insertion
    now = datetime.datetime.now()
    date_time = now.strftime('%m/%d/%Y %H:%M:%S')

    if ROKScanner.save_local:
        save_local_file_name = os.path.join(now.strftime('result/ROK_K283_Top' + str(ROKScanner.no_run) + '_%Y%m%d%H%M%S') + '.csv')


    df = pd.DataFrame(columns=(
        'id', 'nick', 'alliance', 'profile_power', 'dead', 'kill_4', 'kill_5'))

    #Open Bluestack game
    os.system("open /Applications/BlueStacks.app")
    time.sleep(2)
    # Go to profile
    pyautogui.press("G")
    time.sleep(2)

    #Ready load ranking board
    ranking = getX("ranking.png")
    if ranking:
        pyautogui.click(ranking)
        time.sleep(2)
        individual_kills = getX("Power_Ranking.png")
        if individual_kills:
            pyautogui.click(individual_kills)
            time.sleep(2)
            kill_board = getX("Power_Board_Banner.png")
            if kill_board:
                print("Can start scan")
                calculateY()
            else:
                print("Unable to start")
                exit()
        else:
            print("Unable to locate kill board")
            exit()
    else:
        print("Unable to find ranking...")
        exit()




    for i in range(ROKScanner.no_run):
        # move to ranking position 1-3
        ranked_1 = getX("ranked_1.png")
        if ranked_1:
            selectProfile(i)
        else:
            selectProfile(3)

        # crop image to id only
        img_id = ImageGrab.grab(bbox=(935, 360, 1035, 385))
        #img_id.save('id.png')
        # read ID
        id = OCR_digital(img_id)
        print('player id:', id)

        if checkPlayerId(id, df):
            changeProfile(df)
            # crop image to id only
            img_id = ImageGrab.grab(bbox=(935, 360, 1035, 385))
            #img_id.save('id.png')
            # read ID
            id = OCR_digital(img_id)

        #alliance
        img_alliance = ImageGrab.grab(bbox=(823, 485, 880, 505))
        img_alliance = cut_noise(img_alliance)
        #img_alliance.save('alliance.png')
        alliance = pytesseract.image_to_string(img_alliance, config='-c tessedit_char_whitelist=283FC --psm 7').strip()

        if alliance not in ROKScanner.alliance_list:
            print(f'Alliance is not found in alliance whitelist: <{alliance}>')
            #retry for 3 characters alliances
            img_alliance = ImageGrab.grab(bbox=(823, 485, 866, 505))
            img_alliance = cut_noise(img_alliance)
            #img_alliance.save('alliance.png')
            alliance = pytesseract.image_to_string(img_alliance, config='-c tessedit_char_whitelist=283FC --psm 7').strip()

        print(f'Alliance: <{alliance}>')

        # profile_power
        img_profile_power = ImageGrab.grab(bbox=(1050, 480, 1200, 510))
        #img_profile_power.save('profile_power.png')
        profile_power = OCR_digital(img_profile_power)
        print('profile power: ', profile_power)

        # move to kill details and click
        copyNickSelectKillDetail()
        nick = clipboard.paste()
        print("Nick: ", nick)

        img_kill_t4 = ImageGrab.grab(bbox=(1020, 809, 1150, 849))
        #img_kill_t4.save('t4.png')
        kill_t4 = OCR_box(img_kill_t4)
        print('t4 kill:', kill_t4)
        img_kill_t5 = ImageGrab.grab(bbox=(1020, 851, 1150, 889))
        #img_kill_t5.save('t5.png')
        kill_t5 = OCR_box(img_kill_t5)
        print('t5 kill:', kill_t5)

        # move to more info and click
        pyautogui.moveTo(580, 765)
        time.sleep(2)
        pyautogui.click()
        time.sleep(2)
        # capture screen
        img_dead = ImageGrab.grab(bbox=(1320, 560, 1435, 590))
        img_dead = w2b(img_dead)
        #img_dead.save('dead.png')
        dead_troops = OCR_box(img_dead)
        if dead_troops == 0:
            # retry screen capture on info
            img_dead = ImageGrab.grab(bbox=(1320, 560, 1435, 590))
            img_dead = w2b(img_dead)
            #img_dead.save('dead.png')
            dead_troops = OCR_box(img_dead)
        print('dead:', dead_troops)
        # move to close and click (Closing more info box)
        pyautogui.moveTo(1515, 190)
        time.sleep(2)
        pyautogui.click()
        time.sleep(2)
        # move to close and click
        closeProfile()
        #update record
        df.loc[i] = [id, nick,alliance,profile_power, dead_troops, kill_t4, kill_t5]
        if ROKScanner.save_google:
            OCR_Sheet.append_row([str(date_time),int(id),int(profile_power),dead_troops,kill_t4,kill_t5],value_input_option="USER_ENTERED")
            if ROKScanner.updateRegister:
                updateKingdomRegister(df_player_register, id, nick, alliance,Register_Sheet)
        if ROKScanner.save_local:
            df.to_csv(save_local_file_name)
