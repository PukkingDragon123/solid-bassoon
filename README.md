# ศาลาเซียมซี · Sala Siamsee

เซียมซีออนไลน์ที่ให้คุณ **เดินเข้าวัด จุดเทียน จุดธูป ตั้งจิตอธิษฐาน แล้วเขย่ากระบอกเซียมซี** เหมือนไปวัดจริง
พร้อมใบเซียมซีครบ ๒๘ ใบ ตามแบบไทยโบราณ

An online Thai fortune-stick (เซียมซี) app you walk through like a real temple visit:
enter the hall, light a candle, light three incense sticks from its flame, hold to pray,
plant the incense, then shake the bamboo tube until a stick falls out.

---

## เล่นเลย · Run it

```bash
npm start          # → http://localhost:8080
```

ไม่มี build step ไม่มี dependency — เป็น ES modules ล้วน ๆ เปิดด้วย static server อะไรก็ได้
No build step and no runtime dependencies: plain ES modules, served by any static server.
`npm start` uses a zero-dependency Node server (`tools/serve.mjs`).

Deploying: push to `main` and the included GitHub Pages workflow publishes the repository root as-is.

---

## ขั้นตอนในแอป · The ritual

| ฉาก | สิ่งที่ทำ |
|---|---|
| ๑ หน้าวัด | เอียงเครื่อง/เลื่อนเมาส์เพื่อมองรอบ ๆ แล้วแตะ “เข้าวัด” |
| ๒ วิหาร | แตะเทียนเพื่อจุด → ลากธูปไปจ่อเปลวเทียน → กดค้างเพื่อจบธูปอธิษฐาน → ลากไปปักกระถาง |
| ๓ เขย่าเซียมซี | ลากกระบอกขึ้นลง หรือ **เขย่าเครื่องจริง** (DeviceMotion) จนไม้หล่น |
| ๔ ตู้ใบเซียมซี | ลิ้นชักเลขที่ได้เลื่อนออก ใบเซียมซีลอยขึ้นมา |
| ๕ คำทำนาย | อ่านคำทำนายเต็ม แล้วบันทึกเป็นรูปหรือแชร์ได้ |

ทุกใบมี: โคลงสี่บท, คำทำนายรวม, และคำทำนายราย ๗ ด้าน — การงาน การเงิน ความรัก สุขภาพ
การเดินทาง ของหาย คดีความ — พร้อมคำแนะนำ/แก้เคล็ด สีมงคล และเลขมงคล

การสุ่มใช้ `crypto.getRandomValues` แบบ rejection sampling จึงได้ทั้ง ๒๘ ใบด้วยโอกาสเท่ากันจริง
Slips are drawn with the platform CSPRNG using rejection sampling, so all 28 are exactly equally likely.

> เซียมซีนี้จัดทำขึ้นเพื่อความบันเทิงและเป็นกำลังใจ · For entertainment and encouragement.

---

## ภาพในแอป · The artwork

ภาพทุกใบใน `assets/` เป็นไฟล์ **PNG จริง** ที่ *เรนเดอร์ขึ้นมาเอง* ด้วย Python + NumPy + Pillow
ไม่ได้วาดด้วย CSS และไม่ได้ดึงมาจากอินเทอร์เน็ต

Every file in `assets/` is a real PNG, rendered from scratch by the renderer in `tools/artgen/`
— not CSS shapes, not stock photography. It is a small painting engine:

| module | what it does |
|---|---|
| `core.py` | gradients in linear light, fractal noise, float-precision blur, bloom, ACES tonemap, grain-free dithering |
| `thai.py` | Thai temple forms as point lists — kanok flame ornament, chofa, bai raka, naga, chedi, prang, lotus pedestals, Garuda, and a Sukhothai-style seated Buddha |
| `paint.py` | material + lighting compositor: fake normals from mask gradients, specular, rim light, contact shadow, and a colour ramp driven by the light so gold shadows go amber rather than grey |
| `scenes.py` | the composed scenes, including a one-point-perspective hall interior |
| `props.py` | the ritual props as transparent PNGs |

```bash
npm run assets                       # render everything (~4 min on 4 cores)
python3 tools/render_assets.py gate  # or just what you are iterating on
```

Scenes are composed twice — a 16:9 plate and a tall portrait plate — because cropping
16:9 art to a 9:19.5 phone throws away two thirds of the temple. The app picks the set
that matches the viewport.

### เปลี่ยนเป็นภาพถ่ายจริง (AI) · Swapping in photoreal images

หากต้องการใช้ภาพถ่ายจริงหรือภาพจากโมเดล AI แทน มี prompt เตรียมไว้ครบทุกภาพแล้ว:

```bash
python3 tools/install_ai_asset.py                       # list every asset key
python3 tools/install_ai_asset.py props/buddha          # print its prompt
python3 tools/install_ai_asset.py props/buddha out.png  # install it
```

`tools/ai-assets.json` carries a photoreal prompt, the exact target size, and whether the
asset needs alpha, for all 21 keys. The installer cover-crops and resizes to the exact
dimensions the app expects, so **no code changes are needed** — the app keeps loading the
same filenames.

Assets that need transparency (`"alpha": true`) should be generated with a transparent
background or run through a background remover before installing.

---

## โครงสร้าง · Layout

```
index.html            scene shells
styles/               base tokens · scenes · controls · the reading sheet
src/
  main.js             preload, wiring, chrome
  router.js           cross-fade scene switching
  state.js            draw, history, prefs (localStorage)
  audio.js            every sound synthesised — bell, gong, stick rattle, match, paper
  fx.js               canvas particles: incense smoke, embers, dust, fireflies
  parallax.js         pointer + device-tilt parallax
  scenes/             gate · shrine · shake · drawer · reading
  data/fortunes.js    the 28 slips
assets/               rendered PNGs
tools/                the art renderer, the AI swap pipeline, the dev server
```

Sound is synthesised with the Web Audio API (no audio files ship). Haptics use
`navigator.vibrate` where available. `prefers-reduced-motion` is respected throughout,
and the sound toggle also governs haptics.

## License

MIT
