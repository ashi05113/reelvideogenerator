# 🎬 ReelForge — Product Video Generator (Beginner Edition)

Turn any product URL into a 9:16 reel MP4 automatically.

---

## 🗂 Project Structure

```
reelvideo/
├── app.py               ← Flask backend (main file)
├── requirements.txt     ← Python dependencies
├── templates/
│   └── index.html       ← Frontend UI
└── static/
    ├── uploads/         ← Temp scraped images (auto-created)
    └── output/          ← Generated MP4 files (auto-created)
```

---

## ⚙️ Setup (Step by Step)

### 1. Install FFmpeg (required for video)

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg -y
```

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html and add to PATH.

---

### 2. Create a Python virtual environment

```bash
cd reelvideo
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
python app.py
```

Open your browser: **http://localhost:5000**

---

## 🚀 How It Works

```
Product URL
   ↓
Fetch Product Image + Title   (requests + BeautifulSoup)
   ↓
Generate Short Script          (template-based)
   ↓
Generate Voiceover             (gTTS)
   ↓
Create Slideshow Video         (MoviePy + Pillow)
   ↓
Export MP4  ✅
```

---

## ✅ Features (v1 Beginner)

- 3–4 product images per reel
- Fade transitions between slides
- Caption text overlays on each slide
- English or Hindi AI voiceover
- 9:16 reel format (1080×1920)
- One-click MP4 download

---

## 🛠 Tech Stack

| Layer    | Library            |
|----------|--------------------|
| Backend  | Flask              |
| Scraping | BeautifulSoup, requests |
| Voice    | gTTS               |
| Video    | MoviePy + FFmpeg   |
| Images   | Pillow (PIL)       |
| Frontend | HTML + CSS + JS    |

---

## ⚠️ Notes

- Some product sites block scrapers. Try Amazon, Flipkart, Myntra, or any open product page.
- Video generation takes 15–60 seconds depending on your machine.
- For heavy usage, consider adding a task queue (Celery + Redis) in v2.

---

## 🔮 Upgrade Path (v2 Ideas)

- Gemini/GPT for smarter captions
- Background music mixing
- Custom fonts / brand colors
- WhatsApp / social share buttons
- Batch URL processing
