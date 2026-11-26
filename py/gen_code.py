import os
import re
import sys
import argparse
import ollama
from datetime import datetime
from pydantic import BaseModel
import json

# ==========================================
# KONFIGURACJA
# ==========================================

MODEL_NAME = "qwen35-long"  # Możesz zmienić na qwen2.5, llama3.2, itp.
CTX = 65536  # Standardowa wartość kontekstu
SYSTEM_PROMPT_BASE = "Jesteś świetnym generatorem kodu w języku {lang}. Odpowiadaj Tylko na temat kodu."

# Parametry modelu (możesz je tu modyfikować)
MODEL_OPTIONS = {
    "temperature": 0.1,
    "top_p": 0.3,
    "num_ctx": CTX,
}

# ==========================================
# DEFINICJE ZMIENNYCH GLOBAŁNYCH / WARTOŚI DLA METADANACH
# ==========================================
formatted_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
options_str = json.dumps(MODEL_OPTIONS, indent=2)

JSON_SCHEMA = {
    "type": "object",
    "properties": {
      "files": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "content": {"type": "string"}
          },
          "required": ["name", "content"]
        }
      }
    },
    "required": ["files"]
}

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
    # DODANE NOWE JĘZYKI:
    "rust": {
        "prompt_suffix": "Pisz kod w Rust.",
        "pattern": r'```(?:rust|rs)\s*\n([\s\S]*?)\n```',
        "ext": ".rs"
    },
    "html": {
        "prompt_suffix": "Pisz kod HTML.",
        "pattern": r'```(?:html|htm)\s*\n([\s\S]*?)\n```',
        "ext": ".html"
    },
    "java": {
        "prompt_suffix": "Pisz kod w Java.",
        "pattern": r'```(?:java)\s*\n([\s\S]*?)\n```',
        "ext": ".java"
    },
    "nodejs": {
        "prompt_suffix": "Pisz kod w Node.js (JavaScript).",
        "pattern": r'```(?:javascript|node|mjs|js)\s*\n([\s\S]*?)\n```',
        "ext": ".js"
    },
}

# 1. Definicja struktury danych (odpowiada Twojemu schematowi JSON)
class CodeFile(BaseModel):
    name: str
    content: str

class ProjectOutput(BaseModel):
    files: list[CodeFile]

def read_spec_file(file_path):
    """Czyta treść pliku specyfikacji."""
    if not file_path:
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ Błąd: Nie znaleziono pliku specyfikacji w ścieżce: {file_path}")
    except Exception as e:
        print(f"❌ Błąd podczas czytania pliku specyfikacji: {e}")
    return None

def generuj_kod(prompt, verbose, lang="python", timeout=120):
    """Generuje kod w wybranym języku z podglądem strumieniowym.
    
    Oddzielnie zbiera thinking i odpowiedź.
    """
    
    print(f"🚀 Generowanie kodu w języku: {lang}...")
    
    if lang not in LANGUAGES:
        print(f"❌ Nieobsługiwany język: {lang}")
        print(f"Dostępne: {', '.join(LANGUAGES.keys())}")
        return None, None, False
    
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
            format=ProjectOutput.model_json_schema(), # Wymuszenie struktury
            options=MODEL_OPTIONS
        )
        
        # SEPAROWANE zmienne: thinking vs odpowiedź
        thinking: str  = ""
        content: str = ""
        in_thinking: bool = False
        has_thinking = False

        for chunk in response:
            message = chunk.get('message', {})
            
            # 1. Obsługa strumienia MYŚLENIA
            thinking_chunk = message.get('thinking', '')
            if thinking_chunk:
                if not in_thinking:
                    in_thinking = True
                    print("\n🧠 Proces myślenia:\n", end='', flush=True)
                if verbose:
                    print(thinking_chunk, end='', flush=True)
                thinking += thinking_chunk
                has_thinking = True
            
            # 2. Obsługa właściwej ODPOWIEDZI
            content_chunk = message.get('content', '')
            if content_chunk:
                if in_thinking:
                    in_thinking = False
                    print("\n\n💻 Wygenerowany kod:\n", end='', flush=True)
                content += content_chunk
                if verbose:
                    print(content_chunk, end='', flush=True)
            
        print("\n✅ Pełna odpowiedź odebrana.")
        
        # 3. Parsowanie i walidacja odpowiedzi do obiektu Pythona
        try:
            result = ProjectOutput.model_validate_json(content)
            return thinking, result, has_thinking
        except json.JSONDecodeError as e:
            print(f"\n⚠️ Błąd parsowania JSON: {e}")
            return thinking, None, has_thinking
    
    except ollama.ResponseError as e:
        print(f"\n⚠️  Błąd odpowiedzi modelu: {e}")
        return None, None, False
    except Exception as e:
        print(f"\n❌ Błąd: {e}")
        return None, None, False


