# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, Checkbutton, scrolledtext
from tkcalendar import Calendar
import requests
import hashlib
import base64
import json
from datetime import datetime, timedelta
import sqlite3
import os

def log_message(message):
    global log_text
    log_text.configure(state='normal')
    log_text.insert(tk.END, message + "\n")
    log_text.configure(state='disabled')
    log_text.yview(tk.END)  # Przewijanie do najnowszego komunikatu

# Łączenie z plikiem konfiguracyjnym i pobranie danych z JSON
def load_config(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as file:
            return json.load(file)
    else:
        raise FileNotFoundError(f"Nie znaleziono pliku konfiguracyjnego: {filename}")

config = load_config('config.json')

# --- Funkcje pomocnicze (START) ---
def sign_url(api_id, api_key, timestamp, json_payload):
    signable = f"{api_id}{timestamp}{json_payload}".encode()
    raw_signature = hashlib.sha256(signable).digest()
    base64_signature = base64.b64encode(raw_signature).decode()
    return base64_signature

def create_table_from_response_data(c, table_name, data):
    if not data:
        return

    # Usuwanie istniejącej tabeli, jeśli istnieje
    #c.execute(f"DROP TABLE IF EXISTS {table_name}")

    columns = ', '.join([f"{key} TEXT" for key in data[0].keys()])
    c.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})")

def insert_data_into_table(c, table_name, data):
    if not data:
        return

    columns = data[0].keys()
    first_column = next(iter(columns))  # Pobieranie nazwy pierwszej kolumny

    for record in data:
        placeholders = ', '.join(['?'] * len(record))
        query = f"SELECT COUNT(*) FROM {table_name} WHERE {first_column} = ?"
        c.execute(query, (record[first_column],))
        if c.fetchone()[0] == 0:
            c.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", list(record.values()))
                    
# --- Funkcje pomocnicze (KONIEC) ---

# --- Funkcja do wyboru wersji API (START) ---
def choose_api_version(endpoint):
    return API_VERSIONS.get(endpoint, "v1")
# --- Funkcja do wyboru wersji API (KONIEC) ---

# --- Uniwersalna funkcja odpytująca API (START) ---
def get_data_from_api(api_id, api_key, endpoint, user_input):
    endpoint_config = config['apiConfig']['endpoints'][endpoint]
    required_data = endpoint_config.get('requiredData', [])
    payload = {key: user_input.get(key, '') for key in required_data}
    version = config['apiConfig']['endpoints'][endpoint]['version']
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    json_payload = json.dumps(payload)
    signature = sign_url(api_id, api_key, timestamp, json_payload)
    url = f"{config['apiConfig']['baseUrl']}{endpoint_config['url'].format(version=version, apiId=api_id, timestamp=timestamp, signature=signature)}"
    headers = endpoint_config['headers']
    
    # Sprawdzanie, czy endpoint wymaga podziału na segmenty czasowe
    if 'PeriodStart' in payload and 'PeriodEnd' in payload:
        start_date = datetime.strptime(payload['PeriodStart'], '%Y%m%d')
        end_date = datetime.strptime(payload['PeriodEnd'], '%Y%m%d')
        while start_date < end_date:
            next_date = min(start_date + timedelta(days=90), end_date)
            segment_payload = payload.copy()
            segment_payload['PeriodStart'] = start_date.strftime('%Y%m%d')
            segment_payload['PeriodEnd'] = next_date.strftime('%Y%m%d')

            json_payload = json.dumps(segment_payload)
            signature = sign_url(api_id, api_key, timestamp, json_payload)
            response = requests.post(url, headers=headers, data=json_payload)
            
            if response.status_code != 200:
                log_message("ERROR", response.status_code)
                return None
            
            yield response.json()
            start_date = next_date

    else:
        response = requests.post(url, headers=headers, data=json_payload)
        if response.status_code == 200:
            yield response.json()
        else:
            log_message("ERROR", response.status_code)
            return None
        
# --- Uniwersalna funkcja odpytująca API (KONIEC) ---

# --- Główna logika programu z interfejsem graficznym (START) ---

# Funkcja do pobierania danych z API i zapisania do bazy danych
def fetch_and_save_data(api_id, api_key, endpoint, db_file, payload):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    log_message(f"Pobieranie danych dla {endpoint}...")
    data_generator = get_data_from_api(api_id, api_key, endpoint, payload)
    for data in data_generator:
        if data:
            create_table_from_response_data(c, endpoint, data)
            insert_data_into_table(c, endpoint, data)
            log_message(f"Pobrano dane dla {endpoint}")
        else:
            log_message(f"Błąd podczas pobierania danych dla {endpoint}")

    conn.commit()
    conn.close()
    
    
# Funkcja główna wywołująca program
    
