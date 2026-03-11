import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mmflip.settings')
django.setup()

from django.template import engines
engine = engines['django']

try:
    t = engine.get_template('base.html')
    print('base.html - OK')
except Exception as e:
    print(f'base.html - ERROR: {e}')

try:
    t = engine.get_template('coinflip.html')
    print('coinflip.html - OK')
except Exception as e:
    print(f'coinflip.html - ERROR: {e}')

try:
    t = engine.get_template('header.html')
    print('header.html - OK')
except Exception as e:
    print(f'header.html - ERROR: {e}')
