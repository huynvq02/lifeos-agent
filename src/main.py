import os
import asyncio
import logging
import time
from dotenv import load_dotenv

import nest_asyncio
nest_asyncio.apply()

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from notion_mcp.client import NotionMCPManager
from agent.graph import build_graph
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.errors import GraphRecursionError
import aiosqlite

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

mcp_manager = None
agent_graph = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = """Xin chào! 👋 Mình là *LifeOS Assistant* của bạn!

Mình là một trợ lý AI được tích hợp với *Notion workspace* của bạn, chuyên giúp bạn:

📋 *Quản lý công việc*
- Xem danh sách task hôm nay
- Cập nhật trạng thái task (Todo → Done)
- Lên kế hoạch trong ngày

🎯 *Quản lý dự án*
- Theo dõi tiến độ Projects
- Phân chia dự án thành các task nhỏ

🌿 *Quản lý thói quen & cuộc sống*
- Theo dõi Habits
- Quản lý các Area trong cuộc sống (Sức khỏe, Công việc, Cá nhân)

---

Bạn muốn bắt đầu với điều gì hôm nay? 😊
Ví dụ: _"Cho mình xem task hôm nay"_ hoặc _"Lên kế hoạch cho ngày hôm nay"_"""
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    reply_msg = None
    logger.info(f"User saying: {user_text}")
    
    if not agent_graph:
        reply_msg = await update.message.reply_text("Agent is still initializing, please wait...")
        return
        
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    try:
        reply_msg = await update.message.reply_text("⏳ Đang xử lý...", parse_mode="Markdown")
        state = {"messages": [HumanMessage(content=user_text)]}
        config = {
            "configurable": {"thread_id": str(update.effective_chat.id)},
            "recursion_limit": 15
        }
        
        current_text = ""
        last_edit_time = time.time()
        current_message_id = None
        tool_call_announced = False
        
        async for msg, metadata in agent_graph.astream(state, config=config, stream_mode="messages"):
            if metadata.get("langgraph_node") == "agent":
                if msg.id != current_message_id:
                    current_message_id = msg.id
                    current_text = ""
                    tool_call_announced = False
                
                # Show status when agent decides to call a tool
                if hasattr(msg, "tool_call_chunks") and msg.tool_call_chunks:
                    if not tool_call_announced:
                        await reply_msg.edit_text("🛠 Đang truy xuất Notion...")
                        tool_call_announced = True
                        last_edit_time = time.time()
                        
                if msg.content:
                    if isinstance(msg.content, str):
                        current_text += msg.content
                    elif isinstance(msg.content, list):
                        for block in msg.content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                current_text += block.get("text", "")
                                
                    if time.time() - last_edit_time > 1.5 and current_text.strip():
                        try:
                            await reply_msg.edit_text(current_text + " ⏳")
                            last_edit_time = time.time()
                        except Exception:
                            pass
                            
        # Final response output with safe Markdown conversion
        if current_text.strip():
            formatted_text = current_text.replace("**", "*")
            try:
                await reply_msg.edit_text(formatted_text, parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"Markdown parse error: {e}")
                await reply_msg.edit_text(current_text)
                
    except GraphRecursionError:
        logger.error("Circuit breaker triggered: recursion limit reached")
        err_msg = "⚠️ **Ngắt Mạch (Circuit Breaker)**: Quá trình bị ngắt tự động do lỗi liên kết hoặc vòng lặp. Vui lòng kiểm tra lại yêu cầu của bạn!"
        if 'reply_msg' in locals() and reply_msg:
            try:
                await reply_msg.edit_text(err_msg, parse_mode="Markdown")
            except Exception:
                pass
        else:
            await update.message.reply_text(err_msg, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Error invoking agent graph: {e}")
        err_msg = "Xin lỗi, mình gặp lỗi khi xử lý yêu cầu của bạn 😢"
        if 'reply_msg' in locals() and reply_msg:
            try:
                await reply_msg.edit_text(err_msg)
            except Exception:
                pass
        else:
            await update.message.reply_text(err_msg)

async def initialize_app():
    global mcp_manager, agent_graph
    logger.info("Initializing Notion MCP Manager...")
    mcp_manager = NotionMCPManager()
    tools = await mcp_manager.initialize()
    logger.info(f"Loaded {len(tools)} tools from Notion MCP.")
    
    conn = aiosqlite.connect("lifeos_memory.sqlite", check_same_thread=False)
    memory = AsyncSqliteSaver(conn)
    logger.info("Building LangGraph agent...")
    agent_graph = build_graph(tools, memory)

async def main():
    await initialize_app()
    
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment. Please set it in .env")
        if mcp_manager:
            await mcp_manager.cleanup()
        return

    logger.info("Starting Telegram Bot...")
    app = ApplicationBuilder().token(telegram_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    logger.info("Bot is running. Press Ctrl+C to stop.")
    
    try:
        stop_event = asyncio.Event()
        await stop_event.wait()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        if mcp_manager:
            logger.info("Cleaning up Notion MCP Manager...")
            await mcp_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
