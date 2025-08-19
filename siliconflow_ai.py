import requests
import json


def siliconflow_ts(text, target_lang, api_key, model_id):
    API_URL = "https://api.siliconflow.cn/v1/chat/completions"

    lang_prompts = {
        "中文": "请将以下内容翻译成专业、流畅、自然的中文：",
        "中文繁体": "请将以下内容翻译成专业、流畅、自然的繁体中文：",
        "日文": "请将以下内容翻译成专业、流畅、自然的日语：",
    }

    prompt = lang_prompts.get(target_lang, lang_prompts["中文"])

    full_prompt = f"{prompt}\n\n{text}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": full_prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
        "response_format": {"type": "text"}
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        response.raise_for_status()
        translation_result = response.json()['choices'][0]['message']['content']

        return f"[使用 硅基流动API ({model_id}) 翻译]\n\n{translation_result}"

    except requests.exceptions.RequestException as e:
        error_msg = f"翻译请求失败: {str(e)}"
        if hasattr(e, 'response') and e.response:
            try:
                error_details = e.response.json()
                error_msg += f"\n错误详情: {error_details.get('error', {}).get('message', '未知错误')}"
            except:
                error_msg += f"\n状态码: {e.response.status_code}"
        return f"[翻译错误]\n\n{error_msg}\n\n原始文本:\n{text}"

    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return f"[解析响应失败]\n\n错误: {str(e)}\n\n原始文本:\n{text}"