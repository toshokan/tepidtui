import Tepid_Connection
import tcfg
import tptui_util
import urwid
import datetime


class PrinterStatusWidget(urwid.WidgetWrap):
    _selectable = True
    signals = ['form_complete']

    def __init__(self, pd):
        self.down_message = ''
        self.pd = pd
        w = self._build_widget()
        urwid.WidgetWrap.__init__(self, w)

    def _build_widget(self):
        pd = self.pd
        title = urwid.Text(pd.name, align='center')
        if pd.up:
            title = urwid.AttrMap(
                title, 'pd_status_up', focus_map='focus_cursor_line')
        else:
            title = urwid.AttrMap(
                title, 'pd_status_down', focus_map='focus_cursor_line_failed')
        pile = urwid.Pile([title])
        return pile

    def selectable(self):
        return True

    def reload_widget(self):
        w = self._build_widget()
        self._w = w
        self._invalidate()

    def down_form(self):
        w = PrinterMarkForm(self)
        urwid.connect_signal(w, 'form_complete',
                             callback=self.form_complete_callback)
        tcfg.loop.widget = w
        tcfg.loop.draw_screen()

    def form_complete_callback(self, caller=None):
        self.pd.mark_down(self.down_message, tcfg.t)
        self.reload_widget()

    def keypress(self, size, key):
        if key == 'd':
            if self.pd.up:
                self.down_form()
        elif key == 'D':
            self.pd.mark_up(tcfg.t)
            self.reload_widget()
        return key


class PrinterMarkForm(urwid.WidgetWrap):
    signals = ['form_complete']

    def __init__(self, caller):
        self.caller = caller
        header = urwid.Padding(urwid.Text("Mark Printer Down"))
        header = urwid.AttrMap(header, 'footer')
        prompt = urwid.Text("Reason:")
        self.edit = urwid.Edit()
        self.bottom_w = tcfg.loop.widget

        button_ok = urwid.Button('OK', on_press=self.save_message)
        button_cancel = urwid.Button('Cancel', on_press=self.close)
        buttons = urwid.Columns([
            urwid.Divider(),
            (6, button_ok),
            (10, button_cancel),
            urwid.Divider()])

        pile = urwid.Pile([header,
                           urwid.Divider(),
                           prompt,
                           self.edit,
                           buttons])
        linebox = urwid.LineBox(pile)
        f = urwid.Filler(linebox)
        o = urwid.Overlay(f, self.bottom_w, align='center', valign='middle',
                          width=60, height=10)
        urwid.WidgetWrap.__init__(self, o)

    def save_message(self, calling_button=None):
        self.caller.down_message = self.edit.get_edit_text()
        self._emit('form_complete')
        self.close()

    def close(self, calling_button=None):
        tcfg.loop.widget = self.bottom_w


class QueueStatusWidget(urwid.WidgetWrap):
    def __init__(self, name, queue_list):
        queue_name = urwid.Text(name, align='center')
        printer_status_widgets = []
        for pd in queue_list[name]:
            printer_status_widgets.append(PrinterStatusWidget(pd))
        listwalker = urwid.SimpleFocusListWalker(printer_status_widgets)
        listbox = urwid.ListBox(listwalker)
        bx = urwid.BoxAdapter(listbox, height=2)
        pile = urwid.Pile([queue_name, bx])
        urwid.WidgetWrap.__init__(self, pile)


class QueueStatusListWidget(urwid.WidgetWrap):
    def __init__(self, queue_list):
        queue_status_widgets = []
        for name in sorted(queue_list):
            queue_status_widgets.append(QueueStatusWidget(name, queue_list))
        cols = urwid.Columns(queue_status_widgets)
        linebox = urwid.LineBox(cols)
        urwid.WidgetWrap.__init__(self, linebox)


