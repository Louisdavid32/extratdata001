import re
import string
import urllib.parse

from playwright.sync_api import sync_playwright

from memory import Memory
from save import Save

BASE_URL = "https://www.doualazoom.com"


class Crawl:

    def __init__(self, saver, memory):
        self.saver: Save = saver
        self.memory: Memory = memory

    @classmethod
    def normalize_url(cls, base_url, relative_url):
        # Fonction pour normaliser une URL
        if not relative_url:
            return None
        decoded_url = relative_url.replace("httpts://", "https://")  # Corriger les erreurs d'URL
        full_url = f"{base_url}{decoded_url}" if relative_url.startswith("/") else relative_url
        return full_url

    @classmethod
    def extract_name_from_url(cls, url):
        # Fonction pour extraire le nom de l'entreprise depuis l'URL
        try:
            # Extraire la partie contenant le nom
            nom_partie_encodee = url.split("/fr/activite/alpha/A/")[-1].split("/")[0]
            # Décoder la partie encodée
            nom_entreprise = urllib.parse.unquote(nom_partie_encodee).strip()
            return nom_entreprise
        except Exception as e:
            print(f"⚠️ Erreur lors de l'extraction du nom depuis l'URL : {e}")
            return "Non renseigné"

    def extract_entreprise_details(self, page):
        # Fonction pour extraire les détails d'une entreprise
        try:
            print(f"\n⏳ Extraction des détails de l'entreprise sur {page.url}...")

            # Extraire le nom de l'entreprise depuis l'URL
            name = self.extract_name_from_url(page.url)
            print('----------------ijrijer-', name)

            # Boîte postale
            bp_text = page.evaluate(
                """
                () => {
                    const el = Array.from(document.querySelectorAll('div')).find(div => div.textContent.includes('Boite postale'));
                    return el ? el.querySelector('a')?.textContent.trim() : null;
                }
                """
            )
            postal_code = bp_text if bp_text else "Non renseigné"

            # Téléphones, Fax, WhatsApp
            phone_elements = page.query_selector_all("div:has(b)")
            phones = {"Téléphones": [], "WhatsApp": [], "Fax": []}
            seen_numbers = set()
            for el in phone_elements:
                label = el.query_selector("b").text_content().strip() if el.query_selector("b") else ""
                value = el.query_selector("a").text_content().strip() if el.query_selector("a") else ""
                if value and value not in seen_numbers:
                    seen_numbers.add(value)
                    if "Téléphone" in label:
                        phones["Téléphones"].append(value)
                    elif "Fax" in label or "Viber" in label:
                        phones["Fax"].append(value)
                    elif "WhatsApp" in label:
                        phones["WhatsApp"].append(value)

            # Email
            email_el = page.query_selector("a[href^='mailto']")
            email = email_el.text_content().strip() if email_el else "Non renseigné"

            # Site web
            website_el = page.query_selector("a[target='_blanc']")
            website = self.normalize_url(BASE_URL, website_el.get_attribute("href")) if website_el else "Non renseigné"

            # Secteur d'activité
            secteur_activite = page.evaluate(
                """
                () => {
                    const bElement = Array.from(document.querySelectorAll('b')).find(b => b.textContent.trim() === 'Secteur d\\'activité:');
                    return bElement ? bElement.nextElementSibling?.textContent.trim() : 'Non renseigné';
                }
                """
            )

            # Localisation
            location_text = page.text_content(".div_titre_surlacarte") if page.query_selector(
                ".div_titre_surlacarte") else ""
            location_match = re.search(r"latitude ([\d.]+),.*longitude ([\d.]+)", location_text)
            location = (location_match.group(1), location_match.group(2)) if location_match else (
            "Non renseigné", "Non renseigné")

            # Préparer les données extraites
            extracted_data = {
                "Nom": name,
                "Boîte Postale": postal_code,
                "Téléphones": ", ".join(phones["Téléphones"]),
                "WhatsApp": ", ".join(phones["WhatsApp"]),
                "Fax": ", ".join(phones["Fax"]),
                "Email": email,
                "Site Web": website,
                "Secteur d'activité": secteur_activite,
                "Localisation": f"({location[0]}, {location[1]})"
            }
            print(f"✅ Données extraites : {extracted_data}")

            # Enregistrer dans le fichier Excel
            self.saver.add(
                name=extracted_data["Nom"],
                bp=extracted_data["Boîte Postale"],
                tel=extracted_data["Téléphones"],
                whatsapp=extracted_data["WhatsApp"],
                fax=extracted_data["Fax"],
                email=extracted_data["Email"],
                website=extracted_data["Site Web"],
                sector=extracted_data["Secteur d'activité"],
                location=extracted_data["Localisation"]
            )

            return extracted_data
        except Exception as e:
            print(f"⚠️ Erreur lors de l'extraction des détails de l'entreprise sur {page.url}: {e}")
            return None

    def extract_all_companies_on_page(self, context, url):
        # Fonction pour extraire toutes les entreprises d'une page
        try:
            print(f"\n🔄 Chargement de la liste des entreprises depuis {url}...")
            page = context.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_selector(".div_list_nomentreprise a", timeout=15000)

            # Récupérer tous les liens des entreprises
            entreprise_links = page.query_selector_all(".div_list_nomentreprise a")
            if len(entreprise_links) == 0:
                print("⚠️ Aucune entreprise trouvée sur cette page.")
                page.close()
                return False

            # Traiter au maximum 25 entreprises par page
            processed_count = 0
            for i, link in enumerate(entreprise_links[:25]):
                raw_url = link.get_attribute("href")
                clean_url = self.normalize_url(BASE_URL, raw_url)

                if not clean_url:
                    print(f"⚠️ URL invalide pour l'entreprise {i + 1}, ignorée.")
                    continue

                # Ouvrir une nouvelle page pour l'entreprise
                new_page = context.new_page()
                print(f"🔗 Ouvrir l'onglet pour {clean_url}")

                try:
                    new_page.goto(clean_url, timeout=60000)
                    new_page.wait_for_load_state("load", timeout=30000)

                    # Extraire les détails de l'entreprise
                    self.extract_entreprise_details(new_page)

                    # Fermer l'onglet après l'extraction
                    print(f"🔒 Fermeture de l'onglet pour l'entreprise {i + 1}.")
                    new_page.close()

                    processed_count += 1
                except Exception as e:
                    print(f"⚠️ Erreur lors de l'ouverture de l'entreprise {i + 1}: {e}")
                    new_page.close()

            page.close()  # Fermer la page principale
            return processed_count >= 25  # Retourne True si 25 entreprises ont été traitées
        except Exception as e:
            print(f"⚠️ Erreur lors du traitement des entreprises sur {url}: {e}")
            return False

    def start(self):
        # Fonction principale
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()

                # Itérer sur toutes les lettres de l'alphabet
                for letter in string.ascii_uppercase:  # De 'A' à 'Z'
                    print(f"\n🔍 Démarrage de l'extraction pour la lettre {letter}...")
                    page_number = 1

                    while True:
                        url = f"{BASE_URL}/fr/activite/alpha/{letter}?page={page_number}"

                        if not self.memory.has_crawled(url=url):
                            self.memory.started(url=url)

                            print(f"\n🔄 Extraction des données pour la lettre {letter}, page {page_number}...")
                            # Extraire les entreprises de la page actuelle
                            should_continue = self.extract_all_companies_on_page(context, url)

                            self.memory.crawled(url=url)

                            # Vérifier s'il y a une page suivante
                            if not should_continue:
                                print(f"✅ Fin de l'extraction pour la lettre {letter}.")
                                break

                        page_number += 1

                browser.close()
        except (KeyboardInterrupt, Exception):
            print("Interruption !!!")
        finally:
            self.memory.save()
            self.saver.close()
