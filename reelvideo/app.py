from flask import Flask, request, jsonify, send_file, render_template
import os, uuid, requests, textwrap, traceback, re
from bs4 import BeautifulSoup
from gtts import gTTS
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from moviepy.video.fx import FadeIn, FadeOut
from PIL import Image, ImageDraw, ImageFont
import numpy as np

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
OUTPUT_FOLDER = "static/output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

W, H = 1080, 1920
FPS = 24
SLIDE_DURATION = 4.5
FADE_DURATION = 0.4


def clean_for_voice(text):
    text = re.sub(r'[✅✓●•►▶★☆♦◆→←↑↓>>]', '', text)
    text = re.sub(r'[^\w\s\.,!?;:\-\'\"\u0900-\u097f]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def scrape_product(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    r = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    title = ""
    for sel in ["h1", 'meta[property="og:title"]', 'meta[name="title"]', "title"]:
        tag = soup.select_one(sel)
        if tag:
            title = tag.get("content", "") or tag.get_text(strip=True)
            if title: break

    desc = ""
    for sel in ['meta[name="description"]', 'meta[property="og:description"]']:
        tag = soup.select_one(sel)
        if tag and tag.get("content"):
            desc = tag["content"]
            break

    price = ""
    for sel in ['span[class*="price"]', 'div[class*="price"]', 'span[class*="Price"]', 'span[id*="price"]']:
        tag = soup.select_one(sel)
        if tag:
            val = tag.get("content", "") or tag.get_text(strip=True)
            if val and re.search(r'[\d,]+', val):
                price = re.sub(r'\s+', ' ', val).strip()[:30]
                break

    features = []
    for sel in ['#feature-bullets li', '.a-unordered-list .a-list-item', 'ul[class*="feature"] li']:
        for item in soup.select(sel):
            t = item.get_text(strip=True)
            if t and 10 < len(t) < 120:
                features.append(t)
            if len(features) == 5: break
        if features: break

    if not features:
        for li in soup.find_all("li"):
            t = li.get_text(strip=True)
            if 15 < len(t) < 100:
                features.append(t)
            if len(features) == 5: break

    images = []
    for tag in soup.select('meta[property="og:image"]'):
        src = tag.get("content", "")
        if src and src.startswith("http"):
            images.append(src)

    for tag in soup.find_all("img"):
        src = tag.get("src", "") or tag.get("data-src", "")
        if src:
            if src.startswith("//"): src = "https:" + src
            elif src.startswith("/"):
                from urllib.parse import urlparse
                base = urlparse(url)
                src = f"{base.scheme}://{base.netloc}{src}"
            if src.startswith("http") and any(e in src.lower() for e in [".jpg", ".jpeg", ".png", ".webp"]):
                images.append(src)

    seen = set(); unique_imgs = []
    for img in images:
        if img not in seen:
            seen.add(img); unique_imgs.append(img)
        if len(unique_imgs) == 6: break

    return {
        "title": title[:80] if title else "Amazing Product",
        "description": desc[:200] if desc else "",
        "price": price,
        "features": features,
        "images": unique_imgs,
    }


def generate_script(product, lang):
    title = product["title"]
    desc = product["description"]
    price = product["price"]
    features = product["features"]

    if lang == "hi":
        slides = [f"{title}"]
        slides.append(desc[:90] if desc else "एक बेहतरीन प्रोडक्ट जो आपको पसंद आएगा!")
        for f in (features[:3] if features else ["उच्च गुणवत्ता और मजबूती", "आरामदायक और स्टाइलिश", "हर मौके के लिए परफेक्ट"]):
            slides.append(f[:80])
        if price: slides.append(f"कीमत सिर्फ {price}")
        slides.append("अभी ऑर्डर करें — स्टॉक सीमित है!")
        slides.append("आज ही अपना ऑर्डर प्लेस करें!")
    else:
        slides = [f"Introducing — {title}"]
        slides.append(desc[:90] if desc else "The product you have been waiting for!")
        for f in (features[:3] if features else ["Premium quality", "Stylish design", "Ultimate comfort"]):
            slides.append(f[:80])
        if price: slides.append(f"Price: {price}")
        slides.append("Don't miss out — limited stock!")
        slides.append("Order now and get it delivered fast!")

    while len(slides) < 6:
        slides.append("Order now!" if lang != "hi" else "अभी ऑर्डर करें!")
    return slides[:8]


def download_images(urls, folder):
    paths = []
    for i, url in enumerate(urls):
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if resp.status_code == 200 and len(resp.content) > 5000:
                path = os.path.join(folder, f"img_{i}.jpg")
                with open(path, "wb") as f: f.write(resp.content)
                img = Image.open(path); img.verify()
                paths.append(path)
        except Exception: pass
    return paths


def make_static_frame(img_path, caption, slide_num, total):
    canvas = Image.new("RGB", (W, H), (10, 10, 20))

    try:
        prod = Image.open(img_path).convert("RGB")
        img_area_h = int(H * 0.68)
        ratio = min(W / prod.width, img_area_h / prod.height)
        rw = int(prod.width * ratio)
        rh = int(prod.height * ratio)
        resized = prod.resize((rw, rh), Image.LANCZOS)
        canvas.paste(resized, ((W - rw) // 2, (img_area_h - rh) // 2))
    except Exception: pass

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    gy = int(H * 0.52)
    for row in range(gy, H):
        a = int(220 * ((row - gy) / (H - gy)) ** 0.55)
        ov.rectangle([(0, row), (W, row + 1)], fill=(8, 8, 18, a))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0, H - 420), (W, H)], fill=(8, 8, 18))
    for bx in range(W):
        rb = bx / W
        draw.rectangle([(bx, H - 422), (bx + 1, H - 415)],
                       fill=(int(255 - 50 * rb), int(80 - 50 * rb), int(30 + 90 * rb)))

    try:
        f_title = ImageFont.truetype("arialbd.ttf", 58)
        f_body = ImageFont.truetype("arial.ttf", 42)
    except:
        f_title = f_body = ImageFont.load_default()

    lines = textwrap.wrap(caption, width=22)
    y = H - 405
    for idx, line in enumerate(lines[:4]):
        font = f_title if idx == 0 else f_body
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2 + 2, y + 2), line, font=font, fill=(0, 0, 0))
        draw.text(((W - tw) // 2, y), line, font=font,
                  fill=(255, 255, 255) if idx == 0 else (210, 210, 230))
        y += 66 if idx == 0 else 52

    bar_y = H - 14
    draw.rectangle([(0, bar_y), (W, bar_y + 8)], fill=(25, 25, 45))
    pw = int(W * (slide_num + 1) / total)
    draw.rectangle([(0, bar_y), (pw, bar_y + 8)], fill=(255, 80, 30))

    dot_y = H - 36; dot_sp = 26
    sx = (W - total * dot_sp) // 2
    for d in range(total):
        cx = sx + d * dot_sp + dot_sp // 2
        if d == slide_num:
            draw.ellipse([(cx - 9, dot_y - 5), (cx + 9, dot_y + 5)], fill=(255, 80, 30))
        else:
            draw.ellipse([(cx - 4, dot_y - 4), (cx + 4, dot_y + 4)], fill=(70, 70, 90))

    return np.array(canvas)


def build_video(img_paths, captions, audio_path, output_path):
    while len(img_paths) < len(captions):
        img_paths = img_paths + img_paths
    img_paths = img_paths[:len(captions)]

    clips = []
    total = len(captions)

    for i, (img_path, caption) in enumerate(zip(img_paths, captions)):
        frame = make_static_frame(img_path, caption, i, total)
        clip = ImageClip(frame, duration=SLIDE_DURATION)
        clip = clip.with_effects([FadeIn(FADE_DURATION), FadeOut(FADE_DURATION)])
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose", padding=-FADE_DURATION)

    if os.path.exists(audio_path):
        audio = AudioFileClip(audio_path)
        if audio.duration > video.duration:
            audio = audio.subclipped(0, video.duration)
        video = video.with_audio(audio)

    video.write_videofile(output_path, fps=FPS, codec="libx264",
                          audio_codec="aac", logger=None)
    return output_path


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    url = data.get("url", "").strip()
    lang = data.get("lang", "en")
    custom_text = data.get("custom_text", "").strip()

    print(f"DEBUG - lang:{lang} | custom_text_len:{len(custom_text)}")
    print(f"DEBUG - custom_text preview: {custom_text[:80]}")

    if not url:
        return jsonify({"error": "URL required"}), 400

    job_id = str(uuid.uuid4())[:8]
    job_folder = os.path.join(UPLOAD_FOLDER, job_id)
    os.makedirs(job_folder, exist_ok=True)

    try:
        product = scrape_product(url)
        print(f"DEBUG - title:{product['title']} | images:{len(product['images'])}")

        if not product["images"]:
            return jsonify({"error": "No images found. Try another product URL."}), 400

        img_paths = download_images(product["images"], job_folder)
        if not img_paths:
            return jsonify({"error": "Could not download images."}), 400

        # Custom text use karo agar diya ho
        if custom_text:
            slides = [l.strip() for l in custom_text.splitlines() if l.strip()]
            print(f"DEBUG - Using CUSTOM text, slides: {len(slides)}")
        else:
            slides = generate_script(product, lang)
            print(f"DEBUG - Using AUTO text, slides: {len(slides)}")

        slides = slides[:8]
        while len(slides) < 4:
            slides.append("Order now!" if lang != "hi" else "अभी ऑर्डर करें!")

        voice_lines = [clean_for_voice(s) for s in slides]
        full_script = " ... ".join(voice_lines)
        print(f"DEBUG - Voice script: {full_script[:100]}")

        tts = gTTS(text=full_script, lang=lang, slow=False)
        audio_path = os.path.join(job_folder, "voice.mp3")
        tts.save(audio_path)

        output_path = os.path.join(OUTPUT_FOLDER, f"{job_id}.mp4")
        build_video(img_paths, slides, audio_path, output_path)

        return jsonify({
            "success": True,
            "title": product["title"],
            "video_url": f"/download/{job_id}",
            "images_used": len(img_paths),
            "slides": len(slides),
            "duration": f"{int(len(slides) * SLIDE_DURATION)} seconds",
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/download/<job_id>")
def download(job_id):
    path = os.path.join(OUTPUT_FOLDER, f"{job_id}.mp4")
    if not os.path.exists(path):
        return "Not found", 404
    return send_file(path, as_attachment=True, download_name="product_reel.mp4")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
