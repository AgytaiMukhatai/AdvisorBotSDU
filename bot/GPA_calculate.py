import pandas as pd
import matplotlib.pyplot as plt
from transcript import transcript_scrap, transcript_import
import time
import os


def gpa_calculate(chat_id):
    df = transcript_scrap(
        chat_id
    )  # Make sure this function is defined and returns a DataFrame

    df_cleaned = df.dropna(subset=["Point"])
    df_cleaned["Weighted_Points"] = df_cleaned["Point"] * df_cleaned["Credit / ECTS"]

    gpa_data = df_cleaned.groupby("Academic Year").agg(
        {"Weighted_Points": "sum", "Credit / ECTS": "sum"}
    )

    gpa_data["GPA"] = gpa_data["Weighted_Points"] / gpa_data["Credit / ECTS"]
    gpa_data["Cumulative_Mean_GPA"] = gpa_data["GPA"].expanding().mean()

    plt.figure(figsize=(10, 6))
    plt.plot(
        gpa_data.index, gpa_data["GPA"], marker="o", linestyle="-", label="Annual GPA"
    )
    plt.plot(
        gpa_data.index,
        gpa_data["Cumulative_Mean_GPA"],
        marker="o",
        linestyle="--",
        color="g",
        label="Cumulative Mean GPA",
    )
    mean_gpa = gpa_data["GPA"].mean()
    plt.text(
        0.5,
        0.98,
        f"Overall Mean GPA: {mean_gpa:.2f}",
        transform=plt.gca().transAxes,
        horizontalalignment="center",
        color="red",
        fontsize=12,
        verticalalignment="top",
    )
    plt.xlabel("Academic Year")
    plt.ylabel("GPA")
    plt.title("GPA by Academic Year")
    plt.ylim(gpa_data["GPA"].min() - 1, 4.1)  # Adjusted to show min GPA to 4.1
    plt.grid(True)
    plt.xticks(rotation=45)  # Rotate x-axis labels for better readability
    plt.legend()
    plt.tight_layout()
    # plt.show()
    # filename = f"GPA_plot\\{chat_id}_GPA.png"
    # plt.savefig(filename)
    directory = "GPA_plot"
    if not os.path.exists(directory):
        os.makedirs(directory)

    filename = os.path.join(directory, f"{chat_id}_GPA.png")
    plt.savefig(filename)
    plt.close()  # Close the plot to free up memory
    time.sleep(1)
    return filename
