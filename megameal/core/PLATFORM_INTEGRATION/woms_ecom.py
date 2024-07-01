import json
import requests


class WomsEcom():
    def pushMenu(platform, oldMenu):
        # +++++++++ Category process
        catlogHeaders = {
            "Authorization": "Bearer "+platform.secreateKey,
        }
        url = platform.pushMenuUrl
        catlogResponse = requests.request(
            "POST", url, headers=catlogHeaders, data=json.dumps(oldMenu.transactionData))
        if catlogResponse.status_code in [500, 400]:
            print("Unable to connect "+platform.Name)
        return "WomsMenuSync"
