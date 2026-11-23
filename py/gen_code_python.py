import os
import re
import sys
import ollama  # <-- Biblioteka ollama

# ==========================================
# KONFIGURACJA
# ==========================================

# Model, który masz pobrany w Ollama
MODEL_NAME = "qwen35-long"  
SYSTEM_PROMPT = "Jesteś asystentem, który pisze czysty kod Pythona. Odpowiadaj Tylko na temat kodu."

# ==========================================
# GŁÓWNA FUNKCJA
# ==========================================

def generuj_kod(prompt):
    print(f"🚀 Generowanie kodu przy użyciu modelu: {MODEL_NAME}...")
    
    try:
        # Używamy bezpośredniej metody chat z biblioteki ollama
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            options={
                "temperature": 0.7,
            }
        )

        # W bibliotece ollama odpowiedź jest w słowniku: response['message']['content']
        full_output = response['message']['content']
        print("✅ Pełna odpowiedź została odebrana.")
        return full_output

    except Exception as e:
        print(f"❌ Błąd podczas generowania kodu: {e}")
        return None

def wyeksponuj_kod(output_text):
    if not output_text:
        return None, None

    print("🔍 Wyszukiwanie bloku kodu Python...")
    
    # Opcja 1: Specyficznie Pythona
    pattern_python = r'```(?:python|py)\s*\n([\s\S]*?)\n```'
    match_python = re.search(pattern_python, output_text)

    if match_python:
        extracted_code = match_python.group(1).strip()
        print("✅ Znalazłem blok oznaczony jako Python.")
    else:
        # Opcja 2: Ogólny kod bez etykiety języka
        pattern_generic = r'```\s*\n([\s\S]*?)\n```' 
        match_generic = re.search(pattern_generic, output_text)
        
        if match_generic:
            extracted_code = match_generic.group(1).strip()
            print("✅ Znalazłem blok kodu w bloku ogólnym.")
        else:
            print("⚠️  Nie znaleziono żadnego sformułowanego bloku kodu.")
            extracted_code = output_text 
            
    return extracted_code, None

def zapisuj_pliki(output_text, code_content, code_filename):
    if not code_content:
        print("❌ Brak treści do zapisania.")
        return

    # 1. Zapisz całą odpowiedź modelu (zawsze jako output.txt lub dynamicznie)
    with open("output.txt", "w", encoding="utf-8") as f:
        f.write(output_text)
    print(f"📄 Pełna odpowiedź zapisana w: output.txt")

    # 2. Zapisz wyciągnięty kod do nazwy podanej w argumencie
    with open(code_filename, "w", encoding="utf-8") as f:
        f.write(code_content)
    print(f"🐍 Wyciągnięty kod zapisany w: {code_filename}")

# ==========================================
# URUCHOMIENIE
# ==========================================

if __name__ == "__main__":
    # Sprawdzenie czy dostarczono odpowiednią liczbę argumentów
    # sys.argv[0] to nazwa skryptu, sys.argv[1] to prompt, sys.argv[2] to nazwa pliku
    if len(sys.argv) < 3:
        print("❌ Błąd: Nieprawidłowe użycie skryptu.")
        print(f"Użycie: python {sys.argv[0]} \"Twój prompt\" nazwa_pliku.py")
        sys.exit(1)

    # Pobieranie argumentów
    prompt_uzytkownika = sys.argv[1]
    nazwa_pliku_wyjsciowego = sys.argv[2]

    # Dodanie .py jeśli użytkownik zapomniał go wpisać
    if not nazwa_pliku_wyjsciowego.endswith(".py"):
        nazwa_pliku_wyjsciowego += ".py"

    output_text = generuj_kod(prompt_uzytkownika)
    
    if output_text:
        kod_wyciety, _ = wyeksponuj_kod(output_text)
        zapisuj_pliki(output_text, kod_wyciety, nazwa_pliku_wyjsciowego)
    else:
        print("Generowanie się nie powiodło.")
