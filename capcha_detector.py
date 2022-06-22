from config import App
import pytesseract
from PIL import Image
from scipy.ndimage import gaussian_filter, grey_opening, grey_closing, median_filter
import cv2
import numpy as np

TH_MASK_OUT_P1 = 96
COLOR_MASK_IN_P1 = 66
COLOR_MASK_IN_P2 = 63
COLOR_MASK_IN_P3 = 49
C_DIFF_MASK_IN = 60
C_STD_MASK_OUT = 3.3
UNSHARP_TH = 180
GAUSSIAN_IN = 60

WHITE = [255, 255, 255]
RED = [255, 0, 0]


def processImage(path, imgFormat,
                 crop=False, cropSize=(10, 2, 100, 25),
                 resize=False, resizeNewSize=(360, 100),
                 SAVE_PROCESS=False, SAVE_PATH=None):
    # Open image
    imageOpened = Image.open(path + imgFormat)
    # Crop
    if crop:
        imageOpened = imageOpened.crop(cropSize)
    if resize:
        imageOpened = imageOpened.resize(resizeNewSize)
    if SAVE_PATH is None:
        SAVE_PATH = path

    imageOpened.save(SAVE_PATH + "__0_RESIZED" + imgFormat)

    # Convert to channels
    r, g, b = imageOpened.split()
    # GrayScale = imageOpened.convert('L') # Luma = R * 299/1000 + G * 587/1000 + B * 114/1000
    # GL_pixelData = np.array(GrayScale)

    # Convert from Image to NP Array
    RED_pixelData = np.array(r)
    GREEN_pixelData = np.array(g)
    BLUE_pixelData = np.array(b)
    GL_pixelData = (RED_pixelData / 3 + GREEN_pixelData / 3 + BLUE_pixelData / 3).astype(np.uint8)
    GL_pixelDataORG = (RED_pixelData / 3 + GREEN_pixelData / 3 + BLUE_pixelData / 3).astype(np.uint8)

    if SAVE_PROCESS:
        Image.fromarray(RED_pixelData).save(SAVE_PATH + "__0_RED" + imgFormat)
        Image.fromarray(GREEN_pixelData).save(SAVE_PATH + "__0_GREEN" + imgFormat)
        Image.fromarray(BLUE_pixelData).save(SAVE_PATH + "__0_BLUE" + imgFormat)
        Image.fromarray(GL_pixelData).save(SAVE_PATH + "__0_GL" + imgFormat)

    # Captcha noise is presented with grayscale noise (almost single chanel)
    # We start with finding all the pixels that absolutely have color and make sure we do not mask them out
    # While masking out all the general pixels above certain value
    # Start with mask out, later mask in
    GL_pixelData[GL_pixelData > TH_MASK_OUT_P1] = 255
    if SAVE_PROCESS:
        Image.fromarray(GL_pixelData).save(SAVE_PATH + "__1_MASK_OUT_GL_TH" + imgFormat)

    rg_diff = cv2.subtract(RED_pixelData, GREEN_pixelData)
    gr_diff = cv2.subtract(GREEN_pixelData, RED_pixelData)
    rb_diff = cv2.subtract(RED_pixelData, BLUE_pixelData)
    br_diff = cv2.subtract(BLUE_pixelData, RED_pixelData)
    gb_diff = cv2.subtract(GREEN_pixelData, BLUE_pixelData)
    bg_diff = cv2.subtract(BLUE_pixelData, GREEN_pixelData)

    GL_pixelData[rg_diff > C_DIFF_MASK_IN] = 0
    GL_pixelData[gr_diff > C_DIFF_MASK_IN] = 0
    GL_pixelData[rb_diff > C_DIFF_MASK_IN] = 0
    GL_pixelData[br_diff > C_DIFF_MASK_IN] = 0
    GL_pixelData[gb_diff > C_DIFF_MASK_IN] = 0
    GL_pixelData[bg_diff > C_DIFF_MASK_IN] = 0
    if SAVE_PROCESS:
        Image.fromarray(GL_pixelData).save(SAVE_PATH + "__2_MASK_IN_COLOR_DIFF_TH" + imgFormat)

    z_stack = np.stack([RED_pixelData, GREEN_pixelData, BLUE_pixelData], axis=2)
    std_color_array = np.std(z_stack, axis=2)
    GL_pixelData[std_color_array < C_STD_MASK_OUT] = 255
    if SAVE_PROCESS:
        Image.fromarray(GL_pixelData).save(SAVE_PATH + "__3_MASK_OUT_COLOR_STD_TH" + imgFormat)

    GL_pixelData[RED_pixelData < COLOR_MASK_IN_P1] = 0
    GL_pixelData[GREEN_pixelData < COLOR_MASK_IN_P1] = 0
    GL_pixelData[BLUE_pixelData < COLOR_MASK_IN_P1] = 0
    if SAVE_PROCESS:
        Image.fromarray(GL_pixelData).save(SAVE_PATH + "__4_MASK_IN_COLOR_TH" + imgFormat)

    # Create Un-sharp mask
    GaussianGrayScaleData = gaussian_filter(GL_pixelData, sigma=3)
    UnsharpMASK = cv2.subtract(GL_pixelData, GaussianGrayScaleData) * 5
    GL_pixelDataP2 = cv2.add(GL_pixelData, UnsharpMASK)
    GL_pixelDataP2[GL_pixelDataP2 > UNSHARP_TH] = 0
    GL_pixelDataP2[GL_pixelDataP2 >= 1] = 255
    GL_pixelData = cv2.subtract(GL_pixelData, GL_pixelDataP2)
    if SAVE_PROCESS:
        Image.fromarray(GL_pixelData).save(SAVE_PATH + "__5_UNSHARP_MASK" + imgFormat)

    # Mask again with color pixels
    GL_pixelData[RED_pixelData < COLOR_MASK_IN_P2] = 0
    GL_pixelData[GREEN_pixelData < COLOR_MASK_IN_P2] = 0
    GL_pixelData[BLUE_pixelData < COLOR_MASK_IN_P2] = 0
    if SAVE_PROCESS:
        Image.fromarray(GL_pixelData).save(SAVE_PATH + "__6_COLOR_MASK_IN_P2" + imgFormat)

    GL_pixelData[GL_pixelData <= 50] = 0
    GL_pixelData[GL_pixelData >= 1] = 255
    filtered_array_gaussian_filter = gaussian_filter(GL_pixelData, sigma=4, truncate=7)
    GL_pixelData[filtered_array_gaussian_filter <= GAUSSIAN_IN] = 0
    if SAVE_PROCESS:
        Image.fromarray(GL_pixelData).save(SAVE_PATH + "__7_GAUSSIAN_MASK_IN" + imgFormat)

    GL_pixelData = grey_closing(GL_pixelData, size=(4, 4))
    if SAVE_PROCESS:
        Image.fromarray(GL_pixelData).save(SAVE_PATH + "__8_GREY_CLOSING" + imgFormat)

    # Mask again with color pixels
    GL_pixelData[RED_pixelData < COLOR_MASK_IN_P3] = 0
    GL_pixelData[GREEN_pixelData < COLOR_MASK_IN_P3] = 0
    GL_pixelData[BLUE_pixelData < COLOR_MASK_IN_P3] = 0
    if SAVE_PROCESS:
        Image.fromarray(GL_pixelData).save(SAVE_PATH + "__9_COLOR_MASK_IN_P3" + imgFormat)


    GL_pixelData = grey_opening(GL_pixelData, size=(6, 6))
    if SAVE_PROCESS:
        Image.fromarray(GL_pixelData).save(SAVE_PATH + "__10_GREY_OPENING" + imgFormat)


    processedGrayScale = Image.fromarray(GL_pixelData)
    return resolveOCR(processedGrayScale)[0:-1], processedGrayScale


