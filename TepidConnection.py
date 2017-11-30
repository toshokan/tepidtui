from base64 import b64encode
import datetime
import requests
import json


class TepidConnection:

    baseurl = "https://tepid.science.mcgill.ca:8443/tepid"

    def __init__(self, username, password):
        self.user_data = self.do_login(username, password)
        self.auth_token = self.get_auth_token()
        self.reload_print_queues()

    def reload_print_queues(self):
        ql = self.get_queue_list()
        dl = self.get_destination_list()
        self.queues = {}
        for q in ql:
            self.queues[q['name']] = []
            for d in q['destinations']:
                self.queues[q['name']].append(PrintDestination(dl[d]))

    def do_login(self, user, password):
        login_url = '{}/sessions'.format(self.baseurl)
        params = {
            'username': user,
            'persistent': 'false',
            'password': password
        }
        r = requests.post(login_url, json=params)
        if not r.status_code == 200:
            raise ValueError("Failed to authenticate you with TEPID")
        return r.json()

    def get_auth_token(self):
        cleartext = '{}:{}'.format(self.user_data['user']['shortUser'],
                                   self.user_data['_id'])
        return 'Token {}'.format(b64encode(cleartext.encode()).decode())

    def get_queue_list(self):
        req_url = '{}/queues'.format(self.baseurl)
        headers = {'Authorization': self.auth_token}
        r = requests.get(req_url, headers=headers)
        return r.json()

    def get_destination_list(self):
        req_url = '{}/destinations'.format(self.baseurl)
        headers = {'Authorization': self.auth_token}
        r = requests.get(req_url, headers=headers)
        return r.json()

    def get_queue(self, queue):
        req_url = '{}/queues/{}'.format(self.baseurl, queue)
        params = {'limit': 10}
        headers = {'Authorization': self.auth_token}
        r = requests.get(req_url, params=params, headers=headers)
        return r.json()

    def printer_status(self, dest_list):
        for k in dest_list:
            print(dest_list[k]['name'])
            status = dest_list[k]['up']
            if status:
                print('\tThe printer is up.')
            else:
                print('\tThe printer is down.')
                print('\tReason: {}'.format(dest_list[k]['ticket']['reason']))
                print('\tReported by {} ({}) on {}'.format(
                    dest_list[k]['ticket']['user']['shortUser'],
                    dest_list[k]['ticket']['user']['nick'],
                    datetime.datetime.fromtimestamp(
                        int(dest_list[k]['ticket']['reported']) /
                        1000).strftime("%c")))
            print()

    def last_jobs(self, queue, end=10, start=0):
        for i in range(start, end):
            job = queue[i]
            print('Job: {}\nUser: {}\nPages: {}\nRefunded: {}'.format(
                job['name'], job['userIdentification'],
                job['pages'] + job['colorPages'], job['refunded']))
            print()

    def get_print_job(self, job_id):
        req_url = '{}/jobs/job/{}'.format(self.baseurl, job_id)
        headers = {'Authorization': self.auth_token}
        r = requests.get(req_url, headers=headers)
        return PrintJob(r.json())

    def user_lookup(self, shortuser):
        req_url_info = '{}/users/{}'.format(self.baseurl, shortuser)
        req_url_quota = '{}/quota'.format(req_url_info)
        headers = {'Authorization': self.auth_token}
        ri = requests.get(req_url_info, headers=headers)
        quota = requests.get(req_url_quota, headers=headers).json()
        user_info = ri.json()
        print(
            ('Short Username: {}\nLong Username: {}\nPreferred Name: {}\n'
             'Faculty: {}\n21st Century Fund: {}\nStudent Since: {}\n'
             'Colour Printing: {}\nQuota: {}').
            format(user_info['shortUser'], user_info['longUser'],
                   user_info['salutation'], user_info['faculty'], True if
                   '000-21st Century Fund' in user_info['groups'] else False,
                   datetime.datetime.fromtimestamp(
                       int(user_info['activeSince']) / 1000).strftime("%B %Y"),
                   user_info['colorPrinting'], quota))
        print()
        req_url_queue = '{}/jobs/{}'.format(self.baseurl, shortuser)
        rq = requests.get(req_url_queue, headers=headers).json()
        print("This user's latest prints: \n")
        self.last_jobs(rq, 10)

    def user_lookup_obj(self, shortuser):
        req_url_info = '{}/users/{}'.format(self.baseurl, shortuser)
        req_url_quota = '{}/quota'.format(req_url_info)
        headers = {'Authorization': self.auth_token}
        ri = requests.get(req_url_info, headers=headers)
        if ri.status_code == 404:
            return None
        quota = requests.get(req_url_quota, headers=headers).json()
        user_info = ri.json()
        req_url_queue = '{}/jobs/{}'.format(self.baseurl, shortuser)
        rq = requests.get(req_url_queue, headers=headers).json()
        return TepidUser(user_info, quota, rq)

    def get_user_suggestions(self, string):
        req_url = '{}/users/autosuggest/{}'.format(self.baseurl, string)
        params = {
            'limit': 15
            }
        headers = {'Authorization': self.auth_token}
        r = requests.get(req_url, headers=headers, params=params).json()
        if not r:
            return None
        else:
            return r

    def toggle_colour_printing(self, user_data):
        req_url = '{}/users/{}/color'.format(self.baseurl,
                                             user_data['shortUser'])
        headers = {
            'Authorization': self.auth_token,
            'Content-Type': 'application/json'
        }
        r = requests.put(
            req_url,
            headers=headers,
            data=str(not user_data['colorPrinting']).lower())
        return r.json()


