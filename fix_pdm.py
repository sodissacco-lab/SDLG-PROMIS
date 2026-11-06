from core.models import Activity, Department

RENAME = {
    "Beneficiary group training": "PDM: Beneficiary group training",
    "Training of PDM farmers": "PDM: Beneficiary group training",
    "Monitoring visit": "PDM: Monitoring visit",
    "Business plan review": "PDM: Business plan review",
    "Group meeting": "PDM: Group meeting",
    "Loan or recovery follow-up": "PDM: Loan or recovery follow-up",
}

renamed = 0
for old, new in RENAME.items():
    renamed += Activity.objects.filter(activity_type=old).update(activity_type=new)
print("Activity types renamed:", renamed)

pdm = Department.objects.filter(name="PDM").first()
if pdm is None:
    print("No PDM department found.")
else:
    left = 0
    for a in Activity.objects.filter(department=pdm).select_related("officer"):
        target = a.officer.department
        if target is not None and target.pk != pdm.pk:
            a.department = target
            a.save(update_fields=["department"])
        else:
            left += 1
            print("Needs a sector:", a.pk, a.date, a.activity_type, a.officer)
    if left == 0:
        pdm.delete()
        print("PDM department removed.")
    else:
        print("Set the Department on those officers, then run this again.")