import requests as r


def get_default_form_payload(payload_template: dict):
    default_payload = {}
    for key in payload_template.keys():
        default_payload = {**default_payload, **payload_template[key]}
    return default_payload
