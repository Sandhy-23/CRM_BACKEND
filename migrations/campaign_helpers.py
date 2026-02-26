def get_color_from_channel(channel):
    mapping = {
        "Email": "blue",
        "WhatsApp": "green",
        "Social": "pink"
    }
    return mapping.get(channel, "blue")