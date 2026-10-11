import serial
import time
import qrcode
import requests

from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode


# ==========================================
# MA STORE PYTHON BRIDGE
# Arduino Nano + RFID + Dynamic UPI QR
# Telegram Billing System
# ==========================================


# ==========================================
# SERIAL SETTINGS
# ==========================================

SERIAL_PORT = "COM5"
BAUD_RATE = 9600


# ==========================================
# TELEGRAM SETTINGS
# ==========================================

# Paste your replacement Telegram bot token here.
# Do not share active bot tokens publicly.

BOT_TOKEN = "8865444670:AAEfQESGnHJhSGDRVARfnNtpQrWqBqgGq2k"

CHAT_ID = "6041136088"


# ==========================================
# UPI SETTINGS
# ==========================================

UPI_ID = "ashwanthkumar188-1@okicici"

STORE_NAME = "MA STORE"


# ==========================================
# STORAGE
# ==========================================

QR_FOLDER = Path("ma_store_qr")

QR_FOLDER.mkdir(exist_ok=True)


# ==========================================
# TELEGRAM FUNCTIONS
# ==========================================

def send_telegram_photo(image_path, caption):

    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_NEW_BOT_TOKEN_HERE":

        print("ERROR: Configure BOT_TOKEN in the Python file.")

        return False

    url = (
        f"https://api.telegram.org/bot"
        f"{BOT_TOKEN}/sendPhoto"
    )

    try:

        with open(image_path, "rb") as photo:

            response = requests.post(

                url,

                data={
                    "chat_id": CHAT_ID,
                    "caption": caption
                },

                files={
                    "photo": photo
                },

                timeout=30
            )

        print("Telegram HTTP status:", response.status_code)

        print("Telegram response:", response.text)

        return response.ok

    except requests.RequestException as error:

        print("Telegram error:", error)

        return False


# ==========================================
# DYNAMIC UPI PAYMENT QR
# ==========================================

def generate_upi_qr(total, transaction_id):

    # Ensure the total is numeric and non-negative

    total = float(total)

    if total <= 0:

        raise ValueError(
            "Payment amount must be greater than zero."
        )

    # UPI payment parameters

    upi_params = {

        "pa": UPI_ID,

        "pn": STORE_NAME,

        "am": f"{total:.2f}",

        "cu": "INR",

        "tn": f"MA STORE {transaction_id}"

    }

    # Generate UPI payment URI

    upi_url = (

        "upi://pay?"

        + urlencode(upi_params)

    )

    print("\nUPI Payment URI:")

    print(upi_url)

    # Create QR code

    qr = qrcode.QRCode(

        version=None,

        error_correction=qrcode.constants.ERROR_CORRECT_M,

        box_size=10,

        border=4

    )

    qr.add_data(upi_url)

    qr.make(fit=True)

    image = qr.make_image(

        fill_color="black",

        back_color="white"

    )

    filename = QR_FOLDER / f"{transaction_id}_UPI.png"

    image.save(filename)

    print("UPI QR saved:", filename)

    return filename, upi_url


# ==========================================
# BILLING SUMMARY
# ==========================================

def create_bill(items, total, transaction_id):

    current_time = datetime.now().strftime(

        "%Y-%m-%d %H:%M:%S"

    )

    bill_text = (

        "MA STORE\n"

        f"Transaction ID: {transaction_id}\n"

        f"Date: {current_time}\n\n"

    )

    for item in items:

        bill_text += (

            f"{item['product']} | "

            f"UID: {item['uid']} | "

            f"Price: Rs.{item['price']} | "

            f"Qty: {item['qty']}\n"

        )

    bill_text += (

        f"\nTOTAL: Rs.{total:.2f}\n"

        f"UPI ID: {UPI_ID}\n"

        "Payment Status: Pending\n"

        "Thank you for shopping at MA STORE!"

    )

    return bill_text


# ==========================================
# PARSE CHECKOUT LINE
# ==========================================

def parse_checkout(line):

    # Expected format:
    #
    # CHECKOUT|TOTAL=150|ITEMS=FRUIT JUICE x1

    parts = line.strip().split("|")

    total = 0.0

    items_text = ""

    for part in parts:

        if part.startswith("TOTAL="):

            try:

                total = float(

                    part.split("=", 1)[1]

                )

            except ValueError:

                print("Invalid checkout total:", part)

                total = 0.0

        elif part.startswith("ITEMS="):

            items_text = part.split("=", 1)[1]

    return total, items_text


# ==========================================
# PARSE BILL ITEM
# ==========================================

def parse_bill_item(line):

    # Expected format:
    #
    # BILL_ITEM|UID=AA BB CC DD|
    # PRODUCT=Product 1|PRICE=50|QTY=1

    parts = line.strip().split("|")

    data = {}

    for part in parts:

        if "=" in part:

            key, value = part.split("=", 1)

            data[key] = value

    try:

        price = float(data.get("PRICE", "0"))

        quantity = int(data.get("QTY", "1"))

    except ValueError:

        print("Invalid bill item:", line)

        price = 0.0

        quantity = 1

    return {

        "uid": data.get("UID", "UNKNOWN"),

        "product": data.get("PRODUCT", "UNKNOWN"),

        "price": price,

        "qty": quantity

    }


