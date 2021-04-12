import os
import time
import datetime
import pandas as pd
import pytesseract
from collections import defaultdict
import pyautogui
import pyscreenshot as ImageGrab
import clipboard


class ROKScanner:
    bluestackPath = r"/Applications/BlueStacks.app"
    #scale the bluestack to non-full screen
    #location placed at:
    #top left: 208,97
    #bottom right: 1712,984

    def screenCapture(name: str):
        # part of the screen
        if name == 'profile':
            im = ImageGrab.grab(bbox=(815, 361, 1420, 700))  # X1,Y1,X2,Y2
        else:
            im = ImageGrab.grab(bbox=(970, 270, 1450, 590))  # X1,Y1,X2,Y2
        # save image file
        im.save("%s.png" % name)
        return im


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
    text = pytesseract.image_to_string(out, config='digits')
    # 去掉识别结果中的特殊字符
    exclude_char_list = ' .:\\|\'\"?![],()~@#$%^&*_+-={};<>/¥'
    text = ''.join([x for x in text if x not in exclude_char_list])
    text = text.strip()
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
    time.sleep(1)
    pyautogui.click()
    time.sleep(1)


def copyNickSelectKillDetail():
    # Copy Nick before
    pyautogui.moveTo(840, 410)
    time.sleep(1)
    pyautogui.click()
    time.sleep(1)
    # move to kill details and click
    pyautogui.moveTo(1258, 468)
    time.sleep(1)
    pyautogui.click()
    time.sleep(1)


def selectProfile(index):
    x = 960
    y = 400  # 1st profile position
    pyautogui.moveTo(y, y + (index * 95))
    time.sleep(1)
    pyautogui.click()
    time.sleep(1)
    # TODO: check id here and if valid then continue, if not keep try to select next profile cycle
    # TO HANDLE if 4,5,6 unable to select scenario which leads to resource page


def changeProfile(df):
    # select 5th profile, skipping 4th profile
    selectProfile(4)
    # capture screen
    check_img = ROKScanner.screenCapture('profile')
    # crop image to id only
    check_img_id = check_img.crop([120, 0, 220, 25])
    # read ID
    check_id = OCR_digital(check_img_id)
    if checkPlayerId(check_id, df):
        # select 5th profile again
        selectProfile(5)
        # capture screen
        img = ROKScanner.screenCapture('profile')
        # crop image to id only
        check2_img_id = img.crop([120, 0, 220, 25])
        # read ID
        check2_id = OCR_digital(check2_img_id)
        # if 5th profile still doesn't work
        if checkPlayerId(check2_id, df):
            # select 6th profile
            selectProfile(6)
            img = ROKScanner.screenCapture('profile')
        return img
    else:
        return check_img;



