import difflib
import time

import numpy as np
import pyautogui
from win32api import GetSystemMetrics
import cv2
from PIL import Image, ImageGrab
from pytesseract import pytesseract, Output

pytesseract.tesseract_cmd = 'tesseract.exe'
pyautogui.FAILSAFE = False


def check_next(index, split_key, converted_text):
    flag = False
    if len(split_key) > 1:
        for j in range(1, len(split_key)):
            if converted_text['text'][index + j].lower() != split_key[j]:
                flag = True
    return flag


def get_converted_text(image, method="None"):
    converted_text = pytesseract.image_to_data(image, output_type=Output.DICT)
    return converted_text


def text_coordinates(pos, converted_text, key, key_next=None, flag_next=None, contain_flag=False,
                     near_by_match=False, zooming=4):
    split_key = key.lower().split()
    occurrence = 0
    for i in range(len(converted_text['level'])):
        if ((contain_flag and converted_text['text'][i].lower().find(split_key[0]) == 0) or (
                not contain_flag and converted_text['text'][i].lower() == split_key[0]) or (near_by_match and (
                int(difflib.SequenceMatcher(None, converted_text['text'][i].lower(),
                                            split_key[0]).ratio() * 100)) > 80)):
            flag = check_next(i, split_key, converted_text)
            if not flag:
                (x, y, w, h) = (converted_text['left'][i], converted_text['top'][i], converted_text['width'][i],
                                converted_text['height'][i])
                if (key_next is None):
                    return ((x + (w // 2)) // zooming + pos[0], (y + (h // 2)) // zooming + pos[1], w, h)
                else:
                    occurrence = i
                    break
    if occurrence > 0:
        print('worked')
        return get_coordinates_for_next_text((x, y), occurrence, pos, converted_text, key_next, flag_next,
                                             near_by_match, zooming)
    return (-1, -1, -1, -1)


def get_coordinates_for_next_text(pos_for_next, occurrence, pos, converted_text, key_next, flag_next, near_by_match,
                                  zooming):
    split_key_next = key_next.lower().split()
    for i in range(occurrence, len(converted_text['level'])):
        check_next_to_condition = False
        if (flag_next == "nextToX" and converted_text['left'][i] > pos_for_next[0]) or (
                flag_next == "nextToY" and converted_text['top'][i] > pos_for_next[1]):
            check_next_to_condition = True
        if (check_next_to_condition and ((converted_text['text'][i].lower() == split_key_next[0]) or (
                near_by_match and (
        int(difflib.SequenceMatcher(None, converted_text['text'][i].lower(), split_key_next[0]).ratio() * 100)) > 80))):
            flag = check_next(i, split_key_next, converted_text)
            if not flag:
                (x, y, w, h) = (converted_text['left'][i], converted_text['top'][i], converted_text['width'][i],
                                converted_text['height'][i])
                return ((x + (w // 2)) // zooming + pos[0], (y + (h // 2)) // zooming + pos[1], w, h)

    return (-1, -1, -1, -1)


def imagesearch(image, precision=0.8):
    im = pyautogui.screenshot()
    img_rgb = np.array(im)
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
    template = cv2.imread(image, 0)
    template.shape[::-1]

    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val < precision:
        return [-1, -1]
    return max_loc


def image_croping_template(template, height, width=None):
    temp = cv2.imread(template, 0)
    w, _ = temp.shape[::-1]
    x, y = imagesearch(template, 0.5)
    if (x == -1 and y == -1):
        return -1, -1, -1, -1
    else:
        if width is not None:
            w = width
        return x, y, w, height


def image_OCR(text, images):
    x, y, w, h = image_croping_template(images, GetSystemMetrics(1), GetSystemMetrics(0))
    im = ImageGrab.grab(bbox=(x, y, w, h))
    #im.save(r"C:\Users\PyCharmMiscProject\"+{text}")
    np_image = np.array(Image.open(images))
    img = cv2.cvtColor(np_image, cv2.COLOR_BGR2GRAY)
    img = cv2.resize(img, None, fx=1, fy=1, interpolation=cv2.INTER_AREA)
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)

    converted_text = pytesseract.image_to_data(img, output_type=Output.DICT)
    print(converted_text)
    x_reg, y_reg, _, _ = text_coordinates((x, y), converted_text, text, near_by_match=True)
    print(x_reg, y_reg)

    return x_reg, y_reg
def crop_image(sample_image,width, height):
    screenshot = ImageGrab.grab()
    screenshot_np = np.array(screenshot)
    screenshot_bgr = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
    image_path = "dir"
    cv2.imwrite(image_path+"screenshot.png", screenshot_bgr)
    template = cv2.imread(sample_image)

    if template is None:
        raise FileNotFoundError(f"Template image '{sample_image}' not found.")

    screenshot_gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    top_left = max_loc
    h, w = template.shape[:2]
    bottom_right = (top_left[0] + w+width, top_left[1] + h+height)
    cropped = screenshot_bgr[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

    cv2.imwrite(image_path+"cropped_result.png", cropped)


   # cv2.imshow("Cropped", cropped)
   # cv2.waitKey(0)
  #  cv2.destroyAllWindows()
    print(top_left[0], top_left[1], bottom_right[0], bottom_right[1])
    return top_left[0], top_left[1], bottom_right[0], bottom_right[1]

#
# print(crop_image('test_crop.png'))
# ocr_data = get_converted_text(r'image')
# entries = []
# time.sleep(2)
# for i, text in enumerate(ocr_data['text']):
#     if text.strip().startswith("PVD-CR-2"):
#         entry = {
#             'text': text.strip(),
#             'left': ocr_data['left'][i],
#             'top': ocr_data['top'][i],
#             'width': ocr_data['width'][i],
#             'height': ocr_data['height'][i]
#         }
#         entries.append(entry)
#
# # Step 2: Get the last valid entry
# last_entry = entries[-1] if entries else None
#
# # Step 3: Print result
# if last_entry:
#     print("Last matching text:", last_entry['text'])
#     print("Coordinates → Left:", last_entry['left'], "Top:", last_entry['top'],
#           "Width:", last_entry['width'], "Height:", last_entry['height'])
#
# else:
#     print("No matching text found.")
#
# pyautogui.click(last_entry['left'] , last_entry['top'],last_entry['width'],last_entry['height'])
# test_crp = pyautogui.screenshot(last_entry['left'] , last_entry['top'],last_entry['width'],last_entry['height'])
# cv2.imwrite("hltest.png",test_crp)

