#!/usr/bin/env bash

# --- KONFIGURACJA ---
MODEL="qwen35-long"           # Ustawienie nazwy modelu (domyślnie jak w zadaniu)
OLLAMA_PORT="11434"          # Port Ollama (domyślny)

# --- ZMIENNE ZE ARGUMENTAMI ---
PROMPT="$1"                  # Pierwszy argument: treść promptu
OUTPUT_FILE="$2"             # Drugi argument: ścieżka do pliku wyjściowego

CODE_FILE="${OUTPUT_FILE%.txt}.bash"
COMMENT_FILE="${OUTPUT_FILE%-*.txt}_"
# Walidacja argumentów
if [[ $# -lt 2 ]]; then
    echo "Użycie: $0 <prompt> <plik_wyjściowy>"
    echo "Przykład: $0 \"Piszemy kod Python\" wynik.txt"
    exit 1
fi

# Sprawdzenie czy model jest pobrany (opcjonalne, ale przydatne do debugowania)
# Opcja 1: Jeśli nie ma go w liście, skrypt spróbuje go pobrać.
# Opcja 2 (bezpieczniejsza): Możesz tu sprawdzić za pomocą: ollama list | grep -q "$MODEL"
if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
    echo "Model '$MODEL' nie jest znaleziony. Spróbuję go pobrać teraz..."
    ollama pull "$MODEL" || {
         echo "Błąd pobrania modelu: $MODEL. Upewnij się, że masz go wcześniej wgrać za pomocą:"
        echo "  ollama pull qwen3.5:9b (lub innej poprawnej nazwy)"
        exit 1
    }
fi

# --- GENEROWANIE TREŚCI ---
# echo pipe do stdin dla ollama run, stdout przekierowane do pliku, 
# stderr (logi ładowania) ignorujemy w celu czystości pliku.
echo "$PROMPT" | \
     ollama run "$MODEL" > "$OUTPUT_FILE"

if [[ $? -eq 0 ]]; then
    echo "Odpowiedź zapisana w: $OUTPUT_FILE"
    
    # --- Parsowanie pliku wyjściowego ---
    
    # Kod (pomiędzy ```bash i ``` jest blok kodu)

# --- Kod: tylko pierwszy blok ``` po zakończeniu myślenia ---
awk '
  BEGIN {
    in_thinking = 0      # flaga czy jesteśmy w sekcji "myślania"
    in_code = 0          # flaga czy jesteśmy w bloku kodu (pierwszym po myśleniu)
  }

  # --- Detekcja początku sekcji myślenia ---
  /Thinking\.\.\./ { 
    in_thinking = 1      # Ustawiamy, że jesteśmy w thinking mode
    next                 # Nie drukujemy tej linii
  }

  # --- Detekcja końca sekcji myślenia ---
  /done thinking/ { 
    in_thinking = 0      # Koniec myślenia - teraz szukamy kodu
  }

  # --- Pomijanie bloków kodu podczas myślenia ---
  in_thinking && /^[[:space:]]*```/ { 
    next                 # Ignorujemy cały blok, nawet jeśli to ```bash
  }

  # --- Zaczynamy zbierać pierwszy BLOK kodu po zakończeniu thinking ---
  !in_thinking && /^[[:space:]]*```/ {
    if (in_code) exit    # Jeśli już jesteśmy w bloku kodu -> STOP (pamiętaj! To pierwszeństwo!)
    in_code = 1; next    # Zacznijmy zbierać pierwszy blok
  }

  # --- Zbieranie wszystkich linii wewnątrz bloku kodu ---
  in_code { print }
' "$OUTPUT_FILE" > "$CODE_FILE"

    
    # Reszta jako komentarze
    sed '/```bash/d; /^ ```$/d' "$OUTPUT_FILE" | grep -v '```bash\|```' > "$COMMENT_FILE" 2>/dev/null
    
    echo "Kod rozklat do: ${CODE_FILE}"
    echo "Kommentarze do: $COMMENT_FILE"
else
    echo "Błąd generowania." >&2
fi
