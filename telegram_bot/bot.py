import datetime
import json
import logging
import os
import textwrap

import emoji as emoji
from telebot import types, TeleBot
from telebot.apihelper import ApiTelegramException

from build_tester.results_sync import SUCCESS_RESULTS
from telegram_bot.db import DB, SubscribeType

logger = logging.getLogger('Bot')

UNSUBSCRIBE_ERRORS = ['blocked', 'rights', 'kicked', 'not a member']
MAX_BUTTONS_COUNT = 60
MAX_MESSAGE_LENGTH = 4096


class Bot:
    def __init__(self, config_path='./config.json', debug_mode=False):
        self.__debug_mode = debug_mode

        with open(config_path, 'r') as fs:
            config = json.load(fs)

            self.__token = config.get('telegram_token')
            assert self.__token != '1234567890:qWerTyuIOpaSDf-ghJKl-qWerTyuIOpaSDf', \
                'Your should change default Telegram token with your own to use Telegram bot!'
            assert self.__token is not None, 'No Telegram token to use Telegram bot!'

            self.__archive_dir_path = config.get('archive_dir_path', './archive')
            self.__logs_dir_name = config.get('logs_dir_name', 'logs')
            self.__tests_dir_name = config.get('tests_dir_name', 'tests')
            self.__results_file_name = config.get('results_file_name', 'results.json')

        self.__db = DB(config.get('telegram_db', {}))
        self.__bot = TeleBot(self.__token)
        self.__username = f'@{self.__bot.get_me().username}'
        self.__init_handlers()

    #########################
    # Handlers
    #########################

    def __add_message_handler(self, handler, *args, **kwargs):
        self.__bot.message_handler(*args, **kwargs)(handler)

    def __add_channel_post_handler(self, handler, *args, **kwargs):
        self.__bot.channel_post_handler(*args, **kwargs)(handler)

    def __add_callback_query_handler(self, handler, *args, **kwargs):
        self.__bot.callback_query_handler(*args, **kwargs)(handler)

    def __init_handlers(self):
        self.__add_message_handler(commands=['start'], handler=self.__show_info)

        self.__add_message_handler(commands=['subscribe'], handler=self.__subscribe)
        self.__add_channel_post_handler(commands=['subscribe'], handler=self.__subscribe)

        self.__add_message_handler(commands=['subscribe_to_failures'], handler=self.__subscribe_to_failures)
        self.__add_channel_post_handler(commands=['subscribe_to_failures'], handler=self.__subscribe_to_failures)

        self.__add_message_handler(commands=['unsubscribe'], handler=self.__unsubscribe)
        self.__add_channel_post_handler(commands=['unsubscribe'], handler=self.__unsubscribe)

        self.__add_message_handler(commands=['show_results'], handler=self.__send_results_list_command)

        self.__add_callback_query_handler(
            func=lambda call: call.data.startswith('results_list;'),
            handler=self.__send_results_list_call,
        )

        self.__add_callback_query_handler(
            func=lambda call: call.data.startswith('results;all;'),
            handler=self.__send_all_results,
        )
        self.__add_callback_query_handler(
            func=lambda call: call.data.startswith('results;failed;'),
            handler=self.__send_failed_results,
        )

        self.__add_callback_query_handler(
            func=lambda call: call.data.startswith('logs;all;'),
            handler=self.__send_all_logs,
        )
        self.__add_callback_query_handler(
            func=lambda call: call.data.startswith('logs;failed;'),
            handler=self.__send_failed_logs,
        )
        self.__add_callback_query_handler(
            func=lambda call: call.data.startswith('log;'),
            handler=self.__send_log,
        )

        self.__add_callback_query_handler(
            func=lambda call: call.data.startswith('tests;all;'),
            handler=self.__send_all_tests,
        )
        self.__add_callback_query_handler(
            func=lambda call: call.data.startswith('tests;failed;'),
            handler=self.__send_failed_tests,
        )
        self.__add_callback_query_handler(
            func=lambda call: call.data.startswith('test;'),
            handler=self.__send_test,
        )

    def start(self):
        self.__bot.infinity_polling()

    #########################
    # Data transformation
    #########################

    @staticmethod
    def __dir_name_to_date(dir_name):
        try:
            dir_name = os.path.basename(dir_name)
            return datetime.datetime.strptime(dir_name, "%Y%m%d_%H%M%S").strftime("%Y.%m.%d %H:%M:%S")
        except ValueError:
            pass

    @staticmethod
    def __file_name_to_os_build(name):
        name = os.path.basename(name)
        name = os.path.splitext(name)[0]
        params = name.split('_', 2)
        if len(params) == 1:
            return params[0], None
        if len(params) == 2:
            return params[0], params[1]

        return f'{params[0]} {params[1]}', params[2].replace("_", " ")

    @staticmethod
    def __file_name_to_os_build_str(name):
        os_name, build_name = Bot.__file_name_to_os_build(name)
        if build_name is None:
            return os_name
        return f'OS: {os_name}. Build Name: {build_name}'

    @staticmethod
    def __get_failed_results(results):
        new_results = {}
        for os_name, builds in results.items():
            builds = {
                build_name: result
                for build_name, result in builds.items()
                if result not in SUCCESS_RESULTS
            }
            if len(builds) > 0:
                new_results[os_name] = builds
        return new_results

    @classmethod
    def __get_builds_names(cls, results, only_failed=True):
        if only_failed:
            results = cls.__get_failed_results(results)

        builds_names = []
        for os_name, builds in results.items():
            for build_name, result in builds.items():
                builds_names.append(f'{os_name}_{build_name}')
        return builds_names

    def __get_files(self, dir_path, results_path=None):
        if not os.path.exists(dir_path):
            return []

        # Use results_path argument to filter by failed results
        if not results_path or not os.path.exists(results_path):
            return os.listdir(dir_path)

        with open(results_path, mode='r') as fs:
            results = json.load(fs)
            failed_builds = self.__get_builds_names(results, only_failed=True)

        return list(filter(
            lambda build: os.path.splitext(build)[0] in failed_builds,
            os.listdir(dir_path),
        ))

    @staticmethod
    def __get_page(data_list, reverse=False, data_handler=None, count=10, page=1):
        new_data = []
        for data in data_list:
            if data_handler:
                if data_handler(data) is None:
                    continue
            new_data.append(data)
        data_list = sorted(new_data, reverse=reverse)

        is_end = True
        if page != 0:
            if page > 0:
                begin = count * (page - 1)
                end = count * page
            else:
                begin = count * page
                end = len(data_list) + count * (page + 1)

            is_end = end >= len(data_list)
            data_list = data_list[begin:end]

        return data_list, is_end

    def __get_names_keyboard(
        self,
        data_list,
        reverse=False,
        row_width=1,
        data_handler=None,
        prefix='',
        count=6,
        page=0,
        pages_prefix=None,
    ):
        page_data, is_end = self.__get_page(
            data_list=data_list,
            reverse=reverse,
            data_handler=data_handler,
            count=count,
            page=page,
        )

        if len(page_data) == 0:
            return

        keyboard = types.InlineKeyboardMarkup()
        row = []
        for data in page_data:
            name = data
            if data_handler:
                name = data_handler(data)

            data_btn = types.InlineKeyboardButton(text=name, callback_data=f'{prefix}{data}')
            row.append(data_btn)
            if len(row) == row_width:
                keyboard.add(*row)
                row = []

        if len(row) != 0:
            keyboard.add(*row)

        if pages_prefix is not None:
            page_buttons = []
            if abs(page) > 1:
                page_buttons.append(types.InlineKeyboardButton(
                    text=emoji.emojize(':arrow_left:', use_aliases=True),
                    callback_data=f'{pages_prefix}{page - 1}',
                ))
            if not is_end:
                page_buttons.append(types.InlineKeyboardButton(
                    text=emoji.emojize(':arrow_right:', use_aliases=True),
                    callback_data=f'{pages_prefix}{page + 1}',
                ))
            if len(page_buttons) > 0:
                keyboard.add(*page_buttons)

        return keyboard

    @classmethod
    def __get_results_message(cls, results, only_failed=False):
        if only_failed:
            results = cls.__get_failed_results(results)

        message = ''
        for os_name, builds in results.items():
            for build_name, result in builds.items():
                if result not in SUCCESS_RESULTS:
                    result = f'*{result}*'
                message += f'OS: {os_name}. Build: {build_name}. Result: {result}\n'
            message += '\n'
        message = message.replace('_', '\\_')  # escape markdown special symbol
        return message

    @staticmethod
    def __get_results_keyboard(dir_name, only_failed=False):
        keyboard = types.InlineKeyboardMarkup()
        if only_failed:
            show_all = types.InlineKeyboardButton(text='Show all results', callback_data=f'results;all;{dir_name}')
            keyboard.add(show_all)
        show_logs = types.InlineKeyboardButton(text='Show logs', callback_data=f'logs;failed;{dir_name}')
        show_tests = types.InlineKeyboardButton(text='Show tests results', callback_data=f'tests;failed;{dir_name}')
        keyboard.add(show_logs, show_tests)
        return keyboard

    @staticmethod
    def __split_message(text):
        messages = []
        begin = 0
        if text[-1] != '\n':
            text += '\n'

        while begin < len(text):
            i = 0
            max_len = min(MAX_MESSAGE_LENGTH - 1, len(text) - begin - 1)
            for i in range(max_len, -1, -1):
                if text[begin + i] == '\n':
                    break
            if i == 0:
                i = max_len
            i += 1
            messages.append(text[begin:begin + i])
            begin += i

        return messages

    @staticmethod
    def __split_reply_markup(reply_markup):
        if not reply_markup:
            return [None]

        reply_markups = []
        if isinstance(reply_markup, types.InlineKeyboardMarkup):
            for i in range(0, len(reply_markup.keyboard), MAX_BUTTONS_COUNT):
                reply_markups.append(types.InlineKeyboardMarkup(
                    keyboard=reply_markup.keyboard[i:i + MAX_BUTTONS_COUNT],
                    row_width=reply_markup.row_width,
                ))
        else:
            reply_markups.append(reply_markup)

        return reply_markups

    def __send_message(self, chat_id, text, **kwargs):
        reply_markups = self.__split_reply_markup(kwargs.get('reply_markup'))
        kwargs['reply_markup'] = None

        messages = self.__split_message(text)

        if len(messages) > 1:
            self.__bot.send_message(chat_id, messages[0], **kwargs)
            kwargs['reply_to_message_id'] = None

        for i in range(1, len(messages) - 1):
            self.__bot.send_message(chat_id, messages[i], **kwargs)

        kwargs['reply_markup'] = reply_markups[0]
        self.__bot.send_message(chat_id, messages[-1], **kwargs)

        last_line = messages[-1].strip('\n').split('\n')[-1]
        for i in range(1, len(reply_markups)):
            kwargs['reply_markup'] = reply_markups[i]
            self.__bot.send_message(chat_id, f'Page #{i + 1}. {last_line}', **kwargs)

    #########################
    # Commands
    #########################

    def __show_info(self, message):
        self.__send_message(chat_id=message.chat.id, text=textwrap.dedent('''
            Hello!
            This is a bot that sends out the results of Tarantool builds.
            To manage your notifications subscription use:
            • /subscribe to subscribe for all build checks;
            • /subscribe_to_failures to subscribe only for failed build checks;
            • /unsubscribe to unsubscribe from all results of builds.
            • /show_results to show results from archive.
        '''))

    def __subscribe(self, message):
        if message.chat.id < 0 and self.__username not in message.text:
            return

        self.__db.subscribe(message.chat.id, SubscribeType.ALL)
        self.__send_message(
            chat_id=message.chat.id,
            text='You are successfully *subscribed* for *all* build checks notifications!',
            parse_mode='Markdown',
        )

    def __subscribe_to_failures(self, message):
        if message.chat.id < 0 and self.__username not in message.text:
            return

        self.__db.subscribe(message.chat.id, SubscribeType.FAILED)
        self.__send_message(
            chat_id=message.chat.id,
            text='You are successfully *subscribed* for *failed* build checks notifications!',
            parse_mode='Markdown',
        )

    def __unsubscribe(self, message):
        if message.chat.id < 0 and self.__username not in message.text:
            return

        self.__db.unsubscribe(message.chat.id)
        self.__send_message(
            chat_id=message.chat.id,
            text='You are successfully *unsubscribed* from build checks notifications!',
            parse_mode='Markdown',
        )

    #########################
    # Results list
    #########################

    def __send_results_list(self, user_id, page):
        archive_files = []
        if os.path.exists(self.__archive_dir_path):
            archive_files = os.listdir(self.__archive_dir_path)

        keyboard = self.__get_names_keyboard(
            data_list=archive_files,
            reverse=True,
            row_width=2,
            data_handler=self.__dir_name_to_date,
            prefix=f'results;failed;',
            page=page,
            pages_prefix='results_list;',
        )
        if keyboard is None:
            self.__send_message(chat_id=user_id, text=f'No results!')
            return

        self.__send_message(
            chat_id=user_id,
            text=f'To show a specific page use `/show_results <page>`\n\nSelect date:',
            reply_markup=keyboard,
            parse_mode='Markdown',
        )

    def __send_results_list_command(self, message):
        page = 1
        words = message.text.split()
        if len(words) > 1:
            page = int(words[1])

        self.__send_results_list(message.from_user.id, page)

    def __send_results_list_call(self, call):
        page = 1
        words = call.data.split(';')
        if len(words) > 1:
            page = int(words[1])

        self.__bot.answer_callback_query(callback_query_id=call.id)
        self.__send_results_list(call.from_user.id, page)

    #########################
    # Results
    #########################

    def __send_results(self, call, only_failed=False):
        dir_name = call.data.split(';')[-1]
        results_file = os.path.join(self.__archive_dir_path, dir_name, self.__results_file_name)
        if not os.path.exists(results_file):
            self.__bot.answer_callback_query(callback_query_id=call.id, text='No results file for selected time!')
            return

        self.__bot.answer_callback_query(callback_query_id=call.id)
        with open(results_file, mode='r') as fs:
            results = json.load(fs)
            keyboard = self.__get_results_keyboard(dir_name, only_failed=only_failed)
            message = self.__get_results_message(results, only_failed=only_failed)
            if message:
                prefix = 'Failed' if only_failed else 'All'
                self.__send_message(
                    chat_id=call.from_user.id,
                    text=f'{prefix} results from {self.__dir_name_to_date(dir_name)}:\n\n{message}',
                    reply_markup=keyboard,
                    parse_mode='Markdown',
                )
            else:
                prefix = 'failed' if only_failed else ''
                self.__send_message(
                    chat_id=call.from_user.id,
                    text=f'No {prefix} results from {self.__dir_name_to_date(dir_name)}!',
                    reply_markup=keyboard,
                )

    def __send_failed_results(self, call):
        self.__send_results(call, only_failed=True)

    def __send_all_results(self, call):
        self.__send_results(call, only_failed=False)

    #########################
    # Logs + Tests
    #########################

    def __send_build_files(self, call, type_name, dir_name, only_failed=False):
        date_name = call.data.split(';')[-1]
        date_dir_path = os.path.join(self.__archive_dir_path, date_name, dir_name)

        if only_failed:
            results_path = os.path.join(self.__archive_dir_path, date_name, self.__results_file_name)
            files = self.__get_files(date_dir_path, results_path)
        else:
            files = self.__get_files(date_dir_path)

        if len(files) == 0 and not only_failed:
            self.__bot.answer_callback_query(callback_query_id=call.id, text=f'No {type_name}s for selected date!')
            return

        self.__bot.answer_callback_query(callback_query_id=call.id)

        keyboard = self.__get_names_keyboard(
            data_list=files,
            prefix=f'{type_name};{date_name};',
            data_handler=self.__file_name_to_os_build_str,
        )
        if only_failed:
            keyboard = keyboard or types.InlineKeyboardMarkup()
            show_all = types.InlineKeyboardButton(
                text=f'Show list of {type_name}s for all builds',
                callback_data=f'{type_name}s;all;{date_name}',
            )
            keyboard.add(show_all)

        if len(files) > 0:
            text = f'Select one of build to get {type_name}s:'
        else:
            text = f'No {type_name}s for failed builds!'

        self.__send_message(chat_id=call.from_user.id, text=text, reply_markup=keyboard)

    #########################
    # Logs
    #########################

    def __send_failed_logs(self, call):
        return self.__send_build_files(call, 'log', self.__logs_dir_name, only_failed=True)

    def __send_all_logs(self, call):
        return self.__send_build_files(call, 'log', self.__logs_dir_name, only_failed=False)

    def __send_log(self, call):
        dir_name, file_name = call.data.split(';')[1:]
        log_file = os.path.join(self.__archive_dir_path, dir_name, self.__logs_dir_name, file_name)
        if not os.path.exists(log_file):
            self.__bot.answer_callback_query(callback_query_id=call.id, text='No logs for selected build!')
            return

        self.__bot.answer_callback_query(callback_query_id=call.id)
        with open(log_file, mode='r') as fs:
            self.__bot.send_document(
                chat_id=call.from_user.id,
                data=fs,
                caption=f'Logs from {self.__dir_name_to_date(dir_name)}',
            )

    #########################
    # Tests
    #########################

    def __send_failed_tests(self, call):
        return self.__send_build_files(call, 'test', self.__tests_dir_name, only_failed=True)

    def __send_all_tests(self, call):
        return self.__send_build_files(call, 'test', self.__tests_dir_name, only_failed=False)

    def __send_test(self, call):
        dir_name, file_name = call.data.split(';')[1:]
        test_file = os.path.join(self.__archive_dir_path, dir_name, self.__tests_dir_name, file_name)
        if not os.path.exists(test_file):
            self.__bot.answer_callback_query(callback_query_id=call.id, text='No tests for selected build!')
            return

        self.__bot.answer_callback_query(callback_query_id=call.id)
        with open(test_file, mode='r') as fs:
            tests = json.load(fs)

            message = ''
            for test_name, result in tests.items():
                message += f'- {test_name}: {result}\n'

            os_name, build_name = self.__file_name_to_os_build(test_file)
            self.__send_message(
                chat_id=call.from_user.id,
                text=f'OS: {os_name}\n'
                     f'Build Name: {build_name}\n'
                     f'Time: {self.__dir_name_to_date(dir_name)}\n\n'
                     f'Tests results:\n'
                     f'{message}',
            )

    #########################
    # Subscription
    #########################

    def __send_message_to_subscriber(self, chat_id, *args, **kwargs):
        try:
            return self.__send_message(chat_id, *args, **kwargs)
        except ApiTelegramException as e:
            logger.error(e)
            if any(map(
                lambda error: error in e.result_json['description'] or e.error_code == 403,
                UNSUBSCRIBE_ERRORS,
            )):
                logger.warning(f'Unsubscribe {chat_id} because specific error')
                self.__db.unsubscribe(chat_id)
        except Exception as e:
            logger.error(e)

    def send_out_builds_info(self, builds_info, dir_name):
        failed_message = self.__get_results_message(builds_info, only_failed=True)
        keyboard = self.__get_results_keyboard(dir_name, only_failed=True)
        if failed_message:
            for chat_id in self.__db.get_subscribers_for_failed():
                self.__send_message_to_subscriber(
                    chat_id=chat_id,
                    text=f'Some builds are failed:\n\n{failed_message}',
                    reply_markup=keyboard,
                    parse_mode='Markdown',
                )
        else:
            for chat_id in self.__db.get_subscribers_for_all():
                self.__send_message_to_subscriber(
                    chat_id=chat_id,
                    text='All tests are passed!',
                    reply_markup=keyboard,
                )
