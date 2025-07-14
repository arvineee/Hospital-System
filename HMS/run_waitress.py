from waitress import serve
from HMS.wsgi import application

serve(application, host='0.0.0.0', port=8000, threads=4)