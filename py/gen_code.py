import os
import re
import sys
import argparse
import ollama

# ==========================================
# KONFIGURACJA
# ==========================================

MODEL_NAME = "qwen35-long"
CTX = 32767
# Baza promptu systemowego
SYSTEM_PROMPT_BASE = "Jesteś asystentem, który pisze czysty kod. Odpowiadaj Tylko na temat kodu."

# Definicje języków: nazwa, prompt, wzorzec regex, rozszerzenie pliku
LANGUAGES = {
    "python": {
        "prompt_suffix": "Pisz kod w Pythonie.",
        "pattern": r'```(?:python|py)\s*\n([\s\S]*?)\n```',
        "ext": ".py"
    },
    "c": {
        "prompt_suffix": "Pisz kod w języku C.",
        "pattern": r'```(?:c|c99|gcc)\s*\n([\s\S]*?)\n```',
        "ext": ".c"
    },
    "cpp": {
        "prompt_suffix": "Pisz kod w języku C++.",
        "pattern": r'```(?:cpp|c\+\+|cxx)\s*\n([\s\S]*?)\n```',
        "ext": ".cpp"
    },
    "bash": {
        "prompt_suffix": "Pisz kod w Bashu (shell).",
        "pattern": r'```(?:bash|sh|zsh|shell)\s*\n([\s\S]*?)\n```',
        "ext": ".sh"
    },
    "perl": {
        "prompt_suffix": "Pisz kod w Perl.",
        "pattern": r'```(?:perl|pl|pm)\s*\n([\s\S]*?)\n```',
        "ext": ".pl"
    },
    "ruby": {
        "prompt_suffix": "Pisz kod w Ruby.",
        "pattern": r'```(?:ruby|rb|r)\s*\n([\s\S]*?)\n```',
        "ext": ".rb"
    },
}

# ==========================================
# GŁÓWNA FUNKCJA
# ==========================================

def generuj_kod(prompt, lang="python", timeout=60):
    """Generuje kod w wybranym języku.
    
    Args:
        prompt: Prompt do modelu.
        lang: Nazwa języka (musi istnieć w słowniku LANGUAGES).
        timeout: Czas oczekiwania na odpowiedź w sekundach.
    """
    print(f"🚀 Generowanie kodu w języku: {lang}...")
    
    if lang not in LANGUAGES:
        print(f"❌ Nieobsługiwany język: {lang}")
        print(f"Dostępne: {', '.join(LANGUAGES.keys())}")
        return None
    
    lang_cfg = LANGUAGES[lang]
    system_prompt = f"{SYSTEM_PROMPT_BASE}\n{lang_cfg['prompt_suffix']}"
    
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            options={
                "temperature": 0.3,
                "top_p": 0.3,
                "num_ctx": CTX,
                "timeout": timeout
            }
        )
        full_output = response['message']['content']
        print("✅ Pełna odpowiedź odebrana.")
        return full_output
    except ollama.ResponseError as e:
        print(f"⚠️  Błąd odpowiedzi modelu: {e}")
        return None
    except TimeoutError as e:
        print(f"⏱️  Przekroczony limit czasu ({timeout}s).")
        return None
    except Exception as e:
        print(f"❌ Błąd: {e}")
        return None

def wyeksponuj_kod(output_text, lang):
    """Wyciąga kod z odpowiedzi modelu."""
    if not output_text:
        return None, None
    
    print("🔍 Wyszukiwanie bloku kodu...")
    lang_cfg = LANGUAGES[lang]
    
    # Spróbuj specyficznego wzorca dla danego języka
    match = re.search(lang_cfg['pattern'], output_text)
    if match:
        extracted_code = match.group(1).strip()
        print(f"✅ Znalazłem kod {lang}.")
        return extracted_code, lang_cfg['ext']
    else:
        # Opcja ogólna - kod bez etykiety języka
        pattern_generic = r'```\s*\n([\s\S]*?)\n```'
        match_generic = re.search(pattern_generic, output_text)
        
        if match_generic:
            extracted_code = match_generic.group(1).strip()
            print("✅ Znalazłem ogólny blok kodu.")
            return extracted_code, lang_cfg['ext']
        else:
            print("⚠️  Nie znaleziono bloku kodu.")
            return output_text, lang_cfg['ext']

def zapisuj_pliki(output_text, code_content, code_filename):
    """Zapisuje pliki wynikowe."""
    if not code_content:
        print("❌ Brak treści do zapisania.")
        return
    
    # Zapisz pełną odpowiedź
    with open("output.txt", "w", encoding="utf-8") as f:
        f.write(output_text)
    print(f"📄 Pełna odpowiedź zapisana w: output.txt")
    
    # Zapisz wyciągnięty kod
    with open(code_filename, "w", encoding="utf-8") as f:
        f.write(code_content)
    print(f"💾 Kod zapisany w: {code_filename}")

# ==========================================
# URUCHOMIENIE
# ==========================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generuj kod w wybranym języku.")
    parser.add_argument("prompt", help="Prompt do modelu.")
    parser.add_argument("--lang", default="python", choices=list(LANGUAGES.keys()),
                        help="Język kodu (domyślnie: python)")
    parser.add_argument("output_file", help="Nazwa pliku wyjściowego.")
    
    args = parser.parse_args()
    
    prompt = args.prompt
    lang = args.lang
    output_file = args.output_file
    
    # Dodaj rozszerzenie jeśli nie ma
    if not output_file.endswith(LANGUAGES[lang]['ext']):
        output_file += LANGUAGES[lang]['ext']
    
    output_text = generuj_kod(prompt, lang)
    
    if output_text:
        kod_wyciety, ext = wyeksponuj_kod(output_text, lang)
        zapisuj_pliki(output_text, kod_wyciety, output_file)
    else:
        print("Generowanie się nie powiodło.")
