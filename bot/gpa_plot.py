import matplotlib.pyplot as plt
import numpy as np
from scipy.special import jv
from transcript_gpa import transcript_gpa_scrap, transcript_gpa_import
import os
import time
from transcript import transcript_scrap, transcript_import

# Importing the style and setting it
# chat_id = "767413484"


def gpa_plot(chat_id):
    df_soup = transcript_gpa_import(chat_id)
    plt.style.use(
        "https://github.com/dhaitz/matplotlib-stylesheets/raw/master/pitayasmoothie-dark.mplstyle"
    )

    if df_soup["SA"].iloc[-1] == 0:
        df_soup = df_soup.iloc[:-1]

    x = 1 + 0.5 * df_soup.index

    plt.plot(x, df_soup["GPA"], marker="o", linestyle="--", color="C0", label="GPA")
    plt.plot(x, df_soup["SPA"], marker="o", linestyle="--", color="C1", label="SPA")
    plt.xlabel("Course")
    plt.ylabel("Values")
    plt.ylim(df_soup[["GPA", "SPA"]].min().min() - 1, 4.1)
    plt.xticks(x)
    plt.legend()

    # Add text annotation for overall mean GPA
    mean_gpa = df_soup["GPA"].iloc[-1]
    # print(mean_gpa)
    plt.text(
        0.5,
        0.98,
        f"Overall GPA: {mean_gpa:.2f}",
        transform=plt.gca().transAxes,
        horizontalalignment="center",
        fontsize=12,
        verticalalignment="top",
        color="orange",  # Change color to orange
    )

    # plt.show()
    directory = "GPA_plot"
    if not os.path.exists(directory):
        os.makedirs(directory)

    filename = os.path.join(directory, f"{chat_id}_GPA.png")
    plt.savefig(filename)
    time.sleep(1)
    plt.close()  # Close the plot to free up memory
    return filename


def sbj_plot(chat_id):
    df = transcript_import(chat_id)
    df["Course code"] = df["Course code"].str.extract(r"^(\w+)")

    # Use the specified stylesheet
    plt.style.use(
        "https://github.com/dhaitz/matplotlib-stylesheets/raw/master/pitayasmoothie-dark.mplstyle"
    )

    # Accessing the default colors from the style
    default_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    # Calculate the mean grade for each unique course code
    mean_grades = df.groupby("Course code")["Grade"].mean()

    # Define colors using default colors
    colors = [
        default_colors[0] if grade >= mean_grades.median() else default_colors[1]
        for grade in mean_grades
    ]

    # Plotting
    plt.figure(figsize=(10, 6))
    mean_grades.plot(kind="bar", color=colors)
    plt.xlabel("Course code")
    plt.ylabel("Mean Grade")
    plt.title("Mean Grade for Each Course Code")
    plt.grid(True)  # Add grid
    # plt.show()
    directory = "SBJ_plot"
    if not os.path.exists(directory):
        os.makedirs(directory)

    filename = os.path.join(directory, f"{chat_id}_SBJ.png")
    plt.savefig(filename)
    time.sleep(1)
    plt.close()  # Close the plot to free up memory
    return filename
