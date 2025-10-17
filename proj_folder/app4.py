import google.generativeai as genai # IZLABOTS: Pareizais bibliotēkas imports
import json
import os

# Ielādē API atslēgu no api_key.txt faila
try:
    with open("api_key.txt", "r") as f:
        GOOGLE_API_KEY = f.read().strip()
    print("API atslēga veiksmīgi ielādēta no 'api_key.txt'.")
except FileNotFoundError:
    raise FileNotFoundError("Kļūda: Fails 'api_key.txt' nav atrasts. Lūdzu, izveidojiet to un ievietojiet tajā savu Google AI Studio API atslēgu.")
except Exception as e:
    raise Exception(f"Kļūda, lasot 'api_key.txt': {e}")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY ir tukša. Lūdzu, pārbaudiet 'api_key.txt' saturu.")

# Konfigurē genai moduli ar API atslēgu
genai.configure(api_key=GOOGLE_API_KEY)
print("Google Generative AI modulis konfigurēts.")

# Izvēlieties Gemini modeli
# IZLABOTS: Modeļa inicializācija tagad ir globāla un pareiza
model = genai.GenerativeModel('gemini-2.5-flash') # Var izmantot arī 'gemini-1.5-flash' vai citu pieejamo modeli
print(f"Izvēlētais AI modelis: {model.model_name}")


# Konfigurācija
INPUT_DIR = "sample_inputs"
OUTPUT_DIR = "output"

JD_FILE = os.path.join(INPUT_DIR, "jd.txt")
CV_FILES = [
    os.path.join(INPUT_DIR, "cv1.txt"),
    os.path.join(INPUT_DIR, "cv2.txt"),
    os.path.join(INPUT_DIR, "cv3.txt"),
]

# Izveido izvades direktoriju, ja tas neeksistē
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"Pārliecinos, ka izvades direktorijs '{OUTPUT_DIR}' eksistē.")

