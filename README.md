# ⚡️ LINE Sticker ➡️ ezgif 轉檔神器 (sticker-to-gif)

> 一鍵解析 LINE 貼圖商店商品，動態 APNG 透過 ezgif 官方高畫質轉成循環 GIF，靜態無損下載 PNG，支援單張極速下載與全套 ZIP 打包！

🌐 **線上使用**：[https://louis-369.github.io/sticker-to-gif/](https://louis-369.github.io/sticker-to-gif/)  
⚙️ **後端算力**：[Hugging Face Space](https://huggingface.co/spaces/iiou8/sticker-backend)

---

## ✨ 核心特色

- 🎨 **APNG 轉 GIF**：100% 調用 `ezgif.com` 官方線上演算法，保證極致畫質、透明背景與無限循環。
- 🖼 **靜態 PNG**：自動識別非動態貼圖，提取原始高清無損透明 PNG。
- 🔄 **全自動預覽**：網頁載入時所有動態貼圖自動持續無限循環播放。
- 📋 **一鍵貼上**：輸入框支援一鍵讀取剪貼簿並自動開始解析。
- ⚡️ **單張 / 批次雙軌**：支援單張「⚡️ 轉 GIF」一秒下載，或勾選多張一鍵打包 ZIP。
- 📱 **跨平台自適應**：完美支援手機 Safari / 桌面瀏覽器，手機打開即可直接操作！

---

## 🛠 技術架構 (前後端分離)

- **前端**：Tailwind CSS + 原生 JavaScript，部署於 **GitHub Pages**。
- **後端**：FastAPI + Gradio + BeautifulSoup4，部署於 **Hugging Face Spaces (ZeroGPU Free)**。
- **自動化**：GitHub Actions 自動部署 CI/CD。