def resolveOCR(image):
    pytesseract.pytesseract.tesseract_cmd = App.get("TesseractOCR_executable_path")
    return pytesseract.image_to_string(image, config='--psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', lang='eng')


def runCaptchaDecoder(path, imgFormat, length=6):
    captcha_text, imgOUT = processImage(path, imgFormat)

    captcha_text = captcha_text.replace("\n", "")

    if len(captcha_text) != length:
        captcha_text = ""
    else:
        print('Extracted Text', captcha_text)
        imgOUT.save(path + "processed" + imgFormat)

    return captcha_text


def testFunction():
    from csv import reader
    from PIL import ImageDraw
    from shutil import rmtree
    from os import mkdir

    dir_path = r"C:\Users\vital\Desktop\final_project_download_video\szhotel\output\batch"
    csv_path = dir_path + "\\" + "validation.csv"
    out_path = dir_path + "\\" + "results"
    debug_path = out_path + "\\" + "process"
    results = []
    imgFORMAT = ".jpg"

    try:
        rmtree(out_path)
        mkdir(out_path)
        mkdir(debug_path)
    except OSError:
        print("Could not delete the old dir")

    try:
        with open(csv_path, mode='r', newline='') as csv_file:
            index = -1
            correct = 0
            correct_len = 0
            csv_reader = list(reader(csv_file, delimiter=',', quotechar='|'))
    except OSError:
        print("ERROR LOADING CSV")
        exit()

    for i in range(1, 50):
        imgIN_path = dir_path + "\\" + str(i)
        imgOUT_path = out_path + "\\" + str(i)
        imgOUT_debug_path = debug_path + "\\" + str(i)

        captcha_text, outImg = processImage(imgIN_path, imgFormat=imgFORMAT,
                                            crop=True, resize=True,
                                            SAVE_PROCESS=True, SAVE_PATH=imgOUT_debug_path)
        captcha_text = captcha_text.replace("\n", "")
        results.append(captcha_text)
        if len(captcha_text) == 6:
            correct_len += 1
            if captcha_text == csv_reader[i][1]:
                outImg.save(imgOUT_path + "_GOOD" + imgFORMAT)
                correct += 1
            else:
                draw = ImageDraw.Draw(outImg)
                draw.text((0, 0), csv_reader[i][1], fill=(100))
                draw.text((0, 30), captcha_text, fill=(100))
                outImg.save(imgOUT_path + "_BAD" + imgFORMAT)
    print(results)
    print("OK : ~Validating Text Length")
    print("OK : ~Validating results with CSV")


if __name__ == '__main__':
    print("Running test function")
    testFunction()
