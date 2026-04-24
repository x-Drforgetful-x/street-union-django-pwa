# Street Union Django Rebuilt

This version includes:
- editable company settings page
- company logo upload
- automatic quote and invoice number generation
- branded PDF output with company info and logo
- saved PDF file path on each document

## Run on Windows / Git Bash
```bash
cd ~/Downloads/street_union_django_rebuilt
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then open:
- http://127.0.0.1:8000/
- http://127.0.0.1:8000/company/settings/

## Important first step
Open Company Settings first and add:
- company name
- logo
- email and phone
- VAT number
- bank details
- quote prefix
- invoice prefix
- payment terms
- footer note

Then create documents.
