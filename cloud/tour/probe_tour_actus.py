import sys
import odoo
import odoo.addons
print("odoo", odoo.release.version)
try:
    sys.path.insert(0, "/mnt/extra-addons")
    import odoo.addons.tour_actus
    print("tour_actus IMPORT OK")
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
try:
    import odoo.addons.tour_dashboard
    print("tour_dashboard IMPORT OK")
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(2)