import requests
from bs4 import BeautifulSoup
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


# utils
def log(*args):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} -", *args)


def artwork_key(artwork):
    return artwork['link']


# config
WEBSITE_URL = 'https://beruwko.com/'
FETCH_INTERVAL = 600

TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

GMAIL_SOURCE_MAIL = ""
GMAIL_SOURCE_PASSWORD_MAIL = ""
DESTINATION_MAIL = ""


# notifications
def send_telegram_chat(image_url, name, price, link):
    try:
        url_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        caption = f"<b>{name}</b> - {price}\n<a href=\"{link}\">Buy now</a>"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'photo': image_url,
            'caption': caption,
            'parse_mode': 'HTML'
        }
        r = requests.post(url_api, json=payload, timeout=10)
        if r.status_code == 200:
            log(f"Telegram photo sent: {name}")
        else:
            log(f"Telegram error: {r.status_code} - {r.text}")
    except Exception as e:
        log(f"error sending Telegram photo: {e}")


def send_email(subject, html_content):
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = GMAIL_SOURCE_MAIL
    msg['To'] = DESTINATION_MAIL
    msg.attach(MIMEText(html_content, 'html'))
    try:
        serveur = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        serveur.login(GMAIL_SOURCE_MAIL, GMAIL_SOURCE_PASSWORD_MAIL)
        serveur.send_message(msg)
        serveur.quit()
        log("e-mail sent")
    except Exception as e:
        log(f"e-mail error: {e}")


def notify_artwork(artwork):
    send_telegram_chat(
        artwork['image'],
        artwork['name'],
        artwork['price'],
        artwork['link']
    )
    # ...


def notify_artworks(artworks):
    for artwork in artworks:
        notify_artwork(artwork)


# scraping
def check_new_artwork():
    log("checking new artwork...")
    try:
        response = requests.get(WEBSITE_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        artworks = soup.find_all('div', class_='grid-product')

        available_artworks = []
        for artwork in artworks:
            buy_button = artwork.find('span', class_='form-control__button-text')
            if buy_button and "Buy Now" in buy_button.get_text():
                name_tag = artwork.find('div', class_='grid-product__title-inner')
                price_tag = artwork.find('div', class_='grid-product__price-value')
                img_tag = artwork.find('img', class_='grid-product__picture')
                link_tag = artwork.find('a', class_='grid-product__image')
                if name_tag and price_tag and img_tag and link_tag:
                    available_artworks.append({
                        'name': name_tag.get_text().strip(),
                        'price': price_tag.get_text().strip(),
                        'image': img_tag['src'],
                        'link': link_tag['href']
                    })
        return available_artworks
    except requests.exceptions.RequestException as e:
        log(f"connection error: {e}")
        return []


# main
def main():
    initial_artworks = check_new_artwork()

    initial_html_content = "<html><body>"
    if initial_artworks:
        log("--- currently available artworks ---")
        initial_html_content += "<h2>available artworks:</h2>"
        for o in initial_artworks:
            log(f"{o['name']} - {o['price']}")
            initial_html_content += f"<h3>{o['name']} - {o['price']}</h3>"
            initial_html_content += f"<img src='{o['image']}' alt='{o['name']}' style='width:300px;'><br><br>"
        notify_artworks(initial_artworks)
        initial_html_content += "</body></html>"
        send_email("available Beruwko artworks (script launch)", initial_html_content)
    else:
        log("--- no artwork available ---")
        initial_html_content += "<h2>no artwork currently available.</h2></body></html>"
        send_email("no Beruwko artwork available (script launch)", initial_html_content)

    seen_artworks = {artwork_key(o) for o in initial_artworks}

    while True:
        latest_artworks = check_new_artwork()
        new_artworks = [
            o for o in latest_artworks
            if artwork_key(o) not in seen_artworks
        ]

        if new_artworks:
            log("new artwork found!")
            html_content = "<html><body><h2>new artworks:</h2><br>"
            for o in new_artworks:
                html_content += f"<h3>{o['name']} - {o['price']}</h3>"
                html_content += f"<img src='{o['image']}' alt='{o['name']}' style='width:300px;'><br><br>"
            html_content += "</body></html>"

            notify_artworks(new_artworks)
            send_email("new Beruwko artworks!", html_content)

            seen_artworks.update(artwork_key(o) for o in new_artworks)
        else:
            log("no new artwork found")

        time.sleep(FETCH_INTERVAL)


if __name__ == "__main__":
    main()
