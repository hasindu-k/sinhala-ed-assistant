import importlib

def check_library(name, package_name=None):
    if package_name is None:
        package_name = name
    try:
        importlib.import_module(package_name)
        print(f"✅ {name} imported successfully.")
    except ImportError:
        print(f"❌ {name} failed to import. Make sure it is installed.")

if __name__ == "__main__":
    print("Verifying NLP libraries...")
    check_library("Indic NLP Library", "indicnlp")
    print("Verification complete.")
