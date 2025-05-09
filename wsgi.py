import os
import sys

# Ajouter le chemin du projet à sys.path
path = 'c:\Users\Lenovo\CascadeProjects\blog_django'
if path not in sys.path:
    sys.path.append(path)

# Configurer les paramètres Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'blog_django.settings'

# Importer l'application WSGI de Django
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
