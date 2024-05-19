import pandas as pd
import requests
from bs4 import BeautifulSoup
import sqlite3


# chat_id = "767413484"


def get_username_password(chat_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT username, password FROM users WHERE chat_id = ?", (chat_id,))
    result = c.fetchone()
    conn.close()
    return result


def transcript_gpa_scrap(chat_id):
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
    rows = soup.find_all("tr", style="color:Maroon; font-size:10px; font-weight:bold")

    # Extract data from each row
    data = []

    for row in rows[:-1]:
        cols = row.find_all("td")
        # Extract text from each cell, handle empty cells and strip spaces
        cols = [ele.text.strip() if ele.text.strip() != "" else None for ele in cols]
        data.append(cols[2:])

    # Create a DataFrame
    df_sopu = pd.DataFrame(
        data, columns=["Internal_Credit", "Credit_ECTS", "SA", "GA", "SPA", "GPA"]
    )

    df_sopu["SA"] = df_sopu["SA"].str.replace("SA : ", "")
    df_sopu["GA"] = df_sopu["GA"].str.replace("GA : ", "")
    df_sopu["SPA"] = df_sopu["SPA"].str.replace("SPA : ", "")
    df_sopu["GPA"] = df_sopu["GPA"].str.replace("GPA : ", "")
    df_sopu[["Internal_Credit", "Credit_ECTS", "SA", "GA", "SPA", "GPA"]] = df_sopu[
        ["Internal_Credit", "Credit_ECTS", "SA", "GA", "SPA", "GPA"]
    ].apply(pd.to_numeric, errors="coerce")
    df_sopu["chatID"] = chat_id

    print(df_sopu)

    conn = sqlite3.connect("transcriptsgpa.db")
    c = conn.cursor()

    # Create a table with a name dynamically generated from the chat_id
    c.execute(
        f"""CREATE TABLE IF NOT EXISTS u{chat_id} (
                    Internal_Credit INTEGER,
                    Credit_ECTS INTEGER,
                    SA REAL,
                    GA REAL,
                    SPA REAL,
                    GPA REAL,
                    chatID
                )"""
    )
    df_sopu.to_sql(f"u{chat_id}", conn, if_exists="replace", index=False)
    conn.close()


def transcript_gpa_import(chat_id):
    # Connect to the SQLite database
    conn = sqlite3.connect("transcriptsgpa.db")

    # Construct the SQL query to select all columns from the user's transcript table
    sql_query = f"SELECT * FROM u{chat_id}"

    # Use pandas to read the SQL query result directly into a DataFrame
    df = pd.read_sql_query(sql_query, conn)

    # Close the connection
    conn.close()

    return df
