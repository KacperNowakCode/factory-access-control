# Instrukcja instalacji i uruchomienia 

## 1. Tworzenie wirtualnego środowiska (venv)

W terminalu w folderze projektu wpisać:

    python -m venv venv

## 2. Aktywacja środowiska

Należy wybrać komendę odpowiednią dla swojego systemu:

* **Windows (CMD):**
    ```cmd
    venv\Scripts\activate
    ```

* **Windows (PowerShell):**
    ```powershell
    .\venv\Scripts\Activate.ps1
    ```

* **macOS / Linux:**
    ```bash
    source venv/bin/activate
    ```

---

## 3. Instalacja dlib (z pliku lokalnego)

W folderze znajduje się plik z rozszerzeniem `.whl`. Należy go zainstalować ręcznie przed resztą bibliotek.

```bash
pip install dlib-20.0.0-cp310-cp310-win_amd64.whl
```

## 4. Instalacja reszty bibliotek

Gdy dlib jest już zainstalowany:

```bash
 pip install -r requirements.txt
```

---

## 5. Uruchomienie aplikacji
* **backend:**
```bash
python app.py
```
* **frontend:**
```bash
python -m http.server 8000
```
---

## 🔧 TROUBLESHOOTING

**PowerShell blokuje aktywację venv (czerwony błąd "running scripts is disabled")**<br>
Rozwiązanie: Wpisz poniższą komendę w PowerShellu i zatwierdź (T/Y):<br>
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser <br>
Następnie spróbuj aktywować venv ponownie.

**Błąd podczas instalacji pliku .whl ("is not a supported wheel on this platform")**<br>
Rozwiązanie: Pobrany plik `.whl` nie pasuje do Twojej wersji Pythona.
Zalecana wersja to python 3.10.
