import tcfg


def view_widget(widget, stack_index=None, visit=False):
    """Add a widget to the appropriate view stack"""
    if not stack_index:
        stack_index = tcfg._view_index
    tcfg._view_stack[stack_index].append(widget)
    if visit:
        change_view(stack_index)


def back_widget(alternate_stack=None):
    """Remove a widget from the appropriate view stack"""
    stack = tcfg._view_index
    if alternate_stack:
        stack = alternate_stack
    if len(tcfg._view_stack[stack]) < 2:
        return
    tcfg._view_stack[stack].pop()
    change_view(stack)


def change_view(stack_index):
    """Change the view to the top level widget on the given stack"""
    if len(tcfg._view_stack[stack_index]) < 1:
        return
    tcfg._view_index = stack_index
    tcfg.loop.widget.change_widget(tcfg._view_stack[tcfg._view_index][-1])