def wyeksponuj_kod(response_obj, lang):
    """Wyciąga kod z odpowiedzi modelu w formacie JSON. Zwraca listę plików."""
    
    if not response_obj or response_obj is None:
        print("⚠️  Pusta odpowiedź modelu.")
        return [], ''
    
    try:
        files_list = []
        
        # 1. Sprawdź czy to obiekt z atrybutem .files (Pydantic model)
        if hasattr(response_obj, 'files'):
            files_list = response_obj.files
            
        # 2. Jeśli to słownik, użyj get()
        elif isinstance(response_obj, dict):
            files_list = response_obj.get('files', [])
            
        # 3. Jeśli to lista (bezpośrednie wartości)
        elif isinstance(response_obj, list):
            files_list = response_obj
        
        # Sprawdzenie czy mamy pliki
        if files_list and len(files_list) > 0:
            print(f"\n📁 Znalazłem {len(files_list)} plik(-y).")
            
            parsed_files = []  # Zbieramy wszystkie znalezione pliki
            
            for file_obj in files_list:
                extracted_name = None
                extracted_content = None
                
                # Rozróżnij typ obiektu i pobierz dane odpowiednio
                if isinstance(file_obj, dict):
                    extracted_name = file_obj.get('name')
                    extracted_content = file_obj.get('content')
                elif hasattr(file_obj, 'name'):
                    extracted_name = getattr(file_obj, 'name', None)
                    extracted_content = getattr(file_obj, 'content', None)
                
                # Sprawdź czy plik ma zarówno nazwę jak i treść
                if extracted_name and extracted_content:
                    content = str(extracted_content).strip()  # Konwertuj na string
                    
                    # Pobierz rozszerzenie z nazwy pliku
                    ext = get_file_extension(extracted_name)
                    
                    parsed_files.append({
                        'name': extracted_name,
                        'content': content,
                        'ext': ext
                    })
                    
                    print(f"✅ Znalazłem plik: {extracted_name}")
            
            return parsed_files, '.json' if len(parsed_files) > 0 else ''
        
        # Jeśli nie znaleziono plików w strukturze JSON
        print("🔍 Brak właściwości 'files' w odpowiedzi.")
        return [], ''
    
    except Exception as e:
        print(f"⚠️  Błąd parsowania odpowiedzi JSON: {e}")
    
    # Fallback do regex jeśli to nie był format JSON z plikami
    result = fallback_regex_parse(str(response_obj), lang)
    return [result[0]] if result else [], ''


def get_file_extension(filename):
    """Pobiera rozszerzenie z nazwy pliku."""
    if isinstance(filename, str) and '.' in filename:
        return '.' + filename.split('.')[-1].lower()
    return ''

