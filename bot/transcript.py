import pandas as pd
import requests
from bs4 import BeautifulSoup
import sqlite3


def get_username_password(chat_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT username, password FROM users WHERE chat_id = ?", (chat_id,))
    result = c.fetchone()
    conn.close()
    return result


def transcript_scrap(chat_id):
    username, password = get_username_password(chat_id)
    login_data = {
        "username": username,
        "password": password,
        "modstring": "",
        "LogIn": " Log in ",
    }
    print(login_data)
    login_url = "https://oldmy.sdu.edu.kz/index.php"
    transcript_url = "https://oldmy.sdu.edu.kz/index.php?mod=transkript"
    with requests.Session() as session:
        login_response = session.post(login_url, data=login_data, verify=False)
        transcript_response = session.get(transcript_url)
    soup = BeautifulSoup(transcript_response.text, "html.parser")

    rows = soup.find_all("tr")
    academic_year = []
    course_code = []
    course_title = []
    internal_credit = []
    credit_ects = []
    grade = []
    letter_grade = []
    point = []
    traditional = []

    # Initialize a variable to store the current academic year
    current_academic_year = None

    # Iterate over each <tr> tag and extract data into respective lists
    for row in rows:
        # Check if it's an academic year row
        academic_year_cell = row.find("td", colspan="6")
        if academic_year_cell:
            current_academic_year = academic_year_cell.get_text(strip=True)
        else:
            cols = row.find_all("td", class_="clsTd")
            if len(cols) == 8:
                academic_year.append(current_academic_year)
                course_code.append(cols[0].get_text(strip=True))
                course_title.append(cols[1].get_text(strip=True))
                internal_credit.append(cols[2].get_text(strip=True))
                credit_ects.append(cols[3].get_text(strip=True))
                grade.append(cols[4].get_text(strip=True))
                letter_grade.append(cols[5].get_text(strip=True))
                point.append(cols[6].get_text(strip=True))
                traditional.append(cols[7].get_text(strip=True))

    # Create a DataFrame from the extracted data
    df = pd.DataFrame(
        {
            "Academic Year": academic_year,
            "Course code": course_code,
            "Course title": course_title,
            "Internal Credit": internal_credit,
            "Credit / ECTS": credit_ects,
            "Grade": grade,
            "Letter Grade": letter_grade,
            "Point": point,
            "Traditional": traditional,
        }
    )

    def extract_study_program(academic_year):
        # Split the academic year string by whitespace
        parts = academic_year.split()
        # The study program is usually the last part of the academic year
        study_program = parts[-1]
        return study_program

    # Apply the function to extract the study program from the "Academic Year" column
    df["Study Program"] = df["Academic Year"].apply(extract_study_program)

    start_course = int(df["Academic Year"][0].split()[0])

    def map_study_year(academic_year):
        # Split the academic year range by whitespace and retrieve the starting year
        start_year = int(academic_year.split()[0])
        # Calculate the study year based on the starting year
        study_year = (start_year - start_course) + 1
        return study_year

    df["Study Year"] = df["Academic Year"].apply(map_study_year)
    df["Internal Credit"] = pd.to_numeric(df["Internal Credit"], errors="coerce")
    df["Credit / ECTS"] = pd.to_numeric(df["Credit / ECTS"], errors="coerce")
    df["Study Program"] = pd.to_numeric(df["Study Program"], errors="coerce")
    df["Grade"] = pd.to_numeric(df["Grade"], errors="coerce")
    df["Point"] = pd.to_numeric(df["Point"], errors="coerce")
    df["chatID"] = chat_id

    conn = sqlite3.connect("transcripts.db")
    c = conn.cursor()

    # Create the transcripts table if it doesn't exist
    c.execute(
        f"""CREATE TABLE IF NOT EXISTS u{chat_id} (
                    Academic_Year TEXT,
                    Course_Code TEXT,
                    Course_Title TEXT,
                    Internal_Credit INTEGER,
                    Credit_ECTS INTEGER,
                    Grade REAL,
                    Letter_Grade TEXT,
                    Point REAL,
                    Traditional TEXT,
                    Study_Program INTEGER,
                    Study_Year INTEGER,
                    chatID INTEGER
                )"""
    )

    # Commit changes to the database
    conn.commit()

    # Insert transcript data into the transcripts table
    # Add chatID column to the DataFrame
    df.to_sql(f"u{chat_id}", conn, if_exists="replace", index=False)

    # Close the connection
    conn.close()
    return df


def transcript_import(chat_id):
    # Connect to the SQLite database
    conn = sqlite3.connect("transcripts.db")

    # Construct the SQL query to select all columns from the user's transcript table
    sql_query = f"SELECT * FROM u{chat_id}"

    # Use pandas to read the SQL query result directly into a DataFrame
    df = pd.read_sql_query(sql_query, conn)

    # Close the connection
    conn.close()

    return df
