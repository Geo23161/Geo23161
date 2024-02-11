import requests
import asyncio
import json
from app.models import g_v

MTN_URL = "https://api.qosic.net/QosicBridge/user/requestpayment"
MOOV_URL = "https://api.qosic.net/QosicBridge/user/requestpaymentmv"

def get_status(transref, cid) :
    url =  g_v(f"qosic:{typ}:url")
    resp = requests.post(url, json.dumps({
        'transref' : transref,
        'clientid' : cid
    }), headers = {
        "Content-Type": "application/json",
    }, auth=( g_v(f"qosic:username") , g_v(f"qosic:{typ}:password")))
    
    if resp.status_code == 200 :
        res = resp.json()
        code = int(res["responsecode"])
        return code 
    return -1

def launch_payment(number, transref, typ, amount, clientid) :
    headers = {
        "Content-Type": "application/json",
    }

    data = json.dumps({
        "msisdn": number,
        "amount": amount,
        "transref" :transref,
        "clientid": clientid
    })
    try :
        resp = requests.post( g_v(f"qosic:{typ}:url") , data, headers= headers, auth=( g_v(f"qosic:{typ}:username") , g_v(f"qosic:{typ}:password")))
        print(resp.text)
        if resp.status_code == 200 :
            res = resp.json()
            code = int(res["responsecode"])
            
            return code
            
        else :
            return -1
    except Exception as e :
        print(e)
        return -1

async def main() :
    do = await launch_payment("22961555705", '20140', 'mtn', '10', 'KitabuHVVY')
    print(do)

if __name__ == '__main__' :
    asyncio.run(main())


    