class PrintDestination:
    def __init__(self, raw):
        self.name = raw['name']
        self.id = raw['_id']
        self.up = raw['up']
        self._raw_dict = raw

    def mark_up(self, t):
        if self.up:
            return
        req_url = '{}/destinations/{}'.format(t.baseurl, self.id)
        headers = {
            'Authorization': t.auth_token,
            'Content-Type': 'application/json'
        }
        requests.post(
                req_url,
                headers=headers,
                data=json.dumps({'up': True}))
        self.reload_pd(t)

    def mark_down(self, reason, t):
        if not self.up:
            return
        req_url = '{}/destinations/{}'.format(t.baseurl, self.id)
        headers = {
            'Authorization': t.auth_token,
            'Content-Type': 'application/json'
        }
        requests.post(
                req_url,
                headers=headers,
                data=json.dumps({
                    'up': False,
                    'reason': reason}))
        self.reload_pd(t)

    def reload_pd(self, t):
        pd = t.get_destination_list()[self.id]
        self.up = pd['up']
        self._raw_dict = pd


class PrintJob:
    def __init__(self, raw):
        self.name = raw['name']
        self.id = raw['_id']
        self.queue = raw['queueName'] if 'queueName' in raw.keys() else ""
        self.user = raw['userIdentification']
        self.error = raw['error'] if 'error' in raw.keys() else ""
        self.destination_id = raw[
            'destination'] if 'destination' in raw.keys() else ""
        self.colour_pages = raw['colorPages']
        self.host = raw['originalHost']
        self.started = raw['started']
        self.pages = raw['pages']
        self.refunded = raw['refunded']
        self._raw_dict = raw

    def refund(self, t):
        req_url = '{}/jobs/job/{}/refunded'.format(t.baseurl, self.id)
        headers = {
            'Authorization': t.auth_token,
            'Content-Type': 'application/json'
        }
        requests.put(req_url, headers=headers, data='true')
        t.reload_print_queues()

    def unrefund(self, t):
        req_url = '{}/jobs/job/{}/refunded'.format(t.baseurl, self.id)
        headers = {
            'Authorization': t.auth_token,
            'Content-Type': 'application/json'
        }
        requests.put(req_url, headers=headers, data='false')
        t.reload_print_queues()


class TepidUser:
    def __init__(self, info, quota, queue):
        self.display_name = info['displayName']
        self.given_name = info['givenName']
        self.last_name = info['lastName']
        self.short_user = info['shortUser']
        self.long_user = info['longUser']
        self.email = info['email']
        self.faculty = info['faculty']
        self.salutation = info['salutation']
        self.real_name = info['realName']
        self.real_name = info['realName']
        self.student_id = \
            info['studentId'] if 'studentId' in info.keys() else ""
        self.colour_printing = info['colorPrinting']
        self.tf_century = True if '000-21st Century Fund' in info[
            'groups'] else False

        self.raw_info = info
        self.raw_quota = quota
        self.raw_queue = queue