if __name__ == '__main__':
    df = pd.DataFrame(columns=(
    'id', 'nick','alliance','profile_power', 'current_power', 'dead', 'total_kill_pt','kill_1', 'kill_2', 'kill_3', 'kill_4', 'kill_5','validKillPoint','validPower'))

    t = datetime.datetime.now()
    table_name = os.path.join(t.strftime('result/ROK_K530_Top1000_%Y%m%d%H%M%S') + '.csv')

    os.system("open /Applications/BlueStacks.app")

    for i in range(950):
        # move to ranking position 1-3
        if i < 3:
            selectProfile(i)
            #if not starting from rank 1-3
            #selectProfile(3)
        else:
            selectProfile(3)


        # capture screen
        img = ROKScanner.screenCapture('profile')
        # crop image to id only
        img_id = img.crop([120, 0, 220, 25])
        # read ID
        id = OCR_digital(img_id)
        print('player id:', id)

        if checkPlayerId(id, df):
            img = changeProfile(df)
            # crop image to id only
            img_id = img.crop([120, 0, 220, 25])
            # read ID
            id = OCR_digital(img_id)

        #alliance
        img_alliance = img.crop([0, 120, 70, 150])
        img_alliance.save('alliance.png')
        alliance = pytesseract.image_to_string(img_alliance)
        print('alliance: ', alliance)
        # profile_power
        img_profile_power = img.crop([230, 115, 400, 145])
        img_profile_power.save('profile_power.png')
        profile_power = OCR_digital(img_profile_power)
        print('profile power: ', profile_power)

        # move to kill details and click
        copyNickSelectKillDetail()
        nick = clipboard.paste()
        print("Nick: ", nick)
        # capture Total Kills Point
        img_total_kill_point = ImageGrab.grab(bbox=(1075, 505, 1225, 535))
        img_total_kill_point.save('total_kill_pt.png')
        total_kill_point = OCR_box(img_total_kill_point)
        print('total kill point:', total_kill_point)

        # capture T1 Kills
        img_kill_t1 = ImageGrab.grab(bbox=(1020, 714, 1150, 754))
        img_kill_t1.save('t1.png')
        kill_t1 = OCR_box(img_kill_t1)
        print('t1 kill:', kill_t1)
        img_kill_t2 = ImageGrab.grab(bbox=(1020, 755, 1150, 795))
        img_kill_t2.save('t2.png')
        kill_t2 = OCR_box(img_kill_t2)
        print('t2 kill:', kill_t2)
        img_kill_t3 = ImageGrab.grab(bbox=(1020, 796, 1150, 836))
        img_kill_t3.save('t3.png')
        kill_t3 = OCR_box(img_kill_t3)
        print('t3 kill:', kill_t3)
        img_kill_t4 = ImageGrab.grab(bbox=(1020, 838, 1150, 878))
        img_kill_t4.save('t4.png')
        kill_t4 = OCR_box(img_kill_t4)
        print('t4 kill:', kill_t4)
        img_kill_t5 = ImageGrab.grab(bbox=(1020, 880, 1150, 920))
        img_kill_t5.save('t5.png')
        kill_t5 = OCR_box(img_kill_t5)
        print('t5 kill:', kill_t5)
        checksum_kill_point = kill_t1/5 + kill_t2*2 + kill_t3*4 + kill_t4*10 + kill_t5*20
        print('sum kill point:',checksum_kill_point)
        # verify if kill point is valid
        valid = (int(total_kill_point) == int(checksum_kill_point))
        print('is kill point valid?:', valid)

        # move to more info and click
        pyautogui.moveTo(580, 765)
        time.sleep(1)
        pyautogui.click()
        time.sleep(1)
        # capture screen
        img_info = ROKScanner.screenCapture('info')
        img_current_power = img_info.crop([0, 0, 150, 30])
        img_current_power = w2b(img_current_power)
        img_current_power.save('currentPower.png')
        current_power = OCR_box(img_current_power)
        if current_power == 0:
            # retry screen capture on info
            img_info = ROKScanner.screenCapture('info')
            img_current_power = img_info.crop([0, 0, 150, 30])
            img_current_power = w2b(img_current_power)
            img_current_power.save('currentPower.png')
            current_power = OCR_box(img_current_power)
        print('current power:', current_power)
        img_dead = img_info.crop([320, 290, 490, 325])
        img_dead = w2b(img_dead)
        img_dead.save('dead.png')
        dead_troops = OCR_box(img_dead)
        if dead_troops == 0:
            # retry screen capture on info
            img_dead = img_info.crop([320, 290, 490, 325])
            img_dead = w2b(img_dead)
            img_dead.save('dead.png')
            dead_troops = OCR_box(img_dead)
        print('dead:', dead_troops)

        validPower = (int(profile_power) == int(current_power))

        df.loc[i] = [id, nick,alliance,profile_power, current_power, dead_troops,checksum_kill_point, kill_t1, kill_t2, kill_t3, kill_t4, kill_t5,valid,validPower]
        # move to close and click (Closing more info box)
        pyautogui.moveTo(1515, 190)
        time.sleep(1)
        pyautogui.click()
        time.sleep(1)
        # move to close and click
        closeProfile()
        df.to_csv(table_name)


