# 360ksiegowoscAPI

Program do pobierania (aktualnie tylko do pobierania danych wszytkie endpointy z początkiem "GET") danych z API Merit Activa program.360ksiegowosc.pl Dane zapisuje w bazie SQLite3

konfiguracja ustawień do komunikacji api znajduje się w pliku config.json zgodnie z dokumentacją API Merit Activa którą możemy znaleźć na stronie https://api.merit.ee/merit-aktiva-api/

Wyjaśnienie części pliku konfiguracyjnego: potrzebujemy API ID oraz API KEY który musimy wygenerować w ustawieniach baseURL jest to pierwszy człon URL używany do komunikacji dla 360ksiegowosc jest to https://program.360ksiegowosc.pl/api

w następnej części mamy ustawienia "endpointów"

"getinvoices": { #nazwa endpoint

"version": "v1", #wersja

"method": "POST", #metoda zapytań

"url": "/v1/getinvoices?ApiId={apiId}&timestamp={timestamp}&signature={signature}", #drugi człon URL

"requiredData": [ # tu możemy dodać wymagane dane do zapytania

"PeriodStart", # np. jeśli endpoint wymaga daty początkowej

"description": "Pobierz listę faktur sprzedaży" # opis endpointa wyświetlany w GUI

na końcu mamy kategorie endpointów (do przyjaznego wyświetlania w GUI)

jeśli mamy endpoint w ustawieniach musimy mieć go również w kategoriach.

Program do dalszego rozwoju 

Nie testowałem dla wersji estońskiej nie mam dostępu do kluczy API
