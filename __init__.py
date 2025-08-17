

"""
comfyui-hoangyell-video-edit
----------------------------
Custom ComfyUI nodes for professional video editing workflows.
Modular, maintainable, and ready for future expansion.

Author: hoangyell (http://hoangyell.com/)
Coding for fun! If you like this, visit my site or say hi!
"""


from .add_intro_image import AddIntroImage
from . import utils

# Register node
NODE_CLASS_MAPPINGS = {
    "AddIntroImage": AddIntroImage
}