class JobRowWidget(urwid.WidgetWrap):
    def __init__(self, j):
        username = urwid.Text(j.user)
        num_pages_str = str(
            j.pages) if j.colour_pages == 0 else '{} ({} colour)'.format(
                j.pages, j.colour_pages)
        pages = urwid.Text(num_pages_str, align='center')
        status_str = "Failed" if j.error != "" else \
                                            "Printed" if not j.refunded else \
                                            "Refunded"
        status = urwid.Text(status_str, align='right')
        cols = urwid.Columns([username, pages, status])
        urwid.WidgetWrap.__init__(self, cols)


class QueueJobListWidget(urwid.WidgetWrap):
    def __init__(self, name):
        user_title = urwid.Text("User")
        page_title = urwid.Text("Pages", align='center')
        status_title = urwid.Text("Status", align='right')
        title_cols = urwid.Columns([user_title, page_title, status_title])

        q = tcfg.t.get_queue(name)
        job_row_widgets = []
        for j in range(0, min(9, len(q))):
            job_row_widgets.append(
                JobRowWidget(Tepid_Connection.PrintJob(q[j])))
        listwalker = urwid.SimpleFocusListWalker(job_row_widgets)
        listbox = urwid.ListBox(listwalker)
        bx = urwid.BoxAdapter(listbox, height=10)
        pile = urwid.Pile([title_cols, urwid.Divider(), bx])
        padding = urwid.Padding(pile, left=2, right=2)
        linebox = urwid.LineBox(padding)
        urwid.WidgetWrap.__init__(self, linebox)


class QueueJobListListWidget(urwid.WidgetWrap):
    def __init__(self):
        queue_job_list_widgets = []
        for name in sorted(tcfg.t.queues):
            queue_job_list_widgets.append(QueueJobListWidget(name))
        cols = urwid.Columns(queue_job_list_widgets)
        urwid.WidgetWrap.__init__(self, cols)


class UserColourPrintingToggle(urwid.WidgetWrap):
    _selectable = True

    def __init__(self, user_text_info_widget):
        self.user_text_info_widget = user_text_info_widget
        button = urwid.SelectableIcon(
            'Colour Printing: {}'.format(
                user_text_info_widget.user.colour_printing),
            cursor_position=17)
        urwid.WidgetWrap.__init__(self, button)

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key == ' ':
            self.user_text_info_widget.colour_printing_toggle()
        return key


class LoginForm(urwid.WidgetWrap):
    def __init__(self, login_callback):
        self.login_callback = login_callback
        self.bottom_w = tcfg.loop.widget
        self.username = urwid.Edit(caption="McGill short username: ")
        self.password = urwid.Edit(caption="Password: ", mask='*')
        header = urwid.Padding(urwid.Text("Login"))
        header = urwid.AttrMap(header, 'footer')
        button_ok = urwid.Button("OK", on_press=self.do_login)
        button_cancel = urwid.Button("Cancel", on_press=self.close)
        buttons = urwid.Columns([
            urwid.Divider(),
            (10, button_cancel),
            (6, button_ok),
            urwid.Divider()])
        pile = urwid.Pile([
            header,
            urwid.Divider(),
            self.username,
            self.password,
            urwid.Divider(),
            buttons])
        linebox = urwid.LineBox(pile)
        f = urwid.Filler(linebox)
        o = urwid.Overlay(f, self.bottom_w, align='center',
                          valign='middle', width=45, height=10)
        urwid.WidgetWrap.__init__(self, o)

    def do_login(self, calling_button=None):
        self.close()
        self.login_callback(self.username.edit_text,
                            self.password.edit_text)

    def close(self, calling_button=None):
        tcfg.loop.widget = self.bottom_w


class InfoWidget(urwid.WidgetWrap):
    def __init__(self):
        title = urwid.Text("-=\u2261 tepid tui \u2261=-")
        quote = urwid.Text([
            '"why should I even ',
            ('underline', 'have'),
            ' a web browser?"'])
        version = urwid.Text("Version: 0.9.0")
        pile = urwid.Pile([
            urwid.Divider(),
            title,
            urwid.Divider(),
            quote,
            urwid.Divider(),
            version])
        center = urwid.Columns([
            urwid.Divider(),
            pile,
            urwid.Divider()])
        f = urwid.Filler(center)
        urwid.WidgetWrap.__init__(self, f)

    def header(self):
        return "museigen / toshokan"


