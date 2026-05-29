# 🎙️ TalkCalendar — 语音日历工具

基于 Vue 3 + FastAPI 的语音交互日历管理工具，通过自然语言语音输入实现事件的增删查改。

## 功能

- 📅 **月视图 / 周视图** — 切换自如，点击创建事件
- 🎤 **语音输入** — 讯飞 ASR 语音识别 + NLP 智能语义解析
- 🧠 **智能解析** — "明天下午三点和产品开会" 自动提取日期、时间、标题
- ⚠️ **冲突检测** — 新建事件自动检测时间重叠
- 🔄 **周期性事件** — "每周一早九点站会" 自动识别重复规则
- 🔔 **浏览器通知** — 事件开始前 5 分钟弹窗提醒
- 📦 **本地存储** — IndexedDB 浏览器本地持久化

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Pinia + dayjs |
| 后端 | Python FastAPI |
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

### 讯飞 API 配置

设置环境变量启用真实语音识别（不配置则使用 mock 模式）：

```bash
export IFLYTEK_APP_ID="你的AppID"
export IFLYTEK_API_KEY="你的APIKey"
export IFLYTEK_API_SECRET="你的APISecret"
```

或在 `backend/services/iflytek.py` 中直接修改默认值。

## 语音操作示例

| 说 | 效果 |
|---|---|
| "明天下午三点和产品开会" | 创建明天15:00的事件 |
| "周五有什么安排" | 查询周五事件 |
| "取消明天的会议" | 删除匹配事件 |
| "每周一早九点站会" | 创建周期性事件 |

## 项目结构

```
TalkCalendar/
├── frontend/          # Vue 3 SPA
│   ├── src/
│   │   ├── components/   # CalendarGrid, WeekView, VoicePanel...
│   │   ├── composables/  # useVoiceRecorder, useVoiceAssistant...
│   │   ├── stores/       # Pinia 日历状态
│   │   └── utils/        # IndexedDB, 日期工具
│   └── package.json
├── backend/           # FastAPI
│   ├── main.py
│   ├── routers/       # ASR, NLP 路由
│   └── services/      # 讯飞 SDK, 语义解析
└── README.md
```
