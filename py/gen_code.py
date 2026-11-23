import os
import re
import sys
import argparse
import ollama
from datetime import datetime

# ==========================================
# KONFIGURACJA
# ==========================================

MODEL_NAME = "qwen35-long"  # Możesz zmienić na qwen2.5, llama3.2, itp.
CTX = 65536  # Standardowa wartość kontekstu
SYSTEM_PROMPT_BASE = "Jesteś świetnym generatorem kodu w języku {lang}. Odpowiadaj Tylko na temat kodu."

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

def generuj_kod(prompt, verbose, lang="python", timeout=120):
    """Generuje kod w wybranym języku z podglądem strumieniowym."""
    
    print(f"🚀 Generowanie kodu w języku: {lang}...")
    
    if lang not in LANGUAGES:
        print(f"❌ Nieobsługiwany język: {lang}")
        print(f"Dostępne: {', '.join(LANGUAGES.keys())}")
        return None
    
    lang_cfg = LANGUAGES[lang]
    system_prompt = f"{SYSTEM_PROMPT_BASE.replace('{lang}', lang)}\n{lang_cfg['prompt_suffix']}"
    
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            stream=True,
            options={
                "temperature": 0.3,
                "top_p": 0.3,
                "num_ctx": CTX,
            }
        )
        
        full_output = ""
        in_thinking = False  # Flaga pomocnicza do ładnego formatowania w konsoli

        for chunk in response:
            message = chunk.get('message', {})
            
            # 2. Obsługa strumienia MYŚLENIA (wyświetlamy, ale nie dodajemy do full_output)
            thinking_chunk = message.get('thinking', '')
            if thinking_chunk:
                if not in_thinking:
                    in_thinking = True
                    print("\n🧠 Proces myślenia:\n", end='', flush=True)
                if verbose == True:
                    print(thinking_chunk, end='', flush=True)
                full_output+= thinking_chunk
            
            # 3. Obsługa właściwej ODPOWIEDZI (wyświetlamy i zapisujemy do full_output)
            content_chunk = message.get('content', '')
            if content_chunk:
                if in_thinking:
                    in_thinking = False
                    print("\n\n💻 Wygenerowany kod:\n", end='', flush=True)
                full_output += content_chunk

                if verbose:
                    print(content_chunk, end='', flush=True)
            
        print("\n✅ Pełna odpowiedź odebrana.")
        return full_output
    
    except ollama.ResponseError as e:
        print(f"\n⚠️  Błąd odpowiedzi modelu: {e}")
        return None
    except Exception as e:
        print(f"\n❌ Błąd: {e}")
        return None


def wyeksponuj_kod(output_text, lang):
    """Wyciąga kod z odpowiedzi modelu."""
    if not output_text or not output_text.strip():
        return None, None
    
    print("\n🔍 Wyszukiwanie bloku kodu w pełnej odpowiedzi...")
    lang_cfg = LANGUAGES[lang]
    
    match = re.search(lang_cfg['pattern'], output_text)
    if match:
        extracted_code = match.group(1).strip()
        print(f"✅ Znalazłem kod {lang}.")
        return extracted_code, lang_cfg['ext']
    else:
        pattern_generic = r'```\s*\n([\s\S]*?)\n\w*```'
        match_generic = re.search(pattern_generic, output_text)
        
        if match_generic:
            extracted_code = match_generic.group(1).strip()
            print("✅ Znalazłem ogólny blok kodu.")
            return extracted_code, lang_cfg['ext']
        else:
            print("⚠️  Nie znaleziono bloku kodu. Używam całej odpowiedzi jako treści.")
            return output_text, lang_cfg['ext']


def zapisuj_pliki(output_text, code_content, code_filename, lang="python"):
    """Zapisuje pliki wynikowe."""
    if not code_content:
        print("❌ Brak treści do zapisania (może wskazywać na błąd parsowania).")
        return
    
    with open(code_filename+"_info", "w", encoding="utf-8") as f:
        f.write(output_text)
    print(f"📄 Pełna odpowiedź zapisana w: ",code_filename+"_info")
    
    with open(code_filename, "w", encoding="utf-8") as f:
        f.write(code_content)
    print(f"💾 Kod zapisany w: {code_filename}")
    
    info_filename = code_filename + "_model"
    try:
        formatted_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        info_content = f"""=== Proces generacji kodu ===
Czas generacji: {formatted_time}
Model: {MODEL_NAME}
Język: {lang}
Wynik: Zapisany w pliku.
"""
        with open(info_filename, "w", encoding="utf-8") as f:
            f.write(info_content)
        print(f"📝 Informacje o procesie zapisane w: {info_filename}")
    except Exception as e:
        print(f"⚠️  Błąd zapisu pliku info: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generuj kod w wybranym języku z podglądem.")
    parser.add_argument("prompt", help="Prompt do modelu (np. 'Napisz prosty kalkulator').")
    parser.add_argument("--lang", default="python", choices=list(LANGUAGES.keys()),
                        help="Język kodu (domyślnie: python)")
    parser.add_argument("output_file", nargs="?", help="Nazwa pliku wyjściowego (np. kod.py).")
    parser.add_argument("-v", "--verbose", action="store_true",  
                    help="włącz tryb informacyjny (więcej szczegółów podczas generowania)")
    
    args = parser.parse_args()
    
    prompt = args.prompt
    lang = args.lang
    output_file = args.output_file
    
    target_extension = LANGUAGES[lang]['ext']
    
    # Naprawione przypisanie z warunkami
    if not output_file:
        output_file = "output" + target_extension
    elif not output_file.endswith(target_extension):
        output_file += target_extension
        
    print(f"--- START PROCESU ---")
    print(args.verbose)
    
    full_output_text = generuj_kod(prompt, args.verbose, lang)
    
    if full_output_text:
        kod_wyciety, ext = wyeksponuj_kod(full_output_text, lang)
        
        if kod_wyciety:
            zapisuj_pliki(full_output_text, kod_wyciety, output_file, lang=lang)
        else:
            print("⚠️  Nie udało się wyciągnąć czystego kodu z odpowiedzi.")
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(full_output_text)
            print(f"💾 Cała odpowiedź zapisana w: {output_file}")
    else:
        print("Generowanie się nie powiodło.")