def read_file_content(filepath):
    """Nolasa faila saturu."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"Veiksmīgi nolasīts fails: {filepath} (izmērs: {len(content)} rakstzīmes).")
            return content
    except FileNotFoundError:
        print(f"Kļūda: Fails nav atrasts - {filepath}. Lūdzu, pārbaudiet faila ceļu un nosaukumu.")
        return None
    except Exception as e:
        print(f"Kļūda, lasot failu {filepath}: {e}")
        return None

def generate_comparison_with_ai(job_description, cv_content):
    """
    Izmanto Google Gemini modeli, lai salīdzinātu JD un CV un ģenerētu JSON rezultātu.
    """
    prompt = f"""
    Tu esi pieredzējis personāla atlases speciālists. Tavs uzdevums ir salīdzināt doto darba aprakstu ar kandidāta CV un novērtēt kandidāta atbilstību.
    Atbildi **tikai** ar JSON objektu, bez papildu teksta vai paskaidrojumiem. JSON objektam jābūt tieši tādā formātā, kā norādīts zemāk.

    Darba apraksts (JD):
    ---
    {job_description}
    ---

    Kandidāta CV:
    ---
    {cv_content}
    ---

    Lūdzu, ģenerē JSON objektu ar šādu struktūru, novērtējot kandidāta atbilstību:
    {{
      "match_score": 0-100,
      "summary": "Īss apraksts, cik labi CV atbilst JD.",
      "strengths": [
        "Galvenās prasmes/pieredze no CV, kas atbilst JD"
      ],
      "missing_requirements": [
        "Svarīgas JD prasības, kas CV nav redzamas"
      ],
      "verdict": "strong match | possible match | not a match"
    }}

    Ņem vērā:
    - "match_score" jābūt veselam skaitlim no 0 līdz 100.
    - "summary" jābūt īsam, kodolīgam aprakstam latviešu valodā.
    - "strengths" jābūt sarakstam ar galvenajām prasmēm/pieredzi no CV, kas tieši atbilst JD prasībām.
    - "missing_requirements" jābūt sarakstam ar svarīgām JD prasībām, kas nav skaidri redzamas CV.
    - "verdict" jābūt vienam no: "strong match", "possible match", "not a match".
    - Visi teksta lauki (summary, strengths, missing_requirements) jābūt latviešu valodā.
    """

    try:
        print(f"Sūtu pieprasījumu AI modelim par CV ar {len(cv_content)} rakstzīmēm.")
        # IZLABOTS: Izmantojam globāli definēto modeļa objektu
        response = model.generate_content(prompt)
        raw_ai_response = response.text.strip()
        print(f"Saņemta AI atbilde (pirmās 500 rakstzīmes): {raw_ai_response[:500]}...")
        
        json_str = raw_ai_response
        
        # Noņemam potenciālos markdown koda bloku apzīmējumus
        if json_str.startswith("```json"):
            json_str = json_str[len("```json"):].strip()
        if json_str.endswith("```"):
            json_str = json_str[:-len("```")].strip()
        
        # Pārbaudām, vai atbilde sākas ar { un beidzas ar }, lai nodrošinātu, ka tas ir JSON objekts
        if not (json_str.startswith("{") and json_str.endswith("}")):
            print("Brīdinājums: AI atbilde neizskatās pēc tīra JSON objekta. Mēģinu atrast JSON bloku.")
            # Mēģinām atrast pirmo un pēdējo cirtaino iekavu
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}')
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_str = json_str[start_idx : end_idx + 1]
                print(f"Izvilkts JSON bloks (pirmās 500 rakstzīmes): {json_str[:500]}...")
            else:
                print("Neizdevās izvilkt JSON bloku no AI atbildes. Atbilde netika parsēta kā JSON.")
                return None

        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Kļūda, parsējot AI atbildi kā JSON: {e}")
        print(f"AI atbilde, kas radīja kļūdu: \n---\n{json_str}\n---")
        return None
    except Exception as e:
        print(f"Kļūda, sazinoties ar AI modeli vai apstrādājot atbildi: {e}")
        return None

def generate_markdown_report(candidate_name, comparison_results):
    """
    Ģenerē Markdown pārskatu no salīdzināšanas rezultātiem.
    """
    if not comparison_results:
        return f"# Kandidāta {candidate_name} pārskats\n\nNav pieejami salīdzināšanas rezultāti."

    report = f"# Kandidāta {candidate_name} atbilstības pārskats\n\n"
    report += f"**Atbilstības rādītājs:** {comparison_results.get('match_score', 'N/A')}/100\n"
    report += f"**Kopvērtējums:** {comparison_results.get('verdict', 'N/A')}\n\n"
    report += f"**Kopsavilkums:** {comparison_results.get('summary', 'Nav norādīts.')}\n\n"

    strengths = comparison_results.get('strengths', [])
    if strengths:
        report += "**Galvenās stiprās puses (atbilst JD):**\n"
        for strength in strengths:
            report += f"- {strength}\n"
    else:
        report += "**Galvenās stiprās puses (atbilst JD):** Nav tiešu atbilstību.\n"
    report += "\n"

    missing_requirements = comparison_results.get('missing_requirements', [])
    if missing_requirements:
        report += "**Trūkstošās prasības (JD, kas nav CV):**\n"
        for req in missing_requirements:
            report += f"- {req}\n"
    else:
        report += "**Trūkstošās prasības:** Visas svarīgās JD prasības ir atrastas CV.\n"
    report += "\n"

    return report

def main():
    jd_content = read_file_content(JD_FILE)
    if not jd_content:
        print("JD faila saturs nav nolasīts. Pārtraucu izpildi.")
        return

    print("Sāku salīdzināšanu...")

    for cv_file in CV_FILES:
        cv_content = read_file_content(cv_file)
        if not cv_content:
            print(f"CV faila '{cv_file}' saturs nav nolasīts. Izlaižu šo CV.")
            continue

        candidate_name = os.path.basename(cv_file).replace(".txt", "")
        print(f"\nSalīdzinu JD ar {candidate_name} CV...")

        comparison_results = generate_comparison_with_ai(jd_content, cv_content)

        if comparison_results:
            print(f"Veiksmīgi ģenerēti salīdzināšanas rezultāti {candidate_name} CV.")
            # Saglabā JSON failu
            json_output_path = os.path.join(OUTPUT_DIR, f"{candidate_name}_match.json")
            try:
                with open(json_output_path, 'w', encoding='utf-8') as f:
                    json.dump(comparison_results, f, indent=2, ensure_ascii=False)
                print(f"JSON rezultāti veiksmīgi saglabāti: {json_output_path}")
            except IOError as e:
                print(f"Kļūda, rakstot JSON failu '{json_output_path}': {e}. Pārbaudiet direktorija atļaujas.")

            # Saglabā Markdown pārskatu
            markdown_output_path = os.path.join(OUTPUT_DIR, f"{candidate_name}_report.md")
            markdown_report = generate_markdown_report(candidate_name, comparison_results)
            try:
                with open(markdown_output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_report)
                print(f"Markdown pārskats veiksmīgi saglabāts: {markdown_output_path}")
            except IOError as e:
                print(f"Kļūda, rakstot Markdown failu '{markdown_output_path}': {e}. Pārbaudiet direktorija atļaujas.")
        else:
            print(f"Neizdevās ģenerēt salīdzināšanas rezultātus {candidate_name} CV. JSON fails netiks izveidots.")

    print("\nSalīdzināšana pabeigta.")

if __name__ == "__main__":
    main()