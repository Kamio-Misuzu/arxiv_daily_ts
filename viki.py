# API接口文档: https://docs.60s-api.viki.moe/254700383e0
import requests
import json


def viki_translate_text(text, from_lang="auto", to_lang="auto",encoding=None):
    url = "https://60s.viki.moe/v2/fanyi"
    params = {
        "text": text,
        "from": from_lang,
        "to": to_lang,
        "encoding": encoding
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        js_on=response.json()
        return js_on["data"]["target"]["text"]
    except requests.exceptions.RequestException as e:
        print(f"请求出错: {e}")
        return None


if __name__ == "__main__":
    result = viki_translate_text("Kamio-Misuzu")
    if result:
        # print(json.dumps(result, ensure_ascii=False, indent=2))

        print(result)
