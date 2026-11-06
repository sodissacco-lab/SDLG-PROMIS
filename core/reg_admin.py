from django.contrib import admin

from . import reg_models

for _model in reg_models.ALL_MODELS:
    if not admin.site.is_registered(_model):
        admin.site.register(_model)
from . import reg_extra_models  # noqa: E402

for _model in reg_extra_models.EXTRA_MODELS:
    if not admin.site.is_registered(_model):
        admin.site.register(_model)
from . import crop_vet_models  # noqa: E402

for _model in crop_vet_models.CROPVET_MODELS:
    if not admin.site.is_registered(_model):
        admin.site.register(_model)
from . import ent_com_models  # noqa: E402

for _model in ent_com_models.ENTCOM_MODELS:
    if not admin.site.is_registered(_model):
        admin.site.register(_model)
from . import ent2_models  # noqa: E402

for _model in ent2_models.ENT2_MODELS:
    if not admin.site.is_registered(_model):
        admin.site.register(_model)
from . import vet2_models  # noqa: E402

for _model in vet2_models.VET2_MODELS:
    if not admin.site.is_registered(_model):
        admin.site.register(_model)
from . import permit_models  # noqa: E402
if not admin.site.is_registered(permit_models.MovementPermit):
    admin.site.register(permit_models.MovementPermit)