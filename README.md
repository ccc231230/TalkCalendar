# 🎙️ TalkCalendar — 语音日历工具

基于 Vue 3 + FastAPI 的语音交互日历管理工具，通过自然语言语音输入实现事件的增删查改。

## 功能

- 📅 **月视图 / 周视图** — 切换自如，点击创建事件
- 💬 **AI 对话面板** — 文字/语音输入，自然语言交互
- 🎤 **语音输入** — 讯飞 ASR 语音识别 + NLP 智能语义解析
- 🧠 **智能解析** — "明天下午三点和产品开会" 自动提取日期、时间、标题
- ⚡ **规则引擎** — 查询/删除类指令本地即时响应，不依赖 LLM
- 📊 **表格展示** — 查询日程以表格形式清晰列出
- ⚠️ **冲突检测** — 新建事件自动检测时间重叠
- 🔄 **周期性事件** — "每周一早九点站会" 自动识别重复规则
- 🕐 **时区修正** — 自动处理 UTC/本地时间转换，显示正确时间
- 🔔 **浏览器通知** — 事件开始前 5 分钟弹窗提醒
- 📦 **本地存储** — IndexedDB 浏览器本地持久化

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Pinia + dayjs |
| 后端 | Python FastAPI |
| AI | OpenAI 兼容 API（Moonshot/Kimi 等） |
| 语音 | 讯飞语音听写 API |
| 存储 | IndexedDB（浏览器本地） |

## 启动

### 后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173

### LLM 配置

在 `backend/.env` 中配置 OpenAI 兼容的 API：

```env
LLM_API_KEY=你的APIKey
LLM_BASE_URL=https://api.moonshot.cn/v1
LLM_MODEL=kimi-k2.5
```

不配置 LLM 时，创建事件等复杂操作使用本地规则引擎。

### 讯飞 API 配置

设置环境变量启用真实语音识别（不配置则使用 mock 模式）：

```bash
export IFLYTEK_APP_ID="你的AppID"
export IFLYTEK_API_KEY="你的APIKey"
export IFLYTEK_API_SECRET="你的APISecret"
```

## 语音操作示例

| 说 | 效果 |
|---|---|
| "明天下午三点和产品开会" | 创建明天15:00的事件 |
| "今天有什么安排" | 查询今天事件（表格展示） |
| "取消明天的会议" | 模糊匹配并确认删除 |
| "每周一早九点站会" | 创建周期性事件（下周一 09:00） |
| "下周一上午十点站会" | 创建下下周一的站会 |
| "周三有什么事" | 查询周三安排 |
| "本周找个2小时深度工作时间" | 查找空闲时段 |

## 项目结构

```
TalkCalendar/
├── frontend/          # Vue 3 SPA
│   ├── src/
│   │   ├── components/   # CalendarGrid, WeekView, ChatPanel, EventModal...
│   │   ├── composables/  # useVoiceRecorder, useVoiceAssistant, useNotifications
│   │   ├── stores/       # Pinia 日历状态
│   │   └── utils/        # IndexedDB, 日期工具
│   └── package.json
├── backend/           # FastAPI
│   ├── main.py
│   ├── routers/       # ASR, NLP, Dialogue, Scheduler 路由
│   └── services/      # 讯飞 SDK, 语义解析, 对话引擎, 排期引擎
└── README.md
```