def fallback_regex_parse(output_text, lang):
    """Fallback do parsowania regex jeśli JSON nie zadziałał."""
    
    try:
        if not isinstance(output_text, str):
            output_text = str(output_text)
        
        pattern_generic = r'```\s*\n([\s\S]*?)\n```'
        match_generic = re.search(pattern_generic, output_text)
        
        if match_generic:
            extracted_code = match_generic.group(1).strip()
            print("✅ Znalazłem ogólny blok kodu.")
            return [extracted_code], '.json'
    
    except Exception as e:
        print(f"⚠️  Błąd w parsowaniu regex: {e}")
    
    return [], ''


def zapisuj_pliki(thinking, response_obj, files_list,  
                   project_folder="output", lang="python", final_prompt="", options=None):
    """Zapisuje wszystkie pliki z odpowiedzi modelu."""
    
    if not os.path.exists(project_folder):
        os.makedirs(project_folder, exist_ok=True)
    # Plik z procesem myślenia (zapisany w folderze projektu)
    if thinking:
        code_filename = os.path.join(project_folder, "thinking.txt")
        with open(code_filename, "w", encoding="utf-8") as f:
            f.write(thinking)
        print(f"🧠 Thinking zapisany w: {code_filename}")

    if response_obj:
        # Opcjonalnie zapisz całą odpowiedź modelu jako json
        info_file = os.path.join(project_folder, "model_response.json")
        with open(info_file, "w", encoding="utf-8") as f:
            try:
                f.write(json.dumps(response_obj.model_dump(), ensure_ascii=False, indent=2))
            except:
                f.write(str(response_obj))
        print(f"📄 Odpowiedź zapisana w: {info_file}")

    if not files_list or len(files_list) == 0:
        print("⚠️  Brak plików do zapisu.")
        return
    
    # Utwórz katalog wyjściowy (output/) jeśli nie istnieje - używamy project_folder
    # Jeśli folder jest pusty, użyj domyślnego 'output'
    output_dir = project_folder if project_folder else "output"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n💾 Zapisywanie {len(files_list)} pliku(-ów) do katalogu: {output_dir}")
    
    # Zapisz każdy plik z listy
    try:
        for file_info in files_list:
            name = file_info.get('name') or file_info.get('filename') if isinstance(file_info, dict) else None
            content = file_info.get('content')
            
            if not name or not content:
                print(f"⚠️  Pomijam plik bez nazwy lub treści.")
                continue
            
            # Utwórz katalogi (np. output/utils/) - obsługa ścieżek podfolderów z AI
            file_base = os.path.basename(name)
            ext = get_file_extension(file_base)
            dir_name = os.path.dirname(file_base) or ''
            
            if dir_name and not os.path.exists(os.path.join(output_dir, dir_name)):
                os.makedirs(os.path.join(output_dir, dir_name), exist_ok=True)
            
            # Zapisz plik - łączy folder docelowy z nazwą pliku
            file_path = os.path.join(output_dir, name)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(content) + "\n")
            
            print(f"    💾 {file_path}")
        
        # Dodaj metadane do pliku _model w głównym katalogu projektu
        save_meta_info(files_list, final_prompt, output_dir)
    
    except Exception as e:
        print(f"⚠️  Błąd podczas zapisu plików: {e}")


