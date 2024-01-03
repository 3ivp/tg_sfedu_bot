import json
import sqlite3
import datetime

import telebot
from telebot import types
import requests

DB_NAME = "tgdb.sqlite"
bot = telebot.TeleBot("6811788490:AAEmupUNhaPqlKnnl1o7tlYSDbmkz5lscy8")
user = ""
user_group_id = ""
chosen_week = 0
chosen_day = ""
class_num = 0
days = {"Пнд": 0, "Втр": 1, "Срд": 2, "Чтв": 3, "Птн": 4, "Сбт": 5}


def identify_user(func):
    def out_func(message):
        global user, user_group_id
        if user == "":
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            user_id = message.from_user.id
            cur.execute(f"SELECT * FROM users WHERE user_id={user_id}")
            data = cur.fetchall()
            cur.close()
            conn.close()

            if data:
                _, user, user_group_id = data[0]
            else:
                markup = types.ReplyKeyboardMarkup()
                markup.add("📃 Зарегистрироваться")

                bot.send_message(
                    message.chat.id,
                    "Незарегестрированный пользователь! Пожалуйста, зарегестрируйтесь, чтобы продолжить работу с ботом",
                    reply_markup=markup)
        else:
            func(message)
    return out_func



@bot.message_handler(commands=["start"])
def start(message):
    global user, user_group_id
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    user_id = message.from_user.id
    cur.execute(f"SELECT * FROM users WHERE user_id={user_id}")
    data = cur.fetchall()
    cur.close()
    conn.close()

    if data:
        _, user, user_group_id = data[0]
    if user == "":
        reg_menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        reg_menu_markup.add("📃 Зарегистрироваться")
        bot.send_message(message.chat.id,
                         "Добро пожаловать! Зарегистрируйтесь, чтобы работать с ботом",
                         reply_markup=reg_menu_markup)
    else:
        bot.send_message(message.chat.id, f"Добро пожаловать, {user}!")
        show_main_menu(message)


def show_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Расписание на сегодня")
    markup.add("Расписание в другой день")
    markup.add("📝 Смотреть заметки")
    bot.send_message(message.chat.id, "Меню", reply_markup=markup)


def ask_name(message):
    msg = bot.send_message(message.chat.id, 
                           "Введите фамилию и инициалы пользователя (инициалы через пробел)")
    bot.register_next_step_handler(msg, register_user)


def register_user(message):
    global user, user_group_id
    user = message.text.strip()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        user_group_id = get_group_id(user)
    except Exception:
        bot.send_message(message.chat.id, "Некорректно введены данные.")
        user = None
        ask_name(message)
        return
    cur.execute(
        f'INSERT INTO users (user_id, name, group_id) VALUES ({message.from_user.id}, "{user}", "{user_group_id}")'
    )
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, "Пользователь успешно зарегистрирован")
    start(message)


@identify_user
def show_schedule(message):
    global chosen_week, chosen_day
    url = f"https://webictis.sfedu.ru/schedule-api/?group={user_group_id}&week={chosen_week}"
    res = requests.get(url)
    data = json.loads(res.text)
    class_time = data["table"]["table"][1]
    cur_schedule = data["table"]["table"][days[chosen_day[:3]] + 2]
    date = cur_schedule[0]
    answer = ""
    answer += f"Неделя: {chosen_week}\n"
    answer += f"{date}\n\n"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i in range(1, len(cur_schedule)):
        items = cur_schedule[i].split()
        if (cur_schedule[i] != ""):
            answer += class_time[i] + "\n" + items[0] + "\n" + " ".join(items[1:-1]) + "\n" + items[-1] + "\n\n"
            markup.add(f"📝 Добавить заметку: {i} пара")
    if answer.count("\n") == 3:
        answer += "В этот день нет занятий"
    markup.add("↩️ Назад в меню")
    bot.send_message(message.chat.id, f"{answer}", reply_markup=markup)


@identify_user
def ask_week(message):
    res = requests.get(f"https://webictis.sfedu.ru/schedule-api/?query={user}")
    data = json.loads(res.text)
    weeks = data["weeks"]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    row = []
    for week in weeks:
        row.append(f"{week}")
        if len(row) == 4:
            markup.row(*row)
            row.clear()
    if row:
        markup.row(*row)
    bot.send_message(message.chat.id, "Выберете неделю", reply_markup=markup)
    bot.register_next_step_handler(message, ask_day)


