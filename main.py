from Tepid_Connection import Tepid_Connection
import tcfg
import tptui_util
from widgets import TepidWidgets
from getpass import getpass
import urwid


def login_wrap():
    shortuser = input("Enter your McGill short username: ")
    password = getpass("Enter your password: ")
    print()
    return Tepid_Connection(shortuser, password)


def quit(caller):
    raise urwid.ExitMainLoop()


def initialize_widgets():
    if not tcfg.t:
        return
    mv = TepidWidgets.MainView()
    frame = TepidWidgets.MainFrame(mv)
    uv = build_ui_widget()
    tptui_util.view_widget(uv, 2)
    usf = TepidWidgets.UserSearchForm()
    fi = TepidWidgets.FillWrapper(usf)
    tptui_util.view_widget(fi, 3)
    tptui_util.view_widget(
        TepidWidgets.InfoWidget(), 5)
    tptui_util.view_widget(
        TepidWidgets.VeryLongQueueView(), 4)
    tcfg.loop.widget = frame
    tptui_util.view_widget(mv, 1, visit=True)


def build_ui_widget(filled=False):
    u = tcfg.t.user_lookup_obj(tcfg.t.user_data['user']['shortUser'])
    uv = TepidWidgets.UserInfoView(u, filled)
    if not filled:
        f = TepidWidgets.FillWrapper(uv)
        return f
    return uv


def master_keyhandler(key):
    if key in ('q', 'Q'):
        raise urwid.ExitMainLoop()
    elif key == "meta 1":
        tptui_util.change_view(1)
    elif key == "meta 2":
        tptui_util.change_view(2)
    elif key == "meta 3":
        tptui_util.change_view(3)
    elif key == "meta 4":
        tptui_util.change_view(4)
    elif key == "meta 5":
        tptui_util.change_view(5)
    elif key == "backspace":
        tptui_util.back_widget()
    elif key == "meta 0":       # debug
        raise ValueError(tcfg._view_stack)


def loginform_wrap(username, password):
    tcfg.t = Tepid_Connection(username, password)
    initialize_widgets()


def login(caller):
    tcfg.loop.widget = TepidWidgets.LoginForm(loginform_wrap)


div = urwid.Divider()
txt1 = urwid.Text("Welcome to CTF", align='center')
txt2 = urwid.Text("Please Authenticate", align='center')
b1 = urwid.Button("Login", on_press=login)
b2 = urwid.Button("Quit", on_press=quit)
button_row = urwid.Columns([b1, b2], focus_column=0)
browpad = urwid.Padding(button_row, width=30, align='center')
pl = urwid.Pile([div, txt1, txt2, div, browpad], focus_item=browpad)
lb = urwid.LineBox(pl, title="TEPID TUI")
f = urwid.Filler(lb)

palette = [('footer', 'black', 'light gray', 'standout'),
           ('error_heading', 'black', 'dark red'),
           ('status_focused', 'white', 'dark blue'),
           ('status_unfocused', 'black', 'brown'),
           ('pd_status_up', 'light green', ''),
           ('pd_status_down', 'light red', ''),
           ('job_status_failed', 'light red', ''),
           ('underline', 'white, underline', ''),
           ('focus_cursor_line', 'black', 'light gray'),
           ('focus_cursor_line_failed', 'dark red', 'light gray')]

tcfg.loop = urwid.MainLoop(f, palette, unhandled_input=master_keyhandler)

tcfg.loop.screen.set_terminal_properties(colors=256, has_underline=True)
tcfg.loop.run()