# ==========================================
# VALIDATE CART
# ==========================================

def validate_cart(items, total):

    if not items:

        print("WARNING: No bill items received.")

        return False

    calculated_total = sum(

        item["price"] * item["qty"]

        for item in items

    )

    # Allow minor floating-point differences

    if abs(calculated_total - total) > 0.01:

        print("\nWARNING: Total mismatch!")

        print("Arduino total:", total)

        print("Calculated total:", calculated_total)

        print("Using Arduino-reported total.")

    return total > 0


# ==========================================
# SEND CHECKOUT TO TELEGRAM
# ==========================================

def process_checkout(total, items_text, items):

    if not validate_cart(items, total):

        print("Checkout validation failed.")

        return False

    transaction_id = datetime.now().strftime(

        "MA%Y%m%d%H%M%S"

    )

    # Create bill text

    bill_text = create_bill(

        items,

        total,

        transaction_id

    )

    # Generate dynamic UPI QR

    qr_path, upi_url = generate_upi_qr(

        total,

        transaction_id

    )

    # Telegram caption

    caption = (

        "🛒 MA STORE PAYMENT\n\n"

        f"Transaction ID: {transaction_id}\n"

        f"Total Amount: ₹{total:.2f}\n"

        f"UPI ID: {UPI_ID}\n\n"

    )

    if items:

        for item in items:

            caption += (

                f"📦 {item['product']}\n"

                f"UID: {item['uid']}\n"

                f"Price: ₹{item['price']:.2f}\n"

                f"Quantity: {item['qty']}\n\n"

            )

    else:

        caption += f"Items: {items_text}\n\n"

    caption += (

        "💳 Scan the QR code to pay.\n"

        "Payment Status: Pending"

    )

    # Send QR image to Telegram

    success = send_telegram_photo(

        qr_path,

        caption

    )

    if success:

        print("\nDynamic payment QR sent to Telegram.")

        print("UPI ID:", UPI_ID)

        print("Amount: ₹", f"{total:.2f}")

        print("Payment Status: Pending")

    else:

        print("\nFailed to send payment QR.")

    # Print payment URI

    print("\nPayment URI:")

    print(upi_url)

    return success


# ==========================================
# SERIAL BRIDGE
# ==========================================

def main():

    print("==========================================")

    print("       MA STORE PYTHON BRIDGE")

    print("==========================================")

    print("Starting...")

    try:

        ser = serial.Serial(

            SERIAL_PORT,

            BAUD_RATE,

            timeout=1

        )

    except serial.SerialException as error:

        print("Serial connection failed:", error)

        print("Check your USB port and Arduino connection.")

        return

    time.sleep(2)

    print("Connected to Arduino Nano.")

    print("Serial Port:", SERIAL_PORT)

    print("Baud Rate:", BAUD_RATE)

    print("Telegram Chat ID:", CHAT_ID)

    print("UPI ID:", UPI_ID)

    print("\nWaiting for RFID checkout...\n")

    # Current customer cart

    current_items = []

    current_total = 0.0

    current_items_text = ""

    checkout_received = False

    try:

        while True:

            raw_line = ser.readline()

            if not raw_line:

                continue

            line = raw_line.decode(

                "utf-8",

                errors="ignore"

            ).strip()

            if not line:

                continue

            print("Arduino:", line)

            # ---------- BILL ITEM ----------

            if line.startswith("BILL_ITEM|"):

                item = parse_bill_item(line)

                current_items.append(item)

                print(

                    f"Item collected: "

                    f"{item['product']} "

                    f"x{item['qty']}"

                )

            # ---------- CHECKOUT SUMMARY ----------

            elif line.startswith("CHECKOUT|"):

                total, items_text = parse_checkout(line)

                current_total = total

                current_items_text = items_text

                checkout_received = True

                print("\nCheckout detected.")

                print("Waiting for all bill items...")

            # ---------- CHECKOUT END ----------

            elif line == "CHECKOUT_END":

                if checkout_received:

                    print("\nAll bill items received.")

                    print("Total items:", len(current_items))

                    print("Generating dynamic UPI QR...")

                    process_checkout(

                        current_total,

                        current_items_text,

                        current_items

                    )

                    # Reset cart for next customer

                    current_items = []

                    current_total = 0.0

                    current_items_text = ""

                    checkout_received = False

                    print("\nReady for next customer.\n")

            # ---------- CARD UID ----------

            elif line.startswith("CARD_UID|"):

                uid = line.split("|", 1)[1]

                print("Card UID:", uid)

            # ---------- PRODUCT FOUND ----------

            elif line.startswith("PRODUCT_FOUND|"):

                print("Product detected:", line)

            # ---------- CART ADDED ----------

            elif line.startswith("CART_ADDED|"):

                print("Cart item added:", line)

            # ---------- CART UPDATED ----------

            elif line.startswith("CART_UPDATED|"):

                print("Cart item updated:", line)

            # ---------- EMPTY CHECKOUT ----------

            elif line == "CHECKOUT_EMPTY":

                print("Checkout requested but cart is empty.")

    except KeyboardInterrupt:

        print("\nStopping bridge...")

    finally:

        ser.close()

        print("Serial connection closed.")


# ==========================================
# PROGRAM START
# ==========================================

if __name__ == "__main__":

    main()