class ErrorPopup(urwid.WidgetWrap):
    signals = ['user_ok']

    def __init__(self, string):
        self.bottom_w = tcfg.loop.widget
        header = urwid.Padding(urwid.Text("Error!"))
        header = urwid.AttrMap(header, 'error_heading')
        text = urwid.Text(string)
        button_ok = urwid.Button("OK", on_press=self.signal_callback)
        button_ctr = urwid.Columns([
            urwid.Divider(),
            (6, button_ok),
            urwid.Divider()])
        pile = urwid.Pile([
            header,
            urwid.Divider(),
            text,
            urwid.Divider(),
            button_ctr])
        linebox = urwid.LineBox(pile)
        f = urwid.Filler(linebox)
        o = urwid.Overlay(f, self.bottom_w, align='center',
                          valign='middle', width=45, height=10)
        urwid.WidgetWrap.__init__(self, o)

    def signal_callback(self, calling_button=None):
        self._emit('user_ok')
        self.close()

    def close(self):
        tcfg.loop.widget = self.bottom_w


class UserSearchForm(urwid.WidgetWrap):
    def __init__(self):
        self.searchbox = urwid.Edit(caption="Search string: ")
        self.results_w = self.build_results_list([])
        w = self._build_widget()
        urwid.WidgetWrap.__init__(self, w)

    def _build_widget(self):
        button_search = urwid.Button("Get Info",
                                     on_press=self.do_get_info)
        button_suggest = urwid.Button("Get Suggestions",
                                      on_press=self.do_suggest)
        controls = urwid.Columns([
            (16, urwid.Divider()),
            (12, button_search),
            (19, button_suggest),
            urwid.Divider()])
        pile = urwid.Pile([
            self.searchbox,
            controls,
            urwid.Divider(),
            urwid.Text("Results:"),
            self.results_w])
        return pile

    def throw_error(self, string):
        e = ErrorPopup(string)
        tcfg.loop.widget = e
        tcfg.loop.draw_screen()

    def redraw(self):
        w = self._build_widget()
        self._w = w

    def do_get_info(self, calling_button=None):
        if not self.searchbox.edit_text:
            self.results_w = self.build_results_list([])
            self.redraw()
            return
        user = tcfg.t.user_lookup_obj(self.searchbox.edit_text)
        if not user:
            self.throw_error("User could not be found!")
            return
        uv = UserInfoView(user)
        f = FillWrapper(uv)
        tptui_util.view_widget(f, visit=True)

    def do_suggest(self, calling_button=None):
        if not self.searchbox.edit_text:
            self.results_w = self.build_results_list([])
            self.redraw()
            return
        self.results_w = self.build_results_list(self.searchbox.edit_text)
        self.redraw()

    def build_results_list(self, string):
        rlist = tcfg.t.get_user_suggestions(string)
        if not rlist:
            rlist = []
        return UserResultListWidget(rlist)


class UserResultRowWidget(urwid.WidgetWrap):
    _selectable = True

    def __init__(self, raw_user):
        self.raw_user = raw_user
        long_user = urwid.Text(raw_user['longUser'].split('@')[0])
        short_user = urwid.Text(raw_user['shortUser'])
        display_name = urwid.Text(raw_user['displayName'])
        cols = urwid.Columns([
            (30, long_user),
            (9, short_user),
            display_name])
        urwid.WidgetWrap.__init__(self, cols)
        self._w = urwid.AttrMap(self._w, None, 'focus_cursor_line')

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key in (' ', 'enter'):
            user = tcfg.t.user_lookup_obj(self.raw_user['shortUser'])
            uv = UserInfoView(user)
            f = FillWrapper(uv)
            tptui_util.view_widget(f, visit=True)
        return key


class UserResultListWidget(urwid.WidgetWrap):
    def __init__(self, result_list):
        user_result_row_widgets = []
        for r in result_list:
            user_result_row_widgets.append(
                UserResultRowWidget(r))
        listwalker = urwid.SimpleFocusListWalker(user_result_row_widgets)
        listbox = urwid.ListBox(listwalker)
        bx = urwid.BoxAdapter(listbox, height=10)
        linebox = urwid.LineBox(bx)
        urwid.WidgetWrap.__init__(self, linebox)


