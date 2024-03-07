import sys
from shiny._main import main
from sampling import resource_path

sys.argv = ['shiny', 'run', '-b', resource_path("app.py")]
main()
