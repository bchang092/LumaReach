NAME = "LumaReach"
FORMER_NAME = "Baltimore Lifeline"
DISPLAY_NAME = f"{NAME} (Formerly {FORMER_NAME})"


def site_brand(request):
    return {"site_name": DISPLAY_NAME, "brand_name": NAME, "former_name": FORMER_NAME}