class UserTextInfoWidget(urwid.WidgetWrap):
    def __init__(self, u):
        self.user = u
        w = self._build_widget()
        urwid.WidgetWrap.__init__(self, w)

    def _build_widget(self):
        u = self.user
        short_user = urwid.Text('Short Username: {}'.format(u.short_user))
        long_user = urwid.Text('Long Username: {}'.format(u.long_user))
        user_id = urwid.Text('Student ID: {}'.format(u.student_id))
        faculty = urwid.Text('Faculty: {}'.format(u.faculty))
        colour_printing = UserColourPrintingToggle(self)
        quota = urwid.Text('Quota: {}'.format(u.raw_quota))
        pile = urwid.Pile(
            [short_user, long_user, user_id, faculty, colour_printing, quota])
        return pile

    def colour_printing_toggle(self):
        tcfg.t.toggle_colour_printing(self.user.raw_info)
        self.reload_user()

    def reload_user(self):
        updated = tcfg.t.user_lookup_obj(self.user.short_user)
        self.user = updated
        self._w = self._build_widget()
        self._invalidate()


class LongJobRowWidget(urwid.WidgetWrap):
    _selectable = True

    def __init__(self, j, user_text_info_widget):
        self.job = j
        self.user_text_info_widget = user_text_info_widget
        cols = self._build_widget()
        urwid.WidgetWrap.__init__(self, cols)
        self._error_check()

    def _build_widget(self):
        j = self.job
        queue = urwid.Text(j.queue)
        pages_str = str(
            j.pages) if j.colour_pages == 0 else '{} ({} colour)'.format(
                j.pages, j.colour_pages)
        pages = urwid.Text(pages_str)
        status_str = "Failed" if j.error != "" else \
                                            "Printed" if not j.refunded else \
                                            "Refunded"
        status = urwid.Text(status_str)
        started = urwid.Text(
            datetime.datetime.fromtimestamp(
                (j.started) / 1000).strftime("%H:%M %d %b %Y"))
        host = urwid.Text(j.host)
        name = urwid.Text(j.name)
        cols = urwid.Columns([(6, queue), (18, pages), (10, status),
                              (19, started), (16, host), ('weight', 1, name)])
        return cols

    def _error_check(self):
        j = self.job
        if j.error != "":
            self._w = urwid.AttrMap(
                self._w,
                'job_status_failed',
                focus_map='focus_cursor_line_failed')
        else:
            self._w = urwid.AttrMap(
                self._w, None, focus_map='focus_cursor_line')

    def selectable(self):
        return True

    def reload_print_job(self):
        updated = tcfg.t.get_print_job(self.job.id)
        self.job = updated
        self._w = self._build_widget()
        self._error_check()
        self._invalidate()
        self.user_text_info_widget.reload_user()

    def keypress(self, size, key):
        if key == 'r':
            self.job.refund(tcfg.t)
            self.reload_print_job()
        if key == 'R':
            self.job.unrefund(tcfg.t)
            self.reload_print_job()
        return key


class LongJobRowListWidget(urwid.WidgetWrap):
    def __init__(self, queue, w):
        queuetxt = urwid.Text("Queue")
        pages = urwid.Text("Pages")
        status = urwid.Text("Status")
        started = urwid.Text("Started")
        host = urwid.Text("Host")
        name = urwid.Text("Name")
        title_cols = urwid.Columns([(6, queuetxt), (18, pages), (10, status),
                                    (19, started), (16, host), ('weight', 1,
                                                                name)])

        long_job_row_widgets = []
        for j in queue:
            long_job_row_widgets.append(
                LongJobRowWidget(Tepid_Connection.PrintJob(j), w))
        listwalker = urwid.SimpleFocusListWalker(long_job_row_widgets)
        listbox = urwid.ListBox(listwalker)
        bx = urwid.BoxAdapter(listbox, height=10)
        pile = urwid.Pile([title_cols, urwid.Divider(), bx])
        padding = urwid.Padding(pile, left=2, right=2)
        linebox = urwid.LineBox(padding)

        urwid.WidgetWrap.__init__(self, linebox)


