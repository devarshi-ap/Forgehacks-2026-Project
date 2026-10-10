# python -m stormsignal.risk "Miami, FL"
import sys

from .risk import main

sys.exit(main(sys.argv))
