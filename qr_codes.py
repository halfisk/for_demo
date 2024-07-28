import qrcode

def generate_qr_code(category: str, bot_username: str) -> str:
    base_url = f"https://t.me/{bot_username}?start={category}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(base_url)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    img_path = f"{category}_qr.png"
    img.save(img_path)
    return img_path

def get_product_category(qr_code: str) -> str:
    categories = {
        'bed_linen': 'Постельное белье',
        'towel': 'Полотенца',
        'blanket': 'Пледы'
    }
    return categories.get(qr_code, 'Unknown category')

if __name__ == "__main__":
    bot_username = "MirrorSleep_customer_bot"  
    category = "blanket"  
    img_path = generate_qr_code(category, bot_username)
    print(f"QR-код сохранен по адресу: {img_path}")