def main():
    global log_text
    window = tk.Tk()
    window.title("Pobieranie danych z API Merit Aktiva")

    main_frame = tk.Frame(window)  
    main_frame.pack(fill='both', expand=True)
    
    columns_container = tk.Frame(window)
    columns_container.pack(side='top', fill='both', expand=True)

    columns = [tk.Frame(columns_container) for _ in range(3)]
    for column in columns:
        column.pack(side='left', fill='both', expand=True)

    endpoint_vars = {}
    additional_data_entries = {}
    calendar_entries = {}

    def toggle_fields(endpoint_name, is_checked, additional_data_entries):
        required_data = config['apiConfig']['endpoints'][endpoint_name].get('requiredData', [])
        for data_key in required_data:
            label, entry = additional_data_entries[f"{endpoint_name}_{data_key}"]
            if is_checked:
                label.config(state='normal')
                entry.config(state='normal')
            else:
                label.config(state='disabled')
                entry.config(state='disabled')

    def create_calendar(entry):
        def set_date():
            nonlocal cal
            date_str = cal.get_date()  # Pobiera datę w formacie mm/dd/yy
            date_obj = datetime.strptime(date_str, '%m/%d/%y')  # Konwersja na obiekt datetime
            formatted_date = date_obj.strftime('%Y%m%d')  # Formatowanie do yyyymmdd
            entry.delete(0, tk.END)
            entry.insert(0, formatted_date)
            top.destroy()

        top = tk.Toplevel(window)
        cal = Calendar(top, selectmode='day')
        cal.pack(pady=20)
        ok_button = tk.Button(top, text="OK", command=set_date)
        ok_button.pack()

    for i, (category_name, category_details) in enumerate(config['apiConfig']['endpointCategories'].items()):
        if not category_details['visible']:
            continue

        # Sprawdzenie, czy cała kategoria jest aktywna
        is_category_active = category_details.get('active', True)

        frame = tk.LabelFrame(columns[i % 3], text=category_name)
        frame.pack(fill='both', expand=True, padx=10, pady=5)

        for endpoint_name, endpoint_details in category_details['endpoints'].items():
            if not endpoint_details['visible']:
                continue

            endpoint_var = tk.BooleanVar(value=False)
            endpoint_vars[endpoint_name] = endpoint_var

            # Ustawienie stanu elementów na podstawie kategorii i endpointu
            checkbox_state = 'disabled' if not is_category_active or not endpoint_details['active'] else 'normal'
            cb = Checkbutton(frame, text=config['apiConfig']['endpoints'][endpoint_name]['description'], 
                            var=endpoint_var, 
                            state=checkbox_state,
                            command=lambda en=endpoint_name, ev=endpoint_var: toggle_fields(en, ev.get(), additional_data_entries))
            cb.pack(anchor='w')
            
            for data_key in config['apiConfig']['endpoints'][endpoint_name].get('requiredData', []):
                label = tk.Label(frame, text=f"{data_key} dla {endpoint_name}:")
                entry = tk.Entry(frame, state='disabled')
                if data_key.startswith("Period"):
                    entry.bind("<Button-1>", lambda event, e=entry: create_calendar(e) if e['state'] == 'normal' else None)
                    calendar_entries[endpoint_name] = entry
                label.pack()
                entry.pack()
                additional_data_entries[f"{endpoint_name}_{data_key}"] = (label, entry)

    # Pole tekstowe dla nazwy pliku bazy danych
    db_file_label = tk.Label(window, text="Nazwa pliku bazy danych:")
    db_file_label.pack()
    db_file_entry = tk.Entry(window)
    db_file_entry.insert(0, "testowa.db")
    db_file_entry.pack()
    
    # Przycisk do pobierania danych z aktualizacją
    def on_fetch_button_clicked():
        api_id = config['apiConfig']['apiId']  # Pobieranie ID API z pliku konfiguracyjnego
        api_key = config['apiConfig']['apiKey']  # Pobieranie klucza API z pliku konfiguracyjnego
        db_file = db_file_entry.get()

        user_input = {}
        for key, entry_tuple in additional_data_entries.items():
            entry = entry_tuple[1]  # Drugi element krotki to obiekt Entry
            user_input[key] = entry.get()

        for endpoint, is_checked in endpoint_vars.items():
            if is_checked.get():
                endpoint_config = config['apiConfig']['endpoints'][endpoint]
                required_data = endpoint_config.get('requiredData', [])
                payload = {data_key: user_input.get(f"{endpoint}_{data_key}", '') for data_key in required_data}
                fetch_and_save_data(api_id, api_key, endpoint, db_file, payload)

        messagebox.showinfo("Informacja", "Dane zostały pobrane i zapisane.")

    fetch_button = tk.Button(window, text="Pobierz dane", command=on_fetch_button_clicked)
    fetch_button.pack()
    
    # Ramka z informacją o autorze
    author_frame = tk.Frame(window)
    author_frame.pack(side='bottom', fill='x')
    author_label = tk.Label(author_frame, text="Aplikacja stworzona przez:\n Marek Zacharewicz \n Infotel Sp. z o.o. \n infotel.pl \n copyright (c) 2024 \n GNU v3.0")
    author_label.pack()

    def toggle_log_view():
        if log_text.winfo_viewable():
            log_text.pack_forget()  # Chowanie kontrolki z logami
        else:
            log_text.pack(fill=tk.BOTH, expand=True)  # Pokazywanie kontrolki z logami

    # Przycisk do przełączania widoczności logów
    toggle_log_button = tk.Button(window, text="Pokaż/Ukryj Logi", command=toggle_log_view)
    toggle_log_button.pack()

     # Kontrolka do wyświetlania logów
    log_text = scrolledtext.ScrolledText(window, state='disabled', height=10)
    log_text.pack(fill=tk.BOTH, expand=True)

    window.mainloop()

if __name__ == "__main__":
    main()
    
# --- Główna logika programu z interfejsem graficznym (KONIEC) ---