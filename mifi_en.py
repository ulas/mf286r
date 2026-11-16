#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mifi_en.py - eko.one.pl "mifi" (OpenWrt + easyconfig) firmware arayuzunu
Lehceden Ingilizceye cevirir ve yeni bir sysupgrade imaji uretir.

Kullanim (Linux / WSL, root yetkisiyle):
    sudo python3 mifi_en.py mifi-XX-...-sysupgrade.bin            (-> ...-sysupgrade-EN.bin)
    sudo python3 mifi_en.py mifi-XX-...-sysupgrade.bin -o cikti.bin
    sudo python3 mifi_en.py *-sysupgrade.bin                      (toplu: her biri icin ...-EN.bin)
  Secenekler: --no-theme (Preline temasi eklenmez), --no-tr (Turkce eklenmez)

Gerekenler: python3, squashfs-tools (unsquashfs, mksquashfs)
Istege bagli: node (JS sozdizimi kontrolu), wordfreq (daha iyi Lehce tespiti)
"""
import os, re, sys, io, json, struct, shutil, tarfile, tempfile, subprocess, zlib

FULL = {'</strong>. Wybierz ': '</strong>. Press ',
 ' z ': ' of ',
 '% z ': '% of ',
 ' (od ': ' (since ',
 '<span class="visible-xs oneline"></span> (od ': '<span class="visible-xs oneline"></span> (since ',
 '</span><span class="visible-xs oneline"></span><span> (od ': '</span><span class="visible-xs oneline"></span><span> (since ',
 '<div class="col-xs-10">Od: ': '<div class="col-xs-10">From: ',
 'Ping do DNS1 (': 'Ping to DNS1 (',
 'Ping do DNS2 (': 'Ping to DNS2 (',
 'Ping do ': 'Ping to ',
 'Wykryj...': 'Detect...',
 '<table class="table"><tr><td>Dzień / Godzina</td><td>Po</td><td>Wt</td><td>Śr</td><td>Cz</td><td>Pi</td><td>So</td><td>Ni</td></tr>': '<table class="table"><tr><td>Day / '
                                                                                                                                        'Hour</td><td>Mo</td><td>Tu</td><td>We</td><td>Th</td><td>Fr</td><td>Sa</td><td>Su</td></tr>',
 '<bez nazwy>': '<no name>',
 'lat': 'years',
 'Tak': 'Yes',
 'Nie': 'No',
 'maj': 'May'}

PHR = {'brak domeny': 'no domain',
 'ograniczenia': 'restrictions',
 'Wybudzanie': 'Wake',
 'sposób połączenia': 'connection method',
 'dla': 'for',
 'zduplikowane': 'duplicate',
 'porzucaj': 'drop',
 'z dekodowaniem 7BIT': 'with 7BIT decoding',
 'z dekodowaniem UCS': 'with UCS decoding',
 'maj': 'May',
 'Ustawienia': 'Settings',
 'Bezpieczeństwo': 'Security',
 'Sieci dodatkowe': 'Additional networks',
 'Sieć dodatkowa': 'Additional network',
 'Monitor połączenia': 'Connection monitor',
 'Sieci Wi-Fi': 'Wi-Fi networks',
 'Klienci': 'Clients',
 'Historia połączeń': 'Connection history',
 'historia połączeń': 'connection history',
 'Zapytania DNS': 'DNS queries',
 'zapytania DNS': 'DNS queries',
 'Blokada domen': 'Domain blocking',
 'Tryb nocny': 'Night mode',
 'Wyloguj': 'Log out',
 'Logowanie': 'Login',
 'Aktualizacja': 'Update',
 'Diagnostyka': 'Diagnostics',
 'Odśwież': 'Refresh',
 'Hasło': 'Password',
 'Sygnał': 'Signal',
 'Technologia': 'Technology',
 'Status karty SIM': 'SIM card status',
 'więcej parametrów': 'more parameters',
 'lokalizacja stacji bazowej': 'base station location',
 'połączonych: 0': 'connected: 0',
 'połączonych: ': 'connected: ',
 'Liczba wznowień połączenia': 'Number of reconnections',
 'Czas połączenia': 'Connection time',
 'Wysłano wiadomość': 'Message sent',
 'Wysłano': 'Sent',
 'wysłano': 'sent',
 'Pobrano': 'Downloaded',
 'pobrano': 'downloaded',
 'odebrano': 'received',
 'Adres IP w DMZ': 'DMZ IP address',
 'Adres IP': 'IP address',
 'adres IP': 'IP address',
 'Maska': 'Netmask',
 'Brama': 'Gateway',
 'Serwery DNS': 'DNS servers',
 'wyłączony dostęp sieci lokalnej do internetu': 'local network access to the internet is disabled',
 'Wykorzystywane kanały': 'Channels in use',
 'Połączonych klientów': 'Connected clients',
 'Sieć lokalna': 'Local network',
 'Czas pracy': 'Uptime',
 'Udział w ruchu': 'Traffic share',
 'Obciążenie': 'Load',
 'Data i czas': 'Date and time',
 'Typ połączenia': 'Connection type',
 'typ połączenia': 'connection type',
 'Urządzenie': 'Device',
 'panel zarządzania modemu': 'modem management panel',
 'Nazwa użytkownika': 'Username',
 'Próg błędu echa LCP': 'LCP echo failure threshold',
 'Interwał echa LCP': 'LCP echo interval',
 'Adres MAC': 'MAC address',
 'adres MAC': 'MAC address',
 'opis serwera': 'server description',
 'Połączenie mierzone': 'Metered connection',
 'połączenie ma ograniczenia danych lub wiąże się z opłatami': 'the connection has data limits or incurs charges',
 'Dostęp z sieci lokalnej': 'Access from local network',
 'umożliwia dostęp sieci lokalnej do internetu przez': 'allows the local network to access the internet via',
 'musi być z tej samej klasy co sieć lokalna': 'must be in the same subnet as the local network',
 'Serwer DHCP włączony': 'DHCP server enabled',
 'Przechwytywanie zapytań DNS': 'Intercept DNS queries',
 'Logowanie zapytań DNS': 'Log DNS queries',
 'Port WAN dołączony do sieci lokalnej': 'WAN port bridged to local network',
 'Wi-Fi włączone': 'Wi-Fi enabled',
 'Moc nadawania': 'Transmit power',
 'Nazwa sieci (SSID)': 'Network name (SSID)',
 'Kanał': 'Channel',
 'Szyfrowanie Point-to-Point (MPPE)': 'Point-to-Point encryption (MPPE)',
 'Szyfrowanie': 'Encryption',
 'Izolacja klientów': 'Client isolation',
 'Sieć ukryta': 'Hidden network',
 'Losowy adres MAC': 'Random MAC address',
 'Nazwa systemu': 'System name',
 'Wysyłanie statystyki': 'Send statistics',
 'zobacz statystykę': 'view statistics',
 'Przycisk "': 'Button "',
 'Aktywny przycisk reset': 'Reset button active',
 'Okres zapisu danych': 'Data save interval',
 '1 minuta': '1 minute',
 '3 minuty': '3 minutes',
 '5 minut': '5 minutes',
 '10 minut': '10 minutes',
 '15 minut': '15 minutes',
 '30 minut': '30 minutes',
 '1 godzina': '1 hour',
 '3 godziny': '3 hours',
 '6 godzin': '6 hours',
 '12 godzin': '12 hours',
 '24 godziny': '24 hours',
 'Pobieranie danych...': 'Fetching data...',
 'Producent': 'Manufacturer',
 'Wersja oprogramowania': 'Firmware version',
 'Wersja GUI': 'GUI version',
 'Wersja': 'Version',
 'Identyfikator modemu (IMEI)': 'Modem identifier (IMEI)',
 'Numer karty SIM (ICCID)': 'SIM card number (ICCID)',
 'Identyfikator abonenta (IMSI)': 'Subscriber identifier (IMSI)',
 'ustawienia dodatkowe': 'advanced settings',
 'polecenia AT': 'AT commands',
 'pasma LTE': 'LTE bands',
 'pasma 5G NSA': '5G NSA bands',
 'pasma 5G SA': '5G SA bands',
 'Pasma LTE': 'LTE bands',
 'Pasma 5G NSA': '5G NSA bands',
 'Pasma 5G SA': '5G SA bands',
 'Aktywny slot SIM': 'Active SIM slot',
 'Numer seryjny': 'Serial number',
 'Restart urządzenia': 'Reboot device',
 'Przywrócenie ustawień domyślnych': 'Factory reset',
 'Interfejs użytkownika': 'User interface',
 'historia zmian': 'changelog',
 'Motyw': 'Theme',
 'jasny': 'light',
 'ciemny': 'dark',
 'automatycznie': 'automatic',
 'Dostępność aktualizacji': 'Update availability',
 'Pobieranie aktualizacji': 'Downloading update',
 'Zachowaj ustawienia': 'Keep settings',
 'Pomoc': 'Help',
 'opis funkcji': 'feature description',
 'Połączenie z internetem jest wyłączone.': 'Internet connection is disabled.',
 'Kliknij tutaj aby ustawić połączenie': 'Click here to set up the connection',
 'Ostatnie sprawdzenie': 'Last check',
 'maksimum': 'maximum',
 'Opóźnienie przy starcie systemu': 'Delay at system startup',
 '[1 - 59] minut': '[1 - 59] minutes',
 'Adres lub nazwa serwera': 'Server address or name',
 'Adres lub nazwa': 'Address or name',
 'Okres sprawdzenia': 'Check interval',
 'Liczba nieudanych sprawdzeń': 'Number of failed checks',
 'Akcja': 'Action',
 'Ponowne uruchomienie połączenia z internetem': 'Restart internet connection',
 'ponowne uruchomienie połączenia z internetem': 'restart internet connection',
 'Ponowne uruchomienie urządzenia': 'Reboot device',
 'ponowne uruchomienie urządzenia': 'reboot device',
 'Wyliczenia mogą się różnić od wskazań operatora': "Calculations may differ from the operator's figures",
 'Dziś': 'Today',
 'Wczoraj': 'Yesterday',
 'Ostatnie 7 dni': 'Last 7 days',
 'Ostatnie 30 dni': 'Last 30 days',
 'Łącznie': 'Total',
 'Dni do końca okresu rozliczeniowego': 'Days until end of billing period',
 'Bieżący okres rozliczeniowy': 'Current billing period',
 'Przewidywane zużycie danych w bieżącym okresie': 'Projected data usage in current period',
 'Poprzedni okres rozliczeniowy': 'Previous billing period',
 'Okres rozliczeniowy': 'Billing period',
 'Początek okresu rozliczeniowego': 'Start of billing period',
 'dzień miesiąca': 'day of month',
 'liczba dni': 'number of days',
 'Liczba dni w okresie': 'Number of days in period',
 'dzień': 'day',
 'miesiąc': 'month',
 'styczeń': 'January',
 'luty': 'February',
 'marzec': 'March',
 'kwiecień': 'April',
 'czerwiec': 'June',
 'lipiec': 'July',
 'sierpień': 'August',
 'wrzesień': 'September',
 'październik': 'October',
 'listopad': 'November',
 'grudzień': 'December',
 'Ostrzeżenie włączone': 'Warning enabled',
 'Poziom ostrzeżenia': 'Warning level',
 'Kod USSD': 'USSD code',
 'wybierz kod USSD': 'select USSD code',
 'Numer telefonu': 'Phone number',
 'Treść wiadomości': 'Message text',
 'liczba wiadomości do wysyłania:': 'messages to send:',
 'blokada dostępu do internetu bez połączenia VPN': 'block internet access without a VPN connection',
 'Brak sieci VPN': 'No VPN networks',
 'Liczba blokowanych domen': 'Number of blocked domains',
 'Własna lista domen': 'Custom domain list',
 'Domeny blokowane': 'Blocked domains',
 'Domeny dozwolone': 'Allowed domains',
 'Domena': 'Domain',
 'Włączenie Wi-Fi': 'Wi-Fi on',
 'Wyłączenie Wi-Fi': 'Wi-Fi off',
 'Diody LED': 'LEDs',
 'Włączenie LED': 'LEDs on',
 'Wyłączenie LED': 'LEDs off',
 'Automatyczny tryb nocny': 'Automatic night mode',
 'Szerokość geograficzna': 'Latitude',
 'Długość geograficzna': 'Longitude',
 'Pozycja GPS': 'GPS position',
 'Pozycja z GPS': 'Position from GPS',
 'Czas odczytu': 'Reading time',
 'Wysokość': 'Altitude',
 'Kierunek': 'Heading',
 'Szybkość pobierania': 'Download speed',
 'Szybkość wysyłania': 'Upload speed',
 'Szybkość': 'Speed',
 'Brak urządzeń do wybudzenia': 'No devices to wake',
 'Hasło jest wspólne dla interfejsu użytkownika oraz SSH': 'The password is shared by the user interface and SSH',
 'Nowe hasło': 'New password',
 'Potwierdź hasło': 'Confirm password',
 'wyłączenie uniemożliwia logowanie przez protokół SSH': 'disabling prevents login via SSH',
 'Logowanie przy pomocy hasła': 'Password login',
 'po wyłączeniu możliwe jest logowanie tylko przy pomocy kluczy': 'when disabled, login is only possible with keys',
 'Port (sieć lokalna)': 'Port (local network)',
 'port połączenia z sieci lokalnej': 'port for connections from the local network',
 'port połączenia z internetu, zostaw puste aby wyłączyć dostęp z internetu': 'port for connections from the internet, leave empty to disable internet access',
 'Wymagaj uwierzytelniana': 'Require authentication',
 'wymagane podanie hasła przy logowaniu przez UART/port szeregowy': 'password required when logging in via UART/serial port',
 'Zmiana nazwy/typu dla "': 'Change name/type for "',
 'zmiana nazwy/typu': 'change name/type',
 'Nowa nazwa': 'New name',
 'Typ klienta': 'Client type',
 'typ klienta': 'client type',
 'Statyczny adres IP dla "': 'Static IP address for "',
 'Rozłączenie klienta może być niezbędne do pobrania statycznego adresu IP': 'Disconnecting the client may be necessary for it to obtain the static IP address',
 'Statyczny adres IP': 'Static IP address',
 'statyczny adres IP': 'static IP address',
 'obecny statyczny adres IP:': 'current static IP address:',
 'Rozłącz klienta': 'Disconnect client',
 'Blokada dostępu do internetu dla "': 'Internet access block for "',
 'Stała': 'Permanent',
 'Czasowa': 'Scheduled',
 'blokada dostępu': 'access blocked',
 'zaznacz wszystko': 'select all',
 'odznacz wszystko': 'deselect all',
 'Limit szybkości dla "': 'Speed limit for "',
 'Włączony jest flow offloading, limitowanie prędkości może nie działać': 'Flow offloading is enabled, speed limiting may not work',
 'Aby działało limitowanie prędkości należy ustawić statyczny adres IP': 'A static IP address must be set for speed limiting to work',
 'Wysyłanie do': 'Upload up to',
 'Mbps, 0 - brak limitu': 'Mbps, 0 - no limit',
 'Pobieranie do': 'Download up to',
 'Wykryto modem komórkowy, podaj PIN do karty SIM': 'Cellular modem detected, enter the SIM card PIN',
 'Ustawienia modemu': 'Modem settings',
 'Interfejs diagnostyczny modemu': 'Modem diagnostic interface',
 'Odczyt danych przez QMI/MBIM': 'Read data via QMI/MBIM',
 'Odczyt nazwy operatora z pliku': 'Read operator name from file',
 'Miejsce przechowywania SMS': 'SMS storage',
 'Określone przez modem': 'Defined by modem',
 'SM - pamięć karty SIM': 'SM - SIM card memory',
 'ME - pamięć modemu': 'ME - modem memory',
 'Łączenie wieloczęściowych SMS': 'Join multipart SMS',
 'Wysyłanie USSD bez kodowana PDU': 'Send USSD without PDU encoding',
 'Odbieranie USSD': 'Receive USSD',
 'bez dekodowania': 'without decoding',
 'z automatycznym wykrywaniem kodowania': 'with automatic encoding detection',
 'Polecenie AT': 'AT command',
 'Nowy VPN': 'New VPN',
 'Ręczna konfiguracja': 'Manual configuration',
 'Wczytywanie konfiguacji z pliku': 'Load configuration from file',
 'Wybierz plik': 'Choose file',
 'Nazwa pliku': 'File name',
 'Rozmiar pliku jest za duży': 'File size is too large',
 'Rozmiar': 'Size',
 'Uruchamianie': 'Startup',
 'Manualne': 'Manual',
 'Po starcie systemu': 'At system startup',
 'Po połączeniu do internetu': 'After connecting to the internet',
 'Sterowanie przyciskiem': 'Button control',
 'Ruch przychodzący': 'Incoming traffic',
 'odrzucaj': 'reject',
 'akceptuj': 'accept',
 'Zawartość pliku konfiguracyjnego': 'Configuration file contents',
 'Klucz prywatny ma nieprawidłową długość lub format': 'Private key has invalid length or format',
 'Klucz prywatny': 'Private key',
 'Klucz publiczny': 'Public key',
 'Tunele': 'Tunnels',
 'Klucz wstępny': 'Preshared key',
 'Dozwolony adres IP': 'Allowed IP address',
 'uruchamianie dotyczy wszystkich sieci ZeroTier': 'startup applies to all ZeroTier networks',
 'sterowanie dotyczy wszystkich sieci ZeroTier': 'control applies to all ZeroTier networks',
 'Wysyłanie na adres rozgłoszeniowy': 'Send to broadcast address',
 'Wybudzanie przyciskiem': 'Wake by button',
 'Dostęp do internetu': 'Internet access',
 'Zmiana stanu Wi-Fi przyciskiem': 'Toggle Wi-Fi by button',
 'Porty ethernet': 'Ethernet ports',
 'Nazwa portu': 'Port name',
 'Dołączony&nbsp;&nbsp;&nbsp;Przypisanie do sieci': 'Attached&nbsp;&nbsp;&nbsp;Network assignment',
 'Proszę czekać...': 'Please wait...',
 'kopiuj dane z poprzedniej sieci': 'copy data from previous network',
 'kod QR do połączenia': 'QR code for connecting',
 'Zapisz zmiany': 'Save changes',
 'Zapisać zmiany?': 'Save changes?',
 'Domyślne ust.': 'Defaults',
 'przywrócenie ustawień domyślnych': 'restore default settings',
 'Sprawdź online': 'Check online',
 'Sprawdź': 'Check',
 'Pobierz': 'Download',
 'Usuń dane': 'Delete data',
 'Usuń limity': 'Remove limits',
 'Wyślij': 'Send',
 'Zapisz': 'Save',
 'Zezwalaj': 'Allow',
 'Blokuj': 'Block',
 'Harmonogram wyłączenia Wi-Fi': 'Wi-Fi off schedule',
 'Harmonogram': 'Schedule',
 'Wybudź wszyst.': 'Wake all',
 'wybudza wszystkie urządzenia': 'wakes all devices',
 'Wybudź': 'Wake',
 'wybudź': 'wake',
 'Anuluj': 'Cancel',
 'Ustaw': 'Set',
 'Zamknij': 'Close',
 'Restart poł.': 'Reconnect',
 'przywraca domyślne ustawienia modemu': 'restores the modem default settings',
 'Dalej': 'Next',
 'Nowe klucze': 'New keys',
 'usuń adres IP': 'remove IP address',
 'Nowy adres IP': 'New IP address',
 'usuń tunel': 'remove tunnel',
 'usuń dozwolony adres IP': 'remove allowed IP address',
 'Nowy tunel': 'New tunnel',
 'Nowa': 'New',
 'Nowy': 'New',
 '(trwa uruchamianie)': '(starting)',
 'bajtów': 'bytes',
 'temu': 'ago',
 'title="Połączonych klientów: ': 'title="Connected clients: ',
 'title="połączony: ': 'title="connected: ',
 '" (typu ': '" (type ',
 'Usunąć ten VPN (typu ': 'Delete this VPN (type ',
 'musi być niepustym tekstem': 'must be a non-empty string',
 'musi być niepustą tablicą': 'must be a non-empty array',
 'musi być liczbą': 'must be a number',
 'musi być obiektem': 'must be an object',
 'plik jest pusty': 'file is empty',
 'plik musi zawierać obiekt {"klucz": "opis"}': 'file must contain an object {"key": "description"}',
 'plik musi zawierać tablicę [ {...}, {...} ]': 'file must contain an array [ {...}, {...} ]',
 'wartość dla "': 'value for "',
 'otrzymaną': 'received',
 'z listy blokowanych?': 'from the block list?',
 'z listy dozwolonych?': 'from the allow list?',
 'Wszyscy': 'All',
 'wszyscy': 'all',
 'wszystkie': 'all',
 'wszystko': 'all',
 'udziału w ruchu': 'traffic share',
 'udział w ruchu klientów bezprzewodowych': 'traffic share of wireless clients',
 'udziale w ruchu': 'traffic share',
 'połączony': 'connected',
 'blokady': 'blocking',
 'informacje': 'information',
 'limity': 'limits',
 'rozłącz': 'disconnect',
 'usuwanie danych': 'delete data',
 'aktywny': 'active',
 'aktywni': 'active',
 'ostatni raz': 'last time',
 'pierwszy raz': 'first time',
 'wielkość': 'size',
 'Wielkość': 'Size',
 'zachód słońca': 'sunset',
 'zachód': 'sunset',
 'transfer z ostatnich 30 dni': 'traffic for the last 30 days',
 'transfer miesięczny': 'monthly traffic',
 'transfer roczny': 'yearly traffic',
 'Wybierz': 'Choose',
 'Trwa aktualizowanie systemu...': 'System update in progress...',
 '(ostatnie 10)': '(last 10)',
 'Adres IP jest spoza zakresu adresacji sieci lokalnej': 'IP address is outside the local network address range',
 'Adres IP jest spoza zakresu adresacji sieci': 'IP address is outside the address range of network',
 'Data nie może być późniejsza': 'Date cannot be later',
 'Hasło do Wi-Fi musi mieć co najmniej 8 znaków': 'Wi-Fi password must be at least 8 characters long',
 'Nazwa Wi-Fi nie może być dłuższa niż 32 bajty': 'Wi-Fi name cannot be longer than 32 bytes',
 'Niektóre znaki (np. polskie litery lub emoji) zajmują więcej niż 1 bajt': 'Some characters (e.g. accented letters or emoji) take more than 1 byte',
 'Nie zmieniaj konfiguracji i nie wyłączaj urządzenia w czasie tego procesu.': 'Do not change the configuration or power off the device during this process.',
 'Nie zmieniaj ustawień i nie wyłączaj urządzenia w czasie tego procesu.': 'Do not change the settings or power off the device during this process.',
 'Taka data nie istnieje': 'Such a date does not exist',
 'adres jest już wykorzystywany w sieci "': 'the address is already used in network "',
 'Brak wiadomości': 'No messages',
 'Czas działania': 'Uptime',
 'Liczba klientów': 'Number of clients',
 'Po wykonaniu aktualizacji nastąpi ponowne uruchomienie urządzenia.': 'The device will reboot after the update.',
 'Wrogi AP': 'Rogue AP',
 'widoczność': 'last seen',
 'brak połączonych klientów': 'no connected clients',
 'Wi-Fi jest wyłączone. Harmonogram nie będzie działał dopóki Wi-Fi nie zostanie włączone.': 'Wi-Fi is disabled. The schedule will not work until Wi-Fi is enabled.',
 'Brak historii połączeń': 'No connection history',
 'Brak informacji o połączeniach klientów': 'No information about client connections',
 'Brak połączonych klientów': 'No connected clients',
 'Brak sieci bezprzewodowych lub Wi-Fi jest wyłączone': 'No wireless networks or Wi-Fi is disabled',
 'Brak sieci dodatkowych': 'No additional networks',
 'Brak zapytań DNS': 'No DNS queries',
 'Zapytanie': 'Query',
 'Zeskanuj kod QR aby połączyć się z siecią Wi-Fi': 'Scan the QR code to connect to the Wi-Fi network',
 'Sieci': 'Networks',
 'usuń': 'remove',
 'Typ': 'Type',
 'Opis': 'Description',
 'opis': 'description',
 'Klient': 'Client',
 'Czas odpowiedzi': 'Response time',
 'Czas': 'Time',
 'trwa nawiązywanie połączenia': 'connecting',
 'wyłączony': 'disabled',
 'Klientów bezprzewodowych': 'Wireless clients',
 'Klientów przewodowych': 'Wired clients',
 'Klientów bezprzew.': 'Wireless',
 'Klientów przew.': 'Wired',
 'Proponowane ustawienia': 'Suggested settings',
 'Opcje': 'Options',
 'teraz': 'now',
 'maks.': 'max.',
 'Liczba zapytań o niedostępne domeny': 'Queries for unavailable domains',
 'Liczba zapytań': 'Number of queries',
 'Kategoria': 'Category',
 'standard połączenia klientów bezprzewodowych': 'connection standard of wireless clients',
 'czas połączenia klientów bezprzewodowych': 'connection time of wireless clients',
 'sygnał klientów bezprzewodowych': 'signal of wireless clients',
 'Źródła': 'Sources',
 'Obsługiwane sieci bezprzewodowe': 'Supported wireless networks',
 'Zdalni klienci': 'Remote clients',
 'Zdalny klient': 'Remote client',
 'Liczba wiadomości': 'Number of messages',
 'Brak danych': 'No data',
 'Adres prywatny': 'Private address',
 'Liczba domen': 'Number of domains',
 'średnia': 'average',
 'bity': 'bits',
 'bajty': 'bytes',
 'z ostatniego dnia': 'from the last day',
 'z ostatnich 30 dni': 'from the last 30 days',
 'z ostatniego tygodnia': 'from the last week',
 'z ostatniego roku': 'from the last year',
 'wykresy': 'charts',
 'tabelę': 'table',
 'czasie połączenia': 'connection time',
 'nazwie': 'name',
 'adresie IP': 'IP address',
 'ostatniej widoczności': 'last seen',
 'typie połączenia': 'connection type',
 'kanale': 'channel',
 'adresie MAC': 'MAC address',
 'sile sygnału': 'signal strength',
 'widoczności': 'last seen',
 'źle': 'bad',
 'Filtrowanie:': 'Filter:',
 'Pokaż': 'Show',
 'Sortowanie po': 'Sort by',
 'nieznany': 'unknown',
 'nieznane': 'unknown',
 'UWAGA!': 'WARNING!',
 'Wymagana jest zmiana domyślnego hasła do routera!': 'You must change the default router password!',
 'bardzo zły': 'very bad',
 'doskonały': 'excellent',
 'dobry': 'good',
 'słaby': 'weak',
 'zły': 'bad',
 'dBm i': 'dBm and',
 'dB i': 'dB and',
 'Automatyczne wykrywanie': 'Automatic detection',
 'Bez śledzenia': 'No tracking',
 'Bezprzewodowo': 'Wireless',
 'bezprzewodowo': 'wireless',
 'Przewodowo': 'Wired',
 'przewodowo': 'wired',
 'Blokada domen jest wyłączona. Nie można sprawdzić domeny': 'Domain blocking is disabled. Cannot check the domain',
 'Brak akcji': 'No action',
 'Brak możliwości wysłania żądania ICMP': 'Unable to send ICMP request',
 'Brak nazwy sieci Wi-Fi': 'Missing Wi-Fi network name',
 'Brak nowej wersji.': 'No new version.',
 'Brak odpowiedzi z modemu': 'No response from modem',
 'Brak sieci': 'No network',
 'Błąd logowania!': 'Login error!',
 'Błąd odczytu lokalizacji': 'Error reading location',
 'Błąd pobierania danych!': 'Error fetching data!',
 'Błąd w polu': 'Error in field',
 'Błąd wczytywania konfiguracji': 'Error loading configuration',
 'Błąd wylogowania!': 'Logout error!',
 'Czwartek': 'Thursday',
 'Dostępna jest nowa wersja oprogramowania': 'A new firmware version is available',
 'Dostępny': 'Available',
 'Działanie DNSów': 'DNS operation',
 'Działanie trasy domyślnej': 'Default route operation',
 'Dzień': 'Day',
 'Hasła nie są takie same!': 'Passwords do not match!',
 'Inne': 'Other',
 'Kod błędu': 'Error code',
 'Kraj': 'Country',
 'Liczba połączonych klientów': 'Number of connected clients',
 'Miasto': 'City',
 'Miesiąc': 'Month',
 'Modem komórkowy': 'Cellular modem',
 'HiLink lub RNDIS': 'HiLink or RNDIS',
 'Nazwa połączenia': 'Connection name',
 'Nazwa rzeczywista': 'Real name',
 'Nazwa': 'Name',
 'Nie wykryto żadnego dostępnego połączenia z internetem': 'No available internet connection was detected',
 'Niedostępny': 'Unavailable',
 'Niedziela': 'Sunday',
 'Nieobsługiwany': 'Unsupported',
 'Nowi klienci': 'New clients',
 'nowi klienci': 'new clients',
 'Obsługa pasm 5G NSA nie jest dostępna': '5G NSA band selection is not available',
 'Obsługa pasm 5G SA nie jest dostępna': '5G SA band selection is not available',
 'Obsługa pasm LTE nie jest dostępna': 'LTE band selection is not available',
 'Odmowa dostępu': 'Access denied',
 'Ostatni kontakt': 'Last contact',
 'Ostatni raz widziany': 'Last seen',
 'Otrzymane od dostawcy': 'Received from provider',
 'Pasmo': 'Band',
 'Pierwszy raz widziany': 'First seen',
 'Piątek': 'Friday',
 'Plik konfiguracyjny nie zawiera opcji': 'Configuration file does not contain option',
 'Plik nie zawiera konfiguracji obsługiwanych typów VPN': 'The file does not contain a configuration of supported VPN types',
 'Plik nieznanego typu': 'Unknown file type',
 'Podany PIN nie jest odpowiednią wartością': 'The entered PIN is not a valid value',
 'Poniedziałek': 'Monday',
 'Port WAN (Statyczny IP)': 'WAN port (Static IP)',
 'Poziom sygnału': 'Signal level',
 'Połączony do sieci (SSID)': 'Connected to network (SSID)',
 'Połączony': 'Connected',
 'Przekroczono czas oczekiwania na odpowiedź z modemu': 'Timed out waiting for response from modem',
 'Przełączanie awaryjne': 'Failover',
 'Przywrócić ustawienia domyślne urządzenia?': 'Restore device default settings?',
 'Rok': 'Year',
 'Rozłączyć "': 'Disconnect "',
 'Równoważenie obciążenia': 'Load balancing',
 'Sieć': 'Network',
 'Sobota': 'Saturday',
 'Status połączenia z internetem': 'Internet connection status',
 'Statystyka transferu dla "': 'Traffic statistics for "',
 'Szerokość': 'Width',
 'Temperatura': 'Temperature',
 'Trwa ponowne uruchomienie urządzenia, może to potrwać kilka minut...': 'The device is rebooting, this may take a few minutes...',
 'Twoje IP': 'Your IP',
 'Tylko': 'Only',
 'UWAGA: interfejs radiowy jest wyłączony!': 'WARNING: the radio interface is disabled!',
 'UWAGA: zmiana aktywnego slotu SIM spowoduje rozłączenie połączenia z internetem. Zmienić slot?': 'WARNING: changing the active SIM slot will disconnect the internet connection. Change slot?',
 'Uruchom WPS (Wi-Fi Protected Setup)': 'Start WPS (Wi-Fi Protected Setup)',
 'Uruchomić urządzenie ponownie?': 'Reboot the device?',
 'Usunąć VPN "': 'Delete VPN "',
 'Usunąć Wake on LAN dla "': 'Delete Wake on LAN for "',
 'Usunąć dane dla "': 'Delete data for "',
 'Usunąć dane o transferze?': 'Delete traffic data?',
 'Usunąć domenę "': 'Remove domain "',
 'Usunąć sieć dodatkową "': 'Delete additional network "',
 'Usunąć wiadomość od "': 'Delete message from "',
 'Usuń': 'Delete',
 'Wg ustawień modemu': 'Per modem settings',
 'Wi-Fi wyłączone': 'Wi-Fi disabled',
 'Wtorek': 'Tuesday',
 'Wybierz przycisk "Aktualizacja" aby zainstalować nową wersję oprogramowania.': 'Press the "Update" button to install the new firmware version.',
 'Wybudzenie przez Wake on LAN': 'Wake via Wake on LAN',
 'Wybór automatyczny': 'Automatic selection',
 'Wystąpił błąd podczas pobierania pliku. Kod błędu:': 'An error occurred while downloading the file. Error code:',
 'Wystąpił błąd podczas pobierania pliku. Spróbuj ponownie za kilka minut.': 'An error occurred while downloading the file. Try again in a few minutes.',
 'Wystąpił błąd podczas sprawdzania aktualizacji. Kod błędu:': 'An error occurred while checking for updates. Error code:',
 'Wystąpił błąd podczas wykonywania aktualizacji. Kod błędu:': 'An error occurred while performing the update. Error code:',
 'Wystąpił problem z usunięciem wiadomości': 'There was a problem deleting the message',
 'Wystąpił problem z wysłaniem wiadomości': 'There was a problem sending the message',
 'Wyszukiwanie operatora': 'Searching for operator',
 'Wyłącz': 'Disable',
 'Wyłączony': 'Disabled',
 'Wznowienia połączenia z internetem': 'Internet reconnections',
 'Włącz/wyłącz VPN': 'Enable/disable VPN',
 'Włącz/wyłącz Wi-Fi sieci dodatkowych': 'Enable/disable additional networks Wi-Fi',
 'Włącz/wyłącz Wi-Fi': 'Enable/disable Wi-Fi',
 'Włącz/wyłącz diody LED': 'Enable/disable LEDs',
 'Włącz/wyłącz dostęp z sieci lokalnej (killswitch)': 'Enable/disable access from local network (killswitch)',
 'Włącz': 'Enable',
 'Zalogowana do sieci macierzystej, tylko SMS': 'Registered, home network, SMS only',
 'Zalogowana do sieci macierzystej': 'Registered, home network',
 'Zalogowana do sieci w roamingu, tylko SMS': 'Registered, roaming, SMS only',
 'Zalogowana do sieci w roamingu': 'Registered, roaming',
 'Zaznaczając "Zachowaj ustawienia" możliwe jest zapisane bieżących ustawień.': 'By checking "Keep settings" the current settings can be preserved.',
 'Zaznaczono całkowite wyłączenie Wi-Fi': 'Wi-Fi is set to be fully disabled',
 'Wybierz "Wyłącz" żeby usunąć harmonogram i wyłączyć Wi-Fi lub "Anuluj" aby zignorować zmiany.': 'Choose "Disable" to remove the schedule and turn Wi-Fi off, or "Cancel" to ignore the changes.',
 'Znaleziono konfigurację dla': 'Found configuration for',
 'title="połącz"': 'title="connect"',
 'title="rozłącz"': 'title="disconnect"',
 'zmień stan Wi-Fi': 'toggle Wi-Fi',
 'przenieś do blokady domen': 'move to domain blocking',
 'brak sygnału GPS': 'no GPS signal',
 'nieokreślony': 'undefined',
 'południowy wschód': 'southeast',
 'południowy zachód': 'southwest',
 'północny wschód': 'northeast',
 'północny zachód': 'northwest',
 'południe': 'south',
 'północ': 'north',
 'wschód słońca': 'sunrise',
 'wschód': 'east',
 'połączenie': 'connection',
 'rozłączenie': 'disconnection',
 'przestój': 'downtime',
 'przycisk "Pobierz" aby pobrać nową wersję. W zależności od szybkości połączenia': 'the "Download" button to download the new version. Depending on the speed of your connection',
 'z internetem może to potrwać do kilku minut.': 'to the internet, this may take up to a few minutes.',
 'wpis': 'entry',
 'Środa': 'Wednesday',
 'Żądanie zostało wysłane, ale nie otrzymano odpowiedzi.': 'The request was sent, but no response was received.',
 'Brak': 'None',
 'brak': 'none',
 'Włączony': 'Enabled',
 'Włączona': 'Enabled',
 'Włączone': 'Enabled',
 'wyłączone': 'disabled'}

# Arka uc (rpcd) ve diger dosyalar icin duz metin degisimleri
BACKEND = [
    ('Temperatura Wi-Fi', 'Wi-Fi temperature'), ('Temperatura CPU', 'CPU temperature'),
    ('Temperatura baterii', 'Battery temperature'), ('Ładowanie baterii', 'Battery charging'),
    ('Ilość cykli ładowania', 'Charge cycles'), ('Poziom naładowania', 'Charge level'),
    ('"Bateria"', '"Battery"'), ('Nie zainstalowana', 'Not installed'), ('"Obecna"', '"Present"'),
    ('W pełni naładowana', 'Fully charged'), ('Brak odczytu', 'No reading'),
    ('CHARGING="Tak"', 'CHARGING="Yes"'), ('CHARGING="Nie"', 'CHARGING="No"'),
    ('":"Tak"}', '":"Yes"}'), ('":"Nie"}', '":"No"}'), ('Sieć lokalna', 'Local network'),
]
LUCI = [
    ('Na tym routerze zainstalowany jest także <b>easyconfig</b>! Kliknij poniżej aby go otworzyć.',
     '<b>easyconfig</b> is also installed on this router! Click below to open it.'),
    ('Otwórz easyconfig', 'Open easyconfig'),
]
CLIENTTYPES = [
    ('"AGD"', '"Home appliance"'), ('Sprzęt audio', 'Audio equipment'), ('Kamera / monitoring', 'Camera / surveillance'),
    ('Konsola do gier', 'Game console'), ('Odtwarzacz multimedialny', 'Media player'), ('Urządzenie sieciowe', 'Network device'),
    ('"Komputer"', '"Computer"'), ('Telefon stacjonarny / VoIP', 'Desk phone / VoIP'), ('"Drukarka"', '"Printer"'),
    ('Serwer / NAS', 'Server / NAS'), ('"Smartfon"', '"Smartphone"'), ('"Telewizor"', '"TV"'),
    ('Opaska / czujnik noszony', 'Wearable band / sensor'),
]

HUAWEI = [
    ('Wybrano automatyczny tryb pracy modemu.', 'Automatic modem mode selected.'),
    ('Wybrano tryb pracy modemu tylko UMTS wszystkie czestotliwosci.', 'Modem mode selected: UMTS only, all frequencies.'),
    ('Wybrano tryb pracy modemu tylko LTE wszystkie czestotliwosci.', 'Modem mode selected: LTE only, all frequencies.'),
    ('Wybrano tryb pracy modemu tylko ', 'Modem mode selected: only '),
    ('Nie wybrales trybu pracy modemu! Mozliwe tryby pracy:', 'No modem mode selected! Available modes:'),
]

LANG_TR = True  # Turkce dil secenegi; kapatmak icin --no-tr
THEME = True  # Preline (Tailwind) temasi; kapatmak icin --no-theme
TW_CSS = '@font-face{font-family:Inter Variable;font-style:normal;font-display:swap;font-weight:100 900;src:url(/easyconfig/inter.woff2) format("woff2-variations");unicode-range:u+00??,u+0131,u+0152-0153,u+02bb-02bc,u+02c6,u+02da,u+02dc,u+0304,u+0308,u+0329,u+2000-206f,u+20ac,u+2122,u+2191,u+2193,u+2212,u+2215,u+feff,u+fffd}html{font-size:16px;-webkit-font-smoothing:antialiased}body{background-color:#f9fafb;font-family:Inter Variable,Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica Neue,Arial,sans-serif;font-size:.875rem;line-height:1.5rem;color:#1f2937}.container{max-width:64rem}#div_adblock,#div_clients,#div_clientslogs,#div_config,#div_gps,#div_networks,#div_nightmode,#div_queries,#div_security,#div_sitesurvey,#div_status,#div_system,#div_traffic,#div_ussdsms,#div_vpn,#div_watchdog,#div_wol{margin-bottom:2rem;border-radius:.75rem;border:1px solid #e5e7eb;background-color:#fff;padding:.25rem 1rem 1.5rem}@media (min-width:640px){#div_adblock,#div_clients,#div_clientslogs,#div_config,#div_gps,#div_networks,#div_nightmode,#div_queries,#div_security,#div_sitesurvey,#div_status,#div_system,#div_traffic,#div_ussdsms,#div_vpn,#div_watchdog,#div_wol{padding-left:1.75rem;padding-right:1.75rem}}#div_adblock,#div_clients,#div_clientslogs,#div_config,#div_gps,#div_networks,#div_nightmode,#div_queries,#div_security,#div_sitesurvey,#div_status,#div_system,#div_traffic,#div_ussdsms,#div_vpn,#div_watchdog,#div_wol{box-shadow:0 1px rgba(0,0,0,.05)}#div_content>.row:first-child h3{margin-top:1.5rem;margin-bottom:1.25rem}#system_hostname_label{font-size:1.25rem}#system_hostname_label,h3{line-height:1.75rem;font-weight:600;color:#1f2937}h3{font-size:1.125rem}h3.section{margin:1.75rem -1rem 1.25rem;border:solid #e5e7eb;border-width:0 0 1px;padding:0 1rem .875rem;font-size:1rem;line-height:1.5rem;font-weight:600;color:#1f2937}@media (min-width:640px){h3.section{margin-left:-1.75rem;margin-right:-1.75rem;padding-left:1.75rem;padding-right:1.75rem}}#div_config>div:first-child h3.section:first-child,#div_status>div:first-child h3.section:first-child{margin-top:1.25rem}hr{border-color:#e5e7eb}.form-text,.text-muted{font-size:.875rem;line-height:1.25rem;color:#6b7280}.text-danger{color:#dc2626}.control-label,.text-right{color:#6b7280}.click,.click:link,.click:visited,a{font-weight:500;color:#2563eb;text-decoration-line:none}.click:hover,a:focus,a:hover{color:#1d4ed8;text-decoration-line:underline;text-decoration-thickness:2px;text-underline-offset:2px;outline:2px solid transparent;outline-offset:2px}.btn{display:inline-block;border-radius:.5rem;border-width:1px;border-style:solid;padding:.5rem .75rem;text-align:center;font-size:.875rem;line-height:1.25rem;font-weight:500}.btn:active:focus,.btn:focus{outline:2px solid transparent;outline-offset:2px}.btn-default{border-color:#e5e7eb;background-color:#fff;color:#1f2937;box-shadow:0 1px rgba(0,0,0,.05)}.btn-default:active,.btn-default:focus,.btn-default:hover{border-color:#e5e7eb;background-color:#f9fafb;color:#1f2937}.btn-primary{border-color:transparent;background-color:#2563eb;color:#fff;--tw-shadow:0 0 #0000;--tw-shadow-colored:0 0 #0000;box-shadow:var(--tw-ring-offset-shadow,0 0 #0000),var(--tw-ring-shadow,0 0 #0000),var(--tw-shadow)}.btn-primary:active,.btn-primary:focus,.btn-primary:hover{border-color:transparent;background-color:#1d4ed8;color:#fff}.btn.disabled,.btn[disabled]{pointer-events:none;opacity:.5}#div_content>.row:first-child h3>.btn{padding:.625rem}.btn .icon-bar{background-color:#1f2937;width:16px}label{font-weight:500;color:#1f2937}.control-label{font-weight:400}.form-control{display:block;height:auto;width:100%;border-radius:.5rem;border:1px solid #e5e7eb;background-color:#fff;padding:.5rem .75rem;font-size:.875rem;line-height:1.25rem;color:#1f2937;--tw-shadow:0 0 #0000;--tw-shadow-colored:0 0 #0000;box-shadow:var(--tw-ring-offset-shadow,0 0 #0000),var(--tw-ring-shadow,0 0 #0000),var(--tw-shadow)}.form-control::-moz-placeholder{color:#9ca3af}.form-control::placeholder{color:#9ca3af}.form-control:focus{border-color:#3b82f6;--tw-shadow:0 0 #0000;--tw-shadow-colored:0 0 #0000;box-shadow:var(--tw-ring-offset-shadow,0 0 #0000),var(--tw-ring-shadow,0 0 #0000),var(--tw-shadow);outline:2px solid transparent;outline-offset:2px;box-shadow:0 0 0 1px #3b82f6}.form-control[disabled],.form-control[readonly]{background-color:#f9fafb;color:#6b7280;opacity:1}select.form-control{padding-right:2.25rem}.form-group{margin-bottom:1rem}.checkbox label,.radio label{font-weight:400;color:#1f2937}input[type=checkbox],input[type=radio]{accent-color:#2563eb}.switch{width:52px;height:28px}.slider{border-radius:9999px;background-color:#e5e7eb;transition:.2s}.slider:before{background-color:#fff;box-shadow:0 1px 2px rgba(0,0,0,.1);height:24px;width:24px;left:2px;bottom:2px;transition:.2s}input:checked+.slider{background-color:#2563eb}input:checked+.slider:before{transform:translateX(24px)}input:focus+.slider{box-shadow:0 0 0 2px #fff,0 0 0 4px rgba(59,130,246,.4)}.rb .checkmark{border-radius:9999px;border:1px solid #d1d5db;background-color:#fff}.rb:hover input~.checkmark{background-color:#f9fafb}.rb input:checked~.checkmark{border-color:#2563eb;background-color:#2563eb}.sidenav{border:solid #e5e7eb;border-width:0 1px 0 0;background-color:#fff;padding-top:56px;box-shadow:0 10px 15px -3px rgba(0,0,0,.08)}.sidenav a{margin:.125rem .75rem;display:flex;align-items:center;border-radius:.5rem;padding:.5rem .625rem;font-size:.875rem;line-height:1.25rem;font-weight:400;color:#1f2937;text-decoration-line:none}.sidenav a:focus,.sidenav a:hover{background-color:#f3f4f6;color:#1f2937;text-decoration-line:none}.sidenav .iconwithtext{margin-right:.875rem;color:#6b7280;width:16px;height:16px}.sidenav .closebtn{position:absolute;top:.75rem;right:.75rem;left:auto;margin:0;width:2rem;height:2rem;justify-content:center;padding:0;font-size:1.5rem;line-height:2rem;color:#6b7280}.sidenav .closebtn:hover{background-color:#f3f4f6}.modal{background-color:rgba(17,24,39,.5)}.modal-content{max-width:48rem;overflow:hidden;border-radius:.75rem;border:1px solid #e5e7eb;background-color:#fff;padding:1.5rem;box-shadow:0 1px rgba(0,0,0,.05)}.alert{border-radius:.5rem;border-width:1px;border-style:solid;padding:1rem;font-size:.875rem;line-height:1.25rem}.alert-danger{border-color:#fecaca;background-color:#fef2f2;color:#991b1b}.alert-info{border-color:#bfdbfe;background-color:#eff6ff;color:#1e40af}.alert-warning{border-color:#fef08a;background-color:#fefce8;color:#854d0e}.progress{height:.5rem;overflow:hidden;border-radius:9999px;border-width:0;background-color:#e5e7eb}.progress,.progress-bar{--tw-shadow:0 0 #0000;--tw-shadow-colored:0 0 #0000;box-shadow:var(--tw-ring-offset-shadow,0 0 #0000),var(--tw-ring-shadow,0 0 #0000),var(--tw-shadow)}.progress-bar{border-radius:9999px;background-color:#2563eb}.table{font-size:.875rem;line-height:1.25rem}.table,.table td{border-color:#e5e7eb}.tooltip{border-radius:.375rem;border-width:0;background-color:#111827;padding:.25rem .5rem;font-size:.75rem;line-height:1rem;font-weight:500;color:#fff;opacity:1;box-shadow:0 1px rgba(0,0,0,.05)}#div_login>.row{margin-left:auto;margin-right:auto;margin-top:2.5rem;max-width:48rem;border-radius:.75rem;border:1px solid #e5e7eb;background-color:#fff;padding:2.5rem 1rem}@media (min-width:640px){#div_login>.row{margin-top:6rem}}#div_login>.row{box-shadow:0 1px rgba(0,0,0,.05)}#div_login .wifi{color:#2563eb}#div_login label{margin-bottom:.5rem;font-size:.875rem;line-height:1.25rem;font-weight:500;color:#1f2937}.darkmode{background-color:#171717;color:#e5e5e5}.darkmode #div_adblock,.darkmode #div_clients,.darkmode #div_clientslogs,.darkmode #div_config,.darkmode #div_gps,.darkmode #div_login>.row,.darkmode #div_networks,.darkmode #div_nightmode,.darkmode #div_queries,.darkmode #div_security,.darkmode #div_sitesurvey,.darkmode #div_status,.darkmode #div_system,.darkmode #div_traffic,.darkmode #div_ussdsms,.darkmode #div_vpn,.darkmode #div_watchdog,.darkmode #div_wol{border-color:#404040;background-color:#262626;box-shadow:none}.darkmode #system_hostname_label,.darkmode h3,.darkmode h3.section{color:#e5e5e5}.darkmode h3.section,.darkmode hr{border-color:#404040}.darkmode .checkbox label,.darkmode .radio label,.darkmode label{color:#e5e5e5}.darkmode .control-label,.darkmode .text-right{color:#a3a3a3}.darkmode .form-text,.darkmode .text-muted{color:#737373}.darkmode .click,.darkmode a{color:#3b82f6!important}.darkmode .click:hover,.darkmode a:hover{color:#60a5fa!important}.darkmode .btn-default{border-color:#404040;background-color:#262626;color:#fff;box-shadow:none}.darkmode .btn-default:focus,.darkmode .btn-default:hover{background-color:#404040;color:#fff}.darkmode .btn-primary{border-color:transparent;background-color:#3b82f6;color:#fff}.darkmode .btn-primary:focus,.darkmode .btn-primary:hover{background-color:#2563eb}.darkmode .icon-bar{background-color:#e5e5e5}.darkmode .form-control{border-color:#404040;background-color:#171717;color:#e5e5e5}.darkmode .form-control::-moz-placeholder{color:#737373}.darkmode .form-control::placeholder{color:#737373}.darkmode .form-control:focus{border-color:#3b82f6}.darkmode .form-control[disabled],.darkmode .form-control[readonly]{background-color:#262626;color:#737373}.darkmode .slider{background-color:#404040}.darkmode .slider:before{background-color:#d4d4d4}.darkmode input:checked+.slider{background-color:#3b82f6!important}.darkmode input:checked+.slider:before{background-color:#fff}.darkmode input:focus+.slider{box-shadow:0 0 0 2px #262626,0 0 0 4px rgba(59,130,246,.4)}.darkmode .rb .checkmark{border-color:#525252;background-color:#262626}.darkmode .rb input:checked~.checkmark{background-color:#3b82f6!important;border-color:#3b82f6}.darkmode .rb .checkmark:after{background-color:#fff}.darkmode .modal{background-color:rgba(0,0,0,.7)}.darkmode .modal-content{color:#e5e5e5}.darkmode .modal-content,.darkmode .sidenav{border-color:#404040;background-color:#262626}.darkmode .sidenav a{color:#e5e5e5!important}.darkmode .sidenav a:focus,.darkmode .sidenav a:hover{background-color:#404040;color:#e5e5e5!important}.darkmode .sidenav .iconwithtext{color:#a3a3a3}.darkmode .sidenav .closebtn{color:#a3a3a3!important}.darkmode .alert-danger{border-color:#7f1d1d;color:#ef4444;background-color:rgba(153,27,27,.1)}.darkmode .alert-info{border-color:#1e3a8a;color:#3b82f6;background-color:rgba(30,64,175,.1)}.darkmode .alert-warning{border-color:#713f12;color:#eab308;background-color:rgba(133,77,14,.1)}.darkmode .progress{background-color:#404040}.darkmode .progress-bar{background-color:#3b82f6}.darkmode .table,.darkmode .table td{border-color:#404040}.darkmode .tooltip{background-color:#404040;color:#fff}.darkmode #div_login .wifi{color:#3b82f6}'
# Inter Variable (latin, OFL lisansli) - Preline varsayilan yazi tipi
TW_FONT_B64 = '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'

EN2TR = {'</strong>. Press ': '</strong>. ',
 ' of ': ' / ',
 '% of ': '% / ',
 ' (since ': ' (başlangıç: ',
 '<span class="visible-xs oneline"></span> (since ': '<span class="visible-xs oneline"></span> (başlangıç: ',
 '</span><span class="visible-xs oneline"></span><span> (since ': '</span><span class="visible-xs oneline"></span><span> (başlangıç: ',
 '<div class="col-xs-10">From: ': '<div class="col-xs-10">Kimden: ',
 'Ping to DNS1 (': 'DNS1 ping (',
 'Ping to DNS2 (': 'DNS2 ping (',
 'Ping to ': 'Ping: ',
 'Detect...': 'Algıla...',
 '<table class="table"><tr><td>Day / Hour</td><td>Mo</td><td>Tu</td><td>We</td><td>Th</td><td>Fr</td><td>Sa</td><td>Su</td></tr>': '<table class="table"><tr><td>Gün / '
                                                                                                                                   'Saat</td><td>Pt</td><td>Sa</td><td>Ça</td><td>Pe</td><td>Cu</td><td>Ct</td><td>Pz</td></tr>',
 '<no name>': '<adsız>',
 'years': 'yıl',
 'Yes': 'Evet',
 'No': 'Hayır',
 'May': 'Mayıs',
 'no domain': 'alan adı yok',
 'restrictions': 'kısıtlamalar',
 'Wake': 'Uyandır',
 'connection method': 'bağlantı yöntemi',
 'for': '–',
 'duplicate': 'yinelenen',
 'drop': 'düşür',
 'with 7BIT decoding': '7BIT çözümlemeli',
 'with UCS decoding': 'UCS çözümlemeli',
 'Settings': 'Ayarlar',
 'Security': 'Güvenlik',
 'Additional networks': 'Ek ağlar',
 'Additional network': 'Ek ağ',
 'Connection monitor': 'Bağlantı izleme',
 'Wi-Fi networks': 'Wi-Fi ağları',
 'Clients': 'İstemciler',
 'Connection history': 'Bağlantı geçmişi',
 'connection history': 'bağlantı geçmişi',
 'DNS queries': 'DNS sorguları',
 'Domain blocking': 'Alan adı engelleme',
 'Night mode': 'Gece modu',
 'Log out': 'Çıkış yap',
 'Login': 'Giriş',
 'Update': 'Güncelleme',
 'Diagnostics': 'Tanılama',
 'Refresh': 'Yenile',
 'Password': 'Parola',
 'Signal': 'Sinyal',
 'Technology': 'Teknoloji',
 'SIM card status': 'SIM kart durumu',
 'more parameters': 'daha fazla parametre',
 'base station location': 'baz istasyonu konumu',
 'connected: 0': 'bağlı: 0',
 'connected: ': 'bağlı: ',
 'Number of reconnections': 'Yeniden bağlanma sayısı',
 'Connection time': 'Bağlantı süresi',
 'Message sent': 'Mesaj gönderildi',
 'Sent': 'Gönderilen',
 'sent': 'gönderilen',
 'Downloaded': 'İndirilen',
 'downloaded': 'indirilen',
 'received': 'alınan',
 'DMZ IP address': 'DMZ IP adresi',
 'IP address': 'IP adresi',
 'Netmask': 'Ağ maskesi',
 'Gateway': 'Ağ geçidi',
 'DNS servers': 'DNS sunucuları',
 'local network access to the internet is disabled': 'yerel ağın internet erişimi kapalı',
 'Channels in use': 'Kullanılan kanallar',
 'Connected clients': 'Bağlı istemciler',
 'Local network': 'Yerel ağ',
 'Uptime': 'Çalışma süresi',
 'Traffic share': 'Trafik payı',
 'Load': 'Yük',
 'Date and time': 'Tarih ve saat',
 'Connection type': 'Bağlantı türü',
 'connection type': 'bağlantı türü',
 'Device': 'Cihaz',
 'modem management panel': 'modem yönetim paneli',
 'Username': 'Kullanıcı adı',
 'LCP echo failure threshold': 'LCP echo hata eşiği',
 'LCP echo interval': 'LCP echo aralığı',
 'MAC address': 'MAC adresi',
 'server description': 'sunucu açıklaması',
 'Metered connection': 'Sınırlı bağlantı',
 'the connection has data limits or incurs charges': 'bağlantıda kota var veya ücretlendiriliyor',
 'Access from local network': 'Yerel ağdan erişim',
 'allows the local network to access the internet via': 'yerel ağın internete şunun üzerinden erişmesine izin verir:',
 'must be in the same subnet as the local network': 'yerel ağ ile aynı alt ağda olmalı',
 'DHCP server enabled': 'DHCP sunucusu açık',
 'Intercept DNS queries': 'DNS sorgularını yakala',
 'Log DNS queries': 'DNS sorgularını kaydet',
 'WAN port bridged to local network': 'WAN portu yerel ağa bağlı',
 'Wi-Fi enabled': 'Wi-Fi açık',
 'Transmit power': 'Yayın gücü',
 'Network name (SSID)': 'Ağ adı (SSID)',
 'Channel': 'Kanal',
 'Point-to-Point encryption (MPPE)': 'Noktadan noktaya şifreleme (MPPE)',
 'Encryption': 'Şifreleme',
 'Client isolation': 'İstemci yalıtımı',
 'Hidden network': 'Gizli ağ',
 'Random MAC address': 'Rastgele MAC adresi',
 'System name': 'Sistem adı',
 'Send statistics': 'İstatistik gönder',
 'view statistics': 'istatistikleri gör',
 'Button "': 'Düğme "',
 'Reset button active': 'Reset düğmesi etkin',
 'Data save interval': 'Veri kaydetme aralığı',
 '1 minute': '1 dakika',
 '3 minutes': '3 dakika',
 '5 minutes': '5 dakika',
 '10 minutes': '10 dakika',
 '15 minutes': '15 dakika',
 '30 minutes': '30 dakika',
 '1 hour': '1 saat',
 '3 hours': '3 saat',
 '6 hours': '6 saat',
 '12 hours': '12 saat',
 '24 hours': '24 saat',
 'Fetching data...': 'Veriler alınıyor...',
 'Manufacturer': 'Üretici',
 'Firmware version': 'Yazılım sürümü',
 'GUI version': 'Arayüz sürümü',
 'Version': 'Sürüm',
 'Modem identifier (IMEI)': 'Modem kimliği (IMEI)',
 'SIM card number (ICCID)': 'SIM kart numarası (ICCID)',
 'Subscriber identifier (IMSI)': 'Abone kimliği (IMSI)',
 'advanced settings': 'gelişmiş ayarlar',
 'AT commands': 'AT komutları',
 'LTE bands': 'LTE bantları',
 '5G NSA bands': '5G NSA bantları',
 '5G SA bands': '5G SA bantları',
 'Active SIM slot': 'Etkin SIM yuvası',
 'Serial number': 'Seri numarası',
 'Reboot device': 'Cihazı yeniden başlat',
 'Factory reset': 'Fabrika ayarlarına dön',
 'User interface': 'Kullanıcı arayüzü',
 'changelog': 'değişiklik geçmişi',
 'Theme': 'Tema',
 'light': 'açık',
 'dark': 'koyu',
 'automatic': 'otomatik',
 'Update availability': 'Güncelleme durumu',
 'Downloading update': 'Güncelleme indiriliyor',
 'Keep settings': 'Ayarları koru',
 'Help': 'Yardım',
 'feature description': 'özellik açıklaması',
 'Internet connection is disabled.': 'İnternet bağlantısı kapalı.',
 'Click here to set up the connection': 'Bağlantıyı kurmak için tıklayın',
 'Last check': 'Son kontrol',
 'maximum': 'en fazla',
 'Delay at system startup': 'Sistem açılışında gecikme',
 '[1 - 59] minutes': '[1 - 59] dakika',
 'Server address or name': 'Sunucu adresi veya adı',
 'Address or name': 'Adres veya ad',
 'Check interval': 'Kontrol aralığı',
 'Number of failed checks': 'Başarısız kontrol sayısı',
 'Action': 'Eylem',
 'Restart internet connection': 'İnternet bağlantısını yeniden başlat',
 'restart internet connection': 'internet bağlantısını yeniden başlat',
 'reboot device': 'cihazı yeniden başlat',
 "Calculations may differ from the operator's figures": 'Hesaplamalar operatörün verilerinden farklı olabilir',
 'Today': 'Bugün',
 'Yesterday': 'Dün',
 'Last 7 days': 'Son 7 gün',
 'Last 30 days': 'Son 30 gün',
 'Total': 'Toplam',
 'Days until end of billing period': 'Fatura döneminin bitimine kalan gün',
 'Current billing period': 'Mevcut fatura dönemi',
 'Projected data usage in current period': 'Bu dönem için tahmini veri kullanımı',
 'Previous billing period': 'Önceki fatura dönemi',
 'Billing period': 'Fatura dönemi',
 'Start of billing period': 'Fatura dönemi başlangıcı',
 'day of month': 'ayın günü',
 'number of days': 'gün sayısı',
 'Number of days in period': 'Dönemdeki gün sayısı',
 'day': 'gün',
 'month': 'ay',
 'January': 'Ocak',
 'February': 'Şubat',
 'March': 'Mart',
 'April': 'Nisan',
 'June': 'Haziran',
 'July': 'Temmuz',
 'August': 'Ağustos',
 'September': 'Eylül',
 'October': 'Ekim',
 'November': 'Kasım',
 'December': 'Aralık',
 'Warning enabled': 'Uyarı açık',
 'Warning level': 'Uyarı seviyesi',
 'USSD code': 'USSD kodu',
 'select USSD code': 'USSD kodu seçin',
 'Phone number': 'Telefon numarası',
 'Message text': 'Mesaj metni',
 'messages to send:': 'gönderilecek mesaj:',
 'block internet access without a VPN connection': 'VPN bağlantısı yokken internet erişimini engelle',
 'No VPN networks': 'VPN ağı yok',
 'Number of blocked domains': 'Engellenen alan adı sayısı',
 'Custom domain list': 'Özel alan adı listesi',
 'Blocked domains': 'Engellenen alan adları',
 'Allowed domains': 'İzin verilen alan adları',
 'Domain': 'Alan adı',
 'Wi-Fi on': 'Wi-Fi açılış',
 'Wi-Fi off': 'Wi-Fi kapanış',
 'LEDs': "LED'ler",
 'LEDs on': 'LED açılış',
 'LEDs off': 'LED kapanış',
 'Automatic night mode': 'Otomatik gece modu',
 'Latitude': 'Enlem',
 'Longitude': 'Boylam',
 'GPS position': 'GPS konumu',
 'Position from GPS': "GPS'ten konum",
 'Reading time': 'Okuma zamanı',
 'Altitude': 'Rakım',
 'Heading': 'Yön',
 'Download speed': 'İndirme hızı',
 'Upload speed': 'Yükleme hızı',
 'Speed': 'Hız',
 'No devices to wake': 'Uyandırılacak cihaz yok',
 'The password is shared by the user interface and SSH': 'Parola kullanıcı arayüzü ve SSH için ortaktır',
 'New password': 'Yeni parola',
 'Confirm password': 'Parolayı onayla',
 'disabling prevents login via SSH': 'kapatılırsa SSH ile giriş yapılamaz',
 'Password login': 'Parola ile giriş',
 'when disabled, login is only possible with keys': 'kapatılırsa yalnızca anahtarla giriş yapılabilir',
 'Port (local network)': 'Port (yerel ağ)',
 'port for connections from the local network': 'yerel ağdan bağlantı portu',
 'port for connections from the internet, leave empty to disable internet access': 'internetten bağlantı portu; internet erişimini kapatmak için boş bırakın',
 'Require authentication': 'Kimlik doğrulama iste',
 'password required when logging in via UART/serial port': 'UART/seri port ile girişte parola gerekir',
 'Change name/type for "': 'Ad/tür değiştir: "',
 'change name/type': 'ad/tür değiştir',
 'New name': 'Yeni ad',
 'Client type': 'İstemci türü',
 'client type': 'istemci türü',
 'Static IP address for "': 'Statik IP adresi: "',
 'Disconnecting the client may be necessary for it to obtain the static IP address': 'İstemcinin statik IP adresini alması için bağlantısını kesmek gerekebilir',
 'Static IP address': 'Statik IP adresi',
 'static IP address': 'statik IP adresi',
 'current static IP address:': 'mevcut statik IP adresi:',
 'Disconnect client': 'İstemcinin bağlantısını kes',
 'Internet access block for "': 'İnternet erişim engeli: "',
 'Permanent': 'Kalıcı',
 'Scheduled': 'Zamanlanmış',
 'access blocked': 'erişim engelli',
 'select all': 'tümünü seç',
 'deselect all': 'seçimi kaldır',
 'Speed limit for "': 'Hız sınırı: "',
 'Flow offloading is enabled, speed limiting may not work': 'Flow offloading açık, hız sınırlama çalışmayabilir',
 'A static IP address must be set for speed limiting to work': 'Hız sınırlamanın çalışması için statik IP adresi atanmalıdır',
 'Upload up to': 'Yükleme en fazla',
 'Mbps, 0 - no limit': 'Mbps, 0 - sınırsız',
 'Download up to': 'İndirme en fazla',
 'Cellular modem detected, enter the SIM card PIN': 'Hücresel modem algılandı, SIM kart PIN kodunu girin',
 'Modem settings': 'Modem ayarları',
 'Modem diagnostic interface': 'Modem tanılama arayüzü',
 'Read data via QMI/MBIM': 'Verileri QMI/MBIM ile oku',
 'Read operator name from file': 'Operatör adını dosyadan oku',
 'SMS storage': 'SMS depolama',
 'Defined by modem': 'Modem belirler',
 'SM - SIM card memory': 'SM - SIM kart belleği',
 'ME - modem memory': 'ME - modem belleği',
 'Join multipart SMS': "Çok parçalı SMS'leri birleştir",
 'Send USSD without PDU encoding': "USSD'yi PDU kodlaması olmadan gönder",
 'Receive USSD': 'USSD alma',
 'without decoding': 'çözümlemesiz',
 'with automatic encoding detection': 'otomatik kodlama algılamalı',
 'AT command': 'AT komutu',
 'New VPN': 'Yeni VPN',
 'Manual configuration': 'Elle yapılandırma',
 'Load configuration from file': 'Yapılandırmayı dosyadan yükle',
 'Choose file': 'Dosya seç',
 'File name': 'Dosya adı',
 'File size is too large': 'Dosya boyutu çok büyük',
 'Size': 'Boyut',
 'Startup': 'Başlatma',
 'Manual': 'Elle',
 'At system startup': 'Sistem açılışında',
 'After connecting to the internet': 'İnternete bağlandıktan sonra',
 'Button control': 'Düğme ile kontrol',
 'Incoming traffic': 'Gelen trafik',
 'reject': 'reddet',
 'accept': 'kabul et',
 'Configuration file contents': 'Yapılandırma dosyası içeriği',
 'Private key has invalid length or format': 'Özel anahtarın uzunluğu veya biçimi geçersiz',
 'Private key': 'Özel anahtar',
 'Public key': 'Açık anahtar',
 'Tunnels': 'Tüneller',
 'Preshared key': 'Ön paylaşımlı anahtar',
 'Allowed IP address': 'İzin verilen IP adresi',
 'startup applies to all ZeroTier networks': 'başlatma tüm ZeroTier ağları için geçerlidir',
 'control applies to all ZeroTier networks': 'kontrol tüm ZeroTier ağları için geçerlidir',
 'Send to broadcast address': 'Yayın adresine gönder',
 'Wake by button': 'Düğmeyle uyandır',
 'Internet access': 'İnternet erişimi',
 'Toggle Wi-Fi by button': "Wi-Fi'yi düğmeyle aç/kapat",
 'Ethernet ports': 'Ethernet portları',
 'Port name': 'Port adı',
 'Attached&nbsp;&nbsp;&nbsp;Network assignment': 'Bağlı&nbsp;&nbsp;&nbsp;Ağ ataması',
 'Please wait...': 'Lütfen bekleyin...',
 'copy data from previous network': 'önceki ağdan verileri kopyala',
 'QR code for connecting': 'Bağlanmak için QR kod',
 'Save changes': 'Değişiklikleri kaydet',
 'Save changes?': 'Değişiklikler kaydedilsin mi?',
 'Defaults': 'Varsayılanlar',
 'restore default settings': 'varsayılan ayarları geri yükle',
 'Check online': 'Çevrimiçi kontrol et',
 'Check': 'Kontrol et',
 'Download': 'İndir',
 'Delete data': 'Verileri sil',
 'Remove limits': 'Sınırları kaldır',
 'Send': 'Gönder',
 'Save': 'Kaydet',
 'Allow': 'İzin ver',
 'Block': 'Engelle',
 'Wi-Fi off schedule': 'Wi-Fi kapatma zamanlaması',
 'Schedule': 'Zamanlama',
 'Wake all': 'Tümünü uyandır',
 'wakes all devices': 'tüm cihazları uyandırır',
 'wake': 'uyandır',
 'Cancel': 'İptal',
 'Set': 'Ayarla',
 'Close': 'Kapat',
 'Reconnect': 'Yeniden bağlan',
 'restores the modem default settings': 'modemin varsayılan ayarlarını geri yükler',
 'Next': 'İleri',
 'New keys': 'Yeni anahtarlar',
 'remove IP address': 'IP adresini kaldır',
 'New IP address': 'Yeni IP adresi',
 'remove tunnel': 'tüneli kaldır',
 'remove allowed IP address': 'izin verilen IP adresini kaldır',
 'New tunnel': 'Yeni tünel',
 'New': 'Yeni',
 '(starting)': '(başlatılıyor)',
 'bytes': 'bayt',
 'ago': 'önce',
 'title="Connected clients: ': 'title="Bağlı istemciler: ',
 'title="connected: ': 'title="bağlı: ',
 '" (type ': '" (tür ',
 'Delete this VPN (type ': 'Bu VPN silinsin mi (tür ',
 'must be a non-empty string': 'boş olmayan bir metin olmalı',
 'must be a non-empty array': 'boş olmayan bir dizi olmalı',
 'must be a number': 'sayı olmalı',
 'must be an object': 'nesne olmalı',
 'file is empty': 'dosya boş',
 'file must contain an object {"key": "description"}': 'dosya bir nesne içermeli {"anahtar": "açıklama"}',
 'file must contain an array [ {...}, {...} ]': 'dosya bir dizi içermeli [ {...}, {...} ]',
 'value for "': 'değer: "',
 'from the block list?': 'engel listesinden kaldırılsın mı?',
 'from the allow list?': 'izin listesinden kaldırılsın mı?',
 'All': 'Tümü',
 'all': 'tümü',
 'traffic share': 'trafik payı',
 'traffic share of wireless clients': 'kablosuz istemcilerin trafik payı',
 'connected': 'bağlı',
 'blocking': 'engelleme',
 'information': 'bilgi',
 'limits': 'sınırlar',
 'disconnect': 'bağlantıyı kes',
 'delete data': 'verileri sil',
 'active': 'etkin',
 'last time': 'son kez',
 'first time': 'ilk kez',
 'size': 'boyut',
 'sunset': 'gün batımı',
 'traffic for the last 30 days': 'son 30 günün trafiği',
 'monthly traffic': 'aylık trafik',
 'yearly traffic': 'yıllık trafik',
 'Choose': 'Seçin',
 'System update in progress...': 'Sistem güncelleniyor...',
 '(last 10)': '(son 10)',
 'IP address is outside the local network address range': 'IP adresi yerel ağ adres aralığının dışında',
 'IP address is outside the address range of network': 'IP adresi şu ağın adres aralığının dışında:',
 'Date cannot be later': 'Tarih daha ileri olamaz',
 'Wi-Fi password must be at least 8 characters long': 'Wi-Fi parolası en az 8 karakter olmalı',
 'Wi-Fi name cannot be longer than 32 bytes': 'Wi-Fi adı 32 bayttan uzun olamaz',
 'Some characters (e.g. accented letters or emoji) take more than 1 byte': 'Bazı karakterler (ör. Türkçe harfler veya emoji) 1 bayttan fazla yer kaplar',
 'Do not change the configuration or power off the device during this process.': 'Bu işlem sırasında yapılandırmayı değiştirmeyin ve cihazı kapatmayın.',
 'Do not change the settings or power off the device during this process.': 'Bu işlem sırasında ayarları değiştirmeyin ve cihazı kapatmayın.',
 'Such a date does not exist': 'Böyle bir tarih yok',
 'the address is already used in network "': 'adres zaten şu ağda kullanılıyor: "',
 'No messages': 'Mesaj yok',
 'Number of clients': 'İstemci sayısı',
 'The device will reboot after the update.': 'Güncellemeden sonra cihaz yeniden başlayacak.',
 'Rogue AP': 'Sahte AP',
 'last seen': 'son görülme',
 'no connected clients': 'bağlı istemci yok',
 'Wi-Fi is disabled. The schedule will not work until Wi-Fi is enabled.': 'Wi-Fi kapalı. Wi-Fi açılana kadar zamanlama çalışmaz.',
 'No connection history': 'Bağlantı geçmişi yok',
 'No information about client connections': 'İstemci bağlantıları hakkında bilgi yok',
 'No connected clients': 'Bağlı istemci yok',
 'No wireless networks or Wi-Fi is disabled': 'Kablosuz ağ yok veya Wi-Fi kapalı',
 'No additional networks': 'Ek ağ yok',
 'No DNS queries': 'DNS sorgusu yok',
 'Query': 'Sorgu',
 'Scan the QR code to connect to the Wi-Fi network': 'Wi-Fi ağına bağlanmak için QR kodu tarayın',
 'Networks': 'Ağlar',
 'remove': 'kaldır',
 'Type': 'Tür',
 'Description': 'Açıklama',
 'description': 'açıklama',
 'Client': 'İstemci',
 'Response time': 'Yanıt süresi',
 'Time': 'Zaman',
 'connecting': 'bağlanıyor',
 'disabled': 'kapalı',
 'Wireless clients': 'Kablosuz istemciler',
 'Wired clients': 'Kablolu istemciler',
 'Wireless': 'Kablosuz',
 'Wired': 'Kablolu',
 'Suggested settings': 'Önerilen ayarlar',
 'Options': 'Seçenekler',
 'now': 'şimdi',
 'max.': 'en fazla',
 'Queries for unavailable domains': 'Erişilemeyen alan adı sorguları',
 'Number of queries': 'Sorgu sayısı',
 'Category': 'Kategori',
 'connection standard of wireless clients': 'kablosuz istemcilerin bağlantı standardı',
 'connection time of wireless clients': 'kablosuz istemcilerin bağlantı süresi',
 'signal of wireless clients': 'kablosuz istemcilerin sinyali',
 'Sources': 'Kaynaklar',
 'Supported wireless networks': 'Desteklenen kablosuz ağlar',
 'Remote clients': 'Uzak istemciler',
 'Remote client': 'Uzak istemci',
 'Number of messages': 'Mesaj sayısı',
 'No data': 'Veri yok',
 'Private address': 'Özel adres',
 'Number of domains': 'Alan adı sayısı',
 'average': 'ortalama',
 'bits': 'bit',
 'from the last day': 'son gün',
 'from the last 30 days': 'son 30 gün',
 'from the last week': 'son hafta',
 'from the last year': 'son yıl',
 'charts': 'grafikler',
 'table': 'tablo',
 'connection time': 'bağlantı süresi',
 'name': 'ad',
 'channel': 'kanal',
 'signal strength': 'sinyal gücü',
 'bad': 'kötü',
 'Filter:': 'Filtre:',
 'Show': 'Göster',
 'Sort by': 'Sırala:',
 'unknown': 'bilinmiyor',
 'WARNING!': 'UYARI!',
 'You must change the default router password!': 'Varsayılan yönlendirici parolasını değiştirmelisiniz!',
 'very bad': 'çok kötü',
 'excellent': 'mükemmel',
 'good': 'iyi',
 'weak': 'zayıf',
 'dBm and': 'dBm ve',
 'dB and': 'dB ve',
 'Automatic detection': 'Otomatik algılama',
 'No tracking': 'İzleme yok',
 'wireless': 'kablosuz',
 'wired': 'kablolu',
 'Domain blocking is disabled. Cannot check the domain': 'Alan adı engelleme kapalı. Alan adı kontrol edilemiyor',
 'No action': 'Eylem yok',
 'Unable to send ICMP request': 'ICMP isteği gönderilemiyor',
 'Missing Wi-Fi network name': 'Wi-Fi ağ adı eksik',
 'No new version.': 'Yeni sürüm yok.',
 'No response from modem': 'Modemden yanıt yok',
 'No network': 'Ağ yok',
 'Login error!': 'Giriş hatası!',
 'Error reading location': 'Konum okunamadı',
 'Error fetching data!': 'Veriler alınamadı!',
 'Error in field': 'Hatalı alan:',
 'Error loading configuration': 'Yapılandırma yüklenemedi',
 'Logout error!': 'Çıkış hatası!',
 'Thursday': 'Perşembe',
 'A new firmware version is available': 'Yeni yazılım sürümü mevcut',
 'Available': 'Mevcut',
 'DNS operation': 'DNS çalışması',
 'Default route operation': 'Varsayılan rota çalışması',
 'Day': 'Gün',
 'Passwords do not match!': 'Parolalar eşleşmiyor!',
 'Other': 'Diğer',
 'Error code': 'Hata kodu',
 'Country': 'Ülke',
 'Number of connected clients': 'Bağlı istemci sayısı',
 'City': 'Şehir',
 'Month': 'Ay',
 'Cellular modem': 'Hücresel modem',
 'HiLink or RNDIS': 'HiLink veya RNDIS',
 'Connection name': 'Bağlantı adı',
 'Real name': 'Gerçek ad',
 'Name': 'Ad',
 'No available internet connection was detected': 'Kullanılabilir internet bağlantısı bulunamadı',
 'Unavailable': 'Kullanılamıyor',
 'Sunday': 'Pazar',
 'Unsupported': 'Desteklenmiyor',
 'New clients': 'Yeni istemciler',
 'new clients': 'yeni istemciler',
 '5G NSA band selection is not available': '5G NSA bant seçimi kullanılamıyor',
 '5G SA band selection is not available': '5G SA bant seçimi kullanılamıyor',
 'LTE band selection is not available': 'LTE bant seçimi kullanılamıyor',
 'Access denied': 'Erişim reddedildi',
 'Last contact': 'Son temas',
 'Last seen': 'Son görülme',
 'Received from provider': 'Sağlayıcıdan alınan',
 'Band': 'Bant',
 'First seen': 'İlk görülme',
 'Friday': 'Cuma',
 'Configuration file does not contain option': 'Yapılandırma dosyasında şu seçenek yok:',
 'The file does not contain a configuration of supported VPN types': 'Dosya desteklenen bir VPN türünün yapılandırmasını içermiyor',
 'Unknown file type': 'Bilinmeyen dosya türü',
 'The entered PIN is not a valid value': 'Girilen PIN geçerli değil',
 'Monday': 'Pazartesi',
 'WAN port (Static IP)': 'WAN portu (Statik IP)',
 'Signal level': 'Sinyal seviyesi',
 'Connected to network (SSID)': 'Bağlı olduğu ağ (SSID)',
 'Connected': 'Bağlı',
 'Timed out waiting for response from modem': 'Modemden yanıt beklerken zaman aşımı',
 'Failover': 'Yedekleme (failover)',
 'Restore device default settings?': 'Cihaz varsayılan ayarlarına döndürülsün mü?',
 'Year': 'Yıl',
 'Disconnect "': 'Bağlantısı kesilsin mi: "',
 'Load balancing': 'Yük dengeleme',
 'Network': 'Ağ',
 'Saturday': 'Cumartesi',
 'Internet connection status': 'İnternet bağlantı durumu',
 'Traffic statistics for "': 'Trafik istatistikleri: "',
 'Width': 'Genişlik',
 'Temperature': 'Sıcaklık',
 'The device is rebooting, this may take a few minutes...': 'Cihaz yeniden başlatılıyor, bu birkaç dakika sürebilir...',
 'Your IP': 'IP adresiniz',
 'Only': 'Yalnızca',
 'WARNING: the radio interface is disabled!': 'UYARI: radyo arayüzü kapalı!',
 'WARNING: changing the active SIM slot will disconnect the internet connection. Change slot?': 'UYARI: etkin SIM yuvasını değiştirmek internet bağlantısını kesecek. Yuva değiştirilsin mi?',
 'Start WPS (Wi-Fi Protected Setup)': 'WPS başlat (Wi-Fi Protected Setup)',
 'Reboot the device?': 'Cihaz yeniden başlatılsın mı?',
 'Delete VPN "': 'VPN silinsin mi: "',
 'Delete Wake on LAN for "': 'Wake on LAN silinsin mi: "',
 'Delete data for "': 'Veriler silinsin mi: "',
 'Delete traffic data?': 'Trafik verileri silinsin mi?',
 'Remove domain "': 'Alan adı "',
 'Delete additional network "': 'Ek ağ silinsin mi: "',
 'Delete message from "': 'Mesaj silinsin mi, gönderen: "',
 'Delete': 'Sil',
 'Per modem settings': 'Modem ayarlarına göre',
 'Wi-Fi disabled': 'Wi-Fi kapalı',
 'Tuesday': 'Salı',
 'Press the "Update" button to install the new firmware version.': 'Yeni yazılım sürümünü kurmak için "Güncelleme" düğmesine basın.',
 'Wake via Wake on LAN': 'Wake on LAN ile uyandır',
 'Automatic selection': 'Otomatik seçim',
 'An error occurred while downloading the file. Error code:': 'Dosya indirilirken hata oluştu. Hata kodu:',
 'An error occurred while downloading the file. Try again in a few minutes.': 'Dosya indirilirken hata oluştu. Birkaç dakika sonra tekrar deneyin.',
 'An error occurred while checking for updates. Error code:': 'Güncellemeler kontrol edilirken hata oluştu. Hata kodu:',
 'An error occurred while performing the update. Error code:': 'Güncelleme yapılırken hata oluştu. Hata kodu:',
 'There was a problem deleting the message': 'Mesaj silinirken sorun oluştu',
 'There was a problem sending the message': 'Mesaj gönderilirken sorun oluştu',
 'Searching for operator': 'Operatör aranıyor',
 'Disable': 'Kapat',
 'Disabled': 'Kapalı',
 'Internet reconnections': 'İnternet yeniden bağlanmaları',
 'Enable/disable VPN': 'VPN aç/kapat',
 'Enable/disable additional networks Wi-Fi': "Ek ağların Wi-Fi'ını aç/kapat",
 'Enable/disable Wi-Fi': 'Wi-Fi aç/kapat',
 'Enable/disable LEDs': "LED'leri aç/kapat",
 'Enable/disable access from local network (killswitch)': 'Yerel ağdan erişimi aç/kapat (killswitch)',
 'Enable': 'Aç',
 'Registered, home network, SMS only': 'Kayıtlı, ev şebekesi, yalnızca SMS',
 'Registered, home network': 'Kayıtlı, ev şebekesi',
 'Registered, roaming, SMS only': 'Kayıtlı, dolaşım, yalnızca SMS',
 'Registered, roaming': 'Kayıtlı, dolaşım',
 'By checking "Keep settings" the current settings can be preserved.': '"Ayarları koru" işaretlenirse mevcut ayarlar korunur.',
 'Wi-Fi is set to be fully disabled': 'Wi-Fi tamamen kapatılacak şekilde ayarlı',
 'Choose "Disable" to remove the schedule and turn Wi-Fi off, or "Cancel" to ignore the changes.': 'Zamanlamayı kaldırıp Wi-Fi\'yi kapatmak için "Kapat"ı, değişiklikleri yok saymak için "İptal"i '
                                                                                                   'seçin.',
 'Found configuration for': 'Yapılandırma bulundu:',
 'title="connect"': 'title="bağlan"',
 'title="disconnect"': 'title="bağlantıyı kes"',
 'toggle Wi-Fi': 'Wi-Fi aç/kapat',
 'move to domain blocking': 'alan adı engellemeye taşı',
 'no GPS signal': 'GPS sinyali yok',
 'undefined': 'belirsiz',
 'southeast': 'güneydoğu',
 'southwest': 'güneybatı',
 'northeast': 'kuzeydoğu',
 'northwest': 'kuzeybatı',
 'south': 'güney',
 'north': 'kuzey',
 'sunrise': 'gün doğumu',
 'east': 'doğu',
 'connection': 'bağlantı',
 'disconnection': 'bağlantı kesilmesi',
 'downtime': 'kesinti',
 'the "Download" button to download the new version. Depending on the speed of your connection': 'Yeni sürümü indirmek için "İndir" düğmesine basın. İnternet bağlantınızın hızına',
 'to the internet, this may take up to a few minutes.': 'bağlı olarak bu işlem birkaç dakika sürebilir.',
 'entry': 'kayıt',
 'Wednesday': 'Çarşamba',
 'The request was sent, but no response was received.': 'İstek gönderildi ancak yanıt alınamadı.',
 'None': 'Yok',
 'none': 'yok',
 'Enabled': 'Açık'}

EXTRA_TR = {  # orijinalde zaten Ingilizce olan metinler; yalnizca TAM eslesmede degisir
    'Status': 'Durum', 'System': 'Sistem', 'Transfer': 'Veri kullanımı', 'Login': 'Giriş',
    'Operator': 'Operatör', 'Internet': 'İnternet', 'Router': 'Yönlendirici', 'Sensory': 'Sensörler',
    'Restart': 'Yeniden başlat', 'minimum': 'en az', 'Host': 'Sunucu', 'Region': 'Bölge',
    'Standard': 'Standart', 'Cell ID': 'Hücre ID', 'Port WAN (DHCP)': 'WAN portu (DHCP)',
    '<div class="col-xs-7 col-sm-4">Status</div>': '<div class="col-xs-7 col-sm-4">Durum</div>',
    '\\\');" title="status"><i data-feather="info"></i></span>': '\\\');" title="durum"><i data-feather="info"></i></span>',
}

CLIENTTYPES_TR = [
    ('"AGD"', '"Ev aleti"'), ('Sprzęt audio', 'Ses cihazı'), ('Kamera / monitoring', 'Kamera / güvenlik'),
    ('Konsola do gier', 'Oyun konsolu'), ('"Smart home / IoT"', '"Akıllı ev / IoT"'), ('"Laptop"', '"Dizüstü bilgisayar"'),
    ('Odtwarzacz multimedialny', 'Medya oynatıcı'), ('Urządzenie sieciowe', 'Ağ cihazı'), ('"Komputer"', '"Bilgisayar"'),
    ('Telefon stacjonarny / VoIP', 'Masa telefonu / VoIP'), ('"Drukarka"', '"Yazıcı"'), ('"Router"', '"Yönlendirici"'),
    ('Serwer / NAS', 'Sunucu / NAS'), ('"Smartfon"', '"Akıllı telefon"'), ('"Smartwatch"', '"Akıllı saat"'),
    ('"Tablet"', '"Tablet"'), ('"Telewizor"', '"Televizyon"'), ('Opaska / czujnik noszony', 'Bileklik / giyilebilir sensör'),
]

SMS_DELETE_OLD = '\t\t"delete")\n\t\t\tRES="Deleted message"\n\t\t\tfor idx in $arg1; do\n\t\t\t\tT=$(sms_tool -d $DEVICE delete "$idx")\n\t\t\t\techo "$T" | grep -qi "error deleting message" && RES="error deleting message"\n\t\t\tdone\n\t\t\techo "{\\"response\\":\\"$RES\\"}"\n\t\t\t;;\n'
SMS_DELETE_NEW = '\t\t"delete")\n\t\t\tRES="Deleted message"\n\t\t\t# mifi_en: Marvell modemde (ZTE MF286R) SIM mesajlari icin AT+CMGD numarasi\n\t\t\t# AT+CMGL listesindeki numaradan 1 eksik (liste 1\'den, silme 0\'dan basliyor)\n\t\t\tOFF=0\n\t\t\tif sms_tool -d $DEVICE at \'AT+CGMI\' 2>/dev/null | grep -qi marvell && \\\n\t\t\t   sms_tool -d $DEVICE at \'AT+CPMS?\' 2>/dev/null | grep -q \'+CPMS: "SM"\'; then\n\t\t\t\tOFF=1\n\t\t\tfi\n\t\t\tfor idx in $arg1; do\n\t\t\t\tcase "$idx" in \'\'|*[!0-9]*) RES="error deleting message"; continue ;; esac\n\t\t\t\tif [ "$idx" -lt "$OFF" ]; then RES="error deleting message"; continue; fi\n\t\t\t\tT=$(sms_tool -d $DEVICE delete "$((idx - OFF))")\n\t\t\t\techo "$T" | grep -qi "error deleting message" && RES="error deleting message"\n\t\t\tdone\n\t\t\techo "{\\"response\\":\\"$RES\\"}"\n\t\t\t;;\n'
SMS_RECV_OLD = '\t\t*)\n\t\t\tJOIN=$(uci -q get easyconfig.sms.join)\n\t\t\tSTORAGE=""\n\t\t\tT=$(uci -q get easyconfig.sms.storage)\n\t\t\t[ -n "$T" ] && STORAGE="-s $T"\n\t\t\tO=$(sms_tool -d $DEVICE $STORAGE -j -f "%Y%m%d%H%M%S" recv 2>/dev/null)\n\t\t\t[ -n "$O" ] && echo "$O" | sed \'s/"msg"/"join":\'${JOIN:-1}\',"msg"/;s/\\\\u0000//g\' || echo \'{"join":1,"msg":[]}\'\n\t\t\t;;\n'
SMS_RECV_NEW = '\t\t*)\n\t\t\tJOIN=$(uci -q get easyconfig.sms.join)\n\t\t\tSTORAGE=""\n\t\t\tT=$(uci -q get easyconfig.sms.storage)\n\t\t\t[ -n "$T" ] && STORAGE="-s $T"\n\t\t\t# mifi_en: bos bellekte bazi modemler AT+CMGL\'e hata donuyor ve sms_tool\n\t\t\t# 10 sn zaman asimina kadar bekliyor; mesaj sayisi 0 ise listeyi hic okuma\n\t\t\tif [ -n "$T" ]; then\n\t\t\t\tC=$(sms_tool -d $DEVICE at "AT+CPMS=\\"$T\\"" 2>/dev/null | sed -n \'s/^+CPMS: \\([0-9]*\\),.*/\\1/p\')\n\t\t\telse\n\t\t\t\tC=$(sms_tool -d $DEVICE at \'AT+CPMS?\' 2>/dev/null | sed -n \'s/^+CPMS: "[A-Z]*",\\([0-9]*\\),.*/\\1/p\')\n\t\t\tfi\n\t\t\tif [ "$C" = "0" ]; then\n\t\t\t\techo \'{"join":\'${JOIN:-1}\',"msg":[]}\'\n\t\t\t\texit 0\n\t\t\tfi\n\t\t\tO=$(sms_tool -d $DEVICE $STORAGE -j -f "%Y%m%d%H%M%S" recv 2>/dev/null)\n\t\t\t[ -n "$O" ] && echo "$O" | sed \'s/"msg"/"join":\'${JOIN:-1}\',"msg"/;s/\\\\u0000//g\' || echo \'{"join":1,"msg":[]}\'\n\t\t\t;;\n'

DIA = re.compile('[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]')
LIT = re.compile(r"'((?:[^'\\\n]|\\.)*)'|\"((?:[^\"\\\n]|\\.)*)\"")

def _pat(k):
    p = re.escape(k)
    if re.match(r'\w', k): p = r'(?<!\w)' + p
    if re.search(r'\w$', k): p = p + r'(?!\w)'
    return p
def _rx(d): return re.compile('|'.join(_pat(k) for k in sorted(d, key=len, reverse=True)))

class Lang:
    def __init__(self, code, full, phr, extra=None):
        self.code, self.full, self.phr = code, full, phr
        self.rx = _rx(phr)
        self.extra = extra or {}
        self.rxe = _rx(self.extra) if self.extra else None
    def p(self, t):
        return self.rx.sub(lambda m: self.phr[m.group(0)], t)
    def x(self, t):  # orijinalde zaten Ingilizce olan metinler (yalnizca TR, tam eslesme)
        k = t.strip()
        return t.replace(k, self.extra[k]) if k and k in self.extra else t

def _tr_map(d):
    return {k: EN2TR.get(v, v) for k, v in d.items()}

EN = Lang('en', FULL, PHR)
TR = None  # main() icinde kurulur

LANG_COOKIE_JS = ("document.cookie='easyconfig_lang='+L+';path=/;max-age=31536000';"
                  "location.replace(L=='tr'?'/easyconfig-tr.html':'/easyconfig.html');")
LOADER = ("<script>(function(){var m=document.cookie.match(/(?:^|; )easyconfig_lang=([^;]*)/),l=m?m[1]:'en',"
          "t=location.pathname.indexOf('easyconfig-tr')>-1;"
          "if(l=='tr'&&!t)location.replace('/easyconfig-tr.html'+location.hash);"
          "else if(l!='tr'&&t)location.replace('/easyconfig.html'+location.hash);})();</script>")

DATE_FIX = [  # tarih gosterimi: YYYY-AA-GG -> GG.AA.YYYY (yalnizca ekranda gosterilen yerler)
    ('"$1-$2-$3 $4:$5:$6"', '"$3.$2.$1 $4:$5:$6"'),
    ('"$1-$2-$3 $4:$5"', '"$3.$2.$1 $4:$5"'),
    ('"$1-$2-$3"', '"$3.$2.$1"'),
    ('"$1-$2"', '"$2.$1"'),
    ("return '' + d.getFullYear() + '-' + lz(d.getMonth() + 1) + '-' + lz(d.getDate()) + ' ' +",
     "return '' + lz(d.getDate()) + '.' + lz(d.getMonth() + 1) + '.' + d.getFullYear() + ' ' +"),
    ("var t0 = t.getFullYear() + '-' + lz(t.getMonth() + 1) + '-' + lz(t.getDate());",
     "var t0 = lz(t.getDate()) + '.' + lz(t.getMonth() + 1) + '.' + t.getFullYear();"),
]

def fix_dates(src):
    for a, b in DATE_FIX:
        if a not in src and b not in src:
            print('UYARI: tarih bicimi kalibi bulunamadi: ' + a[:60])
        src = src.replace(a, b)
    return src

def tr_js(src, L):
    def rep(m):
        q = "'" if m.group(1) is not None else '"'
        s = m.group(1) if m.group(1) is not None else m.group(2)
        if s in L.full:
            n = L.full[s]
        elif s in L.extra:
            n = L.extra[s]
        else:
            n = L.p(s)
        if n == s: return m.group(0)
        if re.sub(r'\\.', '', n).count(q) != re.sub(r'\\.', '', s).count(q):
            # ceviriden gelen tirnaklari kacisla (orn. Wi-Fi'yi)
            n = re.sub(r"(?<!\\)" + q, "\\\\" + q, n)
            if re.sub(r'\\.', '', n).count(q) != re.sub(r'\\.', '', s).count(q):
                return m.group(0)
        return q + n + q
    src = LIT.sub(rep, src)
    src = fix_dates(src)
    if L.code == 'tr':
        src = re.sub(r"d \+ 'd '", "d + 'g '", src)
        src = re.sub(r"(\bh \+ )'g '", r"\1'sa '", src)
        src = re.sub(r"m \+ 'm '", "m + 'dk '", src)
        src = re.sub(r"m \+ 'm'", "m + 'dk'", src)
        src = re.sub(r"s \+ 's'", "s + 'sn'", src)
        src = src.replace("'def_clienttypeof.json'", "'def_clienttypeof.tr.json'")
    else:
        src = re.sub(r"(\bh \+ )'g '", r"\1'h '", src)
    return src

def tr_html(src, L):
    head, sep, body = src.partition('<body')
    head = head.replace('<html lang="pl">', '<html lang="%s">' % L.code)
    head = re.sub(r'\?v=(\d+)(?!en)', r'?v=\1en', head)
    if THEME and 'easyconfig-tw.css' not in head:
        head = re.sub(r'(<link href="/easyconfig/easyconfig\.css\?v=([0-9a-z]+)" rel="stylesheet">)',
                      r'\1\n<link href="/easyconfig/easyconfig-tw.css?v=\2" rel="stylesheet">', head, count=1)
    if L.code == 'tr':
        head = head.replace('/easyconfig/easyconfig.js?', '/easyconfig/easyconfig.tr.js?')
    if 'easyconfig_lang' not in head:
        head = re.sub(r'(<meta charset[^>]*>)', r'\1\n' + LOADER.replace('\\', '\\\\'), head, count=1)
    body = re.sub(r'>([^<>]+)<', lambda m: '>' + L.x(L.p(m.group(1))) + '<', body)
    body = re.sub(r'(\s(?:title|placeholder|value)=")([^"]*)"', lambda m: m.group(1) + L.x(L.p(m.group(2))) + '"', body)
    body = re.sub(r"(\\?')([^'<>\\]*)(\\?')", lambda m: m.group(1) + L.p(m.group(2)) + m.group(3), body)
    # dil secimi: Sistem > Kullanici arayuzu (Tema'nin altina)
    lbl = 'Dil / Language' if L.code == 'tr' else 'Language'
    sel = ('<div class="form-group">\n<label for="ui_lang" class="col-xs-6 control-label">%s</label>\n<div class="col-xs-6">\n'
           '<select id="ui_lang" class="form-control" onchange="var L=this.value;%s">\n'
           '<option value="en"%s>English</option>\n<option value="tr"%s>Türkçe</option>\n</select>\n</div>\n</div>\n') % (
           lbl, LANG_COOKIE_JS, '' if L.code == 'tr' else ' selected', ' selected' if L.code == 'tr' else '')
    body, n = re.subn(r'(<select id="theme"[^>]*>.*?</select>\s*</div>\s*</div>\s*)', lambda m: m.group(1) + sel, body, count=1, flags=re.S)
    if not n: print('UYARI: tema secimi bulunamadi, dil secimi eklenemedi')
    # giris ekranina kucuk dil baglantilari
    links = ('<div class="text-center margintop"><a href="#" class="click" onclick="var L=\'en\';%s return false;">English</a>'
             ' &middot; <a href="#" class="click" onclick="var L=\'tr\';%s return false;">Türkçe</a></div>\n') % (LANG_COOKIE_JS, LANG_COOKIE_JS)
    body = re.sub(r'(<input type="button" class="btn btn-primary" id="loginbtn"[^>]*>\s*</div>\s*)', lambda m: m.group(1) + links, body, count=1)
    return head + sep + body

def edit(path, fn):
    if not os.path.isfile(path): return False
    s = open(path, encoding='utf-8').read()
    n = fn(s)
    if n != s:
        open(path, 'w', encoding='utf-8').write(n)
    return True

def plain(pairs):
    def f(s):
        for a, b in pairs: s = s.replace(a, b)
        return s
    return f

# ---------------- kalan Lehce raporu ----------------
try:
    from wordfreq import zipf_frequency as _z
except Exception:
    _z = None
def leftover(path, js=False, wf=True):
    out = []
    if not os.path.isfile(path): return out
    for i, l in enumerate(open(path, encoding='utf-8', errors='replace'), 1):
        t = l.strip()
        if t.startswith('//') or t.startswith('#'): continue
        t = re.sub(r'\s//.*$', '', t)
        hit = bool(DIA.search(t))
        if not hit and _z and wf:
            body = ' '.join((a or b) for a, b in LIT.findall(t)) if js else re.sub(r'<[^>]*>', ' ', t)
            body = re.sub(r'\b(on\w+|class|id|style|data-[\w-]+|href|src)="[^"]*"', ' ', body)
            for w in re.findall(r'[A-Za-z]{4,}', body):
                if not w.isupper() and _z(w.lower(), 'pl') >= 2.0 and _z(w.lower(), 'pl') > _z(w.lower(), 'en') + 1.0:
                    hit = True; break
        if hit: out.append('%s:%d: %s' % (os.path.basename(path), i, t[:160]))
    return out

# ---------------- fwtool trailer ----------------
def _crc_upd(r, data):  # fwtool crc32_block (final xor yok)
    return (~zlib.crc32(data, (~r) & 0xffffffff)) & 0xffffffff

def split_trailer(blob):
    if len(blob) > 16 and blob[-16:-12] == b'FWx0':
        magic, crc, typ, size = struct.unpack('>4sIB3xI', blob[-16:])
        if typ == 1 and size <= len(blob):
            meta = blob[-size:-16][8:]
            return blob[:-size], meta
    return blob, None

def add_trailer(data, meta):
    hdr = b'\0' * 8
    crc = _crc_upd(0xffffffff, data)
    crc = _crc_upd(crc, hdr)
    crc = _crc_upd(crc, meta)
    size = 8 + len(meta) + 16
    return data + hdr + meta + struct.pack('>4sIB3xI', b'FWx0', crc, 1, size)

# ---------------- ana akis ----------------
def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        sys.exit('HATA: %s\n%s' % (' '.join(cmd), r.stdout))
    return r.stdout

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    global THEME, LANG_TR
    if '--no-tr' in sys.argv:
        LANG_TR = False; sys.argv.remove('--no-tr')
    if '--no-theme' in sys.argv:
        THEME = False; sys.argv.remove('--no-theme')
    args = sys.argv[1:]
    for t in ('unsquashfs', 'mksquashfs'):
        if not shutil.which(t): sys.exit('HATA: %s bulunamadi (apt install squashfs-tools)' % t)
    if os.geteuid() != 0:
        print('UYARI: root degilsiniz; /dev/console gibi aygit dosyalari icin "sudo" ile calistirin.')

    out = None
    if '-o' in args:
        i = args.index('-o')
        if i + 1 >= len(args): sys.exit('HATA: -o sonrasinda cikti dosyasi adi gerekli')
        out = args[i + 1]; del args[i:i + 2]
    if not args: sys.exit(__doc__)
    if out and len(args) > 1: sys.exit('HATA: -o yalnizca tek girdi dosyasiyla kullanilabilir')
    missing = [a for a in args if not os.path.isfile(a)]
    if missing: sys.exit('HATA: dosya bulunamadi: ' + ', '.join(missing))
    jobs = [(a, out or re.sub(r'(\.bin)?$', '-EN.bin', a, count=1)) for a in args if out or not a.endswith('-EN.bin')]
    for src, dst in jobs:
        if os.path.abspath(src) == os.path.abspath(dst): sys.exit('HATA: girdi ve cikti ayni dosya: ' + src)
    failed = 0
    for src, dst in jobs:
        print('\n=== %s' % os.path.basename(src))
        try:
            process(src, dst)
        except Fail as e:
            failed += 1; print(str(e))
    if len(jobs) > 1:
        print('\n%d imajdan %d tanesi tamam, %d tanesi basarisiz.' % (len(jobs), len(jobs) - failed, failed))
    if failed: sys.exit(1)

class Fail(Exception):
    pass

def process(src, dst):
    blob = open(src, 'rb').read()
    tardata, meta = split_trailer(blob)
    try:
        tf = tarfile.open(fileobj=io.BytesIO(tardata))
    except tarfile.TarError:
        raise Fail('HATA: imaj tar degil (NOR/tek parca imaj). Yalnizca NAND sysupgrade (tar) imajlari destekleniyor.')
    members = tf.getmembers()
    rootm = [m for m in members if m.name.endswith('/root')]
    if not rootm: raise Fail('HATA: tar icinde root bulunamadi (sysupgrade tar degil mi?)')
    rootm = rootm[0]
    sq = tf.extractfile(rootm).read()
    if sq[:4] != b'hsqs': raise Fail('HATA: root squashfs degil')
    mkfs_time, = struct.unpack('<I', sq[8:12])
    block, = struct.unpack('<I', sq[12:16])
    comp, = struct.unpack('<H', sq[20:22])
    compname = {1: 'gzip', 2: 'lzma', 3: 'lzo', 4: 'xz', 5: 'lz4', 6: 'zstd'}.get(comp, 'xz')

    work = tempfile.mkdtemp(prefix='mifi_en_')
    try:
        sqf = os.path.join(work, 'root.sqfs'); open(sqf, 'wb').write(sq)
        rootfs = os.path.join(work, 'rootfs')
        run(['unsquashfs', '-q', '-n', '-d', rootfs, sqf])

        w = lambda *p: os.path.join(rootfs, *p)
        if not os.path.isfile(w('www/easyconfig/easyconfig.js')):
            raise Fail('HATA: easyconfig bulunamadi')
        global TR
        TR = Lang('tr', _tr_map(FULL), _tr_map(PHR), EXTRA_TR)
        orig_js = open(w('www/easyconfig/easyconfig.js'), encoding='utf-8').read()
        orig_html = open(w('www/easyconfig.html'), encoding='utf-8').read()
        orig_ct = open(w('www/easyconfig/def_clienttypeof.json'), encoding='utf-8').read()
        langs = [EN] + ([TR] if LANG_TR else [])
        for L in langs:
            sfx = '' if L.code == 'en' else '.' + L.code
            open(w('www/easyconfig/easyconfig%s.js' % sfx), 'w', encoding='utf-8').write(tr_js(orig_js, L))
            hname = 'easyconfig.html' if L.code == 'en' else 'easyconfig-%s.html' % L.code
            h = tr_html(orig_html, L)
            if not LANG_TR:
                h = re.sub(r'<div class="form-group">\n<label for="ui_lang".*?</div>\n</div>\n', '', h, flags=re.S)
                h = re.sub(r'<div class="text-center margintop"><a href="#" class="click" onclick="var L=.*?</div>\n', '', h, flags=re.S)
            open(w('www/' + hname), 'w', encoding='utf-8').write(h)
            os.chmod(w('www/' + hname), 0o664); os.chmod(w('www/easyconfig/easyconfig%s.js' % sfx), 0o664)
        if LANG_TR:
            open(w('www/easyconfig/def_clienttypeof.tr.json'), 'w', encoding='utf-8').write(plain(CLIENTTYPES_TR)(orig_ct))
            os.chmod(w('www/easyconfig/def_clienttypeof.tr.json'), 0o664)
        if THEME:
            open(w('www/easyconfig/easyconfig-tw.css'), 'w', encoding='utf-8').write(TW_CSS)
            os.chmod(w('www/easyconfig/easyconfig-tw.css'), 0o664)
            import base64
            open(w('www/easyconfig/inter.woff2'), 'wb').write(base64.b64decode(TW_FONT_B64))
            os.chmod(w('www/easyconfig/inter.woff2'), 0o664)
        def sms_fix(t):
            if 'mifi_en: Marvell' not in t:
                if SMS_DELETE_OLD in t: t = t.replace(SMS_DELETE_OLD, SMS_DELETE_NEW)
                else: print('UYARI: SMS silme blogu bulunamadi; Marvell silme duzeltmesi eklenmedi')
            if 'mifi_en: bos bellekte' not in t:
                if SMS_RECV_OLD in t: t = t.replace(SMS_RECV_OLD, SMS_RECV_NEW)
                else: print('UYARI: SMS okuma blogu bulunamadi; bos liste hizlandirmasi eklenmedi')
            return t
        edit(w('usr/libexec/rpcd/easyconfig'), lambda t: sms_fix(plain(BACKEND)(t)))
        edit(w('www/luci-static/resources/view/easyconfig.js'), plain(LUCI))
        edit(w('www/easyconfig/def_clienttypeof.json'), plain(CLIENTTYPES))
        edit(w('usr/bin/huawei.sh'), plain(HUAWEI))

        # kontroller
        if shutil.which('node'):
            r = subprocess.run(['node', '--check', w('www/easyconfig/easyconfig.js')], stderr=subprocess.PIPE, text=True)
            if r.returncode: raise Fail('HATA: cevrilen JS sozdizimi bozuk:\n' + r.stderr)
            if LANG_TR:
                r = subprocess.run(['node', '--check', w('www/easyconfig/easyconfig.tr.js')], stderr=subprocess.PIPE, text=True)
                if r.returncode: raise Fail('HATA: Turkce JS sozdizimi bozuk:\n' + r.stderr)
        r = subprocess.run(['sh', '-n', w('usr/libexec/rpcd/easyconfig')], stderr=subprocess.PIPE, text=True)
        if r.returncode: raise Fail('HATA: rpcd betigi bozuk:\n' + r.stderr)
        json.load(open(w('www/easyconfig/def_clienttypeof.json'), encoding='utf-8'))
        if LANG_TR: json.load(open(w('www/easyconfig/def_clienttypeof.tr.json'), encoding='utf-8'))

        left = leftover(w('www/easyconfig.html')) + leftover(w('www/easyconfig/easyconfig.js'), js=True) \
             + leftover(w('usr/libexec/rpcd/easyconfig'), wf=False)
        newsq = os.path.join(work, 'new.sqfs')
        run(['mksquashfs', rootfs, newsq, '-comp', compname, '-b', str(block), '-all-root',
             '-noappend', '-no-xattrs', '-mkfs-time', str(mkfs_time), '-quiet', '-no-progress'])
        newroot = open(newsq, 'rb').read()

        out = io.BytesIO()
        with tarfile.open(fileobj=out, mode='w', format=tarfile.GNU_FORMAT) as nt:
            for m in members:
                if m is rootm:
                    m2 = tarfile.TarInfo(m.name); m2.size = len(newroot); m2.mtime = m.mtime
                    m2.mode = m.mode; m2.uid = m2.gid = 0; m2.uname = m2.gname = ''
                    nt.addfile(m2, io.BytesIO(newroot))
                elif m.isfile():
                    nt.addfile(m, tf.extractfile(m))
                else:
                    nt.addfile(m)
        data = out.getvalue()
        if meta is not None:
            data = add_trailer(data, meta)
        open(dst, 'wb').write(data)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print('Tamam: %s (%d bayt)' % (dst, len(data)))
    if meta is None: print('UYARI: girdi imajda meta veri yoktu.')
    if left:
        print('\nCevrilmemis olabilecek %d satir (sozluge eklemeniz gerekebilir):' % len(left))
        for l in left[:60]: print('  ' + l)
    else:
        print('Kalan Lehce metin bulunmadi.')

if __name__ == '__main__':
    main()
