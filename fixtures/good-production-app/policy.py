def guardrail(tool_call):
    permission_check(tool_call)
    return True
