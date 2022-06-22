class App:
    __conf = {
        # Use details
        "passport": "FD231B71",
        "password": "A1234567",
        # Captcha output directory
        "captcha_img_output_PATH": r"output//captchaImageOutput",
        "captcha_img_output_format": r".jpeg",
        # Path to chrome driver, can be downloaded online [https://chromedriver.chromium.org/downloads]
        "chromedriverPATH": r"C://webdriver//chromedriver",
        # Path to browsermob-proxy, can be downloaded online [http://bmp.lightbody.net/]
        "browsermob-proxyPATH": r"C://Users//vital//AppData//Local//Programs//Python//Python310//Lib//site-packages//browsermobproxy//browsermob-proxy-2.1.4//bin//browsermob-proxy",
        # Path to TesseractOCR, can be downloaded online [https://github.com/tesseract-ocr/tesseract]
        "TesseractOCR_executable_path": r'C://Program Files//Tesseract-OCR//tesseract.exe'
    }
    __setters = ["passport", "password", "captcha_img_output_PATH", "captcha_img_output_format",
                 "chromedriverPATH", "browsermob-proxyPATH", "TesseractOCR_executable_path"]

    @staticmethod
    def get(name):
        return App.__conf[name]

    @staticmethod
    def set(name, value):
        if name in App.__setters:
            App.__conf[name] = value
        else:
            raise NameError("Name not accepted in set() method")
