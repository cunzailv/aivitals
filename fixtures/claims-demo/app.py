tenant_id = "default"

def handle(resp):
    return json.loads(resp)["answer"]
