import nltk
import sys

def download_nltk_data():
    resource_id = 'punkt_tab'
    try:
        print(f"Attempting to download NLTK resource: '{resource_id}'...")
        nltk.download(resource_id)
        print(f"NLTK resource '{resource_id}' downloaded successfully or was already up-to-date.")
        print("You should now be able to run your application without the LookupError.")
    except Exception as e:
        print(f"Error downloading NLTK resource '{resource_id}': {e}", file=sys.stderr)
        print(f"Please ensure you have an internet connection.", file=sys.stderr)
        print(f"If the problem persists, you might also try downloading the general 'punkt' package:", file=sys.stderr)
        print("In a Python interpreter, run: import nltk; nltk.download('punkt')", file=sys.stderr)

if __name__ == "__main__":
    download_nltk_data()