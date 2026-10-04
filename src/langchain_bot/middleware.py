from datetime import datetime
from langchain.agents.middleware import wrap_model_call, wrap_tool_call  # 1.2.6

def _ts() -> str:
    """Generate a formatted timestamp string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

@wrap_model_call
def model_logging_middleware(request, handler):
    """Log model requests, their content context, and corresponding model responses."""
    messages = request.messages if hasattr(request, "messages") else []
    msg_count = len(messages)
    last_msg_preview = messages[-1].content if msg_count > 0 else "None"
    
    print(f"[{_ts()}] MODEL REQUEST: Processing {msg_count} messages. Last message preview: '{last_msg_preview}'")
    
    try:
        response = handler(request)

        last_msg = response.result[-1]
        res_content = getattr(last_msg, "content", "")
        tool_calls = getattr(last_msg, "tool_calls", [])
        
        print(f"[{_ts()}] MODEL RESPONSE: '{res_content}' | Tool Calls: {tool_calls}")
        return response
    except Exception as e:
        print(f"[{_ts()}] MODEL ERROR: {str(e)}")
        raise e

@wrap_tool_call
def tool_logging_middleware(request, handler):
    """Log targeted tool calls execution payloads and tracking responses."""
    tool_call = request.tool_call
    
    tool_name = tool_call.get("name", "unknown_tool")
    tool_input = tool_call.get("args", "")
    
    print(f"[{_ts()}] TOOL CALL -> Name: {tool_name} | Arguments: {tool_input}")
    
    try:
        result = handler(request)
        print(f"[{_ts()}] TOOL SUCCESS -> Name: {tool_name}")
        return result
    except Exception as e:
        print(f"[{_ts()}] TOOL ERROR -> Name: {tool_name} | Exception: {str(e)}")
        raise e

def get_logging_middleware() -> list:
    """Return the middleware chain list containing both logging functions."""
    return [model_logging_middleware, tool_logging_middleware]