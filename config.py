from dotenv import dotenv_values

config = dotenv_values(f"../.env")
TEMP_MAIL_API_KEY = config.get("TEMP_MAIL_API_KEY")
ANTI_CAPTCHA_API_KEY = config.get("ANTI_CAPTCHA_API_KEY")
HEADLESS = bool(config.get("HEADLESS"))
GECKO_DRIVER_PATH = config.get("GECKO_DRIVER_PATH")
