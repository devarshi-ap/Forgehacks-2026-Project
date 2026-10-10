# python -m stormsignal.rules samples/rules/miami_wheelchair.json
import sys

from .rules import main

sys.exit(main(sys.argv))
