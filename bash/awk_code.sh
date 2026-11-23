#!/bin/bash 

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
' "$1" > "$2"