class VeryLongJobRowWidget(urwid.WidgetWrap):
    _selectable = True

    def __init__(self, j):
        self.job = j
        cols = self._build_widget()
        urwid.WidgetWrap.__init__(self, cols)
        self._error_check()

    def _build_widget(self):
        j = self.job
        user = urwid.Text(j.user)
        pages_str = str(
            j.pages) if j.colour_pages == 0 else '{} ({} colour)'.format(
                j.pages, j.colour_pages)
        pages = urwid.Text(pages_str)
        status_str = "Failed" if j.error != "" else \
                                            "Printed" if not j.refunded else \
                                            "Refunded"
        status = urwid.Text(status_str)
        started = urwid.Text(
            datetime.datetime.fromtimestamp(
                (j.started) / 1000).strftime("%H:%M %d %b %Y"))
        host = urwid.Text(j.host)
        name = urwid.Text(j.name)
        cols = urwid.Columns([(8, user), (18, pages), (10, status),
                              (19, started), (16, host), ('weight', 1, name)])
        return cols

    def _error_check(self):
        j = self.job
        if j.error != "":
            self._w = urwid.AttrMap(
                self._w,
                'job_status_failed',
                focus_map='focus_cursor_line_failed')
        else:
            self._w = urwid.AttrMap(
                self._w, None, focus_map='focus_cursor_line')

    def selectable(self):
        return True

    def reload_print_job(self):
        updated = tcfg.t.get_print_job(self.job.id)
        self.job = updated
        self._w = self._build_widget()
        self._error_check()
        self._invalidate()

    def keypress(self, size, key):
        if key == 'r':
            self.job.refund(tcfg.t)
            self.reload_print_job()
        if key == 'R':
            self.job.unrefund(tcfg.t)
            self.reload_print_job()
        return key


class VeryLongJobRowListWidget(urwid.WidgetWrap):
    def __init__(self, queue):
        user = urwid.Text("User")
        pages = urwid.Text("Pages")
        status = urwid.Text("Status")
        started = urwid.Text("Started")
        host = urwid.Text("Host")
        name = urwid.Text("Name")
        title_cols = urwid.Columns([(8, user), (18, pages), (10, status),
                                    (19, started), (16, host), ('weight', 1,
                                                                name)])

        very_long_job_row_widgets = []
        for j in queue:
            very_long_job_row_widgets.append(
                VeryLongJobRowWidget(Tepid_Connection.PrintJob(j)))
        listwalker = urwid.SimpleFocusListWalker(very_long_job_row_widgets)
        listbox = urwid.ListBox(listwalker)
        bx = urwid.BoxAdapter(listbox, height=30)
        pile = urwid.Pile([title_cols, urwid.Divider(), bx])
        padding = urwid.Padding(pile, left=2, right=2)
        linebox = urwid.LineBox(padding)

        urwid.WidgetWrap.__init__(self, linebox)


class VeryLongQueueView(urwid.WidgetWrap):
    def __init__(self):
        rbuttons = []
        self.rbobjects = []
        self.button = urwid.Button("Load Queue", on_press=self.load_queue)
        ql = tcfg.t.get_queue_list()
        for q in ql:
            self.rbobjects.append((12, urwid.RadioButton(rbuttons, q['name'])))
        self.load_queue()
        w = self._build_widget()
        urwid.WidgetWrap.__init__(self, w)

    def _build_widget(self):
        cols = urwid.Columns(self.rbobjects + [(14, self.button)])
        pile = urwid.Pile([
            cols,
            urwid.Divider(),
            self.vljrlw])

        f = urwid.Filler(pile)
        return f

    def reload_widget(self):
        if hasattr(self, '_w'):
            w = self._build_widget()
            self._w = w

    def load_queue(self, calling_button=None):
        queue = self.rbobjects[0][1]
        for bo in self.rbobjects:
            if bo[1].state:
                queue = bo[1].label
        q = tcfg.t.get_queue(queue)
        w = VeryLongJobRowListWidget(q)
        self.vljrlw = w
        self.reload_widget()


