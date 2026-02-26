from typing import Annotated, Sequence, TypedDict, Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from .prompts import get_dynamic_context, get_static_system_prompt
from .state import AgentState

def build_graph(tools: Sequence[BaseTool], memory: AsyncSqliteSaver):
    llm = ChatOpenAI(model="gpt-5-mini", temperature=0)
    
    if tools:
        llm = llm.bind_tools(tools)

    async def call_model(state: AgentState):
        messages = state["messages"]
        
        sys_msg = SystemMessage(
            content=get_static_system_prompt(),
            additional_kwargs={"cache_control": {"type": "ephemeral"}} 
        )
        
        time_context = SystemMessage(content=get_dynamic_context())
        full_messages = [sys_msg, time_context] + messages
        
        response = await llm.ainvoke(full_messages)
        return {"messages": [response]}

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    
    if tools:
        tool_node = ToolNode(tools)
        workflow.add_node("tools", tool_node)
        
        def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
            last_message = state["messages"][-1]
            if last_message.tool_calls:
                return "tools"
            return "__end__"
            
        workflow.add_edge("tools", "agent")
        workflow.add_conditional_edges("agent", should_continue)
    else:
        workflow.add_edge("agent", END)

    workflow.add_edge(START, "agent")
    
    return workflow.compile(checkpointer=memory)