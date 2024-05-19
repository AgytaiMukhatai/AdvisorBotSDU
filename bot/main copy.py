import telebot
import sqlite3
from telebot import types
import pandas as pd
import requests
from bs4 import BeautifulSoup
from transcript import transcript_scrap, transcript_import
from transcript_gpa import transcript_gpa_scrap, transcript_gpa_import
from gpa_plot import gpa_plot, sbj_plot
from fpdf import FPDF
import os
import numpy as np
import re
import spacy
from spacy.matcher import Matcher
from nltk.stem.snowball import SnowballStemmer
from nltk.corpus import stopwords
import nltk
import time

# Ensure NLTK resources are downloaded
nltk.download("stopwords")
nltk.download("punkt")

# Загрузка английской модели
nlp = spacy.load("en_core_web_sm")


TOKEN = "7108747833:AAFDwjRiofG-fpge1a4ToHbtuZGQIRG6z-g"
# TOKEN = "6898801075:AAGFGEaPfukiQAOGGmh3cbyakKsgEoL3NQU"
bot = telebot.TeleBot(TOKEN)
user_data = {}
0
# Initialize the database and create a table if it doesn't exist
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()
c.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY,
    username TEXT,
    password TEXT,
    name_student TEXT,
    faculty TEXT,
    specialty TEXT,
    level TEXT,
    education_language TEXT,
    entry_date TEXT,
    graduation_date TEXT
)
"""
)
conn.commit()

chat_histories = {}

def get_answer(history):
    data = {
        "messages": history,
        'mode': 'chat',
        'character': 'SDU Advisor Assistant'
    }
    headers = {
        "Content-Type": "application/json",
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip, deflate, br'
    }
    url = 'http://localhost:5000/v1/chat/completions'
    
    response = requests.post(url=url, headers=headers, json=data)
    if response.status_code != 200:
        return None
    response = response.json()
    if response['choices'][0]['message']:
        return response['choices'][0]['message']
    return None


@bot.message_handler(commands=["start"])
def send_welcome(message):
    chat_id = message.chat.id
    student_data = get_student_data_by_chat_id(chat_id)
    if student_data:
        main_page(chat_id)
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text="Log in", callback_data="login"))
        sent_message = bot.send_message(
            chat_id,
            "Hi! 👋 I am an AI Advisor BOT by SDU University 📚🤖.\nClick on the 'Log in' button, and let's immerse ourselves in the world of your studies! 🚀",
            reply_markup=markup,
        )
    # message_to_delete = sent_message.message_id
    # print(message_to_delete)


@bot.message_handler(commands=["menu"])
def send_menu(message):
    chat_id = message.chat.id
    student_data = get_student_data_by_chat_id(chat_id)
    if student_data is None:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text="Log in", callback_data="login"))
        bot.send_message(
            chat_id,
            "I'm sorry, you need to log in from the beginning 😔",
            reply_markup=markup,
        )
    else:
        main_page(chat_id)


@bot.callback_query_handler(func=lambda call: call.data == "logout")
def callback_confirm_logout(call):
    chat_id = call.message.chat.id

    # Prepare markup with Yes/No buttons
    markup = types.InlineKeyboardMarkup()
    yes_button = types.InlineKeyboardButton("✅", callback_data="confirm_logout")
    no_button = types.InlineKeyboardButton("❌", callback_data="cancel_logout")
    markup.add(yes_button, no_button)

    # Send confirmation message with inline buttons
    bot.send_message(
        chat_id, "Are you sure you want to logout? Make sure?", reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "confirm_logout")
def callback_study_year(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    chat_id = call.message.chat.id

    # Animation indicating logout
    with open("logout.gif", "rb") as photo:
        bot.send_animation(chat_id, photo)

    bot.send_message(
        chat_id, "I will be waiting for your arrival 🥹\nSend me /start for start"
    )

    # Database operations to delete user and drop tables
    delete_user_and_tables(chat_id)


@bot.callback_query_handler(func=lambda call: call.data == "cancel_logout")
def callback_cancel_logout(call):
    chat_id = call.message.chat.id
    bot.send_message(chat_id, "Logout cancelled.")
    handle_main_page_callback(call)


def delete_user_and_tables(chat_id):
    # Delete user from 'users.db'
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    if c.fetchone():
        c.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
        conn.commit()
        print(f"Record with chat_id {chat_id} has been deleted.")
    conn.close()

    # Drop user-specific tables in 'transcripts.db' and 'transcriptsgpa.db'
    for db_name in ["transcripts.db", "transcriptsgpa.db"]:
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        table_name = f"u{chat_id}"
        c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        if c.fetchone():
            c.execute(f"DROP TABLE {table_name}")
            conn.commit()
            print(f"Table {table_name} has been successfully deleted.")
        conn.close()


# @bot.callback_query_handler(func=lambda call: call.data == "logout")
# def callback_study_year(call):
#     chat_id = call.message.chat.id
#     photo = open("logout.gif", "rb")
#     bot.send_animation(chat_id, photo)

#     bot.send_message(chat_id, "I will be waiting for your arrival 🥹")

#     conn = sqlite3.connect("users.db")
#     c = conn.cursor()
#     c.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
#     exists = c.fetchone()
#     if exists:
#         c.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
#         conn.commit()
#         print(f"Record with chat_id {chat_id} has been deleted.")
#     else:        # If no record is found, print that no action was taken
#         print(f"No record found with chat_id {chat_id} to delete.")
#     conn.close()

#     conn = sqlite3.connect("transcripts.db")
#     c = conn.cursor()

#     # Formulate the table name based on chat_id
#     table_name = f"u{chat_id}"

#     # Check if the table exists before trying to drop it
#     c.execute(
#         "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
#     )
#     if c.fetchone():
#         # If the table exists, execute the drop table command
#         c.execute(f"DROP TABLE {table_name}")
#         conn.commit()
#         print(f"Table {table_name} has been successfully deleted.")
#     else:
#         # If no table is found, print that no action was taken
#         print(f"No table found with name {table_name} to delete.")

#     # Close the database connection
#     conn.close()

#     conn = sqlite3.connect("transcriptsgpa.db")
#     c = conn.cursor()

#     # Formulate the table name based on chat_id
#     table_name = f"u{chat_id}"

#     # Check if the table exists before trying to drop it
#     c.execute(
#         "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
#     )
#     if c.fetchone():
#         # If the table exists, execute the drop table command
#         c.execute(f"DROP TABLE {table_name}")
#         conn.commit()
#         print(f"Table {table_name} has been successfully deleted.")
#     else:
#         # If no table is found, print that no action was taken
#         print(f"No table found with name {table_name} to delete.")

#     # Close the database connection
#     conn.close()

# @bot.message_handler(commands=["logout"])
# def delete_user_if_exists(message):
#     # bot.delete_message(chat_id, wait_mes.message_id)
#     chat_id = message.chat.id
#     photo = open("logout.gif", "rb")
#     bot.send_animation(chat_id, photo)
#     # wait_message = bot.send_message(chat_id, text="Please wait ⏳")
#     # filename = gpa_plot(chat_id)
#     # bot.delete_message(chat_id, wait_mes.message_id)
#     # Connect to the SQLite database
#     conn = sqlite3.connect("users.db")
#     c = conn.cursor()

#     # First, check if a record with the given chat_id exists
#     c.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
#     exists = c.fetchone()

#     if exists:
#         # If the record exists, delete it
#         c.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
#         conn.commit()
#         print(f"Record with chat_id {chat_id} has been deleted.")
#     else:
#         # If no record is found, print that no action was taken
#         print(f"No record found with chat_id {chat_id} to delete.")

#     # Close the database connection
#     conn.close()

# conn = sqlite3.connect("transcriptsgpa.db")
# c = conn.cursor()

# # Properly format the table name to avoid SQL injection
# table_name = f"u{chat_id}"

# # First, check if the table exists using SQL meta commands
# c.execute(
#     "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
# )
# exists = c.fetchone()

# if exists:
#     # If the table exists, execute the deletion statement
#     c.execute(f"DROP TABLE u{table_name}")
#     conn.commit()
#     print(f"Table {table_name} has been deleted.")
# else:
#     # If no table is found, print that no action was taken
#     print(f"No table found with name {table_name} to delete.")

# # Close the database connection
# conn.close()

# conn = sqlite3.connect("transcripts.db")
# c = conn.cursor()
# table_name = f"u{chat_id}"

# # First, check if the table exists using SQL meta commands
# c.execute(
#     "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
# )
# exists = c.fetchone()

# if exists:
#     # If the table exists, execute the deletion statement
#     c.execute(f"DROP TABLE u{table_name}")
#     conn.commit()
#     print(f"Table {table_name} has been deleted.")
# else:
#     # If no table is found, print that no action was taken
#     print(f"No table found with name {table_name} to delete.")

# Close the database connection


@bot.message_handler(commands=["help"])
def send_help(message):
    chat_id = message.chat.id
    student_data = get_student_data_by_chat_id(chat_id)
    if student_data is None:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text="Log in", callback_data="login"))
        bot.send_message(
            chat_id,
            "I'm sorry, you need to log in from the beginning 😔",
            reply_markup=markup,
        )
    else:
        bot.send_message(
            chat_id,
            "Здесь может быть ваша реклама 🙂",
            # reply_markup=markup,
        )


@bot.callback_query_handler(func=lambda call: call.data == "update")
def update_all(call):
    transcript_gpa_scrap(call.message.chat.id)
    transcript_scrap(call.message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data == "transcript")
def callback_transcript(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    chat_id = call.message.chat.id
    # transcript_gpa_scrap(chat_id)
    # transcript_scrap(chat_id)

    print(chat_id)
    # bot.send_message(chat_id, "Обновление Транскрипта")

    # Создаем InlineKeyboardMarkup
    keyboard = types.InlineKeyboardMarkup(row_width=2)

    # Добавляем кнопки с названиями
    buttons = [
        types.InlineKeyboardButton("Year of study", callback_data="study_year"),
        types.InlineKeyboardButton("GPA Calculate", callback_data="gpa_calculate"),
        types.InlineKeyboardButton("GPA Statistics", callback_data="gpa_statistics"),
        types.InlineKeyboardButton(
            "Subject Statistics", callback_data="subject_statistics"
        ),
        types.InlineKeyboardButton("🔙", callback_data="main_page"),
        # types.InlineKeyboardButton("Credit / ECTS", callback_data="credit_ects"),
        # types.InlineKeyboardButton("Point", callback_data="point"),
    ]

    keyboard.add(*buttons)

    # Отправляем сообщение с клавиатурой
    bot.send_message(chat_id, "Select an option to display:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "study_year")
def callback_study_year(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    chat_id = call.message.chat.id
    print(chat_id)
    df = transcript_import(chat_id)
    unique_study_year = df["Study Year"].unique()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for study_year in unique_study_year:
        button = types.InlineKeyboardButton(
            str(study_year), callback_data=f"study_year_{study_year}"
        )
        keyboard.add(button)
    # Add a button for all study years
    keyboard.add(
        types.InlineKeyboardButton("All", callback_data="study_year_all"),
        types.InlineKeyboardButton("🔙", callback_data="transcript"),
    )

    bot.send_message(chat_id, "Select a study year:", reply_markup=keyboard)


def get_max_column_widths(pdf, df, padding=6):
    col_widths = []
    for col in df.columns:
        header_width = pdf.get_string_width(str(col))
        max_data_width = max([pdf.get_string_width(str(item)) for item in df[col]])
        max_width = max(header_width, max_data_width) + padding
        col_widths.append(max_width)
    return col_widths


@bot.callback_query_handler(func=lambda call: call.data.startswith("study_year_"))
def handle_study_year_selection(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    chat_id = call.message.chat.id
    # keyboard = types.InlineKeyboardMarkup()
    # keyboard.add(
    #     # types.InlineKeyboardButton("Go to menu", callback_data="main_page"),
    #     types.InlineKeyboardButton("🔙", callback_data="study_year")
    # )
    df = transcript_import(chat_id)

    # df.drop(columns=["chatID"], inplace=True)  # Delete the "chatID" column
    print(chat_id)

    df["Point"] = df["Point"].replace(np.nan, 0)
    print(df)
    study_year = call.data.split("_")[2]
    print(study_year)

    transcripts_folder = "Transcripts"
    if not os.path.exists(transcripts_folder):
        os.makedirs(transcripts_folder)

    if study_year == "all":
        # Send the original DataFrame without filtering

        # file_path = os.path.join(transcripts_folder, f"{chat_id}_transcript_all.xlsx")
        # df.to_excel(file_path, index=False)

        # Определяем ширину столбцов и высоту строк автоматически
        # col_widths = [pdf.get_string_width(str(col)) + 6 for col in df.columns]
        # pdf = FPDF(orientation="L")
        pdf = FPDF(orientation="L")
        pdf.add_page()
        pdf.add_font("DejaVu", "", "DejaVuSansCondensed.ttf", uni=True)
        pdf.set_font("DejaVu", "", 8)
        df = df.drop(columns=["chatID", "Study Program", "Study Year"])
        print(df)
        col_widths = get_max_column_widths(pdf, df)

        row_height = 10

        # Adding column headers
        for col_width, col in zip(col_widths, df.columns):
            pdf.cell(col_width, row_height, str(col), border=1)
        pdf.ln(row_height)

        # Adding data rows
        for row in df.values:
            for col_width, item in zip(col_widths, row):
                pdf.cell(col_width, row_height, str(item), border=1)
            pdf.ln(row_height)

        # Save PDF to file
        file_path_pdf = f"{transcripts_folder}/{chat_id}_transcript_all.pdf"
        pdf.output(file_path_pdf)

        # Send PDF to user via Telegram Bot
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Go to menu", callback_data="main_page")
        )

        # Open and send the PDF file as a document
        try:
            with open(file_path_pdf, "rb") as file:
                bot.send_document(chat_id, file, reply_markup=keyboard)
        except FileNotFoundError:
            print("Error: File not found.")
    else:
        # pdf = FPDF(orientation="L")
        pdf = FPDF(orientation="L")
        pdf.add_page()
        pdf.add_font("DejaVu", "", "DejaVuSansCondensed.ttf", uni=True)
        pdf.set_font("DejaVu", "", 8)
        filtered_df = df[df["Study Year"] == int(study_year)]
        # filtered_df = filtered_df.drop(columns=["chatID"])
        sorted_df = filtered_df.sort_values(by=["Study Program"])
        sorted_df = filtered_df.drop(columns=["chatID", "Study Program", "Study Year"])
        print(sorted_df)
        # file_path = os.path.join(
        #     transcripts_folder, f"{chat_id}_transcript_{study_year}.xlsx"
        # )
        # sorted_df.to_excel(file_path, index=False)

        # # Add a button for all study years
        # keyboard_all = types.InlineKeyboardMarkup()
        # keyboard_all.add(
        #     types.InlineKeyboardButton(
        #         "All Study Years", callback_data="study_year_all"
        #     )
        # )

        # keyboard = types.InlineKeyboardMarkup()
        # keyboard.add(
        #     types.InlineKeyboardButton("Go to menu", callback_data="main_page")
        # )
        # with open(file_path, "rb") as file:
        #     bot.send_document(chat_id, file, reply_markup=keyboard)
        #     # bot.send_message(
        #     #     chat_id, "Please select a study year:", reply_markup=keyboard_all
        #     # )

        col_widths = get_max_column_widths(pdf, sorted_df)

        row_height = 10

        # Adding column headers
        for col_width, col in zip(col_widths, sorted_df.columns):
            pdf.cell(col_width, row_height, str(col), border=1)
        pdf.ln(row_height)

        # Adding data rows
        for row in sorted_df.values:
            for col_width, item in zip(col_widths, row):
                pdf.cell(col_width, row_height, str(item), border=1)
            pdf.ln(row_height)

        # Save PDF to file
        file_path_pdf = f"{transcripts_folder}/{chat_id}_transcript_{study_year}.pdf"
        pdf.output(file_path_pdf)

        # Send PDF to user via Telegram Bot
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Go to menu", callback_data="main_page")
        )

        # Open and send the PDF file as a document
        try:
            with open(file_path_pdf, "rb") as file:
                bot.send_document(chat_id, file, reply_markup=keyboard)
        except FileNotFoundError:
            print("Error: File not found.")


# os.remove(file_path)


user_gpa_calculate = {}


# @bot.callback_query_handler(func=lambda call: call.data == "gpa_calculate")
# def callback_gpa_calculate_trash(call):
#     chat_id = call.message.chat.id
#     if chat_id in user_gpa_calculate:
#         user_gpa_calculate[chat_id] = {
#             "ip_df_keys": [],
#             "current_index": 0,
#             "ip_scores": {},
#         }
# return user_gpa_calculate[chat_id]


@bot.callback_query_handler(func=lambda call: call.data == "trash_generate_gpa")
def callback_trash_generate_gpa(call):
    # bot.delete_message(call.message.chat.id, call.message.message_id)
    chat_id = call.message.chat.id
    # user_info = get_user_gpa_data(chat_id)
    # Remove the GPA data associated with the user
    # keyboard = types.InlineKeyboardMarkup(row_width=1)
    # keyboard.add(
    #     types.InlineKeyboardButton("🔙", callback_data="transcript"),
    # )
    user_gpa_calculate[chat_id] = {
        "ip_df_keys": [],
        "current_index": 0,
        "ip_scores": {},
    }
    # bot.send_message(chat_id, "GPA data deleted.", reply_markup=keyboard)
    callback_gpa_calculate(call)


def get_user_gpa_data(chat_id):
    if chat_id not in user_gpa_calculate:
        user_gpa_calculate[chat_id] = {
            "ip_df_keys": [],
            "current_index": 0,
            "ip_scores": {},
        }
    return user_gpa_calculate[chat_id]


@bot.callback_query_handler(func=lambda call: call.data == "gpa_statistics")
def gpa_statistics(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    chat_id = call.message.chat.id
    photo = open("sticker.gif", "rb")
    wait_mes = bot.send_animation(chat_id, photo)
    wait_message = bot.send_message(chat_id, text="Please wait ⏳")
    filename = gpa_plot(chat_id)
    bot.delete_message(chat_id, wait_message.message_id)
    bot.delete_message(chat_id, wait_mes.message_id)
    try:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Go to menu", callback_data="main_page")
        )
        with open(filename, "rb") as file:
            bot.send_photo(
                chat_id, file, reply_markup=keyboard
            )  # Changed from send_document to send_photo
    finally:
        if os.path.exists(filename):
            print(f"File {filename} has been deleted.")


@bot.callback_query_handler(func=lambda call: call.data == "subject_statistics")
def sbj_statistics(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    chat_id = call.message.chat.id
    photo = open("sticker.gif", "rb")
    wait_mes = bot.send_animation(chat_id, photo)
    wait_message = bot.send_message(chat_id, text="Please wait ⏳")
    filename = sbj_plot(chat_id)
    bot.delete_message(chat_id, wait_message.message_id)
    bot.delete_message(chat_id, wait_mes.message_id)
    try:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Go to menu", callback_data="main_page")
        )
        with open(filename, "rb") as file:
            bot.send_photo(
                chat_id, file, reply_markup=keyboard
            )  # Changed from send_document to send_photo
    finally:
        if os.path.exists(filename):
            print(f"File {filename} has been deleted.")


@bot.callback_query_handler(func=lambda call: call.data == "gpa_calculate")
def callback_gpa_calculate(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    chat_id = call.message.chat.id
    df = transcript_import(chat_id)  # Assuming this function retrieves a DataFrame
    ip_df = df[df["Traditional"] == "In progress"]
    ip_df_keys = ip_df["Course title"].unique()

    user_info = get_user_gpa_data(chat_id)
    user_info["ip_df_keys"] = list(ip_df_keys)
    user_info["current_index"] = 0
    # user_info["ip_scores"] = {}

    # Create buttons with course titles
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for index, course_title in enumerate(ip_df_keys):
        selected_score = user_info["ip_scores"].get(course_title, "🚫")
        if selected_score.startswith("gpa_"):
            lower_bound, upper_bound = selected_score.split("_")[1:]
            selected_score = f"{lower_bound}-{upper_bound}"
        button_text = f"{course_title} [{selected_score}]"
        button = types.InlineKeyboardButton(
            text=button_text, callback_data=f"select_course_{index}"
        )
        keyboard.add(button)
    keyboard.add(
        types.InlineKeyboardButton("Generate GPA ➡️", callback_data="generate_gpa"),
        types.InlineKeyboardButton("🗑", callback_data="trash_generate_gpa"),
        types.InlineKeyboardButton("🔙", callback_data="transcript"),
    )
    bot.send_message(chat_id, text="Please select a course:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("select_course_"))
def callback_select_course(call):
    # bot.delete_message(call.message.chat.id, call.message.message_id)
    print("Select course callback triggered")
    chat_id = call.message.chat.id
    index = int(call.data.split("_")[2])  # Use index to fetch course title
    user_info = get_user_gpa_data(chat_id)
    selected_course = user_info["ip_df_keys"][index]  # Get course title using index
    user_info["selected_course"] = selected_course  # Store the selected course

    # Call send_score_request with the selected course title
    send_score_request(call, selected_course)


def send_score_request(call, selected_course):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    chat_id = call.message.chat.id
    user_info = get_user_gpa_data(chat_id)
    ip_df_keys = user_info["ip_df_keys"]
    current_index = user_info["current_index"]

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    score_ranges = [
        ("SKIP", None),
        (0, 49),
        (50, 54),
        (55, 59),
        (60, 64),
        (65, 69),
        (70, 74),
        (75, 79),
        (80, 84),
        (85, 89),
        (90, 94),
        (95, 100),
    ]

    column1 = []
    column2 = []

    for score_range in score_ranges:
        if score_range[0] == "SKIP":
            button_text = "🔙"  # Using the back arrow symbol for the button text
            button_data = "gpa_calculate"  # Setting callback data to trigger GPA calculation or return to a previous menu
        else:
            button_text = f"{score_range[0]}-{score_range[1]}"
            print(button_text)
            button_data = f"gpa_{score_range[0]}_{score_range[1]}"
            print(button_data)

        button = types.InlineKeyboardButton(button_text, callback_data=button_data)
        if len(column1) <= len(column2):
            column1.append(button)
        else:
            column2.append(button)

    for button1, button2 in zip(column1, column2):
        keyboard.add(button1, button2)

    if selected_course:  # Check if a course is selected
        bot.send_message(
            chat_id,
            text=f"Please select your score range for course\n <b>{selected_course}</b>",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    elif current_index < len(ip_df_keys):
        course_key = ip_df_keys[current_index]
        bot.send_message(
            chat_id,
            text=f"Please select your score range for course\n <b>{course_key}</b>",
            reply_markup=keyboard,
            parse_mode="HTML",
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("gpa_"))
def callback_score_selection(call):
    # bot.delete_message(call.message.chat.id, call.message.message_id)
    chat_id = call.message.chat.id
    user_info = get_user_gpa_data(chat_id)
    score_data = call.data  # data will be like gpa_0, gpa_50, etc.
    user_info["ip_scores"][user_info["selected_course"]] = score_data
    print(user_info["ip_scores"])
    callback_gpa_calculate(call)


@bot.callback_query_handler(func=lambda call: call.data == "generate_gpa")
def callback_gpa_calculate_generate(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    chat_id = call.message.chat.id
    print(chat_id)

    # Assuming transcript_import retrieves a DataFrame for the chat_id
    df = transcript_import(chat_id)
    print(df)

    # Assuming user_gpa_calculate is a dictionary containing ip_scores for each chat_id
    user_info = user_gpa_calculate.get(chat_id, {})
    ip_scores = user_info.get("ip_scores", {})
    print(ip_scores)

    # Mapping score ranges to GPA grades
    score_range_to_gpa = {
        "gpa_95_100": 4.0,
        "gpa_90_94": 3.67,
        "gpa_85_89": 3.33,
        "gpa_80_84": 3.0,
        "gpa_75_79": 2.67,
        "gpa_70_74": 2.33,
        "gpa_65_69": 2.0,
        "gpa_60_64": 1.67,
        "gpa_55_59": 1.33,
        "gpa_50_54": 1.0,
        "gpa_0_49": 0.0,
    }

    # Convert score ranges to GPA grades
    updated_ip_scores = {}
    for key, value in ip_scores.items():
        if value in score_range_to_gpa:
            updated_ip_scores[key] = score_range_to_gpa[value]
        else:
            updated_ip_scores[key] = 0.0  # Default value if score range not found

    print(updated_ip_scores)

    # Replace GPA grades with Points in the DataFrame
    for index, row in df.iterrows():
        course_title = row["Course title"]
        if course_title in updated_ip_scores:
            df.at[index, "Point"] = updated_ip_scores[course_title]
            print(f"{course_title} changed")

    spa_ip_scores_df = df.copy()

    course_titles = list(ip_scores.keys())

    # Filter the DataFrame
    spa_ip_scores_df = spa_ip_scores_df[
        spa_ip_scores_df["Course title"].isin(course_titles)
    ]
    # print(spa_ip_scores_df)

    # df['Point'].fillna(0, inplace=True)

    # Drop rows with NaN values in the "Point" column
    # df.dropna(subset=['Point'], inplace=True)
    # Remove rows where "Letter Grade" is either "P" or "IP"
    df.dropna(subset=["Point"], inplace=True)
    df = df[df["Letter Grade"] != "P"]

    print(df)
    total_points = sum(df["Point"] * df["Credit / ECTS"])
    total_credits = sum(df["Credit / ECTS"])
    gpa = total_points / total_credits if total_credits != 0 else 0.0
    formatted_gpa = "{:.2f}".format(gpa)

    # Print formatted GPA
    print("GPA:", formatted_gpa)

    spa_ip_scores_df.dropna(subset=["Point"], inplace=True)
    spa_ip_scores_df = spa_ip_scores_df[spa_ip_scores_df["Letter Grade"] != "P"]

    print(spa_ip_scores_df)
    total_points_spa = sum(
        spa_ip_scores_df["Point"] * spa_ip_scores_df["Credit / ECTS"]
    )
    total_credits_spa = sum(spa_ip_scores_df["Credit / ECTS"])
    gpa = total_points_spa / total_credits_spa if total_credits_spa != 0 else 0.0
    formatted_spa = "{:.2f}".format(gpa)

    # Print formatted GPA
    print("SPA:", formatted_spa)

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🔙", callback_data="gpa_calculate"),
        types.InlineKeyboardButton("Go to menu", callback_data="main_page"),
    )
    bot.send_message(
        chat_id,
        f"Your GPA will be : {formatted_gpa} 📊\nYour SPA will be : {formatted_spa} 📝",
        reply_markup=keyboard,
    )


# # Proceed to the next course or finish
# current_index = user_info["current_index"]
# if current_index + 1 < len(user_info["ip_df_keys"]):
#     user_info["current_index"] += 1
#     next_course = user_info["ip_df_keys"][current_index + 1]
#     send_score_request(
#         call, next_course
#     )
#     callback_gpa_calculate(
#         chat_id
#     )  # Call send_score_request to continue to the next course
# else:
#     bot.send_message(chat_id, "All courses processed.")
#     print("All courses have been processed, score selection complete.")

#     # Redirect back to callback_gpa_calculate


# @bot.callback_query_handler(
#     func=lambda call: call.data.startswith("gpa_") or call.data == "skip_button"
# )
# def handle_score_range_selection(call):
#     chat_id = call.message.chat.id
#     user_info = get_user_gpa_data(chat_id)
#     ip_df_keys = user_info["ip_df_keys"]
#     current_index = user_info["current_index"]
#     score_range = call.data

#     # Store the score
#     if score_range != "skip_button":
#         ip_scores = user_info["ip_scores"]
#         course_key = ip_df_keys[current_index]
#         ip_scores[course_key] = score_range

#     # Move to the next course
#     if current_index + 1 < len(ip_df_keys):
#         if score_range == "skip_button":
#             bot.answer_callback_query(call.id, "Course skipped")
#         else:
#             bot.answer_callback_query(call.id, "Score recorded")
#         user_info["current_index"] += 1
#         send_score_request(call)
#     else:
#         bot.answer_callback_query(call.id, "All scores recorded. Processing results.")
#         # Print the stored scores
#         ip_scores = user_info["ip_scores"]
#         for course, score_range in ip_scores.items():
#             print(f"Course: {course}, Score Range: {score_range}")


# Process results here, like calculating GPA, etc.
# Process results here, like calculating GPA, etc.

# Once all scores are collected, you can continue processing
# For example, you can calculate GPA based on the collected scores


# @bot.callback_query_handler(func=lambda call: call.data == "1_term")
# def callback_study_year(call):
#     chat_id = call.message.chat.id
#     df = transcript_scrap(chat_id, 1)
#     df =
#     # bot.send_message(chat_id, "Выберите семестр:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    # bot.delete_message(call.message.chat.id, call.message.message_id)
    user_id = call.from_user.id
    if call.data == "login":
        handle_login_callback(call)
    elif call.data in ["confirm", "cancel"]:
        if user_data.get(user_id):
            if call.data == "confirm":
                bot.delete_message(call.message.chat.id, call.message.message_id)
                confirm_registration(call, user_id)
                transcript_gpa_scrap(call.message.chat.id)
                transcript_scrap(call.message.chat.id)
            elif call.data == "cancel":
                bot.delete_message(call.message.chat.id, call.message.message_id)
                cancel_registration(call, user_id)
        else:
            bot.answer_callback_query(call.id, "Session expired, please start again.")
    elif call.data == "profile":
        handle_profile_callback(call)
    elif call.data == "main_page":
        handle_main_page_callback(call)


def handle_login_callback(call):
    bot.reply_to(call.message, "Enter your StudentID")
    bot.register_next_step_handler(call.message, process_username_step)


def process_username_step(message):
    user_id = message.from_user.id

    user_data[user_id] = {"chat_id": user_id, "username": message.text}
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (message.text,))
    existing_user = c.fetchone()

    if existing_user:
        bot.send_message(user_id, "A user with that name already exists!")
        send_welcome(message)
    else:
        bot.reply_to(message, "Enter your portal password")
        bot.register_next_step_handler(message, process_password_step)


def process_password_step(message):
    user_id = message.from_user.id
    user_data[user_id]["password"] = message.text
    url = "https://oldmy.sdu.edu.kz/index.php"
    data = {
        "username": user_data[user_id]["username"],
        "password": message.text,
        "modstring": "",
        "LogIn": " Log in ",
    }

    response = requests.post(url, data=data, verify=False)
    soup = BeautifulSoup(response.text, "html.parser")
    if "incorrect" in soup.text.lower():
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text="Log in", callback_data="login"))
        bot.send_message(
            user_id,
            "The login or password is incorrect. Please try again!🫣",
            reply_markup=markup,
        )
        # send_welcome(message)
    else:
        # td_elements = soup.find_all("td", class_="clsTdInfo", style="color:#333")
        # user_data[user_id]["name_student"] = td_elements[1].text.strip()
        # user_data[user_id]["name_advisor"] = td_elements[3].text.strip()
        # user_data[user_id]["majority_student"] = td_elements[5].text.strip()

        login_url = "https://oldmy.sdu.edu.kz/index.php"

        # Perform login request to get cookies
        session = requests.Session()
        login_response = session.post(login_url, data=data, verify=False)

        # Check if login was successful
        if login_response.status_code == 200:
            print("Login successful.")
        else:
            print("Login failed.")
            exit()

        # URL for fetching transcript data
        transcript_url = "https://oldmy.sdu.edu.kz/index.php?mod=transkript"

        # Fetch transcript data using the established session (with cookies)
        transcript_response = session.get(transcript_url)

        # Parse the response HTML using BeautifulSoup
        soup = BeautifulSoup(transcript_response.text, "html.parser")
        print(soup)

        td = soup.find("td", text="Student №:")
        if td is None:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="Log in", callback_data="login"))
            bot.send_message(
                user_id,
                "The login or password is incorrect. Please try again!🫣",
                reply_markup=markup,
            )
            # send_welcome(message)
        else:

            user_data[user_id]["username"] = (
                soup.find("td", text="Student №:")
                .find_next_sibling("td")
                .get_text(strip=True)
            )

            user_data[user_id]["name_student"] = (
                soup.find("td", text="Student Name:")
                .find_next_sibling("td")
                .get_text(strip=True)
            )
            user_data[user_id]["faculty"] = (
                soup.find("td", text="Faculty:")
                .find_next_sibling("td")
                .get_text(strip=True)
            )
            user_data[user_id]["specialty"] = (
                soup.find("td", text="Specialty:")
                .find_next_sibling("td")
                .get_text(strip=True)
            )
            user_data[user_id]["level"] = (
                soup.find("td", text="Level:")
                .find_next_sibling("td")
                .get_text(strip=True)
            )
            user_data[user_id]["education_language"] = (
                soup.find("td", text="Education Language:")
                .find_next_sibling("td")
                .get_text(strip=True)
            )
            user_data[user_id]["entry_date"] = (
                soup.find("td", text="Entry Date:")
                .find_next_sibling("td")
                .get_text(strip=True)
            )
            user_data[user_id]["graduation_date"] = (
                soup.find("td", text="Graduation Date:")
                .find_next_sibling("td")
                .get_text(strip=True)
            )
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(
                types.InlineKeyboardButton("✅", callback_data="confirm"),
                types.InlineKeyboardButton("❌", callback_data="cancel"),
            )
            bot.send_message(
                message.chat.id,
                f"Confirm your details:\nStudent name: {user_data[user_id]['name_student']}\nAlso by confirming, you consent to the collection and processing of your data!",
                reply_markup=keyboard,
            )


def confirm_registration(call, user_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (chat_id, username, password, name_student, faculty, specialty, level, education_language, entry_date, graduation_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user_data[user_id]["chat_id"],
            user_data[user_id]["username"],
            user_data[user_id]["password"],
            user_data[user_id]["name_student"],
            user_data[user_id]["faculty"],
            user_data[user_id]["specialty"],
            user_data[user_id]["level"],
            user_data[user_id]["education_language"],
            user_data[user_id]["entry_date"],
            user_data[user_id]["graduation_date"],
        ),
    )

    conn.commit()
    # bot.send_message(user_id, "The data has been saved successfully!")
    main_page(call.message.chat.id)


def cancel_registration(call, user_id):
    bot.send_message(user_id, "Please repeat the data entry.")
    send_welcome(call.message)


def get_student_data_by_chat_id(chat_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    student_data = c.fetchone()
    return student_data


def handle_profile_callback(call):
    chat_id = call.message.chat.id
    bot.delete_message(call.message.chat.id, call.message.message_id)
    student_data = get_student_data_by_chat_id(chat_id)
    if student_data:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Go to menu", callback_data="main_page")
        )
        message_text = (
            f"<b>Student number:</b> {student_data[1]} 😊\n"
            f"<b>Student name:</b> {student_data[3]} 😇\n"
            f"<b>Faculty:</b> {student_data[4]} 🏫\n"
            f"<b>Specialty:</b> {student_data[5]} 📘\n"
            f"<b>Level:</b> {student_data[6]} 🎓\n"
            f"<b>Education Language:</b> {student_data[7]} 🗣️\n"
            f"<b>Entry Date:</b> {student_data[8]} 📅\n"
            f"<b>Graduation Date:</b> {student_data[9]}🎉"
        )

        bot.send_message(
            chat_id, message_text, parse_mode="HTML", reply_markup=keyboard
        )

    else:
        bot.send_message(chat_id, "You don't have any saved profile data.")


def handle_main_page_callback(call):

    main_page(call.message.chat.id)


def main_page(chat_id):
    student_data = get_student_data_by_chat_id(chat_id)
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Profile 👤", callback_data="profile"))
    keyboard.add(types.InlineKeyboardButton("Transcript 🗂", callback_data="transcript"))
    keyboard.add(
        types.InlineKeyboardButton("Update the data 🔄", callback_data="update")
    )
    keyboard.add(types.InlineKeyboardButton("Logout 🚪", callback_data="logout"))
    bot.send_message(
        chat_id,
        f"Welcome, {student_data[3]}🙌🏻! How can I help you?😇",
        reply_markup=keyboard,
    )

@bot.message_handler()
def talk(message):
    start_time = time.time()
    chat_id = message.chat.id
    student_data = get_student_data_by_chat_id(chat_id)
    text = message.text
    if student_data is None:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text="Log in", callback_data="login"))
        bot.send_message(
            chat_id,
            "To use the AdvisorBot, you must first log in.",
            reply_markup=markup,
        )
        return
    
    document_info = {
        "transcript": {"measurement": "semester", "period": ["first", "second"]},
        "documentation": {
            "measurement": "year",
            "period": ["first", "second", "third", "fourth"],
        },
        # Добавьте другие типы документов и их соответствия measurement и period
    }

    def extract_information_spacy(request):
        doc = nlp(request.lower())
        matcher = Matcher(nlp.vocab)

        # Шаблоны для поиска ключевых слов
        document_type_patterns = [[{"LEMMA": {"IN": ["transcript", "transcription"]}}]]
        measurement_patterns = [
            [{"LEMMA": document_info[doc_type]["measurement"]}]
            for doc_type in document_info.keys()
        ]
        period_patterns = [
            [{"LEMMA": period}]
            for doc_type in document_info.keys()
            for period in document_info[doc_type]["period"]
        ]

        # Добавление шаблонов в matcher
        matcher.add("DOCUMENT_TYPE", document_type_patterns)
        matcher.add("MEASUREMENT", measurement_patterns)
        matcher.add("PERIOD", period_patterns)

        # Поиск в тексте
        document_type, measurement, period = None, None, None
        matches = matcher(doc)
        for match_id, start, end in matches:
            rule_id = nlp.vocab.strings[match_id]
            span = doc[start:end]  # Полученный фрагмент текста
            if rule_id == "DOCUMENT_TYPE":
                document_type = span.text
            elif rule_id == "MEASUREMENT":
                measurement = span.text
            elif rule_id == "PERIOD":
                period = span.text

        return document_type, measurement, period

    ordinal_to_number = {
        "all": 0,
        "first": 1,
        "second": 2,
        "third": 3,
        "fourth": 4,
        "fifth": 5,
        # Add more if needed
    }

    def convert_ordinal_to_number(ordinal_word):
        # Convert the ordinal word to lower case to handle case insensitivity
        ordinal_word = ordinal_word.lower()
        # Return the corresponding number or None if not found
        return ordinal_to_number.get(ordinal_word)

    def stemming(content):
        if pd.isnull(content):
            return content
        stemmed_content = re.sub("[^a-zA-Z]", " ", content)
        stemmed_content = stemmed_content.lower()
        stemmed_content = stemmed_content.split()
        snowball_stemmer = SnowballStemmer("english")
        english_stopwords = stopwords.words("english")
        stemmed_content = [
            snowball_stemmer.stem(word)
            for word in stemmed_content
            if word not in english_stopwords
        ]
        stemmed_content = " ".join(stemmed_content)
        return stemmed_content

    # request = "Could you provide me transcript a  for the third year of studies?"
    
    stemmed_request = stemming(text)
    print(stemmed_request)
    document_type, measurement, period = extract_information_spacy(stemmed_request)
    # Check if any required information is missing
    if document_type is None or measurement is None or period is None:
        if chat_id not in chat_histories.keys():
            chat_histories[chat_id] = [{
                'role': 'assistant',
                'content': 'Hi! 👋 I am an AI Advisor BOT by SDU University.'
            }]
        history = chat_histories[chat_id]
        current = {
            'role': 'user',
            'content': text
        }
        history.append(current)
        answer = get_answer(history)
        if answer is None:
            bot.send_message(chat_id, 'Sorry, can you repeat the question.')
            return
        history.append(answer)
        chat_histories[chat_id] = history
        end_time = time.time()
        time_taken = round(end_time - start_time, 2)
        bot.send_message(chat_id, answer['content'] + f"\n\nThe time spent on executing the request: <b>{time_taken}</b> seconds ⏳", parse_mode="HTML")

    else:
        period = convert_ordinal_to_number(period)
        print(
            f"Document Type: {document_type}, Measurement: {measurement}, Period: {period}"
        )
        df = transcript_import(chat_id)

        # df.drop(columns=["chatID"], inplace=True)  # Delete the "chatID" column
        print(chat_id)

        df["Point"] = df["Point"].replace(np.nan, 0)
        print(df)
        transcripts_folder = "Transcripts"
        if not os.path.exists(transcripts_folder):
            os.makedirs(transcripts_folder)
        pdf = FPDF(orientation="L")
        pdf.add_page()
        pdf.add_font("DejaVu", "", "DejaVuSansCondensed.ttf", uni=True)
        pdf.set_font("DejaVu", "", 8)
        filtered_df = df[df["Study Year"] == int(period)]
        # filtered_df = filtered_df.drop(columns=["chatID"])
        sorted_df = filtered_df.sort_values(by=["Study Program"])
        sorted_df = filtered_df.drop(columns=["chatID", "Study Program", "Study Year"])
        print(sorted_df)
        # file_path = os.path.join(
        #     transcripts_folder, f"{chat_id}_transcript_{study_year}.xlsx"
        # )
        # sorted_df.to_excel(file_path, index=False)

        # # Add a button for all study years
        # keyboard_all = types.InlineKeyboardMarkup()
        # keyboard_all.add(
        #     types.InlineKeyboardButton(
        #         "All Study Years", callback_data="study_year_all"
        #     )
        # )

        # keyboard = types.InlineKeyboardMarkup()
        # keyboard.add(
        #     types.InlineKeyboardButton("Go to menu", callback_data="main_page")
        # )
        # with open(file_path, "rb") as file:
        #     bot.send_document(chat_id, file, reply_markup=keyboard)
        #     # bot.send_message(
        #     #     chat_id, "Please select a study year:", reply_markup=keyboard_all
        #     # )

        col_widths = get_max_column_widths(pdf, sorted_df)

        row_height = 10

        # Adding column headers
        for col_width, col in zip(col_widths, sorted_df.columns):
            pdf.cell(col_width, row_height, str(col), border=1)
        pdf.ln(row_height)

        # Adding data rows
        for row in sorted_df.values:
            for col_width, item in zip(col_widths, row):
                pdf.cell(col_width, row_height, str(item), border=1)
            pdf.ln(row_height)

        # Save PDF to file
        file_path_pdf = f"{transcripts_folder}/{chat_id}_transcript_{period}.pdf"
        pdf.output(file_path_pdf)

        # Send PDF to user via Telegram Bot
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Go to menu", callback_data="main_page")
        )

        # Open and send the PDF file as a document
        try:
            with open(file_path_pdf, "rb") as file:
                bot.send_document(chat_id, file, reply_markup=keyboard)
        except FileNotFoundError:
            print("Error: File not found.")

    
    if chat_id not in chat_histories.keys():
        chat_histories[chat_id] = [{
            'role': 'assistant',
            'content': 'Hi! 👋 I am an AI Advisor BOT by SDU University.'
        }]
    
    # history = chat_histories[chat_id]
    # current = {
    #     'role': 'user',
    #     'content': text
    # }
    # history.append(current)
    # answer = get_answer(history)
    # if answer is None:
    #     bot.send_message(chat_id, 'Sorry, can you repeat the question.')
    #     return
    # history.append(answer)
    # chat_histories[chat_id] = history
    # bot.send_message(chat_id, answer['content'])


bot.polling()