def save_meta_info(files_list, prompt, output_dir):
    """Zapisuje metadane do pliku _model."""
    
    # Używa folderu output_dir jako bazę dla pliku metadanych
    meta_file = os.path.join(output_dir, "project_metadata.txt")
    try:
        content = f"""=== Proces generacji kodu ===
Czas generacji: {formatted_time}
Model: {MODEL_NAME}
Język: 
Thinking: {'Tak' if 'thinking' in dir() else 'Nie'} # Upewnienie się że to działa lokalnie, ale lepiej przekazać flagę
Wynik: Zapisany w plikach.

=== Parametry Modelu ===
{options_str}

=== Pełny Prompt (w tym specyfikacja) ===
{prompt}

=== Lista plików zapytanych ===
"""
        # Upewnij się że lang jest dostępny (jeśli nie, użyj 'python')
        local_lang = None
        try:
            if hasattr(sys.modules.get('argparse'), 'parse_args'): pass 
            # Prosta obsługa - zakładamy ze zmienna lang jest przekazywana w logice głównej
            # Tutaj dodamy placeholder jeśli nie podany globalnie
        except:
            local_lang = "python"

        for file_info in files_list:
            if isinstance(file_info, dict):
                name = file_info.get('name') or str(file_info)
                content_text = file_info.get('content', '').replace('\n', ' | ')[:50]
                content_text += "..."
                content_text += "\n"
            else:
                name = str(file_info) if isinstance(file_info, (str, dict)) else ''
                content_text = getattr(file_info, 'content', '') or file_info.get('content', '')
                if isinstance(content_text, str):
                    content_text = f"{name}: {content_text[:50]}..." + "\n"
            # Zapisz fragment do pliku - tu po prostu dodajemy do stringu
        content += "\n".join([str(name) for name in [f['name'] for f in files_list]])

        with open(meta_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📝 Metadane zapisane w: {meta_file}")
    
    except Exception as e:
        print(f"⚠️  Błąd zapisu pliku metadata: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generuj kod w wybranym języku z podglądem.")
    parser.add_argument("prompt", help="Prompt do modelu (np. 'Napisz prosty kalkulator').")
    parser.add_argument("--lang", default="python", choices=list(LANGUAGES.keys()),
                        help="Język kodu (domyślnie: python)")
    parser.add_argument("-o", "--out_folder", nargs="?", default=None, help="Nazwa folderu wyjściowego projektu (np. proj1).")
    parser.add_argument("-v", "--verbose", action="store_true",  
                    help="włącz tryb informacyjny (więcej szczegółów podczas generowania)")
    parser.add_argument("-s", "--spec", help="Ścieżka do pliku spec.md z wymaganiami.")
    
    args = parser.parse_args()
    
    # Pobieranie specyfikacji, jeśli podano ścieżkę
    spec_content = read_spec_file(args.spec)
    
    # Budowanie końcowego promptu
    if spec_content:
        final_prompt = f"SPECYFIKACJA WYMAGAŃ:\n{spec_content}\n\nZADANIE UŻYTKOWNIKA:\n{args.prompt}"
    else:
        final_prompt = args.prompt

    # Ustawienie nazwy folderu projektu - jeśli nie podane, użyj domyślnego 'output'
    target_folder_name = args.out_folder
    if not target_folder_name or target_folder_name.strip() == "":
        target_folder_name = "generated_project"
    
    # Zapisz rozszerzenie docelowy dla folderu (opcjonalne, np. logi w .log) - tu domyślnie None
    target_extension = LANGUAGES[args.lang]['ext'] if args.lang else '.py'
    
    # Ustawienie zmiennych używanych przez zapisuj_pliki
    thinking = None
    response_obj = None
    files_code = []
    ext = ''
    
    print(f"--- START PROCESU ---")
    
    # Generowanie kodu (zwraca thinking, result, has_thinking)
    thinking, response_obj, has_thinking = generuj_kod(final_prompt, args.verbose, args.lang)
    
    if response_obj is not None:
        files_code, ext = wyeksponuj_kod(response_obj, args.lang)
        
        if files_code:
            zapisuj_pliki(thinking, response_obj, files_code,  
                          project_folder=target_folder_name,  # Używamy zdefiniowanego folderu projektu
                          lang=args.lang, final_prompt=final_prompt, options=MODEL_OPTIONS)
        else:
            print("⚠️  Nie udało się wyciągnąć plików z odpowiedzi.")
            
            # Fallback zapis całej odpowiedzi w folderze głównym
            save_folder = target_folder_name if target_folder_name else "output"
            with open(os.path.join(save_folder, "error.txt"), "w", encoding="utf-8") as f:
                f.write(str(response_obj))
            print(f"💾 Cała odpowiedź zapisana w błędzie w: {save_folder}/error.txt")
    else:
        print("Generowanie się nie powiodło.")