class UserInfoView(urwid.WidgetWrap):
    def __init__(self, u, filled=False):
        w = UserTextInfoWidget(u)

        ljrlw = LongJobRowListWidget(u.raw_queue, w)

        pile = urwid.Pile([w, ljrlw])

        if filled:
            f = FillWrapper(pile, footer=self.footer)
            urwid.WidgetWrap.__init__(self, f)

        urwid.WidgetWrap.__init__(self, pile)

    def footer(self):
        return ("Press r to refund a job, R to unrefund,"
                " [bspc] to go back (if possible)")


class MainFrame(urwid.WidgetWrap):
    def __init__(self, widget, default_header_str=None,
                 default_footer_str=None):
        if default_header_str:
            self.default_header_str = default_header_str
        else:
            self.default_header_str = "-=\u2261 tepid tui \u2261=-"
        if default_footer_str:
            self.default_footer_str = default_footer_str
        else:
            self.default_footer_str = ("Press Q to exit, "
                                       "Meta-[1-5] to change view")
        def_header = ViewStatusIndicator(self.default_header_str)
        def_footer = urwid.AttrMap(urwid.Padding(
            urwid.Text(self.default_footer_str)), 'footer')

        frame = urwid.Frame(widget,
                            header=def_header,
                            footer=def_footer)
        urwid.WidgetWrap.__init__(self, frame)

    def change_widget(self, widget):
        self._w.contents['body'] = (widget, None)
        f = urwid.Text("")

        if hasattr(widget, 'header'):
            h = ViewStatusIndicator(widget.header())
        else:
            h = ViewStatusIndicator(self.default_header_str)

        if hasattr(widget, 'footer'):
            f.set_text(('footer', widget.footer()))
        else:
            f.set_text(('footer', self.default_footer_str))
        f = urwid.AttrMap(urwid.Padding(f), 'footer')
        self._w.contents['header'] = (h, None)
        self._w.contents['footer'] = (f, None)


class ViewStatusIndicator(urwid.WidgetWrap):
    def __init__(self, text):
        text_widgets = [None]
        for x in range(1, 6):
            if x == tcfg._view_index:
                text_widgets.append(urwid.Text(('status_focused',
                                                "* " +
                                                tcfg._view_stack_names[
                                                    x])))
            else:
                text_widgets.append(urwid.Text(('status_unfocused',
                                                "  " +
                                                tcfg._view_stack_names[
                                                    x])))
        cols = urwid.Columns([
            urwid.AttrMap(urwid.Padding(urwid.Text(text)), 'footer'),
            (8, text_widgets[1]),
            (8, text_widgets[2]),
            (8, text_widgets[3]),
            (8, text_widgets[4]),
            (8, text_widgets[5])])
        urwid.WidgetWrap.__init__(self, cols)


class FillWrapper(urwid.WidgetWrap):
    def __init__(self, widget, header=None, footer=None):
        if hasattr(widget, 'header'):
            self.header = widget.header
        if hasattr(widget, 'footer'):
            self.footer = widget.footer
        if header:
            self.header = header
        if footer:
            self.footer = footer
        f = urwid.Filler(widget)

        urwid.WidgetWrap.__init__(self, f)


class MainView(urwid.WidgetWrap):
    def __init__(self):
        greeting = urwid.Text("Hello {}!".format(
            tcfg.t.user_data['user']['salutation']))
        queue_statuses = QueueStatusListWidget(tcfg.t.queues)

        queue_job_w = QueueJobListListWidget()

        pile = urwid.Pile([
            greeting,
            urwid.Divider(),
            queue_statuses,
            urwid.Divider(),
            queue_job_w])

        f = urwid.Filler(pile)
        urwid.WidgetWrap.__init__(self, f)

    def footer(self):
        return ("Press 'Q' to exit, 'd' to mark a printer as down,"
                " 'D' to mark it back up, Meta-[1-5] to change view")
