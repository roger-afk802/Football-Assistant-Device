# user_input_gui.py

import tkinter as tk
from tkinter import ttk
def get_user_settings(match_list):
    result = {}

    window = tk.Tk()
    window.title("")
    window.geometry("400x400")

    title_label = tk.Label(
        window,
        text="Football Assistant",
        font=("Arial", 18, "bold")
    )
    title_label.pack(pady=10)

    match_label = tk.Label(
        window,
        text="選擇要看的比賽："
    )
    match_label.pack()

    
    display_list = [
        f'{match["home"]} vs {match["away"]}'
        for match in match_list
    ]

    match_var = tk.StringVar()

    match_box = ttk.Combobox(
        window,
        textvariable=match_var,
        values=display_list,
        state="readonly",
        width=35
    )
    match_box.pack(pady=5)

    if display_list:
        match_box.current(0)

    time_label = tk.Label(
        window,
        text="明天幾點有事？例如 08:00"
    )
    time_label.pack(pady=(15, 0))

    time_entry = tk.Entry(window)
    time_entry.pack()
    time_entry.insert(0, "08:00")

    event_label = tk.Label(
        window,
        text="明天要做什麼？"
    )
    event_label.pack(pady=(15, 0))

    event_entry = tk.Entry(window)
    event_entry.pack()
    event_entry.insert(0, "上課")

    def submit():
        selected_index = match_box.current()

        if selected_index == -1:
            print("請先選擇一場比賽")
            return

        # 回傳整筆 dictionary
        result["match"] = match_list[selected_index]
        result["event_time"] = time_entry.get()
        result["event_name"] = event_entry.get()

        window.destroy()

    submit_button = tk.Button(
        window,
        text="確認",
        command=submit
    )
    submit_button.pack(pady=20)

    window.mainloop()

    return result