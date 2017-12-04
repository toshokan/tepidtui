# Hold "global variables"

# TepidConnection
t = None

# urwid MainLoop object
loop = None

# View names for status indicator
_view_stack_names = [None,
                     "main  ",
                     "me    ",
                     "lookup",
                     "queues",
                     "info  "]

# List to use as a stack of views
_view_stack = [None, [], [], [], [], []]

# Index of the current view
_view_index = 0
