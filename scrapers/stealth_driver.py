# ============================================================================
# ULTRA STEALTH SILENT CHROME DRIVER
# ============================================================================

import random
import os
import undetected_chromedriver as uc


class StealthChromeDriver:

    @staticmethod
    def create_driver(config):

        # Hide console spam
        os.environ["WDM_LOG_LEVEL"] = "0"
        os.environ["UC_LOG_LEVEL"] = "0"

        options = uc.ChromeOptions()

        # =============================
        # TRUE BACKGROUND MODE
        # =============================
        options.add_argument("--headless=new")

        # =============================
        # HIDE DEVTOOLS LOGS
        # =============================
        options.add_argument("--log-level=3")
        options.add_argument("--disable-logging")
        options.add_argument("--silent")

        # =============================
        # PERFORMANCE + STABILITY
        # =============================
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # =============================
        # DISABLE CHROME BACKGROUND NOISE
        # =============================
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--disable-sync")

        # =============================
        # HUMAN WINDOW SIZE
        # =============================
        width = random.choice([1920, 1600, 1366])
        height = random.choice([1080, 900, 768])
        options.add_argument(f"--window-size={width},{height}")

        # =============================
        # USER AGENT
        # =============================
        options.add_argument(f"user-agent={config['user_agent']}")

        # =============================
        # ANTI DETECTION
        # =============================
        options.add_argument("--disable-blink-features=AutomationControlled")

        driver = uc.Chrome(
            options=options,
            headless=True,
            use_subprocess=True,
            log_level=3
        )

        # Extra stealth JS patch
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        return driver