def ask_day(message):
    global chosen_week
    chosen_week = int(message.text)
    res = requests.get(f"https://webictis.sfedu.ru/schedule-api/?query={user}")
    data = json.loads(res.text)
    days = [i[0] for i in data["table"]["table"][2:]]

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    row_1 = [f"{days[0]}",
             f"{days[1]}",
             f"{days[2]}"]
    row_2 = [f"{days[3]}",
             f"{days[4]}",
             f"{days[5]}"]
    markup.row(*row_1)
    markup.row(*row_2)
    bot.send_message(message.chat.id, "Выберете день недели", reply_markup=markup)
    bot.register_next_step_handler(message, set_day_for_schedule)


def set_day_for_schedule(message):
    global chosen_day, days
    chosen_day = message.text
    show_schedule(message)


def get_group_id(name: str) -> str:
    res = requests.get(f"https://webictis.sfedu.ru/schedule-api/?query={name}")
    data = json.loads(res.text)
    group = data["table"]["group"]
    return group


def add_note(message):
    text = message.text
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(f"""INSERT INTO notes (
                                    user_id,
                                    week, 
                                    day, 
                                    class_num, 
                                    note_text
                                   ) 
                         VALUES (
                                    {message.from_user.id},
                                    {chosen_week},
                                    "{chosen_day}",
                                    {class_num},
                                    "{text}"
                                 )""")
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, "Заметка добавленна")



@identify_user
def choose_notes_by_weeks(message):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(f"SELECT (week) FROM notes WHERE user_id={message.from_user.id}")
    data = cur.fetchall()
    cur.close()
    conn.close()

    data_set = set(data[0])
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if data_set:
        row = []
        for week in data_set:
            row.append(f"{week}")
            if len(row) == 4:
                markup.row(*row)
                row.clear()
        if row:
            markup.row(*row)
        bot.send_message(message.chat.id, "Выберете неделю", reply_markup=markup)
        bot.register_next_step_handler(message, choose_notes_by_day)
    else:
        markup.add("↩️ Назад в меню")
        bot.send_message(message.chat.id,"Заметок нет", reply_markup=markup)


def choose_notes_by_day(message):
    week = message.text
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(f"SELECT (day) FROM notes WHERE week={week} and user_id={message.from_user.id}")
    data = cur.fetchall()
    cur.close()
    conn.close()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    row = []
    for day in data[0]:
        markup.add(f"{day}")
    bot.send_message(message.chat.id, "Выберете день", reply_markup=markup)
    bot.register_next_step_handler(message, show_notes_by_day)


def show_notes_by_day(message):
    day = message.text
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(f'SELECT class_num, note_text FROM notes WHERE day="{day}" and user_id={message.from_user.id}')
    data = cur.fetchall()
    cur.close()
    conn.close()

    data = data
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("↩️ Назад в меню")
    for note in data:
        bot.send_message(message.chat.id, f"{note[0]} пара:\n{note[1]}", reply_markup=markup)


@bot.message_handler(content_types=["text"])
def bot_message_handler(message):
    if message.chat.type == "private":
        if message.text == "📃 Зарегистрироваться":
            ask_name(message)
        elif message.text == "Расписание на сегодня":
            global chosen_week, chosen_day
            res = requests.get(f"https://webictis.sfedu.ru/schedule-api/?query={user}")
            data = json.loads(res.text)
            chosen_week = data["table"]["week"]
            chosen_day = data["table"]["table"][datetime.date.weekday(datetime.date.today()) + 2][0]
            show_schedule(message)
        elif message.text == "Расписание в другой день":
            ask_week(message)
        elif message.text == "📝 Смотреть заметки":
            choose_notes_by_weeks(message)
        elif message.text == "↩️ Назад в меню":
            show_main_menu(message)
        elif message.text.startswith("📝 Добавить заметку:"):
            global class_num
            class_num = int(message.text.split()[-2])
            bot.send_message(message.chat.id, "Введите текст")
            bot.register_next_step_handler(message, add_note)

if __name__ == "__main__":
    bot.polling(non_stop=True)