# 算算 AI 国学工具箱

一个面向传统文化解读、AI 互动娱乐和个人生活建议的国学/易经/民俗文化工具箱。

## 功能

- 易经算卦：时间起卦、铜钱起卦、数字起卦、手动摇卦
- 卦象展示：本卦、变卦、互卦、错卦、综卦
- AI 问卜聊天：通过 DeepSeek `deepseek-v4-flash` 生成文化化解读
- 掷圣杯 / 筊杯：虚拟掷杯动画、圣杯/笑杯/阴杯、连续三次规则
- 手相 AI：上传手掌照片，本地预览并生成娱乐解读示例
- 面相 AI：上传照片，本地预览并输出合规的文化化描述
- 风水罗盘：八卦方位、二十四山、九宫飞星、户型图预览
- 国学内容库：易经、历法、五行、民俗、道教、风水知识卡片

## 技术栈

- FastAPI
- 原生 HTML / CSS / JavaScript
- DeepSeek Chat Completions API

## 本地启动

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

编辑 `.env`：

```env
SECRET_KEY=change_me_to_long_secret
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_MODEL=deepseek-v4-flash
```

启动：

```bash
uvicorn app.main:app --reload
```

打开：

```text
http://127.0.0.1:8000
```

## 部署

服务器安装依赖后运行：

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

生产环境建议使用 Nginx/Caddy 做反向代理，并通过系统服务或容器托管 Uvicorn。

## 安全说明

- `.env` 已加入 `.gitignore`，不要把 API Key 提交到公开仓库。
- 手相、面相模块当前只做本地预览与娱乐解读示例，不做身份识别。
- 所有解读仅供传统文化参考和互动娱乐，不替代医学、法律、财务或心理咨询。
