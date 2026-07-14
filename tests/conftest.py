# Permet aux tests d'importer les modules du projet (config, src, ml) sans installation
# Lets tests import the project's modules (config, src, ml) without installation

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
