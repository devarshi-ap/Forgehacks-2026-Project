# python -m stormsignal.verifier PLAN.md RULES.json
import sys

from .verifier import main

sys.exit(main(sys.argv))
